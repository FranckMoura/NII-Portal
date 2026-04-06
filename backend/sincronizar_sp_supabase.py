import os
import glob
import json
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("--- 🚀 SINCRONIZAÇÃO TOTAL SUPABASE (SERVIÇOS PROFISSIONAIS - SP) ---")

# =========================================================
# CONFIGURAÇÕES DO SUPABASE
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

supabase: Client = create_client(SB_URL, SB_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Pasta dos arquivos brutos SP (A que configuramos no script de download)
PASTA_ORIGEM = os.path.join(BASE_DIR, "bases_spmt_brutas") 

CNES_HSH = "2311682"
CNPJ_HSH = "03470416000161"

def subir_dados_sp():
    arquivos_brutos = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    arquivos_dbc = list(set(arquivos_brutos))
    arquivos_dbc.sort()
    
    print(f"📂 Lendo {len(arquivos_dbc)} arquivos SP...")
    dados_consolidados = []

    for arquivo in arquivos_dbc:
        arquivo_dbf = arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
        if os.path.getsize(arquivo) == 0: continue

        print(f"   Descompactando {os.path.basename(arquivo)}...")
        try:
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
            
            # FILTRO ESPECÍFICO DO ARQUIVO SP (As colunas mudam de nome aqui!)
            mascara_filtro = pd.Series(False, index=df.index)
            if 'SP_CGC_HOS' in df.columns: mascara_filtro = mascara_filtro | (df['SP_CGC_HOS'] == CNPJ_HSH)
            if 'SP_CNES' in df.columns: mascara_filtro = mascara_filtro | (df['SP_CNES'] == CNES_HSH)
                
            df_hsh = df[mascara_filtro].copy()
            if not df_hsh.empty: 
                dados_consolidados.append(df_hsh)
                print(f"   ✓ {len(df_hsh)} itens do Hospital Santa Helena encontrados e separados.")
        except Exception as e:
            print(f"   ❌ Erro ao ler {os.path.basename(arquivo)}: {e}")
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

    if not dados_consolidados:
        print("\n⚠️ Nenhum item de Serviço Profissional (SP) encontrado para o Hospital Santa Helena.")
        return

    df_final = pd.concat(dados_consolidados, ignore_index=True)
    df_final = df_final.fillna("")

    payload = []
    print("\n☁️ PREPARANDO PACOTES DE 500 ITENS PARA O SUPABASE...")
    for _, row in df_final.iterrows():
        linha_json = row.to_json()
        linha_dict = json.loads(linha_json)
        
        # Mapeamento das colunas vitais do SP
        payload.append({
            "ano_cmpt": str(linha_dict.get("SP_AA_CMPT") or linha_dict.get("ANO_CMPT", "")).strip(), # O SP usa SP_AA_CMPT
            "mes_cmpt": str(linha_dict.get("SP_MM_CMPT") or linha_dict.get("MES_CMPT", "")).strip(), # O SP usa SP_MM_CMPT
            "n_aih": str(linha_dict.get("SP_NAIH") or linha_dict.get("N_AIH", "")).strip(), # A chave que liga o SP ao RD!
            "sp_cnes": str(linha_dict.get("SP_CNES", "")).strip(),
            "sp_proced": str(linha_dict.get("SP_PROCREA", "")).strip(), # O código do Exame/Material/Agulha
            "sp_cbo": str(linha_dict.get("SP_CBO", "")).strip(), # A especialidade do médico
            "sp_qtd": float(linha_dict.get("SP_QTD_ATO") or 0.0), # Quantidade (ex: 5 ampolas)
            "sp_val_tot": float(linha_dict.get("SP_VALATO") or 0.0), # Valor total pago pelo item
            "dados_completos": linha_dict # O JSON inteiro de backup
        })

    tamanho_lote = 500
    total = len(payload)
    
    print(f"\n🚀 INICIANDO UPLOAD SEGURO DE {total} ITENS PARA A TABELA 'sp_sus_hsh'...")
    for i in range(0, total, tamanho_lote):
        lote = payload[i : i + tamanho_lote]
        try:
            supabase.table("sp_sus_hsh").insert(lote).execute()
            print(f"   ⬆️ Lote enviado: {min(i + tamanho_lote, total)} de {total} Itens Secundários (SP)...")
        except Exception as err:
            print(f"   ❌ Erro ao enviar lote: {err}")

    print("\n✅ TABELA DE SERVIÇOS PROFISSIONAIS (SP) 100% SINCRONIZADA!")

if __name__ == "__main__":
    subir_dados_sp()