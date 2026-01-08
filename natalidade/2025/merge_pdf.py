import os
import glob
from PyPDF2 import PdfMerger

print("--- 📑 UNIFICADOR DE ARQUIVOS PDF ---")

# --- CONFIGURAÇÃO ---
PASTA_ORIGEM = r"C:\Users\DELL\OneDrive\HBSH\natalidade\2025"
ARQUIVO_SAIDA = os.path.join(PASTA_ORIGEM, "Relatorio_Completo_2025.pdf")

# Encontrar arquivos
arquivos = sorted(glob.glob(os.path.join(PASTA_ORIGEM, "*.pdf")))

if not arquivos:
    print("❌ Nenhum PDF encontrado.")
    exit()

merger = PdfMerger()

print(f">> Unindo {len(arquivos)} arquivos...")

for arquivo in arquivos:
    try:
        print(f"   + Adicionando: {os.path.basename(arquivo)}")
        merger.append(arquivo)
    except Exception as e:
        print(f"   ❌ Erro ao adicionar {os.path.basename(arquivo)}: {e}")

# Salvar
merger.write(ARQUIVO_SAIDA)
merger.close()

print(f"\n✅ Arquivo único criado com sucesso:")
print(f"   {ARQUIVO_SAIDA}")