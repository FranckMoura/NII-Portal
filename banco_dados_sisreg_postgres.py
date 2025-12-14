import pandas as pd
import glob
import os
import json
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- 2. PROCESSAMENTO SISREG -> POSTGRESQL ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123" # <--- SUA SENHA DO POSTGRES
HOST_DB = "localhost"
NOME_DB = "nii_portal"

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")

# Conexão
url_db = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_db)

# Arquivos
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
arquivos_sisreg = [f for f in arquivos if "2311682" in f or "SISREG" in f]

if not arquivos_sisreg:
    print("❌ Nenhum arquivo CSV encontrado (Extração falhou?).")
    # Não sai do script, apenas avisa, para não quebrar o processo todo
else:
    print(f"   -> Lendo {len(arquivos_sisreg)} arquivos CSV...")
    dfs = []
    for arq in arquivos_sisreg:
        try:
            try: df = pd.read_csv(arq, sep=';', encoding='utf-8', dtype=str, on_bad_lines='skip')
            except: df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
            
            new_cols = []
            for c in df.columns:
                clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
                if "SOLICITAA" in clean: clean = clean.replace("SOLICITAA§A£O", "SOLICITACAO")
                if "INTERNAA" in clean: clean = clean.replace("INTERNAA§A£O", "INTERNACAO")
                new_cols.append(clean)
            df.columns = new_cols
            dfs.append(df)
        except: pass

    if dfs:
        df_total = pd.concat(dfs, ignore_index=True)
        
        # Renomeia
        mapa = {
            'DATA_DA_SOLICITACAO': 'data_visual', 'NOME_DO_PACIENTE': 'paciente',
            'CNS_DO_PACIENTE': 'cns', 'N_DA_SOLICITACAO': 'num_sol',
            'N_AIH': 'aih', 'NOME_DO_PROCEDIMENTO_SOLICITADO': 'proc',
            'STATUS_DA_SOLICITACAO_DE_INTERNACAO': 'status', 'CARATER_INTERNACAO': 'carater'
        }
        cols = [c for c in mapa.keys() if c in df_total.columns]
        df_db = df_total[cols].rename(columns=mapa)
        
        # Limpa duplicatas
        df_db = df_db.drop_duplicates(subset=['num_sol'], keep='first')
        
        # Data ISO
        df_db['data_obj'] = pd.to_datetime(df_db['data_visual'], dayfirst=True, errors='coerce')
        df_db['data_iso'] = df_db['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
        df_db = df_db.drop(columns=['data_obj'])
        df_db = df_db.fillna("-")

        # Salva no Banco
        df_db.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)
        print(f"✅ Banco atualizado com {len(df_db)} registros.")

# GERA JSON (Sempre, lendo do banco)
try:
    df_site = pd.read_sql("SELECT * FROM sisreg_solicitacoes ORDER BY data_iso DESC", engine)
    df_site.to_json(CAMINHO_JSON, orient='records', force_ascii=False)
    print("✅ JSON atualizado.")
except Exception as e:
    print(f"❌ Erro ao gerar JSON (Banco vazio?): {e}")