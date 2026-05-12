import re
import PyPDF2
import os

print("--- 🔍 COMPARADOR DE AIHs: SOULMV vs SISAIH01 ---")

def extrair_aihs(caminho_arquivo):
    aihs = set()
    # Padrão Regex para capturar exatos 13 números seguidos (Formato da AIH).
    # O "\b" garante que ele ignore qualquer "-01" que venha depois no SISAIH01.
    padrao_aih = re.compile(r'\b(\d{13})\b')
    
    if not os.path.exists(caminho_arquivo):
        print(f"❌ Arquivo não encontrado: {caminho_arquivo}")
        return aihs
        
    try:
        with open(caminho_arquivo, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    encontrados = padrao_aih.findall(texto)
                    aihs.update(encontrados)
    except Exception as e:
        print(f"Erro ao ler {caminho_arquivo}: {e}")
        
    return aihs

# Nomes dos arquivos (certifique-se de que estão na mesma pasta do script)
arquivo_soulmv = "aih_soulmv.pdf"
arquivo_sisaih = "aih_sisaih01.pdf"

print(f"\nLendo {arquivo_soulmv}...")
aihs_soulmv = extrair_aihs(arquivo_soulmv)
print(f"Total de AIHs únicas encontradas: {len(aihs_soulmv)}")

print(f"\nLendo {arquivo_sisaih}...")
aihs_sisaih = extrair_aihs(arquivo_sisaih)
print(f"Total de AIHs únicas encontradas: {len(aihs_sisaih)}")

# --- A MÁGICA DO CRUZAMENTO ---
faltando_no_sisaih = aihs_soulmv - aihs_sisaih
sobrando_no_sisaih = aihs_sisaih - aihs_soulmv

print("\n================ RESULTADO DO CRUZAMENTO ================")

if faltando_no_sisaih:
    print(f"🚨 AIHs que estão no SOULMV, mas FALTAM no SISAIH01 ({len(faltando_no_sisaih)}):")
    for aih in faltando_no_sisaih:
        print(f"  -> {aih} (Verifique se não foi rejeitada ou glosada)")
else:
    print("✅ Nenhuma AIH faltando no SISAIH01.")

if sobrando_no_sisaih:
    print(f"\n⚠️ AIHs que estão no SISAIH01, mas NÃO ESTÃO no SOULMV ({len(sobrando_no_sisaih)}):")
    for aih in sobrando_no_sisaih:
        print(f"  -> {aih} (Pode ser repasse de mês anterior)")
        
print("=========================================================\n")