import pdfplumber
import re

def extrair_aihs(caminho_arquivo):
    aihs = set()
    print(f"\n[>] Abrindo e analisando: {caminho_arquivo}")
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            total_paginas = len(pdf.pages)
            for num_pagina, pagina in enumerate(pdf.pages, start=1):
                # Extrai o texto mantendo a estrutura tabular o máximo possível
                texto = pagina.extract_text()
                
                if texto:
                    # Busca qualquer sequência de 13 dígitos começando com 51
                    numeros = re.findall(r'51\d{11}', texto)
                    aihs.update(numeros)
                    # Imprime o progresso para você auditar a leitura
                    print(f"    Lendo página {num_pagina:02d}/{total_paginas} -> {len(numeros)} AIHs encontradas")
                else:
                    print(f"    Lendo página {num_pagina:02d}/{total_paginas} -> [Página sem texto reconhecível]")
                    
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
    except Exception as e:
        print(f"Erro inesperado ao processar '{caminho_arquivo}': {e}")
        
    return aihs

# 1. Nomes dos arquivos
arquivo_sisaih = 'aih_sisaih01.pdf'
arquivo_soulmv = 'aih_soulmv.pdf'

# 2. Execução
aihs_sisaih = extrair_aihs(arquivo_sisaih)
aihs_soulmv = extrair_aihs(arquivo_soulmv)

print("\n" + "="*50)
print(f"TOTAL GERAL SISAIH01: {len(aihs_sisaih)} AIHs")
print(f"TOTAL GERAL SOULMV:   {len(aihs_soulmv)} AIHs")
print("="*50)

# 3. Cruzamento
faltando_no_soulmv = aihs_sisaih - aihs_soulmv
sobrando_no_soulmv = aihs_soulmv - aihs_sisaih

if faltando_no_soulmv:
    print(f"\n[!] Encontradas {len(faltando_no_soulmv)} AIH(s) no SISAIH01 que estão FALTANDO no SOULMV:")
    for aih in sorted(faltando_no_soulmv):
        print(f"   -> {aih}")
else:
    print("\n[OK] Nenhuma AIH do SISAIH01 está faltando no SOULMV.")

if sobrando_no_soulmv:
    print(f"\n[!] Encontradas {len(sobrando_no_soulmv)} AIH(s) SOBRANDO no SOULMV (Não constam no SISAIH01):")
    for aih in sorted(sobrando_no_soulmv):
        print(f"   -> {aih}")
else:
    print("\n[OK] Nenhuma AIH sobrando no SOULMV.")