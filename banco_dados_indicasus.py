import sqlite3
import pandas as pd
import os
import glob
from unidecode import unidecode 

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1" # Caminho absoluto para garantir
ARQUIVO_DB = os.path.join(PASTA_PROJETO, "dados_sisreg.db")

print("--- ATUALIZANDO BANCO DE DADOS (INDICASUS V2) ---")

# Procura o arquivo CSV do Indicasus automaticamente
padrao_arquivo = os.path.join(PASTA_PROJETO, "*Indicasus*.csv")
arquivos_encontrados = glob.glob(padrao_arquivo)

if not arquivos_encontrados:
    print(f"❌ ERRO: Nenhum arquivo CSV com 'Indicasus' no nome foi encontrado na pasta.")
    exit()

# Pega o arquivo mais recente se tiver mais de um
arquivo_csv = max(arquivos_encontrados, key=os.path.getmtime)
print(f"   -> Processando arquivo: {os.path.basename(arquivo_csv)}")

conn = sqlite3.connect(ARQUIVO_DB)
cursor = conn.cursor()

# Recria a tabela
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
    # Tenta ler com diferentes codificações (UTF-8 ou Latin-1)
    try:
        df = pd.read_csv(arquivo_csv, sep=',', encoding='utf-8', dtype=str)
    except UnicodeDecodeError:
        print("   ⚠️ Codificação UTF-8 falhou. Tentando Latin-1 (Excel)...")
        df = pd.read_csv(arquivo_csv, sep=',', encoding='latin-1', dtype=str)
    
    # Normaliza nomes das colunas (remove acentos, espaços e deixa minúsculo)
    df.columns = [unidecode(c.strip().lower()) for c in df.columns]
    
    # Debug: Mostra colunas encontradas para conferência
    # print(f"Colunas no arquivo: {list(df.columns)}")

    df_final = pd.DataFrame()
    
    # Mapeamento Seguro (Usa .get para não quebrar se a coluna mudar de nome)
    # Ajustei os nomes baseado no padrão comum do Indicasus
    df_final['paciente'] = df.get('nome do paciente', df.get('paciente', '-'))
    df_final['cns'] = df.get('cartao nacional do sus', df.get('cns', '-'))
    df_final['data_internacao'] = df.get('data da internacao', '-')
    df_final['data_evolucao'] = df.get('data da evolucao', df.get('data evolucao', '-'))
    df_final['municipio'] = df.get('municipio de residencia', df.get('municipio', '-'))
    df_final['tipo_leito'] = df.get('tipo de leito', '-')
    df_final['nome_leito'] = df.get('identificacao dos leitos', df.get('leito', '-'))
    df_final['evolucao'] = df.get('evolucao do quadro clinico', df.get('evolucao', 'Internado'))
    df_final['aih'] = df.get('numero aih', df.get('aih', '-'))

    # Tratamento de Datas (Converte para YYYY-MM-DD para o banco e ordenação)
    # Se der erro na conversão, deixa vazio
    df_final['data_internacao'] = pd.to_datetime(df_final['data_internacao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
    
    # Preenche nulos
    df_final = df_final.fillna("-")
    
    # Salva
    df_final.to_sql('indicasus', conn, if_exists='append', index=False)
    
    print(f"✅ Sucesso! {len(df_final)} internações importadas.")

except Exception as e:
    print(f"❌ Erro grave ao processar CSV: {e}")

conn.close()