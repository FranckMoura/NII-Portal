import pandas as pd
from supabase import create_client, Client
import math

# 1. Configurações de Conexão com o Supabase
URL = "https://voweywtzoldwfhgkniup.supabase.co"
# Usando sua service_role_key para garantir permissão de inserção
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

supabase: Client = create_client(URL, KEY)

print("Lendo a planilha do Excel...")
# 2. Lê os dados
df = pd.read_excel('procedimentos_contrato.xlsx')

# 3. Limpeza Bruta
# Garante 10 dígitos no código
df['CODIGO'] = df['CODIGO'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(10)
# Limpa as descrições
df['DESCRICAO DO PROCEDIMENTO'] = df['DESCRICAO DO PROCEDIMENTO'].astype(str).str.replace('\n', ' ', regex=False)
# Trata valores vazios na meta física
df['Físico Mês'] = df['Físico Mês'].fillna(0).astype(int)

print("Agrupando duplicatas para evitar o Erro 23505...")
# 4. O SEGREDO: Agrupar SOMENTE pelo código. 
# Ele pega a primeira descrição que encontrar e soma todas as metas físicas desse código.
df_agrupado = df.groupby('CODIGO').agg({
    'DESCRICAO DO PROCEDIMENTO': 'first',
    'Físico Mês': 'sum'
}).reset_index()

# 5. Prepara os dados para o Supabase (formato de dicionário JSON)
records = []
for index, row in df_agrupado.iterrows():
    records.append({
        "codigo": row['CODIGO'],
        "descricao": row['DESCRICAO DO PROCEDIMENTO'],
        "meta_fisica": int(row['Físico Mês'])
    })

print(f"Iniciando envio de {len(records)} procedimentos únicos para o Supabase...")

# 6. Envia os dados em lotes (batch) para não sobrecarregar a rede
batch_size = 100
for i in range(0, len(records), batch_size):
    batch = records[i : i + batch_size]
    # Faz o Insert no Supabase
    data, count = supabase.table('procedimentos_contrato').insert(batch).execute()
    print(f"Lote {i} a {i + len(batch)} enviado com sucesso!")

print("✅ Upload finalizado! Pode ir para o Passo 3 no Supabase.")