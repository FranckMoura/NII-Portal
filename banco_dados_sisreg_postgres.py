import pandas as pd
import glob
import os
import time
import json
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- 2. PROCESSAMENTO: CSV -> POSTGRESQL -> JSON (V44 - PRESERVAÇÃO DE LINKS) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123"  # <--- SUA SENHA AQUI
HOST_DB = "localhost"
NOME_DB = "nii_portal"

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")
# Mantemos o Parquet como backup para garantir compatibilidade com scripts antigos
CAMINHO_PARQUET = os.path.join(PASTA_ARQUIVOS, "base_sisreg.parquet")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# --- CONEXÃO COM O BANCO ---
try:
    # 1. Tenta criar o banco se não existir
    url_inicial = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/postgres"
    engine_temp = create_engine(url_inicial, isolation_level="AUTOCOMMIT")
    with engine_temp.connect() as conn:
        res = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{NOME_DB}'"))
        if not res.fetchone():
            print(f"   Criando banco de dados '{NOME_DB}'...")
            conn.execute(text(f"CREATE DATABASE {NOME_DB}"))
            
    # 2. Conecta no banco oficial
    url_final = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
    engine = create_engine(url_final)
except Exception as e:
    print(f"❌ Erro fatal no Banco de Dados: {e}")
    exit()

# --- LEITURA DOS CSVs (Extração V18) ---
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
arquivos_sisreg = [f for f in arquivos if "2311682" in f or "SISREG" in f]

if not arquivos_sisreg:
    print("❌ Nenhum arquivo CSV encontrado.")
    exit()

print(f"   -> Processando {len(arquivos_sisreg)} arquivos...")
dfs = []

for arq in arquivos_sisreg:
    try:
        try: df = pd.read_csv(arq, sep=';', encoding='utf-8', dtype=str, on_bad_lines='skip')
        except: df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
        # Limpeza de Colunas
        new_cols = []
        for c in df.columns:
            clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
            # Correção para o bug de codificação antigo (segurança)
            if "SOLICITAA" in clean: clean = clean.replace("SOLICITAA§A£O", "SOLICITACAO")
            new_cols.append(clean)
        df.columns = new_cols
        dfs.append(df)
    except: pass

if not dfs: exit()
df_total = pd.concat(dfs, ignore_index=True)

# --- ETL (Transformação) ---
mapa = {
    'DATA_DA_SOLICITACAO': 'data_visual', 'NOME_DO_PACIENTE': 'paciente',
    'CNS_DO_PACIENTE': 'cns', 'N_DA_SOLICITACAO': 'num_sol',
    'N_AIH': 'aih', 'NOME_DO_PROCEDIMENTO_SOLICITADO': 'proc',
    'STATUS_DA_SOLICITACAO_DE_INTERNACAO': 'status', 'CARATER_INTERNACAO': 'carater'
}
# Filtra só colunas que existem
cols = [c for c in mapa.keys() if c in df_total.columns]
df_db = df_total[cols].rename(columns=mapa)

# Remove duplicatas e formata
df_db = df_db.drop_duplicates(subset=['num_sol'], keep='first')
df_db['data_obj'] = pd.to_datetime(df_db['data_visual'], dayfirst=True, errors='coerce')
df_db['data_iso'] = df_db['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
df_db = df_db.drop(columns=['data_obj'])
df_db = df_db.fillna("-")

# --- CARGA (Load) ---
print("   -> Salvando no PostgreSQL...")
df_db.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)

print("   -> Gerando arquivos para o Portal...")
# Lê do banco para garantir integridade
df_final = pd.read_sql("SELECT * FROM sisreg_solicitacoes ORDER BY data_iso DESC", engine)

# --- CORREÇÃO VITAL: PRESERVAR LINKS DOS PDFs ---
# O script de impressão salva os links no JSON, mas o banco não tem essa coluna.
# Aqui nós mesclamos os dados novos do banco com os links antigos do JSON.

links_pdf_existentes = {}
if os.path.exists(CAMINHO_JSON):
    try:
        with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
            dados_antigos = json.load(f)
            # Cria um mapa { "AIH": "caminho/do/pdf" }
            for item in dados_antigos:
                aih_key = str(item.get("aih", "")).strip()
                pdf_link = item.get("arquivo_pdf")
                if aih_key and pdf_link:
                    links_pdf_existentes[aih_key] = pdf_link
        print(f"   (Links de PDF recuperados: {len(links_pdf_existentes)})")
    except Exception as e:
        print(f"   ⚠️ Aviso: Erro ao ler JSON antigo: {e}")

# Converte DataFrame para lista de dicionários para facilitar a mesclagem
registros_finais = df_final.to_dict(orient='records')

# Injeta os links de volta
cont_links = 0
for reg in registros_finais:
    aih_atual = str(reg.get("aih", "")).strip()
    if aih_atual in links_pdf_existentes:
        reg["arquivo_pdf"] = links_pdf_existentes[aih_atual]
        cont_links += 1

print(f"   (Links aplicados no novo arquivo: {cont_links})")

# Salva o JSON final mesclado (Com indentação para ficar legível)
with open(CAMINHO_JSON, 'w', encoding='utf-8') as f:
    json.dump(registros_finais, f, indent=4, ensure_ascii=False)

# Gera Parquet (Backup)
try:
    df_final.to_parquet(CAMINHO_PARQUET, index=False)
except:
    pass

print(f"✅ SUCESSO! Base atualizada com {len(registros_finais)} registros.")