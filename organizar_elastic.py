import os
import shutil

# --- CONFIGURAÇÕES ---
PASTA_ORIGEM = "." # Pasta onde você baixou os arquivos (raiz)
PASTA_DESTINO = "arquivos"

print("📂 --- ORGANIZADOR ELASTICNES ---")

# Garante que a pasta destino existe
if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

# Lista arquivos na raiz que começam com 'elastic_' e terminam com .csv (ou .csv.csv)
arquivos = [f for f in os.listdir(PASTA_ORIGEM) if f.startswith("elastic_") and ".csv" in f]

if not arquivos:
    print("⚠️ Nenhum arquivo 'elastic_*.csv' encontrado na pasta raiz.")
else:
    for arquivo in arquivos:
        # Corrige o nome duplicado .csv.csv se existir
        nome_limpo = arquivo.replace(".csv.csv", ".csv")
        
        origem = os.path.join(PASTA_ORIGEM, arquivo)
        destino = os.path.join(PASTA_DESTINO, nome_limpo)
        
        # Move e Renomeia
        shutil.move(origem, destino)
        print(f"✅ Movido: {arquivo}  ->  arquivos/{nome_limpo}")

print("\n🚀 Arquivos prontos na pasta 'arquivos'.")
print("Agora atualize o 'institucional.html' e rode o 'upload_manager.py'.")