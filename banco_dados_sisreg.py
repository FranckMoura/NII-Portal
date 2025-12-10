import pandas as pd
import duckdb
import os
import glob
from unidecode import unidecode 

# --- CONFIGURAÇÕES ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
ARQUIVO_PARQUET = os.path.join(PASTA_ARQUIVOS, "base_sisreg.parquet")

print("--- PROCESSAMENTO SISREG (V21 - REMOVEDOR DE DUPLICATAS) ---")

if not os.path.exists(PASTA_ARQUIVOS):
    os.makedirs(PASTA_ARQUIVOS)

# Filtra arquivos
todos_csvs = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
arquivos_sisreg = [f for f in todos_csvs if "2311682" in os.path.basename(f) or "SISREG" in os.path.basename(f)]

if not arquivos_sisreg:
    print("❌ Nenhum arquivo do SISREG encontrado.")
    exit()

print(f"   -> Lendo {len(arquivos_sisreg)} arquivos da pasta...")

dfs = []

for arq in arquivos_sisreg:
    try:
        # Tenta UTF-8 (Prioridade)
        try:
            df = pd.read_csv(arq, sep=';', encoding='utf-8', dtype=str, on_bad_lines='skip')
        except:
            # Fallback Latin-1
            df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')

        # Limpeza de cabeçalho
        df.columns = [unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '') for c in df.columns]
        dfs.append(df)
    except Exception as e:
        pass

if not dfs: exit()

df_total = pd.concat(dfs, ignore_index=True)

# --- MAPEAMENTO ---
df_final = pd.DataFrame()

def pegar(nome):
    if nome in df_total.columns: return df_total[nome]
    return "-"

# Nomes exatos
df_final['data_visual'] = pegar('DATA_DA_SOLICITACAO')
df_final['paciente'] = pegar('NOME_DO_PACIENTE')
df_final['cns'] = pegar('CNS_DO_PACIENTE')
df_final['num_sol'] = pegar('N_DA_SOLICITACAO') 
df_final['aih'] = pegar('N_AIH')                
df_final['proc'] = pegar('NOME_DO_PROCEDIMENTO_SOLICITADO')
df_final['status'] = pegar('STATUS_DA_SOLICITACAO_DE_INTERNACAO') 
df_final['carater'] = pegar('CARATER_INTERNACAO')

# --- FAXINA DE DUPLICATAS (O PULO DO GATO) ---
qtd_antes = len(df_final)
print(f"   -> Registros brutos lidos: {qtd_antes}")

# Remove linhas onde o 'num_sol' é igual (mantém a primeira que aparecer)
# Ignora linhas onde num_sol é traço ou vazio para não apagar dados sem ID
mask_validos = (df_final['num_sol'] != "-") & (df_final['num_sol'].notna())
df_validos = df_final[mask_validos].drop_duplicates(subset=['num_sol'], keep='first')
df_invalidos = df_final[~mask_validos] # Mantém os sem número por segurança (se houver)

df_final = pd.concat([df_validos, df_invalidos])
qtd_depois = len(df_final)

print(f"   -> 🧹 DUPLICATAS REMOVIDAS: {qtd_antes - qtd_depois}")
print(f"   -> Registros únicos finais: {qtd_depois}")

# --- TRATAMENTOS ---
print("   -> Formatando e Salvando...")

df_final['data_obj'] = pd.to_datetime(df_final['data_visual'], dayfirst=True, errors='coerce')
df_final['data_iso'] = df_final['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
df_final = df_final.sort_values(by='data_iso', ascending=False)
df_final = df_final.drop(columns=['data_obj'])

df_final = df_final.fillna("-")
for col in ['cns', 'num_sol', 'aih']:
    df_final[col] = df_final[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '-')

# Salvar
duckdb.sql("COPY df_final TO '{}' (FORMAT PARQUET, CODEC 'ZSTD')".format(ARQUIVO_PARQUET.replace('\\', '/')))
print(f"✅ Sucesso! Base atualizada.")