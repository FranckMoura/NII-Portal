import sqlite3
import pandas as pd
import os
import glob
from unidecode import unidecode 

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
ARQUIVO_DB = os.path.join(PASTA_PROJETO, "dados_sisreg.db")

print("--- ATUALIZANDO BANCO DE DADOS (INDICASUS V4 - FINAL) ---")

# 1. Localizar o arquivo CSV do IndicaSUS
padrao = os.path.join(PASTA_PROJETO, "*Indicasus*.csv")
arquivos = glob.glob(padrao)

if not arquivos:
    print("❌ ERRO: Nenhum arquivo CSV do IndicaSUS encontrado.")
    print("   Dica: Salve o arquivo na pasta do projeto como 'Indicasus.csv'.")
    exit()

# Pega o mais recente
arquivo_alvo = max(arquivos, key=os.path.getmtime)
print(f"   -> Lendo arquivo: {os.path.basename(arquivo_alvo)}")

conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()

# 2. Recriar Tabela
cursor.execute("DROP TABLE IF EXISTS indicasus")
cursor.execute('''
    CREATE TABLE indicasus (
        paciente TEXT,
        cns TEXT,
        data_internacao TEXT,
        data_evolucao TEXT,
        municipio TEXT,
        tipo_leito TEXT,
        nome_leito TEXT,
        evolucao TEXT,
        aih TEXT
    )
''')
conn.commit()

try:
    # 3. Leitura Blindada (Codificação do Excel)
    try:
        # Tenta o padrão do Windows/Excel Brasil
        df = pd.read_csv(arquivo_alvo, sep=',', encoding='latin-1', dtype=str, on_bad_lines='skip')
    except:
        # Se falhar, tenta UTF-8
        df = pd.read_csv(arquivo_alvo, sep=',', encoding='utf-8', dtype=str, on_bad_lines='skip')

    # Normaliza nomes das colunas para evitar erro de maiúscula/minúscula
    # Ex: "Nome do Paciente" vira "nomedopaciente"
    df.columns = [unidecode(c.strip().lower().replace(' ', '')) for c in df.columns]
    
    # 4. Mapeamento Direto (Baseado no seu arquivo)
    df_final = pd.DataFrame()
    
    # Busca colunas flexíveis
    def get_col(termos):
        for col in df.columns:
            if all(t in col for t in termos): return df[col]
        return "-"

    df_final['paciente'] = get_col(['nome', 'paciente'])
    df_final['cns'] = get_col(['cartao', 'nacional']) # Cartão Nacional do SUS
    df_final['data_internacao'] = get_col(['data', 'internacao'])
    df_final['data_evolucao'] = get_col(['data', 'evolucao'])
    df_final['municipio'] = get_col(['municipio'])
    df_final['tipo_leito'] = get_col(['tipo', 'leito'])
    df_final['nome_leito'] = get_col(['identificacao', 'leito'])
    df_final['evolucao'] = get_col(['evolucao', 'quadro'])
    df_final['aih'] = get_col(['numero', 'aih']) # Número AIH

    # 5. Tratamento de Dados
    # Converte Data (DD/MM/AAAA -> YYYY-MM-DD) para ordenação
    df_final['data_internacao'] = pd.to_datetime(df_final['data_internacao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
    df_final = df_final.fillna("-")

    # Salva
    df_final.to_sql('indicasus', conn, if_exists='append', index=False)
    print(f"✅ Sucesso! {len(df_final)} registros importados para o banco.")

except Exception as e:
    print(f"❌ Erro ao ler CSV: {e}")

conn.close()