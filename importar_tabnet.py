import pandas as pd
import os
from sqlalchemy import create_engine, text
from unidecode import unidecode
import json

print("--- IMPORTAÇÃO TABNET V3 (RIGOROSA) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123" 
HOST_DB = "localhost"
NOME_DB = "nii_portal"

PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
arquivos = [f for f in os.listdir(PASTA_PROJETO) if f.startswith("sih_cnv") and f.endswith(".csv")]

if not arquivos:
    print("❌ Nenhum arquivo do TabNet encontrado.")
    exit()

ARQUIVO_CSV = os.path.join(PASTA_PROJETO, arquivos[0])
print(f"   Arquivo: {ARQUIVO_CSV}")

url_db = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_db)

# --- 1. LEITURA ---
try:
    # Lê tudo como texto (dtype=str) para não perder formatação
    df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin-1', skiprows=3, dtype=str, on_bad_lines='skip')
    if "Ano/mês" not in str(df.columns[0]):
        df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin-1', skiprows=4, dtype=str, on_bad_lines='skip')
except Exception as e:
    print(f"❌ Erro leitura: {e}")
    exit()

# --- 2. FILTRO ANTI-DUPLICIDADE (O SEGREDO) ---
# O TabNet tem linhas "2008", "2009" que são somas. Precisamos remover.
# Apenas linhas que contêm "/" (ex: "Jan/2008") são meses reais.

print(f"   Linhas antes do filtro: {len(df)}")

# Remove aspas da primeira coluna para testar
col_periodo = df.columns[0]
df[col_periodo] = df[col_periodo].str.replace('"', '').str.strip()

# MANTÉM APENAS SE TIVER "/" (Barra)
df = df[df[col_periodo].str.contains('/', na=False)]

print(f"   Linhas após remover totais anuais: {len(df)}")

# --- 3. TRADUÇÃO DE DATAS ---
meses_pt = {
    'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06',
    'Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12',
    'Janeiro': '01', 'Fevereiro': '02', 'Março': '03', 'Abril': '04', 'Maio': '05', 'Junho': '06',
    'Julho': '07', 'Agosto': '08', 'Setembro': '09', 'Outubro': '10', 'Novembro': '11', 'Dezembro': '12'
}

def converter_data(texto):
    try:
        p = texto.split('/')
        mes = meses_pt.get(p[0].capitalize())
        ano = p[1]
        if mes and ano: return f"{ano}-{mes}-01"
    except: pass
    return None

df['data_iso'] = df[col_periodo].apply(converter_data)
df = df[df['data_iso'].notna()] # Garante que só ficou data válida

# --- 4. RENOMEAR COLUNAS ---
cols_novas = []
contagem = {}
for col in df.columns:
    clean = unidecode(str(col)).strip().replace('"', '').lower()
    clean = clean.replace(' ', '_').replace('.', '').replace('/', '_').replace('-', '')
    
    if 'aih_aprov' in clean: nome = 'qtd_aih'
    elif 'internac' in clean: nome = 'internacoes'
    elif 'valor_total' in clean: nome = 'valor_total'
    elif 'media_perm' in clean: nome = 'media_permanencia'
    elif 'mortalidade' in clean: nome = 'taxa_mortalidade'
    elif 'obitos' in clean: nome = 'obitos'
    elif 'iso' in clean: nome = 'data_iso'
    elif 'periodo' in clean or 'ano_mes' in clean: nome = 'periodo_txt' # Força nome padrão
    else: nome = clean[:20]

    if nome in contagem:
        contagem[nome] += 1
        nome = f"{nome}_{contagem[nome]}"
    else: contagem[nome] = 1
    cols_novas.append(nome)

df.columns = cols_novas

# --- 5. LIMPAR NÚMEROS ---
for col in df.columns:
    if col not in ['data_iso', 'periodo_txt']:
        df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# --- 6. SALVAR ---
print(">> Salvando no Banco e JSON...")
df.to_sql('historico_tabnet', engine, if_exists='replace', index=False)

df_ordem = df.sort_values(by='data_iso', ascending=True)
caminho_json = os.path.join(PASTA_PROJETO, "arquivos", "dados_tabnet.json")
df_ordem.to_json(caminho_json, orient='records', force_ascii=False)

print(f"✅ SUCESSO! JSON limpo gerado em: {caminho_json}")