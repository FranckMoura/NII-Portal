import pandas as pd
import os
from supabase import create_client

print("--- RESTAURADOR DE DADOS SUPABASE ---")
print("⚠️ ATENÇÃO: Isso vai INSERIR dados no banco.")

# CONFIG
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

# QUAL TABELA RESTAURAR?
NOME_TABELA = "historico_aih" 
ARQUIVO_CSV = "backups/backup_2026-02-17_.../banco_de_dados/historico_aih.csv" # <--- Aponte para o arquivo certo

try:
    supabase = create_client(SB_URL, SB_KEY)
    
    if not os.path.exists(ARQUIVO_CSV):
        print(f"❌ Arquivo não encontrado: {ARQUIVO_CSV}")
        exit()

    print(f"📖 Lendo {ARQUIVO_CSV}...")
    df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='utf-8-sig')
    
    # Converte para lista de dicionários (formato JSON)
    # Trata valores NaN como None (null no banco)
    dados = df.where(pd.notnull(df), None).to_dict('records')
    
    print(f"🚀 Enviando {len(dados)} registros para '{NOME_TABELA}'...")
    
    # Envia em lotes de 100 para não travar
    lote = 100
    for i in range(0, len(dados), lote):
        chunk = dados[i:i+lote]
        supabase.table(NOME_TABELA).upsert(chunk).execute()
        print(f"   Pacote {i} a {i+len(chunk)} enviado.")

    print("\n✅ RESTAURAÇÃO CONCLUÍDA!")

except Exception as e:
    print(f"❌ Erro: {e}")