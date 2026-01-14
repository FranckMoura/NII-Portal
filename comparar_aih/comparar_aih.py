import re
from pypdf import PdfReader

def extrair_aihs(caminho_arquivo):
    """
    Lê um arquivo PDF e extrai números de AIH válidos (13 dígitos).
    Padrão: 51 (MT) + Ano (24/25/26) + 9 dígitos sequenciais.
    """
    aihs = set()
    try:
        reader = PdfReader(caminho_arquivo)
        text_completo = ""
        
        # Agrupa todo o texto
        for page in reader.pages:
            text_completo += page.extract_text() + "\n"
            
        # --- CORREÇÃO AQUI ---
        # A regex antiga esperava 14 dígitos. A AIH tem 13.
        # 51 (UF) + (24|25|26) (Ano) + 9 dígitos = 13 dígitos total
        padrao = r'51(?:24|25|26)\d{9}'
        
        encontrados = re.findall(padrao, text_completo)
        aihs.update(encontrados)
        
        print(f"-> Lido {caminho_arquivo}: Encontradas {len(aihs)} AIHs únicas.")
        
    except Exception as e:
        print(f"Erro ao processar {caminho_arquivo}: {e}")
        
    return aihs

# --- CONFIGURAÇÃO DOS ARQUIVOS ---
# Certifique-se de que os nomes estão corretos na pasta
arquivo_mv = 'AIH_MV.pdf'
arquivo_sus = 'AIH_SISAIH01.pdf' 

# --- EXECUÇÃO ---
print("\n--- INICIANDO COMPARAÇÃO (CORRIGIDO 13 DÍGITOS) ---\n")

conjunto_mv = extrair_aihs(arquivo_mv)
conjunto_sus = extrair_aihs(arquivo_sus)

# --- COMPARAÇÃO ---
apenas_no_sus = conjunto_sus - conjunto_mv
apenas_no_mv = conjunto_mv - conjunto_sus
ambos = conjunto_sus & conjunto_mv

print(f"\n--- RESUMO GERAL ---")
print(f"AIHs no MV:     {len(conjunto_mv)}")
print(f"AIHs no SISAIH: {len(conjunto_sus)}")
print(f"Em ambos:       {len(ambos)}")

if apenas_no_sus:
    print(f"\n[ATENÇÃO] {len(apenas_no_sus)} AIHs constam no SISAIH mas FALTAM no MV:")
    for aih in sorted(apenas_no_sus):
        print(f" -> {aih}")
else:
    print("\n[OK] Todas as AIHs do SISAIH estão no MV.")

if apenas_no_mv:
    print(f"\n[ATENÇÃO] {len(apenas_no_mv)} AIHs constam no MV mas FALTAM no SISAIH:")
    for aih in sorted(apenas_no_mv):
        print(f" -> {aih}")
else:
    print("\n[OK] Todas as AIHs do MV estão no SISAIH.")