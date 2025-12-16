import pandas as pd
import os
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- IMPORTAÇÃO DE FATURAMENTO (AIH) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123"  # <--- SUA SENHA
HOST_DB = "localhost"
NOME_DB = "nii_portal"

ARQUIVO_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\pDetAIH.csv"

# --- CONEXÃO ---
url_db = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_db)

if not os.path.exists(ARQUIVO_CSV):
    print(f"❌ Arquivo não encontrado: {ARQUIVO_CSV}")
    exit()

print(">> Lendo arquivo CSV...")
try:
    # O arquivo tem 2 linhas de cabeçalho inútil, o real é a linha 3 (header=2)
    # Tenta UTF-8 (padrão moderno)
    df = pd.read_csv(ARQUIVO_CSV, sep='\t', header=2, encoding='utf-8', dtype=str)
except:
    # Se falhar, tenta Latin-1 (padrão antigo do DATASUS)
    print("   (Tentando codificação alternativa...)")
    df = pd.read_csv(ARQUIVO_CSV, sep='\t', header=2, encoding='latin-1', dtype=str)

# --- LIMPEZA DE COLUNAS ---
print(">> Limpando colunas...")
new_cols = []
for c in df.columns:
    # Remove acentos, espaços e deixa maiúsculo (ex: 'Descrição' -> 'DESCRICAO')
    clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
    new_cols.append(clean)
df.columns = new_cols

# Mapeamento para nomes mais amigáveis no Banco
mapa_banco = {
    'AIH': 'aih',
    'ADMISSAO': 'data_admissao',
    'SAIDA': 'data_saida',
    'PROCEDIMENTO': 'procedimento_cod',
    'DESCRICAO_DO_PROCEDIMENTO': 'procedimento_desc',
    'COMPETENCIA': 'competencia',
    'VALOR_TOTAL': 'valor_total',
    'MOTIVO_SAIDA': 'motivo_saida',
    'CAR_INT_DESC': 'carater',
    'VALOR_SH': 'valor_sh',
    'VALOR_SP': 'valor_sp',
    'QT_DIARIAS': 'diarias'
}

# Seleciona só as colunas que conseguimos mapear (para não sujar o banco)
colunas_validas = [c for c in mapa_banco.keys() if c in df.columns]
df_db = df[colunas_validas].rename(columns=mapa_banco)

# --- TRATAMENTO DE DADOS ---
print(">> Formatando dados...")

# 1. Datas (De DD/MM/YY para YYYY-MM-DD)
cols_data = ['data_admissao', 'data_saida', 'competencia']
for col in cols_data:
    if col in df_db.columns:
        df_db[col] = pd.to_datetime(df_db[col], dayfirst=True, errors='coerce')

# 2. Valores Numéricos (Trocar vírgula por ponto, se houver)
cols_valor = ['valor_total', 'valor_sh', 'valor_sp']
for col in cols_valor:
    if col in df_db.columns:
        df_db[col] = df_db[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_db[col] = pd.to_numeric(df_db[col], errors='coerce').fillna(0)

# 3. Remover duplicatas de AIH (Garante integridade da Chave Primária)
df_db = df_db.drop_duplicates(subset=['aih'], keep='last')

# --- SALVAR NO POSTGRESQL ---
print(">> Salvando na tabela 'faturamento_producao'...")
df_db.to_sql('faturamento_producao', engine, if_exists='replace', index=False)

# --- DEFINIR CHAVE PRIMÁRIA (A Mágica do SQL) ---
print(">> Configurando Chave Primária (AIH)...")
with engine.connect() as conn:
    conn.execute(text("COMMIT")) # Necessário para alterar estrutura
    try:
        # Define AIH como PRIMARY KEY (Isso torna ela o ID oficial)
        conn.execute(text("ALTER TABLE faturamento_producao ADD PRIMARY KEY (aih);"))
        print("✅ Chave Primária definida com sucesso!")
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível definir PK (talvez duplicatas?): {e}")

print(f"✅ SUCESSO! {len(df_db)} registros importados.")
print("   A tabela 'faturamento_producao' está pronta para ser cruzada com o SISREG.")