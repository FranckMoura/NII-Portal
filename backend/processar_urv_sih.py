import os
import glob
import json
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("--- 🚀 PROCESSADOR DUAL SIH/SUS: JURÍDICO + SUPABASE ---")

# =========================================================
# CONFIGURAÇÕES DO SUPABASE (NII-PORTAL)
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

supabase: Client = create_client(SB_URL, SB_KEY)

# =========================================================
# MAPEAMENTO DE PASTAS
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(os.path.dirname(BASE_DIR), "bases_rdmt_brutas") 
PASTA_DESTINO = os.path.join(BASE_DIR, "planilhas_urv_hsh")

CNES_HSH = "2311682"
CNPJ_HSH = "03470416000161"

COLUNAS_JURIDICO = [
    'UF_ZI', 'ANO_CMPT', 'MES_CMPT', 'CGC_HOSP', 'CNES', 'N_AIH',
    'NASC', 'SEXO', 'IDADE', 'DT_INTER', 'DT_SAIDA', 'DIAG_PRINC',
    'VAL_SH', 'VAL_SP', 'VAL_SADT', 'VAL_SANGUE', 'VAL_TOT'
]

def processar_dados():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)

    # Radar Antiduplicidade e Organizado (Para o bug do Windows)
    arquivos_brutos = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    # O set() elimina duplicados (arquivos lidos duas vezes)
    arquivos_dbc = list(set(arquivos_brutos))
    arquivos_dbc.sort() # Coloca em ordem alfabética/cronológica
    
    if not arquivos_dbc:
        print(f"❌ Nenhum arquivo .dbc encontrado na pasta: {PASTA_ORIGEM}")
        return

    print(f"📂 Encontrados {len(arquivos_dbc)} arquivos ÚNICOS para processar.")
    dados_consolidados = []

    for arquivo in arquivos_dbc:
        nome_dbc = os.path.basename(arquivo)
        arquivo_dbf = arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
        
        print(f"⏳ Extraindo: {nome_dbc}...", end="\r")
        
        if os.path.getsize(arquivo) == 0:
            continue

        try:
            # Descompacta nativamente pelo Python
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            
            # Lê o DBF
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            if os.path.exists(arquivo_dbf):
                os.remove(arquivo_dbf)
            
            # Filtra o Hospital
            mascara_filtro = pd.Series(False, index=df.index)
            if 'CGC_HOSP' in df.columns: 
                mascara_filtro = mascara_filtro | (df['CGC_HOSP'] == CNPJ_HSH)
            if 'CNES' in df.columns: 
                mascara_filtro = mascara_filtro | (df['CNES'] == CNES_HSH)
                
            df_hsh = df[mascara_filtro].copy()
            
            if not df_hsh.empty:
                # Guardamos TODAS as colunas para o banco de dados
                dados_consolidados.append(df_hsh)
                print(f"✅ {nome_dbc} -> {len(df_hsh)} AIHs capturadas.          ")
                
        except Exception as e:
            if os.path.exists(arquivo_dbf):
                os.remove(arquivo_dbf)

    if not dados_consolidados:
        print("\n⚠️ Nenhuma internação encontrada.")
        return

    print("\n🔄 Consolidando Super Dataframe...")
    df_final = pd.concat(dados_consolidados, ignore_index=True)
    
    # Converte colunas financeiras vitais para números reais
    colunas_fin = ['VAL_SH', 'VAL_SP', 'VAL_SADT', 'VAL_SANGUE', 'VAL_TOT']
    for col in colunas_fin:
        if col in df_final.columns:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0.0)

    # Preenche o restante dos dados vazios com strings para não quebrar a inserção JSON
    df_final = df_final.fillna("")

    # =========================================================
    # OBJETIVO 1: TRILHO JURÍDICO (EXCEL)
    # =========================================================
    print("\n⚖️ GERANDO ARQUIVOS PARA O JURÍDICO (URV 9,56%)...")
    colunas_existentes_jur = [col for col in COLUNAS_JURIDICO if col in df_final.columns]
    df_juridico = df_final[colunas_existentes_jur].copy()

    if 'ANO_CMPT' in df_juridico.columns:
        for ano in df_juridico['ANO_CMPT'].unique():
            if not str(ano).strip(): continue
            df_ano = df_juridico[df_juridico['ANO_CMPT'] == ano]
            nome_excel = os.path.join(PASTA_DESTINO, f"AIHs_SIH_{ano}.xlsx")
            df_ano.to_excel(nome_excel, index=False)
            print(f"   -> Salvo: AIHs_SIH_{ano}.xlsx")

    resumo_fin = df_juridico.groupby('ANO_CMPT')[colunas_fin].sum().reset_index()
    resumo_fin['DIFERENCA_URV_9_56%'] = resumo_fin['VAL_SH'] * 0.0956
    resumo_fin.to_excel(os.path.join(PASTA_DESTINO, "RESUMO_CONSOLIDADO_URV.xlsx"), index=False)
    print("✅ Resumo URV gerado com sucesso!")

    # =========================================================
    # OBJETIVO 2: TRILHO INTELIGÊNCIA NII-PORTAL (SUPABASE)
    # =========================================================
    print("\n☁️ ENVIANDO DADOS RICOS PARA O SUPABASE (Sincronização em Lotes)...")
    
    payload = []
    # Usando JSON interno do Pandas para garantir que os tipos sejam compatíveis com a nuvem
    for _, row in df_final.iterrows():
        linha_json = row.to_json()
        linha_dict = json.loads(linha_json)
        
        payload.append({
            "ano_cmpt": str(linha_dict.get("ANO_CMPT", "")).strip(),
            "mes_cmpt": str(linha_dict.get("MES_CMPT", "")).strip(),
            "n_aih": str(linha_dict.get("N_AIH", "")).strip(),
            "dt_inter": str(linha_dict.get("DT_INTER", "")).strip(),
            "dt_saida": str(linha_dict.get("DT_SAIDA", "")).strip(),
            "diag_princ": str(linha_dict.get("DIAG_PRINC", "")).strip(),
            "val_sh": float(linha_dict.get("VAL_SH") or 0.0),
            "val_sp": float(linha_dict.get("VAL_SP") or 0.0),
            "val_tot": float(linha_dict.get("VAL_TOT") or 0.0),
            "dados_completos": linha_dict # O "cofre" com as +100 colunas intactas!
        })

    # Divide os envios em pacotes de 2.000 (Batch Insert) para otimizar velocidade
    tamanho_lote = 2000
    total = len(payload)
    
    for i in range(0, total, tamanho_lote):
        lote = payload[i : i + tamanho_lote]
        try:
            supabase.table("sih_sus_hsh").insert(lote).execute()
            print(f"   ⬆️ Lote enviado: {min(i + tamanho_lote, total)} de {total} AIHs...")
        except Exception as err:
            print(f"   ❌ Erro ao enviar lote: {err}")

    print("\n🚀 DECOLAGEM CONCLUÍDA! Jurídico atendido e NII-Portal alimentado com sucesso!")

if __name__ == "__main__":
    processar_dados()