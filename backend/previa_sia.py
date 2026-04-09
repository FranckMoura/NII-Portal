import os
import pandas as pd
from dbfread import DBF
import datasus_dbc

print("--- 🔍 RAIO-X DATASUS: LENDO ARQUIVO PAMT0001.dbc ---")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(BASE_DIR, "bases_pamt_brutas") 

# Vamos investigar o primeiro ficheiro do ano 2000
arquivo_dbc = os.path.join(PASTA_ORIGEM, "PAMT0001.dbc")

if not os.path.exists(arquivo_dbc):
    # Tenta com letra maiúscula caso o Windows tenha salvo assim
    arquivo_dbc = os.path.join(PASTA_ORIGEM, "PAMT0001.DBC")

if not os.path.exists(arquivo_dbc):
    print("❌ Ficheiro PAMT0001.dbc não encontrado na pasta.")
else:
    arquivo_dbf = arquivo_dbc.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
    
    try:
        # Descomprime e lê
        datasus_dbc.decompress(arquivo_dbc, arquivo_dbf)
        dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
        df = pd.DataFrame(iter(dbf))
        
        # Apaga o temporário
        if os.path.exists(arquivo_dbf):
            os.remove(arquivo_dbf)

        print("\n📋 1. LISTA EXATA DE COLUNAS NESTE ARQUIVO:")
        print("--------------------------------------------------")
        colunas = df.columns.tolist()
        print(colunas)
        
        print("\n👁️ 2. PRÉVIA DOS DADOS (Primeiras 5 linhas):")
        print("--------------------------------------------------")
        # Mostrar todas as colunas lado a lado
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df.head(5))
        
        # Procura colunas suspeitas que possam ser o Hospital
        print("\n🕵️ 3. DIAGNÓSTICO DO ANALISTA:")
        colunas_suspeitas = [c for c in colunas if "CGC" in c or "CNPJ" in c or "CNES" in c or "HOSP" in c or "ESTAB" in c or "COD" in c]
        print(f"Colunas que podem identificar o Hospital Santa Helena: {colunas_suspeitas}")

    except Exception as e:
        print(f"❌ Erro ao ler o ficheiro: {e}")