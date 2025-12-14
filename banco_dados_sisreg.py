import pandas as pd
import glob
import os
import json
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- PROCESSAMENTO SISREG -> POSTGRESQL ---")

# --- CONFIGURAÇÕES DE BANCO ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123"  # <--- COLOQUE SUA SENHA AQUI
HOST_DB = "localhost"
NOME_DB = "nii_portal"

# --- CONFIGURAÇÕES DE ARQUIVOS ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")

# 1. CRIAR CONEXÃO COM O BANCO
# String de conexão: postgresql://usuario:senha@host/banco
engine_url = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/postgres" # Conecta no 'postgres' primeiro para criar o banco
engine = create_engine(engine_url)

# Cria o banco 'nii_portal' se não existir
with engine.connect() as conn:
    conn.execute(text("COMMIT")) # Postgres exige autocommit para criar DB
    try:
        conn.execute(text(f"CREATE DATABASE {NOME_DB}"))
        print(f"✅ Banco de dados '{NOME_DB}' criado!")
    except:
        print(f"ℹ️ Banco de dados '{NOME_DB}' já existe.")

# Reconecta agora no banco certo
engine = create_engine(f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}")

# 2. LER OS ARQUIVOS CSV (Mesma lógica robusta do V23)
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
        
        # Limpeza de colunas
        new_cols = []
        for c in df.columns:
            clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
            # Correção para o bug de codificação específico
            if "SOLICITAA" in clean: clean = clean.replace("SOLICITAA§A£O", "SOLICITACAO")
            if "INTERNAA" in clean: clean = clean.replace("INTERNAA§A£O", "INTERNACAO")
            new_cols.append(clean)
        df.columns = new_cols
        dfs.append(df)
    except: pass

df_total = pd.concat(dfs, ignore_index=True)

# 3. FILTRAR E RENOMEAR COLUNAS (Para o padrão SQL)
# Mapeamento: Nome no CSV -> Nome no Banco de Dados
mapa_colunas = {
    'DATA_DA_SOLICITACAO': 'data_solicitacao',
    'NOME_DO_PACIENTE': 'paciente',
    'CNS_DO_PACIENTE': 'cns',
    'N_DA_SOLICITACAO': 'numero_solicitacao',
    'N_AIH': 'aih',
    'NOME_DO_PROCEDIMENTO_SOLICITADO': 'procedimento',
    'STATUS_DA_SOLICITACAO_DE_INTERNACAO': 'status',
    'CARATER_INTERNACAO': 'carater'
}

# Seleciona apenas as colunas que existem
colunas_existentes = [c for c in mapa_colunas.keys() if c in df_total.columns]
df_db = df_total[colunas_existentes].rename(columns=mapa_colunas)

# Tratamentos finais
df_db = df_db.drop_duplicates(subset=['numero_solicitacao'], keep='first')
df_db['data_obj'] = pd.to_datetime(df_db['data_solicitacao'], dayfirst=True, errors='coerce')
df_db['data_iso'] = df_db['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
df_db = df_db.drop(columns=['data_obj']) # Remove auxiliar

# Preenche nulos
df_db = df_db.fillna("-")

# 4. SALVAR NO POSTGRESQL
print("   -> Salvando no PostgreSQL...")
# if_exists='replace': Apaga a tabela antiga e cria uma nova (Ideal para carga total)
# index=False: Não cria uma coluna de índice numérico extra
df_db.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)
print(f"✅ Tabela 'sisreg_solicitacoes' atualizada com {len(df_db)} registros.")

# 5. GERAR JSON PARA O SITE
# Agora lemos DO BANCO para garantir que o site mostre o que está no banco
print("   -> Gerando JSON para o Portal...")
df_site = pd.read_sql("SELECT * FROM sisreg_solicitacoes ORDER BY data_iso DESC", engine)

# Mapeia de volta para os nomes que o seu HTML já usa (data_visual, num_sol, etc)
df_site = df_site.rename(columns={
    'data_solicitacao': 'data_visual',
    'numero_solicitacao': 'num_sol',
    # As outras colunas no banco já tem nomes simples, mas seu JSON usa chaves específicas?
    # Vamos garantir que o JSON saia igual ao que você enviou:
    'procedimento': 'proc' 
    # paciente, cns, aih, status, carater já estão iguais
})

df_site.to_json(CAMINHO_JSON, orient='records', force_ascii=False)
print("✅ JSON gerado com sucesso!")