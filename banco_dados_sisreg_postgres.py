import pandas as pd
import glob
import os
import json
import time
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- 2. PROCESSAMENTO: CSV -> POSTGRESQL -> JSON (V47 - DIAGNÓSTICO E CORREÇÃO) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123"  # <--- SUA SENHA
HOST_DB = "localhost"
NOME_DB = "nii_portal"

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")
CAMINHO_PARQUET = os.path.join(PASTA_ARQUIVOS, "base_sisreg.parquet")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# --- CONEXÃO COM O BANCO ---
try:
    url_inicial = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/postgres"
    engine_temp = create_engine(url_inicial, isolation_level="AUTOCOMMIT")
    with engine_temp.connect() as conn:
        res = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{NOME_DB}'"))
        if not res.fetchone():
            print(f"   Criando banco de dados '{NOME_DB}'...")
            conn.execute(text(f"CREATE DATABASE {NOME_DB}"))
    
    url_final = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
    engine = create_engine(url_final)
except Exception as e:
    print(f"❌ Erro fatal no Banco de Dados: {e}")
    exit()

# --- LEITURA DOS CSVs ---
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
        
        new_cols = []
        for c in df.columns:
            clean = unidecode(str(c)).strip().upper().replace(' ', '_').replace('.', '').replace('/', '')
            if "SOLICITAA" in clean: clean = clean.replace("SOLICITAA§A£O", "SOLICITACAO")
            new_cols.append(clean)
        df.columns = new_cols
        dfs.append(df)
    except: pass

if not dfs: exit()
df_total = pd.concat(dfs, ignore_index=True)

# --- ETL ---
mapa = {
    'DATA_DA_SOLICITACAO': 'data_visual', 'NOME_DO_PACIENTE': 'paciente',
    'CNS_DO_PACIENTE': 'cns', 'N_DA_SOLICITACAO': 'num_sol',
    'N_AIH': 'aih', 'NOME_DO_PROCEDIMENTO_SOLICITADO': 'proc',
    'STATUS_DA_SOLICITACAO_DE_INTERNACAO': 'status', 'CARATER_INTERNACAO': 'carater'
}
cols = [c for c in mapa.keys() if c in df_total.columns]
df_db = df_total[cols].rename(columns=mapa)

df_db = df_db.drop_duplicates(subset=['num_sol'], keep='first')
df_db['data_obj'] = pd.to_datetime(df_db['data_visual'], dayfirst=True, errors='coerce')
df_db['data_iso'] = df_db['data_obj'].dt.strftime('%Y-%m-%d').fillna("1900-01-01")
df_db = df_db.drop(columns=['data_obj'])
df_db = df_db.fillna("-")

# --- CARGA NO BANCO ---
print("   -> Salvando no PostgreSQL...")
df_db.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)

# --- RESGATE E INTEGRAÇÃO DOS LINKS ---
print("   -> Lendo JSON anterior para resgatar links...")

def normalizar_aih(valor):
    """Remove tudo que não for número."""
    if not valor: return ""
    return "".join(filter(str.isdigit, str(valor)))

links_map = {}
if os.path.exists(CAMINHO_JSON):
    try:
        with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
            dados_antigos = json.load(f)
        
        count_validos = 0
        for item in dados_antigos:
            aih_limpa = normalizar_aih(item.get('aih'))
            link_pdf = item.get('arquivo_pdf')
            
            # Só guarda se tiver AIH e Link válidos
            if aih_limpa and len(aih_limpa) > 5 and link_pdf:
                links_map[aih_limpa] = link_pdf
                count_validos += 1
        
        print(f"      Links recuperados da memória: {count_validos}")
        if count_validos > 0:
            exemplo_chave = list(links_map.keys())[0]
            print(f"      [DEBUG] Exemplo de AIH no JSON: '{exemplo_chave}' -> '{links_map[exemplo_chave]}'")
            
    except Exception as e:
        print(f"      ⚠️ Erro ao ler JSON antigo: {e}")
else:
    print("      ⚠️ Arquivo JSON antigo não encontrado (primeira execução?).")

# Lê dados novos do banco
df_final = pd.read_sql("SELECT * FROM sisreg_solicitacoes ORDER BY data_iso DESC", engine)

# Aplica os links
def aplicar_link(row):
    aih_banco = normalizar_aih(row.get('aih'))
    if aih_banco in links_map:
        return links_map[aih_banco]
    return None

df_final['arquivo_pdf'] = df_final.apply(aplicar_link, axis=1)

# Estatísticas
total_links = df_final['arquivo_pdf'].notna().sum()
print(f"   -> Integração Final: {total_links} registros ficaram com PDF associado.")

# Diagnóstico se deu 0
if total_links == 0 and len(links_map) > 0:
    print("      [ALERTA] NENHUM LINK FOI APLICADO! Verificando divergência...")
    aih_banco_exemplo = normalizar_aih(df_final.iloc[0]['aih'])
    print(f"      [DEBUG] Exemplo AIH no Banco: '{aih_banco_exemplo}'")
    print(f"      [DEBUG] Exemplo AIH no Mapa:  '{list(links_map.keys())[0]}'")

# Salva
df_final.to_json(CAMINHO_JSON, orient='records', indent=4, force_ascii=False)

try:
    df_final.to_parquet(CAMINHO_PARQUET, index=False)
except: pass

print(f"✅ SUCESSO! Base atualizada com {len(df_final)} registros.")