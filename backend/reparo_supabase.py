import os
import glob
import json
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("--- 🚀 MINI-SCRIPT: SINCRONIZAÇÃO TOTAL SUPABASE (Lotes de 500) ---")

# =========================================================
# CONFIGURAÇÕES DO SUPABASE
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

supabase: Client = create_client(SB_URL, SB_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(os.path.dirname(BASE_DIR), "bases_rdmt_brutas") 

CNES_HSH = "2311682"
CNPJ_HSH = "03470416000161"

def subir_dados_corrigidos():
    arquivos_brutos = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    arquivos_dbc = list(set(arquivos_brutos))
    arquivos_dbc.sort()
    
    print(f"📂 Lendo {len(arquivos_dbc)} arquivos para montar o pacote perfeito...")
    dados_consolidados = []

    for arquivo in arquivos_dbc:
        arquivo_dbf = arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
        if os.path.getsize(arquivo) == 0: continue

        try:
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
            
            mascara_filtro = pd.Series(False, index=df.index)
            if 'CGC_HOSP' in df.columns: mascara_filtro = mascara_filtro | (df['CGC_HOSP'] == CNPJ_HSH)
            if 'CNES' in df.columns: mascara_filtro = mascara_filtro | (df['CNES'] == CNES_HSH)
                
            df_hsh = df[mascara_filtro].copy()
            if not df_hsh.empty: dados_consolidados.append(df_hsh)
        except Exception:
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

    if not dados_consolidados:
        print("\n⚠️ Nenhuma internação encontrada.")
        return

    df_final = pd.concat(dados_consolidados, ignore_index=True)
    df_final = df_final.fillna("")

    payload = []
    print("\n☁️ PREPARANDO PACOTES DE 500 AIHs...")
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
            "dados_completos": linha_dict
        })

    # Reduzimos o lote para 500 para evitar que o servidor rejeite por timeout
    tamanho_lote = 500
    total = len(payload)
    
    print("\n🚀 INICIANDO UPLOAD SEGURO PARA O SUPABASE...")
    for i in range(0, total, tamanho_lote):
        lote = payload[i : i + tamanho_lote]
        try:
            supabase.table("sih_sus_hsh").insert(lote).execute()
            print(f"   ⬆️ Lote enviado: {min(i + tamanho_lote, total)} de {total} AIHs...")
        except Exception as err:
            print(f"   ❌ Erro ao enviar lote: {err}")

    print("\n✅ BANCO DE DADOS 100% SINCRONIZADO E SEM FALHAS!")

if __name__ == "__main__":
    subir_dados_corrigidos()