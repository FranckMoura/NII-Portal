import os
import ftplib
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("==========================================================")
print(" 🔄 ROBÔ DE ATUALIZAÇÃO MENSAL (SIH / SP) - SANTA HELENA ")
print("==========================================================")

# =========================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}"); exit()

CNES_HSH = "2311682"
ESTADO = "MT"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOADS = os.path.join(BASE_DIR, "downloads_mensais")

if not os.path.exists(PASTA_DOWNLOADS):
    os.makedirs(PASTA_DOWNLOADS)

# =========================================================
# 2. FUNÇÃO DE DOWNLOAD FTP DO DATASUS
# =========================================================
def baixar_arquivo_ftp(tipo, ano_yy, mes_mm):
    nome_arquivo = f"{tipo}{ESTADO}{ano_yy}{mes_mm}.dbc"
    caminho_local = os.path.join(PASTA_DOWNLOADS, nome_arquivo)
    
    if os.path.exists(caminho_local):
        print(f"⏭️ O arquivo {nome_arquivo} já existe. Pulando download.")
        return caminho_local

    print(f"🌐 Baixando {nome_arquivo} do FTP Datasus...")
    try:
        ftp = ftplib.FTP('ftp.datasus.gov.br')
        ftp.login()
        ftp.cwd('/dissemin/publicos/SIHSUS/200801_/Dados')
        
        with open(caminho_local, 'wb') as f:
            ftp.retrbinary(f'RETR {nome_arquivo}', f.write)
        ftp.quit()
        print(f"   ✅ Download concluído: {nome_arquivo}")
        return caminho_local
    except Exception as e:
        print(f"   ❌ Erro no download de {nome_arquivo}: {e}")
        if os.path.exists(caminho_local): os.remove(caminho_local)
        return None

# =========================================================
# 3. PROCESSAMENTO E UPLOAD: CAPAS DA AIH (RD)
# =========================================================
def processar_e_subir_rd(arquivo_dbc, ano_completo, mes_mm):
    if not arquivo_dbc: return False
    print(f"\n⚙️ Processando arquivo RD (Capas): {os.path.basename(arquivo_dbc)}")
    arquivo_dbf = arquivo_dbc.replace('.dbc', '.dbf')
    
    try:
        datasus_dbc.decompress(arquivo_dbc, arquivo_dbf)
        dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
        df = pd.DataFrame(iter(dbf))
        os.remove(arquivo_dbf)
        
        df = df[df['CNES'] == CNES_HSH]
        if df.empty:
            print("   ⚠️ Nenhuma AIH encontrada para o hospital neste mês.")
            return True

        col_aih = 'N_AIH'
        aihs_unicas = df[col_aih].dropna().astype(str).unique().tolist()
        print(f"   🧹 Limpando dados antigos (em lotes) para evitar timeout...")
        
        for i in range(0, len(aihs_unicas), 200):
            lote_delete = aihs_unicas[i : i + 200]
            try:
                supabase.table("sih_sus_hsh").delete().in_("n_aih", lote_delete).execute()
            except: pass

        payload = []
        for _, row in df.iterrows():
            payload.append({
                "ano_cmpt": ano_completo,
                "mes_cmpt": mes_mm,
                "n_aih": str(row.get("N_AIH", "")),
                "dt_inter": str(row.get("DT_INTER", "")),
                "dt_saida": str(row.get("DT_SAIDA", "")),
                "dias_perm": int(row.get("DIAS_PERM", 0)),
                "proc_rea": str(row.get("PROC_REA", "")),
                "val_tot": float(row.get("VAL_TOT", 0.0)),
                "espec": str(row.get("ESPEC", "")),
                "car_int": str(row.get("CAR_INT", "")),
                "cobranca": str(row.get("COBRANCA", ""))
            })

        for i in range(0, len(payload), 500):
            lote = payload[i : i + 500]
            supabase.table("sih_sus_hsh").insert(lote).execute()
        print(f"   🚀 Sucesso! {len(payload)} capas de AIH enviadas ao banco.")
        return True
            
    except Exception as e:
        print(f"❌ Erro grave ao processar RD: {e}")
        if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
        return False

