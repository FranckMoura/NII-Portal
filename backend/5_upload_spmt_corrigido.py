import os
import glob
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("--- 🚀 SCRIPT DEFINITIVO: UPLOAD SPMT COM DOCUMENTOS (CNS/CNES) ---")

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"
supabase: Client = create_client(SB_URL, SB_KEY)

# Aponte para a pasta onde estão os seus arquivos SPMT brutos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(BASE_DIR, "bases_spmt_brutas") 
CNES_HSH = "2311682"

def subir_sp_correto():
    arquivos_dbc = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    
    if not arquivos_dbc:
        print("⚠️ Nenhum arquivo SPMT (.dbc) encontrado.")
        return

    for arquivo in arquivos_dbc:
        arquivo_dbf = arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
        try:
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
            
            # Filtra apenas o seu hospital para ser rápido
            if 'SP_CNES' in df.columns:
                df = df[df['SP_CNES'] == CNES_HSH]
            
            if df.empty: continue
            
            payload = []
            for _, row in df.iterrows():
                payload.append({
                    "ano_cmpt": str(row.get("SP_AA", row.get("ANO_CMPT", "")))[:4],
                    "mes_cmpt": str(row.get("SP_MM", row.get("MES_CMPT", "")))[:2],
                    "n_aih": str(row.get("SP_NAIH", "")),
                    "sp_proced": str(row.get("SP_PROCREA", row.get("SP_ATOPROF", ""))),
                    "sp_cbo": str(row.get("SP_CBO", row.get("SP_PF_CBO", ""))),
                    "sp_qtd": float(row.get("SP_QTD_ATO", 1)),
                    "sp_val_tot": float(row.get("SP_VALATO", 0.0)),
                    # AQUI ESTÁ O SEGREDO QUE FALTAVA:
                    "sp_pf_doc": str(row.get("SP_PROF_SUS", row.get("SP_PF_DOC", ""))).strip(),
                    "sp_pj_doc": str(row.get("SP_PJ_DOC", row.get("SP_CGC_HOSP", ""))).strip()
                })
            
            # Subir em lotes de 500
            for i in range(0, len(payload), 500):
                lote = payload[i : i + 500]
                try:
                    # Usamos upsert para evitar duplicatas e sobrescrever os 'nulls' antigos
                    supabase.table("sp_sus_hsh").upsert(lote).execute()
                    print(f"   ⬆️ Lote SPMT enviado: {min(i + 500, len(payload))} de {len(payload)}...")
                except Exception as err:
                    print(f"   ❌ Erro: {err}")

        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

if __name__ == "__main__":
    subir_sp_correto()