import os
import glob
import math
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("==========================================================")
print(" 🏥 MEGA PROCESSADOR CNES (DBC -> CSV LOCAL -> SUPABASE) ")
print("==========================================================")

# =========================================================
# CONFIGURAÇÕES
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}"); exit()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(BASE_DIR, "bases_cnes_brutas") 
PASTA_DESTINO_CSV = os.path.join(BASE_DIR, "bases_cnes_csv")

if not os.path.exists(PASTA_DESTINO_CSV):
    os.makedirs(PASTA_DESTINO_CSV)

# =========================================================
# FASE 1: CONVERTER DBC PARA CSV LOCALMENTE
# =========================================================
def converter_dbc_para_csv():
    print("\n--- 🛠️ FASE 1: CONVERSÃO DE ARQUIVOS PARA CSV ---")
    arquivos_dbc = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    
    if not arquivos_dbc:
        print("⚠️ Nenhum arquivo .dbc encontrado na pasta de origem.")
        return

    for arquivo in arquivos_dbc:
        nome_base = os.path.basename(arquivo).upper().replace(".DBC", "")
        arquivo_dbf = os.path.join(PASTA_DESTINO_CSV, f"{nome_base}.dbf")
        arquivo_csv = os.path.join(PASTA_DESTINO_CSV, f"{nome_base}.csv")

        if os.path.exists(arquivo_csv):
            print(f"⏭️ {nome_base}.csv já existe. Pulando conversão.")
            continue

        print(f"⚙️ Convertendo {nome_base}.DBC para CSV...")
        try:
            # Descompacta nativamente
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            
            # Lê o DBF e converte para Pandas
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            # Salva fisicamente no computador como CSV
            df.to_csv(arquivo_csv, sep=';', index=False, encoding='latin-1')
            print(f"   ✅ Sucesso! Salvo como: {arquivo_csv}")
            
            # Apaga o DBF temporário
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

        except Exception as e:
            print(f"   ❌ Erro ao descompactar {nome_base}: {e}")
            print(f"   💡 DICA: O arquivo do Datasus está corrompido para o Python. Use o TabWin para converter este arquivo para CSV manualmente e cole na pasta 'bases_cnes_csv'.")
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

# =========================================================
# FASE 2: LER OS CSVS LOCAIS E ENVIAR PARA O SUPABASE
# =========================================================
def upload_em_lotes(df, nome_tabela, tamanho_lote=1000):
    total_linhas = len(df)
    lotes = math.ceil(total_linhas / tamanho_lote)
    print(f"☁️ Iniciando envio para '{nome_tabela}': {total_linhas} registros em {lotes} lotes.")
    
    for i in range(lotes):
        inicio = i * tamanho_lote
        fim = inicio + tamanho_lote
        lote_df = df.iloc[inicio:fim]
        dados_json = lote_df.to_dict(orient='records')
        try:
            supabase.table(nome_tabela).upsert(dados_json).execute()
            print(f"   ⬆️ Lote {i+1}/{lotes} enviado com sucesso!")
        except Exception as e:
            print(f"   ❌ Erro no lote {i+1}: {e}")

def subir_csvs_para_supabase():
    print("\n--- 🚀 FASE 2: UPLOAD DOS ARQUIVOS CSV PARA O BANCO ---")
    arquivos_csv = glob.glob(os.path.join(PASTA_DESTINO_CSV, "*.csv"))
    
    if not arquivos_csv:
        print("⚠️ Nenhum arquivo .csv encontrado na pasta de destino para subir.")
        return

    for arq in arquivos_csv:
        nome_arquivo = os.path.basename(arq).upper()
        print(f"\n📂 Lendo arquivo local: {nome_arquivo}")
        
        try:
            df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
            colunas = [c.upper().replace('"', '').strip() for c in df.columns]
            df.columns = colunas
            df = df.fillna("")

            # LÓGICA: ESTABELECIMENTOS (ST)
            if nome_arquivo.startswith("ST"):
                col_cnes = next((c for c in colunas if 'CNES' in c), None)
                col_fantasia = next((c for c in colunas if 'FANTASIA' in c), None)
                col_razao = next((c for c in colunas if 'NOME' in c or 'RAZAO' in c), None)

                if not col_cnes: continue

                df = df[df[col_cnes].str.strip() != ""]
                df = df.drop_duplicates(subset=[col_cnes], keep='first')

                payload = []
                for _, row in df.iterrows():
                    payload.append({
                        "cnes": str(row[col_cnes]).strip(),
                        "nome_fantasia": str(row[col_fantasia]).strip().upper() if col_fantasia else "",
                        "razao_social": str(row[col_razao]).strip().upper() if col_razao else "",
                        "gestao": str(row.get('GESTAO', '')).strip()
                    })
                
                upload_em_lotes(pd.DataFrame(payload), "cnes_estabelecimentos")

            # LÓGICA: PROFISSIONAIS (PF)
            elif nome_arquivo.startswith("PF"):
                col_cnes = next((c for c in colunas if 'CNES' in c), None)
                col_cns = next((c for c in colunas if 'PROF_SUS' in c or 'CNS' in c), None)
                col_nome = next((c for c in colunas if 'NOME_PROF' in c or 'NOME' in c), None)
                col_cbo = next((c for c in colunas if 'CBO' in c), None)

                if not col_cns: continue

                ano_abrev = nome_arquivo[4:6]
                mes_abrev = nome_arquivo[6:8]

                df = df[df[col_cns].str.strip() != ""]
                df = df.drop_duplicates(subset=[col_cns, col_cnes, col_cbo], keep='first')

                payload = []
                for _, row in df.iterrows():
                    payload.append({
                        "cnes": str(row[col_cnes]).strip() if col_cnes else "",
                        "cns_prof": str(row[col_cns]).strip(),
                        "nome_prof": str(row[col_nome]).strip().upper() if col_nome else "",
                        "cbo": str(row[col_cbo]).strip() if col_cbo else "",
                        "comp_ano": f"20{ano_abrev}",
                        "comp_mes": mes_abrev
                    })
                
                upload_em_lotes(pd.DataFrame(payload), "cnes_profissionais")

        except Exception as e:
            print(f"❌ Erro ao ler o CSV {nome_arquivo}: {e}")

if __name__ == "__main__":
    converter_dbc_para_csv()
    subir_csvs_para_supabase()
    print("\n🎉 ROTINA COMPLETA FINALIZADA!")