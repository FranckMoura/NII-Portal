import pandas as pd
import glob
import os
import json
import time
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- PROCESSAMENTO SISREG -> POSTGRESQL (V1 - UPGRADE) ---")

# --- 1. CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123"  # <--- COLOQUE SUA SENHA AQUI
HOST_DB = "localhost"
NOME_DB = "nii_portal"

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# --- 2. PREPARAÇÃO DO BANCO ---
# Conecta no 'postgres' (banco padrão) para poder criar o nosso
url_inicial = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/postgres"
engine_inicial = create_engine(url_inicial, isolation_level="AUTOCOMMIT")

try:
    with engine_inicial.connect() as conn:
        # Verifica se o banco já existe
        res = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{NOME_DB}'"))
        if not res.fetchone():
            print(f"   Criando banco de dados '{NOME_DB}'...")
            conn.execute(text(f"CREATE DATABASE {NOME_DB}"))
        else:
            print(f"   Banco '{NOME_DB}' já existe. Conectando...")
except Exception as e:
    print(f"❌ Erro ao criar banco: {e}")
    exit()

# Conecta no banco oficial agora
url_final = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_final)

# --- 3. LEITURA DOS CSVS (Lógica Robusta V23) ---
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
arquivos_sisreg = [f for f in arquivos if "2311682" in f or "SISREG" in f]

if not arquivos_sisreg:
    print("❌ Nenhum arquivo CSV encontrado.")
    exit()

print(f"   -> Lendo {len(arquivos_sisreg)} arquivos CSV...")
dfs = []

for arq in arquivos_sisreg:
    try:
        # Tenta ler (Lógica de codificação mantida)
        try:
            df = pd.read_csv(arq, sep=';', encoding='utf-8', dtype=str, on_bad_lines='skip')
        except:
            df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
        # Limpeza de colunas (Correção de bugs de caracteres)
        new_cols = []
        for c in df.columns:
            clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
            if "SOLICITAA" in clean: clean = clean.replace("SOLICITAA§A£O", "SOLICITACAO")
            if "INTERNAA" in clean: clean = clean.replace("INTERNAA§A£O", "INTERNACAO")
            new_cols.append(clean)
        df.columns = new_cols
        dfs.append(df)
    except: pass

if not dfs:
    print("❌ Erro ao processar CSVs.")
    exit()

df_total = pd.concat(dfs, ignore_index=True)

# --- 4. FILTRAR E RENOMEAR COLUNAS (ETL) ---
# Mapeamento: Nome CSV -> Nome Banco
mapa = {
    'DATA_DA_SOLICITACAO': 'data_visual',
    'NOME_DO_PACIENTE': 'paciente',
    'CNS_DO_PACIENTE': 'cns',
    'N_DA_SOLICITACAO': 'num_sol',
    'N_AIH': 'aih',
    'NOME_DO_PROCEDIMENTO_SOLICITADO': 'proc',
    'STATUS_DA_SOLICITACAO_DE_INTERNACAO': 'status',
    'CARATER_INTERNACAO': 'carater'
}

# Seleciona e renomeia
cols_existentes = [c for c in mapa.keys() if c in df_total.columns]
df_db = df_total[cols_existentes].rename(columns=mapa)

# Tratamentos
df_db = df_db.drop_duplicates(subset=['num_sol'], keep='first')
df_db['data_obj'] = pd.to_datetime(df_db['data_visual'], dayfirst=True, errors='coerce')
df_db['data_iso'] = df_db['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
df_db = df_db.drop(columns=['data_obj'])
df_db = df_db.fillna("-")

# --- 5. SALVAR NO POSTGRESQL ---
print("   -> Salvando dados no PostgreSQL...")
try:
    # Salva na tabela 'sisreg_solicitacoes'
    df_db.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)
    print(f"✅ Sucesso! {len(df_db)} registros gravados no banco.")
except Exception as e:
    print(f"❌ Erro ao salvar no banco: {e}")

# --- 6. GERAR JSON PARA O SITE ---
print("   -> Gerando JSON para o Portal...")
# Lê direto do banco (garantia de que o dado está lá)
df_site = pd.read_sql("SELECT * FROM sisreg_solicitacoes ORDER BY data_iso DESC", engine)
df_site.to_json(CAMINHO_JSON, orient='records', force_ascii=False)

print("✅ JSON gerado com sucesso!")