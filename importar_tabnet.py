import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime
import json
from unidecode import unidecode

print("--- IMPORTAÇÃO TABNET V2 (CORREÇÃO DE COLUNAS) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123" # <--- SUA SENHA
HOST_DB = "localhost"
NOME_DB = "nii_portal"

PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
arquivos = [f for f in os.listdir(PASTA_PROJETO) if f.startswith("sih_cnv") and f.endswith(".csv")]

if not arquivos:
    print("❌ Nenhum arquivo do TabNet encontrado.")
    exit()

ARQUIVO_CSV = os.path.join(PASTA_PROJETO, arquivos[0])
print(f"   Arquivo detectado: {ARQUIVO_CSV}")

# --- CONEXÃO ---
url_db = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_db)

# --- 1. LEITURA INTELIGENTE ---
print(">> Lendo e tratando arquivo TabNet...")
try:
    df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin-1', skiprows=3, on_bad_lines='skip')
    if "Ano/mês" not in df.columns[0]:
        df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin-1', skiprows=4, on_bad_lines='skip')
except Exception as e:
    print(f"❌ Erro ao ler CSV: {e}")
    exit()

# Remove a última linha "Total"
df = df[df.iloc[:,0] != "Total"]

# --- 2. TRADUÇÃO DE DATAS ---
meses_pt = {
    'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06',
    'Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12',
    'Janeiro': '01', 'Fevereiro': '02', 'Março': '03', 'Abril': '04', 'Maio': '05', 'Junho': '06',
    'Julho': '07', 'Agosto': '08', 'Setembro': '09', 'Outubro': '10', 'Novembro': '11', 'Dezembro': '12'
}

def converter_data_tabnet(texto):
    try:
        texto = str(texto).replace('"', '').strip()
        if '/' not in texto: return None 
        mes_nome, ano = texto.split('/')
        mes_num = meses_pt.get(mes_nome.capitalize())
        if mes_num: return f"{ano}-{mes_num}-01"
        return None
    except: return None

df['data_iso'] = df.iloc[:, 0].apply(converter_data_tabnet)
df_mensal = df[df['data_iso'].notna()].copy()
print(f"   Linhas processadas: {len(df_mensal)}")

# --- 3. RENOMEAÇÃO E DEDUPLICAÇÃO DE COLUNAS (A CORREÇÃO) ---
print(">> Normalizando nomes das colunas...")
cols_novas = []
contagem_nomes = {}

for col_csv in df_mensal.columns:
    # Limpa o nome
    col_limpa = unidecode(str(col_csv)).strip().replace('"', '').lower()
    col_limpa = col_limpa.replace(' ', '_').replace('.', '').replace('/', '_').replace('-', '')
    
    # Mapeamento manual para os principais
    if 'aih_aprov' in col_limpa: novo_nome = 'qtd_aih'
    elif 'internac' in col_limpa: novo_nome = 'internacoes'
    elif 'valor_total' in col_limpa: novo_nome = 'valor_total'
    elif 'media_perm' in col_limpa: novo_nome = 'media_permanencia'
    elif 'mortalidade' in col_limpa: novo_nome = 'taxa_mortalidade'
    elif 'obitos' in col_limpa: novo_nome = 'obitos'
    elif 'iso' in col_limpa: novo_nome = 'data_iso'
    else: 
        # Encurta nomes muito longos mas mantem o final para diferenciar
        novo_nome = col_limpa[:20] 

    # Lógica de Deduplicação (Se já existe, adiciona _2, _3...)
    if novo_nome in contagem_nomes:
        contagem_nomes[novo_nome] += 1
        novo_nome = f"{novo_nome}_{contagem_nomes[novo_nome]}"
    else:
        contagem_nomes[novo_nome] = 1
    
    cols_novas.append(novo_nome)

df_mensal.columns = cols_novas
print(f"   Colunas finais: {cols_novas}")

# --- 4. TRATAMENTO DE VALORES ---
for col in df_mensal.columns:
    if col != 'data_iso':
        try:
            df_mensal[col] = df_mensal[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_mensal[col] = pd.to_numeric(df_mensal[col], errors='coerce').fillna(0)
        except: pass

# --- 5. SALVAR NO BANCO ---
print(">> Salvando tabela 'historico_tabnet' no Banco...")
df_mensal.to_sql('historico_tabnet', engine, if_exists='replace', index=False)

# --- 6. GERAR JSON ---
print(">> Gerando JSON...")
CAMINHO_JSON = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos\dados_tabnet.json"
df_mensal = df_mensal.sort_values(by='data_iso', ascending=True)
df_mensal.to_json(CAMINHO_JSON, orient='records', force_ascii=False)

print(f"✅ SUCESSO! Histórico TabNet importado.")