import os
import re
from supabase import create_client, Client
from datetime import datetime

print("--- ☁️ PUBLICADOR MANUAL (CORREÇÃO DE LINK E HTML) ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

# Pastas (Baseado na estrutura que combinamos)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Onde seu script original salva o arquivo? (Geralmente cria uma pasta 'arquivos')
CAMINHO_HTML_LOCAL = os.path.join(BASE_DIR, "arquivos", "indice_pacientes.html") 
# Onde você coloca o PDF original?
PASTA_PDFS = os.path.join(BASE_DIR, "entradas_pdf") 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    exit()

def upload_arquivo(caminho_local, nome_remoto, tipo_mime):
    print(f"⬆️  Subindo: {nome_remoto}...")
    try:
        # Tenta remover o arquivo antigo para limpar configurações erradas
        try:
            supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except:
            pass

        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto,
                file=f,
                file_options={
                    "content-type": tipo_mime,  # <--- O SEGREDO ESTÁ AQUI
                    "upsert": "true"
                }
            )
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def publicar():
    # 1. Verifica se você já gerou o HTML com seu script
    if not os.path.exists(CAMINHO_HTML_LOCAL):
        print(f"❌ Arquivo não encontrado: {CAMINHO_HTML_LOCAL}")
        print("👉 Rode seu script original de geração primeiro!")
        return

    # 2. Ler o HTML para descobrir qual PDF ele está usando
    print("📖 Lendo HTML gerado...")
    with open(CAMINHO_HTML_LOCAL, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Procura o nome do PDF no link (ex: href="../SIMULADAS 0126.pdf")
    # O regex procura qualquer coisa que termine em .pdf dentro de um href
    match = re.search(r'href="\.\./(.*?\.pdf)', conteudo)
    
    if not match:
        print("❌ Não consegui achar o nome do PDF dentro do HTML.")
        print("Verifique se o seu script gerou o link como href='../nome.pdf'")
        return
    
    nome_pdf = match.group(1) # Ex: SIMULADAS 0126.pdf
    caminho_pdf_local = os.path.join(PASTA_PDFS, nome_pdf)
    
    print(f"📄 PDF Detectado no HTML: {nome_pdf}")

    # Verifica se o PDF existe na pasta
    if not os.path.exists(caminho_pdf_local):
        print(f"❌ O PDF '{nome_pdf}' não está na pasta '{PASTA_PDFS}'.")
        print("👉 Mova o PDF para a pasta backend/entradas_pdf e tente de novo.")
        return

    # 3. Subir o PDF (Para gerar o link de internet)
    data_hoje = datetime.now().strftime('%d-%m-%Y')
    # Nome limpo na nuvem
    nome_pdf_remoto = f"PDFs/{data_hoje}_{nome_pdf}"
    
    link_pdf_nuvem = upload_arquivo(caminho_pdf_local, nome_pdf_remoto, "application/pdf")
    
    if not link_pdf_nuvem: return

    # 4. Corrigir o HTML (Trocar link local por link da nuvem)
    print("🔧 Ajustando links no HTML...")
    # Substitui "../SIMULADAS 0126.pdf" pelo Link Completo do Supabase
    novo_conteudo = conteudo.replace(f"../{nome_pdf}", link_pdf_nuvem)

    # Salva um arquivo temporário já corrigido
    temp_html = os.path.join(BASE_DIR, "temp_upload.html")
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)

    # 5. Sobe o HTML (Forçando text/html)
    # O nome na nuvem será padronizado para o site encontrar
    nome_html_remoto = f"INDICES/Indice_{data_hoje}_{nome_pdf.replace('.pdf', '.html')}"
    
    url_final = upload_arquivo(temp_html, nome_html_remoto, "text/html; charset=utf-8")
    
    # Limpa o temporário
    if os.path.exists(temp_html): os.remove(temp_html)

    print("\n✅ PUBLICADO COM SUCESSO!")
    print(f"🔗 O arquivo '{nome_html_remoto}' está online.")
    print("👉 Agora vá no Portal > Simuladas e aperte Ctrl+F5.")

if __name__ == "__main__":
    publicar()