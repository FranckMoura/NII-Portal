import sqlite3
import pandas as pd
import os
import glob
from unidecode import unidecode 

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
ARQUIVO_DB = os.path.join(PASTA_PROJETO, "dados_sisreg.db")

print("--- ATUALIZANDO BANCO INDICASUS (V6 - LEITOR UNIVERSAL) ---")

# Procura qualquer arquivo Indicasus (seja xls ou csv)
padrao = os.path.join(PASTA_PROJETO, "arquivos", "*Indicasus*.*")
arquivos = glob.glob(padrao)

if not arquivos:
    print("❌ ERRO: Nenhum arquivo Indicasus encontrado na pasta 'arquivos'.")
    exit()

# Pega o mais recente
arquivo_alvo = max(arquivos, key=os.path.getmtime)
print(f"   -> Lendo: {os.path.basename(arquivo_alvo)}")

conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS indicasus")
cursor.execute('''
    CREATE TABLE indicasus (
        paciente TEXT,
        cns TEXT,
        data_internacao TEXT,
        municipio TEXT,
        tipo_leito TEXT,
        nome_leito TEXT,
        evolucao TEXT,
        aih TEXT
    )
''')
conn.commit()

try:
    df = None
    
    # 1. TENTATIVA EXCEL (XLS/XLSX)
    if arquivo_alvo.lower().endswith(('.xls', '.xlsx')):
        try:
            print("   -> Tentando ler como Excel...")
            df = pd.read_excel(arquivo_alvo)
        except:
            print("   ⚠️ Falha ao ler como Excel real. Pode ser HTML disfarçado.")
            try:
                # Tenta ler como HTML (comum em sistemas do governo)
                tabelas = pd.read_html(arquivo_alvo, decimal=',', thousands='.')
                df = tabelas[0] # Pega a primeira tabela
            except Exception as e:
                print(f"   ⚠️ Falha ao ler como HTML: {e}")

    # 2. TENTATIVA CSV (Se as anteriores falharem ou for .csv)
    if df is None:
        print("   -> Tentando ler como CSV...")
        try:
            df = pd.read_csv(arquivo_alvo, sep=';', encoding='latin-1', on_bad_lines='skip')
        except:
            df = pd.read_csv(arquivo_alvo, sep=',', encoding='utf-8', on_bad_lines='skip')

    # Limpa colunas
    df.columns = [unidecode(str(c).strip().lower()) for c in df.columns]
    
    # Mapeamento
    df_final = pd.DataFrame()
    
    def get_col(termos):
        for col in df.columns:
            if all(t in col for t in termos): return df[col]
        return "-"

    df_final['paciente'] = get_col(['nome', 'paciente'])
    df_final['cns'] = get_col(['cartao', 'nacional'])
    df_final['data_internacao'] = get_col(['data', 'internacao'])
    df_final['municipio'] = get_col(['municipio'])
    df_final['tipo_leito'] = get_col(['tipo', 'leito'])
    df_final['nome_leito'] = get_col(['identificacao', 'leito'])
    df_final['evolucao'] = get_col(['evolucao'])
    df_final['aih'] = get_col(['aih'])

    # Tratamento de Data
    df_final['data_internacao'] = pd.to_datetime(df_final['data_internacao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
    df_final = df_final.fillna("-")
    
    df_final.to_sql('indicasus', conn, if_exists='append', index=False)
    print(f"✅ Sucesso! {len(df_final)} registros importados.")

except Exception as e:
    print(f"❌ Erro fatal: {e}")

conn.close()