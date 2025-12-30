import os
from pypdf import PdfWriter

def mesclar_pdfs(nome_arquivo_saida="RELATORIO_COMPLETO.pdf"):
    # Cria o objeto que fará a união
    merger = PdfWriter()
    
    # Pega o diretório onde o script está rodando
    diretorio_atual = os.getcwd()
    
    # Lista todos os arquivos da pasta
    arquivos = [f for f in os.listdir(diretorio_atual) if f.endswith('.pdf')]
    
    # Ordena os arquivos por nome (importante numerar seus arquivos: 1.pdf, 2.pdf...)
    arquivos.sort()
    
    # Se não houver PDFs, avisa e para
    if not arquivos:
        print("❌ Nenhum arquivo PDF encontrado nesta pasta.")
        return

    print(f"📂 Encontrados {len(arquivos)} arquivos para unir.")

    # Loop para adicionar cada arquivo
    for pdf in arquivos:
        # Evita unir o próprio arquivo de saída se ele já existir
        if pdf == nome_arquivo_saida:
            continue
            
        caminho_completo = os.path.join(diretorio_atual, pdf)
        print(f"➕ Adicionando: {pdf}")
        
        try:
            merger.append(caminho_completo)
        except Exception as e:
            print(f"⚠️ Erro ao adicionar {pdf}: {e}")

    # Salva o arquivo final
    with open(nome_arquivo_saida, "wb") as saida:
        merger.write(saida)
    
    print("-" * 30)
    print(f"✅ Sucesso! Arquivo criado: {nome_arquivo_saida}")
    print("-" * 30)

# Executa a função
if __name__ == "__main__":
    mesclar_pdfs()