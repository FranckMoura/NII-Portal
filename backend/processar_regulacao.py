import os
import pandas as pd
import glob
import time
from datetime import datetime
from supabase import create_client, Client

print("\n--- 🏥 PROCESSADOR DE REGULAÇÃO V16 (UPSERT SEGURO) ---")

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

# Caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOADS = os.path.join(BASE_DIR, "downloads")

# Conexão
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def limpar_dados(df):
    """Padroniza colunas e limpa valores nulos"""
    # De-para de colunas (CSV Sisreg -> Banco Supabase)
    mapa_colunas = {
        'Código': 'num_solicitacao',
        'Data Solicitação': 'data_solicitacao',
        'Data Autorização': 'data_autorizacao',
        'Nome': 'nome_paciente',
        'Paciente': 'nome_paciente', # Sisreg varia as vezes
        'Município': 'municipio_residencia',
        'Procedimento': 'procedimento',
        'Situação': 'status',
        'Status': 'status',
        'Executante': 'nome_clinica',
        'Unidade Executante': 'nome_clinica',
        'CNES Executante': 'cnes_executante',
        'Profissional Solicitante': 'medico_solicitante',
        'Classificação de Risco': 'classificacao_risco',
        'Caráter': 'carater_internacao'
    }
    
    # Renomeia
    df = df.rename(columns=mapa_colunas)
    
    # Remove colunas que não estão no mapa (opcional, para limpar sujeira)
    colunas_validas = list(mapa_colunas.values())
    # Mantém apenas as que existem no DF e no Banco
    cols_existentes = [c for c in df.columns if c in colunas_validas]
    df = df[cols_existentes]

    # Converte datas (dd/mm/aaaa -> aaaa-mm-dd)
    for col_data in ['data_solicitacao', 'data_autorizacao']:
        if col_data in df.columns:
            df[col_data] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce').dt.date.astype(str)
            df[col_data] = df[col_data].replace('NaT', None)

    # Adiciona timestamp de atualização
    df['data_atualizacao'] = datetime.now().isoformat()

    # Limpa NaN do Pandas (o JSON não aceita NaN)
    df = df.where(pd.notnull(df), None)
    
    return df

def processar():
    arquivos = glob.glob(os.path.join(PASTA_DOWNLOADS, "*.csv"))
    
    if not arquivos:
        print("⚠️ Nenhum arquivo CSV encontrado na pasta downloads.")
        return

    todos_dados = []

    for arq in arquivos:
        nome_arq = os.path.basename(arq)
        print(f"Lendo: {nome_arq}...")
        try:
            # Lê CSV (pula a primeira linha que costuma ser cabeçalho do filtro)
            df = pd.read_csv(arq, encoding='latin1', sep=';', skiprows=0, on_bad_lines='skip')
            
            # Se o CSV vier com cabeçalho na linha 2, ajusta
            if 'Código' not in df.columns and 'Solicitação' not in df.columns:
                 df = pd.read_csv(arq, encoding='latin1', sep=';', skiprows=1, on_bad_lines='skip')

            df_limpo = limpar_dados(df)
            
            # Converte para lista de dicionários
            registros = df_limpo.to_dict(orient='records')
            todos_dados.extend(registros)
            
        except Exception as e:
            print(f"❌ Erro ao ler {nome_arq}: {e}")

    # Remove duplicatas locais (se o mesmo ID aparecer em 2 CSVs, pega o último)
    # Isso economiza chamadas de API
    dic_unicos = {d.get('num_solicitacao'): d for d in todos_dados if d.get('num_solicitacao')}
    lista_final = list(dic_unicos.values())

    print(f"Enviando {len(lista_final)} registros únicos...")

    # Envia em Lotes (Batch) para não estourar a API
    TAMANHO_LOTE = 500
    total_enviado = 0

    for i in range(0, len(lista_final), TAMANHO_LOTE):
        lote = lista_final[i : i + TAMANHO_LOTE]
        try:
            # --- AQUI ESTÁ A CORREÇÃO MÁGICA ---
            # upsert: Atualiza se existir, Cria se não existir.
            # on_conflict: Usa a coluna 'num_solicitacao' como chave única.
            
            supabase.table("regulacao").upsert(lote, on_conflict="num_solicitacao").execute()
            
            total_enviado += len(lote)
            print(f"   ✅ Lote {total_enviado}/{len(lista_final)} processado.")
            time.sleep(0.5) # Pausa para respirar
            
        except Exception as e:
            print(f"   ❌ Erro no lote: {e}")
            # Se der erro, tenta um por um (fallback) para não perder o lote todo
            print("      Tentando um por um...")
            for item in lote:
                try:
                    supabase.table("regulacao").upsert(item, on_conflict="num_solicitacao").execute()
                except:
                    pass 

    print("✅ Processamento Concluído!")

if __name__ == "__main__":
    processar()