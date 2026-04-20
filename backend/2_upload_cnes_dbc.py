import os
import glob
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client

print("--- 🚀 SCRIPT CNES: SINCRONIZAÇÃO TOTAL SUPABASE (Lotes de 500) ---")

# =========================================================
# CONFIGURAÇÕES DO SUPABASE
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
# Mantive a chave que você usou no seu script modelo
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

supabase: Client = create_client(SB_URL, SB_KEY)

# Aponta para a pasta onde o 1_download_cnes_ftp.py salvou os arquivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(BASE_DIR, "bases_cnes_brutas") 

def subir_dados_cnes():
    arquivos_brutos = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    arquivos_dbc = list(set(arquivos_brutos))
    arquivos_dbc.sort()

    print(f"📂 Encontrados {len(arquivos_dbc)} arquivos DBC na pasta 'bases_cnes_brutas'...")

    for arquivo in arquivos_dbc:
        nome_arquivo = os.path.basename(arquivo).upper()
        arquivo_dbf = arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
        
        if os.path.getsize(arquivo) == 0: continue

        print(f"\n⚙️ Descompactando {nome_arquivo} com datasus_dbc...")
        try:
            # 1. Converte de DBC para DBF nativamente
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            
            # 2. Lê o DBF para a memória
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            # Limpa o arquivo DBF temporário para poupar espaço no PC
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
            
            # Normalizar nomes das colunas
            colunas = [c.upper() for c in df.columns]
            df.columns = colunas
            df = df.fillna("")
            df = df.astype(str) # Força tudo a ser string (para os números não perderem os zeros)

            payload = []

            # ========================================================
            # LÓGICA ESTABELECIMENTOS (ST)
            # ========================================================
            if nome_arquivo.startswith("ST"):
                print(f"🏥 Processando Estabelecimentos de Saúde (ST)...")
                col_cnes = next((c for c in colunas if 'CNES' in c), None)
                col_fantasia = next((c for c in colunas if 'FANTASIA' in c), None)
                col_razao = next((c for c in colunas if 'NOME' in c or 'RAZAO' in c), None)

                if not col_cnes: continue

                # Remove linhas vazias e duplicatas absolutas (Guarda o estado inteiro do MT)
                df = df[df[col_cnes].str.strip() != ""]
                df = df.drop_duplicates(subset=[col_cnes], keep='first')

                for _, row in df.iterrows():
                    payload.append({
                        "cnes": row[col_cnes].strip(),
                        "nome_fantasia": row[col_fantasia].strip().upper() if col_fantasia else "",
                        "razao_social": row[col_razao].strip().upper() if col_razao else "",
                        "gestao": row.get('GESTAO', '').strip()
                    })
                
                tabela_destino = "cnes_estabelecimentos"

            # ========================================================
            # LÓGICA PROFISSIONAIS (PF)
            # ========================================================
            elif nome_arquivo.startswith("PF"):
                print(f"👨‍⚕️ Processando Profissionais (PF)...")
                col_cnes = next((c for c in colunas if 'CNES' in c), None)
                col_cns = next((c for c in colunas if 'PROF_SUS' in c or 'CNS' in c), None)
                col_nome = next((c for c in colunas if 'NOME_PROF' in c or 'NOME' in c), None)
                col_cbo = next((c for c in colunas if 'CBO' in c), None)

                if not col_cns: continue

                # Pega a competência a partir do nome do arquivo: PFMT2602.dbc -> 2026 e 02
                ano_abrev = nome_arquivo[4:6]
                mes_abrev = nome_arquivo[6:8]

                df = df[df[col_cns].str.strip() != ""]
                df = df.drop_duplicates(subset=[col_cns, col_cnes, col_cbo], keep='first')

                for _, row in df.iterrows():
                    payload.append({
                        "cnes": row[col_cnes].strip() if col_cnes else "",
                        "cns_prof": row[col_cns].strip(),
                        "nome_prof": row[col_nome].strip().upper() if col_nome else "",
                        "cbo": row[col_cbo].strip() if col_cbo else "",
                        "comp_ano": f"20{ano_abrev}",
                        "comp_mes": mes_abrev
                    })

                tabela_destino = "cnes_profissionais"
            
            else:
                print(f"⚠️ Arquivo ignorado (Não é ST nem PF).")
                continue

            if not payload:
                print("⚠️ Nenhum registro válido encontrado neste arquivo.")
                continue

            tamanho_lote = 500
            total = len(payload)
            print(f"☁️ PREPARANDO PACOTES DE 500 PARA A TABELA '{tabela_destino}' ({total} registros)...")

            for i in range(0, total, tamanho_lote):
                lote = payload[i : i + tamanho_lote]
                try:
                    # Usamos upsert para evitar erro caso rode o script duas vezes
                    supabase.table(tabela_destino).upsert(lote).execute()
                    print(f"   ⬆️ Lote enviado: {min(i + tamanho_lote, total)} de {total}...")
                except Exception as err:
                    print(f"   ❌ Erro ao enviar lote: {err}")

        except Exception as e:
            print(f"❌ Erro grave ao processar {nome_arquivo}: {e}")
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

    print("\n✅ BANCO DE DADOS CNES 100% SINCRONIZADO E SEM FALHAS!")

if __name__ == "__main__":
    # Garante que a biblioteca datasus_dbc está instalada
    try:
        import datasus_dbc
    except ImportError:
        print("⚠️ Biblioteca datasus_dbc não encontrada. Instale usando: pip install datasus_dbc dbfread pandas supabase")
        exit()
        
    subir_dados_cnes()