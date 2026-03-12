import os
import re
from supabase import create_client, Client

print("--- 🚀 ROBÔ DE UPLOAD DE PDFS EM MASSA ---")

# --- CONFIGURAÇÕES ---
# Coloque aqui o caminho onde estão os PDFs no seu computador
PASTA_PDFS = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\temp_fichas" 

SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
BUCKET = "arquivos-faturamento"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    exit()

def extrair_aih(nome_arquivo):
    # Tenta achar um número de 13 dígitos ou padrão AIH (12 dígitos + digito)
    match = re.search(r'(\d{12}-\d{1})|(\d{13})', nome_arquivo)
    if match:
        return match.group(0)
    return None

def processar_pasta():
    arquivos = os.listdir(PASTA_PDFS)
    print(f"📂 Encontrei {len(arquivos)} arquivos na pasta.")

    for arquivo in arquivos:
        if not arquivo.lower().endswith(".pdf"): continue
        
        caminho_local = os.path.join(PASTA_PDFS, arquivo)
        aih = extrair_aih(arquivo)
        
        if not aih:
            print(f"⚠️ Pulei {arquivo}: Não achei AIH no nome.")
            continue

        print(f"⬆️ Subindo: {arquivo} (AIH: {aih})...", end=" ")

        try:
            # 1. Upload para o Storage
            caminho_remoto = f"Fichas_Internacao/{arquivo}"
            with open(caminho_local, 'rb') as f:
                supabase.storage.from_(BUCKET).upload(
                    path=caminho_remoto,
                    file=f,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            
            # 2. Pega o Link Público
            link_publico = supabase.storage.from_(BUCKET).get_public_url(caminho_remoto)

            # 3. Atualiza o Banco de Dados
            # Atualiza a linha onde num_aih OU num_solicitacao for igual ao encontrado
            # (Porque lembra que para pendentes usamos a solicitacao como chave)
            r = supabase.table("regulacao").update({
                "arquivo_pdf": link_publico
            }).eq("num_aih", aih).execute()

            if not r.data:
                # Tenta pela coluna num_solicitacao se nao achou pela AIH
                # (Caso o arquivo tenha o nome da solicitação em vez da AIH)
                supabase.table("regulacao").update({
                    "arquivo_pdf": link_publico
                }).eq("num_solicitacao", aih.replace("-","")).execute()

            print("✅ OK!")

        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    if os.path.exists(PASTA_PDFS):
        processar_pasta()
    else:
        print(f"❌ A pasta {PASTA_PDFS} não existe.")