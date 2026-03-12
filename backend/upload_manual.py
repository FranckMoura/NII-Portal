import os
import re
from supabase import create_client, Client
from datetime import datetime

print("--- ☁️ PUBLICADOR MANUAL (CORREÇÃO HTML) ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

# Pastas (Ajuste se necessário)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Onde o seu script original salvou o arquivo? Geralmente é na pasta 'arquivos'
CAMINHO_HTML_LOCAL = os.path.join(BASE_DIR, "arquivos", "indice_pacientes.html") 
# Onde está o PDF original?
PASTA_PDFS = os.path.join(BASE_DIR, "entradas_pdf") 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    exit()

def upload_arquivo(caminho_local, nome_remoto, tipo_mime):
    print(f"⬆️  Subindo: {nome_remoto}...")
    try:
        # Primeiro remove o antigo para garantir que o Supabase aceite o novo Content-Type
        try:
            supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except:
            pass

        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto,
                file=f,
                file_options={
                    "content-type": tipo_mime,  # AQUI ESTÁ O SEGREDO
                    "upsert": "true"
                }
            )
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def publicar():
    # 1. Verifica se você já gerou o HTML
    if not os.path.exists(CAMINHO_HTML_LOCAL):
        print(f"❌ Arquivo não encontrado: {CAMINHO_HTML_LOCAL}")
        print("👉 Rode seu script original de geração primeiro!")
        return

    # 2. Lê o HTML para descobrir qual PDF ele está usando
    print("📖 Lendo HTML gerado...")
    with open(CAMINHO_HTML_LOCAL, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Procura o nome do PDF no link do botão (ex: href="../NOME.pdf")
    match = re.search(r'href="\.\./(.*?\.pdf)', conteudo)
    if not match:
        print("❌ Não encontrei o link do PDF dentro do HTML.")
        return
    
    nome_pdf = match.group(1)
    caminho_pdf = os.path.join(PASTA_PDFS, nome_pdf)
    
    print(f"📄 PDF Detectado: {nome_pdf}")

    # 3. Sobe o PDF primeiro
    data_hoje = datetime.now().strftime('%d-%m-%Y')
    # Adicionamos um prefixo fixo para não acumular lixo
    nome_pdf_remoto = f"PDFs/{data_hoje}_{nome_pdf}"
    
    if os.path.exists(caminho_pdf):
        link_pdf = upload_arquivo(caminho_pdf, nome_pdf_remoto, "application/pdf")
    else:
        print(f"⚠️ PDF não encontrado em '{caminho_pdf}'. Tentando usar link existente...")
        link_pdf = supabase.storage.from_(NOME_BUCKET).get_public_url(nome_pdf_remoto)

    if not link_pdf: return

    # 4. Corrige o HTML
    # Substitui o link local "../arquivo.pdf" pelo Link do Supabase
    print("🔧 Ajustando links no HTML...")
    novo_conteudo = conteudo.replace(f"../{nome_pdf}", link_pdf)

    # Salva um arquivo temporário já corrigido
    temp_html = os.path.join(BASE_DIR, "temp_upload.html")
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)

    # 5. Sobe o HTML (Forçando text/html)
    # Mantemos o nome padronizado para o portal encontrar
    nome_html_remoto = f"INDICES/Indice_{data_hoje}_{nome_pdf.replace('.pdf', '.html')}"
    
    url_final = upload_arquivo(temp_html, nome_html_remoto, "text/html")
    
    # Limpa
    if os.path.exists(temp_html): os.remove(temp_html)

    print("\n✅ PUBLICADO COM SUCESSO!")
    print(f"🔗 Link: {url_final}")
    print("👉 DICA: Se ainda abrir como texto, aguarde 1 minuto ou abra em janela anônima.")

if __name__ == "__main__":
    publicar()