# =========================================================
# 4. PROCESSAMENTO E UPLOAD: ITENS PROFISSIONAIS (SP)
# =========================================================
def processar_e_subir_sp(arquivo_dbc, ano_completo, mes_mm):
    if not arquivo_dbc: return False
    print(f"\n⚙️ Processando arquivo SP (Itens): {os.path.basename(arquivo_dbc)}")
    arquivo_dbf = arquivo_dbc.replace('.dbc', '.dbf')
    
    try:
        datasus_dbc.decompress(arquivo_dbc, arquivo_dbf)
        dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
        df = pd.DataFrame(iter(dbf))
        os.remove(arquivo_dbf)
        
        col_cnes = 'SP_CNES' if 'SP_CNES' in df.columns else 'CNES'
        df = df[df[col_cnes] == CNES_HSH]
        if df.empty:
            print("   ⚠️ Nenhum item SP encontrado para o hospital neste mês.")
            return True

        # NOVA ESTRATÉGIA ANTI-TIMEOUT: Deletar em Lotes pelas AIHs do mês
        col_aih = 'SP_NAIH' if 'SP_NAIH' in df.columns else 'N_AIH'
        aihs_unicas = df[col_aih].dropna().astype(str).unique().tolist()
        print(f"   🧹 Limpando dados antigos de {len(aihs_unicas)} AIHs (em lotes de 200) para evitar timeout da API...")
        
        for i in range(0, len(aihs_unicas), 200):
            lote_delete = aihs_unicas[i : i + 200]
            try:
                supabase.table("sp_sus_hsh").delete().in_("n_aih", lote_delete).execute()
            except Exception as e:
                print(f"      ⚠️ Aviso num lote de limpeza: {e}")

        payload = []
        for _, row in df.iterrows():
            payload.append({
                "ano_cmpt": ano_completo,
                "mes_cmpt": mes_mm,
                "n_aih": str(row.get("SP_NAIH", "")),
                "sp_proced": str(row.get("SP_PROCREA", row.get("SP_ATOPROF", ""))),
                "sp_cbo": str(row.get("SP_CBO", row.get("SP_PF_CBO", ""))),
                "sp_qtd": float(row.get("SP_QTD_ATO", 1)),
                "sp_val_tot": float(row.get("SP_VALATO", 0.0)),
                "sp_pf_doc": str(row.get("SP_PROF_SUS", row.get("SP_PF_DOC", ""))).strip(),
                "sp_pj_doc": str(row.get("SP_PJ_DOC", row.get("SP_CGC_HOSP", ""))).strip()
            })

        for i in range(0, len(payload), 500):
            lote = payload[i : i + 500]
            supabase.table("sp_sus_hsh").insert(lote).execute()
        print(f"   🚀 Sucesso! {len(payload)} itens e honorários (SP) enviados ao banco.")
        return True
            
    except Exception as e:
        print(f"❌ Erro grave ao processar SP: {e}")
        if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
        return False

# =========================================================
# 5. EXECUÇÃO PRINCIPAL
# =========================================================
if __name__ == "__main__":
    print("Por favor, informe a competência que deseja atualizar:")
    ano_input = input("Ano (ex: 2026): ").strip()
    mes_input = input("Mês (ex: 02): ").strip().zfill(2)
    
    if len(ano_input) == 4 and len(mes_input) == 2:
        ano_yy = ano_input[2:]
        
        arq_rd = baixar_arquivo_ftp("RD", ano_yy, mes_input)
        rd_ok = processar_e_subir_rd(arq_rd, ano_input, mes_input)
        
        if rd_ok:
            arq_sp = baixar_arquivo_ftp("SP", ano_yy, mes_input)
            sp_ok = processar_e_subir_sp(arq_sp, ano_input, mes_input)
            
            if sp_ok:
                print("\n🎉 ATUALIZAÇÃO MENSAL CONCLUÍDA COM SUCESSO!")
                print(f"Os dados de {mes_input}/{ano_input} já estão disponíveis no seu Painel HTML.")
            else:
                print("\n❌ A atualização falhou durante o processamento do arquivo SP.")
        else:
            print("\n❌ A atualização falhou durante o processamento do arquivo RD.")
    else:
        print("❌ Formato inválido. Use ano com 4 dígitos e mês com 2 dígitos.")