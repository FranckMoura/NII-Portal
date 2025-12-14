import pandas as pd
import duckdb
import os
import glob
from unidecode import unidecode 

# --- CONFIGURAÇÕES ---
print(f"--- 2. INICIANDO PROCESSAMENTO DE DADOS (V22) ---")
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
ARQUIVO_PARQUET = os.path.join(PASTA_ARQUIVOS, "base_sisreg.parquet")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# Pega CSVs
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
arquivos_sisreg = [f for f in arquivos if "2311682" in f or "SISREG" in f]

if not arquivos_sisreg:
    print("❌ Nenhum arquivo CSV encontrado na pasta de Exportação.")
    exit()

print(f"   -> Lendo {len(arquivos_sisreg)} arquivos CSV...")
dfs = []

for arq in arquivos_sisreg:
    try:
        # Tenta UTF-8 primeiro (Seu arquivo novo é UTF-8)
        try:
            df = pd.read_csv(arq, sep=';', encoding='utf-8', dtype=str, on_bad_lines='skip')
        except:
            df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
            
        # Limpeza de cabeçalho
        df.columns = [unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '') for c in df.columns]
        dfs.append(df)
    except: pass

if not dfs: 
    print("❌ Erro ao ler arquivos.")
    exit()

df_total = pd.concat(dfs, ignore_index=True)

# --- MAPEAMENTO (Baseado no seu arquivo 20251214) ---
df_final = pd.DataFrame()
def get_col(nome, df):
    if nome in df.columns: return df[nome]
    return "-"

df_final['data_visual'] = get_col('DATA_DA_SOLICITACAO', df_total)
df_final['paciente'] = get_col('NOME_DO_PACIENTE', df_total)
df_final['cns'] = get_col('CNS_DO_PACIENTE', df_total)
df_final['num_sol'] = get_col('N_DA_SOLICITACAO', df_total) 
df_final['aih'] = get_col('N_AIH', df_total)
df_final['proc'] = get_col('NOME_DO_PROCEDIMENTO_SOLICITADO', df_total)
df_final['status'] = get_col('STATUS_DA_SOLICITACAO_DE_INTERNACAO', df_total) # Campo vital
df_final['carater'] = get_col('CARATER_INTERNACAO', df_total)

# Remove Duplicatas de Solicitação
df_final = df_final.drop_duplicates(subset=['num_sol'], keep='first')

# Formatação
print("   -> Formatando datas e números...")
df_final['data_obj'] = pd.to_datetime(df_final['data_visual'], dayfirst=True, errors='coerce')
df_final['data_iso'] = df_final['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
df_final = df_final.sort_values(by='data_iso', ascending=False)
df_final = df_final.drop(columns=['data_obj'])

df_final = df_final.fillna("-")
for col in ['cns', 'num_sol', 'aih']:
    df_final[col] = df_final[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '-')

# Salvar
duckdb.sql("COPY df_final TO '{}' (FORMAT PARQUET, CODEC 'ZSTD')".format(ARQUIVO_PARQUET.replace('\\', '/')))
print(f"✅ Sucesso! Base de dados atualizada com {len(df_final)} registros.")