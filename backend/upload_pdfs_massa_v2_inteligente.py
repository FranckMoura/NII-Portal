import os
import re
from supabase import create_client, Client

print("--- 🚀 ROBÔ DE UPLOAD EM MASSA V2 (INTELIGENTE) ---")

# --- CONFIGURAÇÕES ---
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
    # Procura número no padrão XXXXXXXXXXXXX ou XXXXXXXXXXXX-X
    match = re.search(r'(\d{12}-\d{1})|(\d{13})', nome_arquivo)
    if match:
        return match.group(0)
    return None

def ja_tem_pdf_no_banco(aih):
    """ Verifica se essa AIH já tem um link de PDF válido no banco """
    try:
        # Consulta apenas a coluna arquivo_pdf para ser rápido
        res = supabase.table("regulacao").select("arquivo_pdf").eq("num_aih", aih).execute()
        
        if res.data and len(res.data) > 0:
            link = res.data[0].get('arquivo_pdf')
            # Se o link existir e for maior que 10 caracteres, consideramos que já tem
            if link and len(link) > 10:
                return True
        return False
    except:
        return False

def processar_pasta():
    if not os.path.exists(PASTA_PDFS):
        print(f"❌ Pasta não encontrada: {PASTA_PDFS}")
        return

    arquivos = os.listdir(PASTA_PDFS)
    total_arquivos = len([f for f in arquivos if f.lower().endswith(".pdf")])
    print(f"📂 Encontrei {total_arquivos} PDFs na pasta.")

    for arquivo in arquivos:
        if not arquivo.lower().endswith(".pdf"): continue
        
        aih = extrair_aih(arquivo)
        
        if not aih:
            # Se não tem AIH no nome, ignoramos (o robô de repescagem cuida desses)
            # print(f"⚠️ Ignorado (Sem AIH no nome): {arquivo}") 
            continue

        print(f"📄 {arquivo} (AIH: {aih})...", end=" ")

        # --- A MÁGICA DA INTELIGÊNCIA AQUI ---
        if ja_tem_pdf_no_banco(aih):
            print("⏩ Já existe no site. Pulei.")
            continue
        # -------------------------------------

        print("⬆️ Subindo...", end=" ")

        try:
            caminho_local = os.path.join(PASTA_PDFS, arquivo)
            caminho_remoto = f"Fichas_Internacao/{arquivo}"
            
            # 1. Upload
            with open(caminho_local, 'rb') as f:
                supabase.storage.from_(BUCKET).upload(
                    path=caminho_remoto,
                    file=f,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            
            # 2. Pega Link
            link_publico = supabase.storage.from_(BUCKET).get_public_url(caminho_remoto)

            # 3. Atualiza Banco (Tenta pela AIH, se falhar tenta pela Solicitação)
            r = supabase.table("regulacao").update({
                "arquivo_pdf": link_publico
            }).eq("num_aih", aih).execute()

            if not r.data:
                # Tenta match removendo o traço, caso esteja salvo como solicitação
                supabase.table("regulacao").update({
                    "arquivo_pdf": link_publico
                }).eq("num_solicitacao", aih.replace("-","")).execute()

            print("✅ Sucesso!")

        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    processar_pasta()