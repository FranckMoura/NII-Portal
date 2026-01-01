import pandas as pd
import glob
import os
import json
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO DE DADOS TABNET V2 (COM DATAS ISO) ---")

# --- CONFIGURAÇÕES ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

engine = create_engine(f"sqlite:///{CAMINHO_DB}")

# Mapa de meses para converter "Jan" -> "01"
MESES_MAPA = {
    'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06',
    'Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'
}

def limpar_numero(valor):
    """Converte '1.234,56' para float 1234.56"""
    if pd.isna(valor) or str(valor).strip() in ['-', '']: return 0.0
    try:
        return float(str(valor).replace('.', '').replace(',', '.'))
    except: return 0.0

def converter_data(texto_periodo):
    """Converte 'Jan/2024' ou 'Jan-2024' para '2024-01-01'"""
    try:
        texto = texto_periodo.replace("/", "-").strip()
        mes_txt, ano = texto.split("-")
        mes_num = MESES_MAPA.get(mes_txt, "01")
        return f"{ano}-{mes_num}-01"
    except:
        return None

# --- 1. LEITURA ---
print(f">> Lendo arquivos na pasta: {PASTA_CSV}...")
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
dfs = []

if not arquivos:
    print("❌ Nenhum arquivo CSV encontrado! Verifique a pasta.")
    exit()

print(f"   Encontrados {len(arquivos)} arquivos. Processando...")

for i, arq in enumerate(arquivos):
    try:
        # Pula cabeçalho inútil do TabNet (procura onde começa 'Procedimento')
        with open(arq, 'r', encoding='latin-1') as f:
            linhas = f.readlines()
        
        inicio = 0
        for idx, linha in enumerate(linhas):
            if "Procedimento" in linha:
                inicio = idx
                break
        
        # Lê o CSV
        df = pd.read_csv(arq, sep=';', encoding='latin-1', skiprows=inicio, on_bad_lines='skip')
        
        # Remove rodapé (linhas com 'Total', 'Fonte', etc)
        df = df[~df.iloc[:,0].astype(str).str.contains("Total|Fonte|Notas|Legenda", case=False, na=False)]
        
        # Pega a data do nome do arquivo (ex: ..._Jan-2008.csv)
        nome = os.path.basename(arq).replace(".csv", "")
        periodo_txt = nome.split("_")[-1] # Pega a última parte
        
        # Cria colunas novas
        df['competencia_txt'] = periodo_txt
        df['data_iso'] = converter_data(periodo_txt)
        
        # Normaliza nomes de colunas
        df.columns = [unidecode(c.strip().lower()) for c in df.columns]
        
        dfs.append(df)
        
        if (i+1) % 50 == 0: print(f"   ... processados {i+1} arquivos")
        
    except Exception as e:
        print(f"   ⚠️ Erro em {os.path.basename(arq)}: {e}")

# --- 2. CONSOLIDAÇÃO ---
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    
    # Renomear colunas para padrão do banco
    mapa_cols = {
        'procedimento': 'procedimento',
        'aih_aprovadas': 'qtd_aih',
        'valor_total': 'valor',
        'dias_permanencia': 'dias',
        'obitos': 'obitos',
        'taxa_mortalidade': 'taxa_mortalidade',
        'competencia_txt': 'periodo',
        'data_iso': 'data'
    }
    # Filtra só as colunas que existem
    cols_para_renomear = {k: v for k,v in mapa_cols.items() if k in df_final.columns}
    df_final.rename(columns=cols_para_renomear, inplace=True)
    
    # Limpa números
    cols_num = ['qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade']
    for c in cols_num:
        if c in df_final.columns:
            df_final[c] = df_final[c].apply(limpar_numero)
            
    # Ordena por data (Antigo -> Novo)
    df_final.sort_values(by='data', inplace=True)

    # --- 3. SALVAR ---
    print(">> Salvando no Banco de Dados SQLite...")
    df_final.to_sql('historico_producao', engine, if_exists='replace', index=False)
    
    print(">> Gerando JSON para o Portal...")
    df_final.to_json(CAMINHO_JSON, orient='records', force_ascii=False, indent=4)
    
    print(f"✅ SUCESSO! {len(df_final)} registros processados de 2008 a 2025.")
    print(f"   Arquivo JSON gerado em: {CAMINHO_JSON}")
else:
    print("❌ Falha crítica: Nenhum dado foi processado.")