import sqlite3
import os
import pandas as pd

NOME_BANCO = "dados_sisreg.db"

print(f"🕵️ --- DIAGNÓSTICO DO BANCO DE DADOS ---")

if not os.path.exists(NOME_BANCO):
    print(f"❌ CRÍTICO: O arquivo '{NOME_BANCO}' NÃO EXISTE na pasta.")
    print("Isso significa que o script 'banco_dados_sisreg.py' nunca rodou com sucesso.")
else:
    print(f"✅ Arquivo '{NOME_BANCO}' encontrado.")
    
    try:
        conn = sqlite3.connect(NOME_BANCO)
        
        # 1. Verifica se a tabela existe
        query_tabelas = "SELECT name FROM sqlite_master WHERE type='table';"
        tabelas = pd.read_sql_query(query_tabelas, conn)
        
        if tabelas.empty:
            print("⚠️ O banco existe, mas está VAZIO (sem tabelas).")
        else:
            print(f"✅ Tabelas encontradas: {tabelas['name'].tolist()}")
            
            # 2. Conta quantos registros tem na tabela 'solicitacoes'
            if 'solicitacoes' in tabelas['name'].values:
                df = pd.read_sql_query("SELECT * FROM solicitacoes", conn)
                qtd = len(df)
                print(f"📊 Total de solicitações gravadas: {qtd}")
                
                if qtd > 0:
                    print("\n--- Amostra dos Dados (Primeira linha) ---")
                    print(df.head(1).T)
                else:
                    print("⚠️ A tabela 'solicitacoes' existe, mas tem 0 linhas.")
            else:
                print("❌ A tabela 'solicitacoes' NÃO foi encontrada.")
                
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao abrir o banco: {e}")

print("\n------------------------------------------------")
print("CONCLUSÃO:")
print("Se deu 0 registros -> O problema é na EXTRAÇÃO (Login, Senha ou Site mudou).")
print("Se tem registros -> O problema é no DASHBOARD (Filtro de data errado).")