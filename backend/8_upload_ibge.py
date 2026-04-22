import os
import pandas as pd
from supabase import create_client, Client

print("--- 🚜 ROBÔ DE UPLOAD: CATÁLOGO IBGE (ESTADOS E MUNICÍPIOS) ---")

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try: 
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e: 
    print(f"❌ Erro Conexão Supabase: {e}"); exit()

# Caminhos dos arquivos
PASTA_BACKEND = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend"
ARQUIVO_ESTADOS = os.path.join(PASTA_BACKEND, "estados.csv")
ARQUIVO_MUNICIPIOS = os.path.join(PASTA_BACKEND, "municipios.csv")

def subir_estados():
    if not os.path.exists(ARQUIVO_ESTADOS):
        print(f"⚠️ Arquivo não encontrado: {ARQUIVO_ESTADOS}")
        return
    
    print(">> Processando estados.csv...")
    try:
        # Lemos o CSV com o Pandas
        df = pd.read_csv(ARQUIVO_ESTADOS, encoding='utf-8')
        # Substitui NaN por None (para o banco de dados aceitar)
        df = df.where(pd.notnull(df), None) 
        
        payload = df.to_dict('records')
        
        print(f"   Limpando tabela antiga...")
        try: supabase.table('tb_estados').delete().neq("codigo_uf", 0).execute()
        except: pass
        
        print(f"   Enviando {len(payload)} estados...")
        supabase.table('tb_estados').insert(payload).execute()
        print("✅ tb_estados atualizada com sucesso!\n")
    except Exception as e:
        print(f"❌ Erro na tb_estados: {e}")

def subir_municipios():
    if not os.path.exists(ARQUIVO_MUNICIPIOS):
        print(f"⚠️ Arquivo não encontrado: {ARQUIVO_MUNICIPIOS}")
        return
    
    print(">> Processando municipios.csv...")
    try:
        df = pd.read_csv(ARQUIVO_MUNICIPIOS, encoding='utf-8')
        df = df.where(pd.notnull(df), None)
        
        payload = df.to_dict('records')
        
        print(f"   Limpando tabela antiga...")
        try: supabase.table('tb_municipios').delete().neq("codigo_ibge", 0).execute()
        except: pass
        
        print(f"   Enviando {len(payload)} municípios em lotes...")
        # Envia em lotes de 1000 para não estourar o limite de tempo da API
        for i in range(0, len(payload), 1000):
            lote = payload[i:i+1000]
            supabase.table('tb_municipios').insert(lote).execute()
            print(f"     Lote {i} a {i+len(lote)} enviado.")
            
        print("✅ tb_municipios atualizada com sucesso!\n")
    except Exception as e:
        print(f"❌ Erro na tb_municipios: {e}")

# Executa as funções
subir_estados()
subir_municipios()
print("🎉 Carga do IBGE concluída!")