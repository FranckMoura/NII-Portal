import re
# É necessário instalar a biblioteca pypdf: pip install pypdf
from pypdf import PdfReader

def extrair_aihs(caminho_arquivo):
    """
    Lê um arquivo PDF e retorna um conjunto (set) com os números das AIHs encontrados.
    Remove sufixos como '-01' para padronizar a comparação.
    """
    aihs = set()
    try:
        leitor = PdfReader(caminho_arquivo)
        for pagina in leitor.pages:
            texto = pagina.extract_text()
            # Regex para encontrar números que começam com 51 e têm 13 dígitos
            # O padrão \b garante que pegamos o número completo
            encontrados = re.findall(r'\b(51\d{11})', texto)
            aihs.update(encontrados)
    except Exception as e:
        print(f"Erro ao processar {caminho_arquivo}: {e}")
    return aihs

# Caminhos dos arquivos (certifique-se de que estão na mesma pasta do script)
arquivo_mv = 'aih_mv.pdf'
arquivo_sus = 'aih_sisaih01.pdf'

# Executa a extração
print("Lendo arquivos...")
conjunto_mv = extrair_aihs(arquivo_mv)
conjunto_sus = extrair_aihs(arquivo_sus)

# Realiza a comparação (Diferença entre conjuntos)
apenas_no_sus = conjunto_sus - conjunto_mv
apenas_no_mv = conjunto_mv - conjunto_sus

# Exibe os resultados
print(f"\n--- RESUMO ---")
print(f"Total de AIHs no MV: {len(conjunto_mv)}")
print(f"Total de AIHs no SISAIH: {len(conjunto_sus)}")

if apenas_no_sus:
    print(f"\n[!] AIHs que estão no SISAIH mas FALTAM no MV ({len(apenas_no_sus)}):")
    for aih in apenas_no_sus:
        print(f" -> {aih}")
else:
    print("\n[OK] Todas as AIHs do SISAIH estão no MV.")

if apenas_no_mv:
    print(f"\n[!] AIHs que estão no MV mas NÃO estão no SISAIH ({len(apenas_no_mv)}):")
    for aih in apenas_no_mv:
        print(f" -> {aih}")
else:
    print("\n[OK] Todas as AIHs do MV estão no SISAIH.")