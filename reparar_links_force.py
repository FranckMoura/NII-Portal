import os
import json
import glob
from unidecode import unidecode

print("--- REPARADOR DE LINKS V2 (BUSCA INTELIGENTE) ---")

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
CAMINHO_JSON = os.path.join(PASTA_PROJETO, "arquivos", "dados_sisreg.json")

# Lista de lugares onde a pasta de PDFs pode estar escondida
lugares_para_procurar = [
    os.path.join(PASTA_PROJETO, "arquivos", "Fichas_Internacao"), # Onde procuramos antes
    os.path.join(PASTA_PROJETO, "Fichas_Internacao"),             # Na raiz do projeto (Mais provável)
    os.path.join(PASTA_PROJETO, "SISREG_Export", "Fichas_Internacao"),
    os.path.join(PASTA_PROJETO, "downloads", "Fichas_Internacao")
]

pasta_pdf_encontrada = None

print(">> Procurando pasta de PDFs...")
for caminho in lugares_para_procurar:
    if os.path.exists(caminho):
        print(f"   ✅ ENCONTRADA EM: {caminho}")
        pasta_pdf_encontrada = caminho
        break
    else:
        print(f"   (Não está em: {caminho})")

if not pasta_pdf_encontrada:
    print("\n❌ ERRO CRÍTICO: Não achei a pasta 'Fichas_Internacao' em lugar nenhum!")
    print("   Pastas que existem na raiz do projeto:")
    try:
        for item in os.listdir(PASTA_PROJETO):
            if os.path.isdir(os.path.join(PASTA_PROJETO, item)):
                print(f"    - {item}")
    except: pass
    exit()

# --- INÍCIO DO MAPEAMENTO ---
def normalizar_aih(valor):
    if not valor: return ""
    return "".join(filter(str.isdigit, str(valor)))

print(f"\n>> Mapeando arquivos em: {pasta_pdf_encontrada}")
pdfs_encontrados = glob.glob(os.path.join(pasta_pdf_encontrada, "*.pdf"))
mapa_pdf = {}

print(f"   -> Encontrados {len(pdfs_encontrados)} arquivos PDF físicos.")

for caminho_completo in pdfs_encontrados:
    nome_arquivo = os.path.basename(caminho_completo)
    numeros = "".join(filter(str.isdigit, nome_arquivo))
    
    # Se tiver pelo menos 13 digitos, assumimos que é uma AIH
    if len(numeros) >= 13:
        aih_chave = numeros[:13] 
        # O link para o site SEMPRE deve ser relativo à pasta 'arquivos' ou raiz web
        # Se a pasta estiver na raiz, o link precisa ser ajustado.
        # Vamos assumir que o upload move para a pasta certa ou o link aponta direto.
        
        # Padrão: NomeDaPasta/NomeDoArquivo
        link_relativo = f"Fichas_Internacao/{nome_arquivo}"
        mapa_pdf[aih_chave] = link_relativo

print(f"   -> Links válidos gerados: {len(mapa_pdf)}")

# --- ATUALIZAÇÃO DO JSON ---
print(">> Atualizando JSON...")
if not os.path.exists(CAMINHO_JSON):
    print("❌ ERRO: dados_sisreg.json não encontrado.")
    exit()

with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
    dados = json.load(f)

links_aplicados = 0
for item in dados:
    aih_item = normalizar_aih(item.get("aih"))
    
    if aih_item in mapa_pdf:
        item["arquivo_pdf"] = mapa_pdf[aih_item]
        links_aplicados += 1

# Salvar
with open(CAMINHO_JSON, 'w', encoding='utf-8') as f:
    json.dump(dados, f, indent=4, ensure_ascii=False)

print(f"✅ SUCESSO! {links_aplicados} registros foram atualizados no JSON.")

if links_aplicados > 0:
    print("   Agora execute: python upload_manager_v6.py")
else:
    print("⚠️ AVISO: Nenhum link foi aplicado. Verifique se os números das AIHs batem.")