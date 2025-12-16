import pandas as pd
import os
import io
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- IMPORTAÇÃO DE FATURAMENTO V3 (REPARO DE CODIFICAÇÃO) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123"  # <--- SUA SENHA AQUI
HOST_DB = "localhost"
NOME_DB = "nii_portal"
ARQUIVO_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\pDetAIH.csv"

# --- CONEXÃO ---
url_db = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_db)

if not os.path.exists(ARQUIVO_CSV):
    print("❌ Arquivo não encontrado.")
    exit()

# --- 1. DESCOBRIR A CODIFICAÇÃO E A LINHA DO CABEÇALHO ---
print(">> Analisando estrutura do arquivo...")

codificacoes_para_tentar = ['utf-8', 'latin-1', 'utf-16', 'cp1252']
df_final = None

for cod in codificacoes_para_tentar:
    try:
        print(f"   Tentando ler como {cod}...")
        # Lê apenas as primeiras linhas para achar o cabeçalho
        with open(ARQUIVO_CSV, 'r', encoding=cod) as f:
            linhas = [f.readline() for _ in range(10)]
            
        header_row = -1
        sep = '\t' # O seu arquivo é separado por TAB
        
        for i, linha in enumerate(linhas):
            # Procura por AIH ou YTH (caso esteja corrompido)
            if "AIH" in linha or "YTH" in linha:
                header_row = i
                print(f"   -> Cabeçalho encontrado na linha {i} usando {cod}!")
                break
        
        if header_row != -1:
            # Tenta carregar o DataFrame inteiro com essa configuração
            df_final = pd.read_csv(ARQUIVO_CSV, sep=sep, header=header_row, encoding=cod, dtype=str, on_bad_lines='skip')
            break # Sucesso! Para o loop.
            
    except Exception as e:
        continue # Tenta a próxima codificação

if df_final is None:
    print("❌ ERRO FATAL: Não foi possível ler o arquivo em nenhuma codificação conhecida.")
    exit()

# --- 2. CORREÇÃO DE NOMES DE COLUNAS ---
print(">> Normalizando colunas...")

# Correção específica para o erro "YTH"
if "YTH" in df_final.columns:
    print("   ⚠️ Corrigindo coluna corrompida: 'YTH' -> 'AIH'")
    df_final.rename(columns={"YTH": "AIH"}, inplace=True)

# Limpeza geral (Caixa alta -> minúscula, sem acentos)
new_cols = []
for c in df_final.columns:
    clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
    new_cols.append(clean)
df_final.columns = new_cols

print(f"   Colunas detectadas: {df_final.columns.tolist()}")

# Verifica se AIH existe agora
if 'AIH' not in df_final.columns:
    print("❌ ERRO: A coluna 'AIH' ainda não foi encontrada. Verifique o arquivo.")
    exit()

# --- 3. PREPARAR DADOS ---
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

colunas_validas = [c for c in mapa_banco.keys() if c in df_final.columns]
df_db = df_final[colunas_validas].rename(columns=mapa_banco)

# Tratamento de valores (R$)
cols_valor = ['valor_total', 'valor_sh', 'valor_sp']
for col in cols_valor:
    if col in df_db.columns:
        df_db[col] = df_db[col].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_db[col] = pd.to_numeric(df_db[col], errors='coerce').fillna(0)

# Datas
cols_data = ['data_admissao', 'data_saida', 'competencia']
for col in cols_data:
    if col in df_db.columns:
        df_db[col] = pd.to_datetime(df_db[col], dayfirst=True, errors='coerce')

# REMOVE DUPLICATAS NA CHAVE (CRUCIAL PARA PRIMARY KEY)
df_db = df_db.drop_duplicates(subset=['aih'], keep='first')
# Remove AIH vazia ou inválida
df_db = df_db[df_db['aih'].notna()]
df_db = df_db[df_db['aih'].str.len() > 5] 

# --- 4. SALVAR NO BANCO ---
print(">> Salvando no PostgreSQL...")
with engine.connect() as conn:
    conn.execute(text("COMMIT"))
    # Drop table para garantir estrutura limpa
    conn.execute(text("DROP TABLE IF EXISTS faturamento_producao CASCADE"))

df_db.to_sql('faturamento_producao', engine, if_exists='replace', index=False)

# --- 5. CRIAR CHAVE ESTRANGEIRA / PRIMÁRIA ---
print(">> Configurando Banco de Dados...")
with engine.connect() as conn:
    conn.execute(text("COMMIT"))
    try:
        # 1. Define AIH como Primary Key na tabela de Faturamento
        conn.execute(text("ALTER TABLE faturamento_producao ADD PRIMARY KEY (aih);"))
        print("✅ PK criada na tabela 'faturamento_producao'.")
        
        # 2. Tenta criar índice na tabela do SISREG para o cruzamento ficar rápido
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sisreg_aih ON sisreg_solicitacoes (aih);"))
        print("✅ Índice criado na tabela 'sisreg_solicitacoes'.")
        
    except Exception as e:
        print(f"⚠️ Erro ao configurar chaves (verifique se há AIHs duplicadas): {e}")

# ... (código anterior) ...

# --- 6. ENRIQUECIMENTO DE DADOS (Trazer Nome do Paciente) ---
print(">> Buscando nomes dos pacientes no SISREG...")
with engine.connect() as conn:
    conn.execute(text("COMMIT"))
    try:
        # 1. Cria a coluna se não existir
        conn.execute(text("ALTER TABLE faturamento_producao ADD COLUMN IF NOT EXISTS paciente VARCHAR(255);"))
        
        # 2. Atualiza os nomes
        sql_update = """
        UPDATE faturamento_producao f
        SET paciente = s.paciente
        FROM sisreg_solicitacoes s
        WHERE f.aih = REPLACE(REPLACE(s.aih, '-', ''), '.', '')
        AND f.paciente IS NULL; -- Só atualiza quem está sem nome
        """
        conn.execute(text(sql_update))
        print("✅ Nomes dos pacientes atualizados no Faturamento!")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar nomes: {e}")

# ... (print final de sucesso) ...

print(f"✅ FINALIZADO! {len(df_db)} registros importados com sucesso.")