import pandas as pd
import glob

# Pega o arquivo Excel
arquivos = glob.glob("*.xlsx")
if not arquivos:
    print("Nenhum arquivo Excel encontrado.")
else:
    arquivo = arquivos[0]
    print(f"Lendo arquivo: {arquivo}")
    
    # Lê apenas a aba de Dezembro, sem tentar adivinhar cabeçalho
    try:
        df = pd.read_excel(arquivo, sheet_name='DEZEMBRO 2024', header=None, nrows=10)
        
        print("\n--- AS 10 PRIMEIRAS LINHAS DA PLANILHA (Do jeito que o Python vê) ---")
        # Imprime tudo para a gente ler
        print(df.to_string())
        print("---------------------------------------------------------------------")
    except Exception as e:
        print(f"Erro ao ler a aba: {e}")