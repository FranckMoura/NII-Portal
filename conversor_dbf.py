import pandas as pd
from dbfread import DBF
import os

PASTA = "arquivos"

print("🔄 --- CONVERSOR DBF PARA CSV ---")

if not os.path.exists(PASTA):
    print("❌ Pasta 'arquivos' não encontrada.")
    exit()

arquivos_dbf = [f for f in os.listdir(PASTA) if f.lower().endswith('.dbf')]

if not arquivos_dbf:
    print("⚠️ Nenhum arquivo .dbf encontrado para converter.")
    print("DICA: Use o TabWin para descompactar os .dbc (Menu: Arquivo > Decriptografia).")
else:
    for arquivo in arquivos_dbf:
        caminho_dbf = os.path.join(PASTA, arquivo)
        nome_csv = arquivo.lower().replace('.dbf', '.csv')
        caminho_csv = os.path.join(PASTA, nome_csv)
        
        print(f"   🔨 Convertendo {arquivo}...", end="")
        try:
            # Lê o DBF
            dbf = DBF(caminho_dbf, encoding='iso-8859-1')
            df = pd.DataFrame(iter(dbf))
            
            # Salva como CSV para o site
            df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
            print(" ✅ OK!")
            
            # Remove o DBF para limpar a área (Opcional)
            os.remove(caminho_dbf)
            
        except Exception as e:
            print(f" ❌ Erro: {e}")

print("\n🚀 Conversão concluída!")