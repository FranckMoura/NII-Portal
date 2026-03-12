import os
import pdfplumber
import pandas as pd
import re
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR V6: UPLOAD + REGISTRO NO BANCO ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ENTRADA = os.path.join(BASE_DIR, "entradas_pdf")

if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    exit()

def forcar_upload_correto(caminho_local, nome_remoto, content_type):
    print(f"☁️  Subindo: {nome_remoto} ({content_type})...")
    try:
        # Remove antigo se existir
        try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except: pass

        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto,
                file=f,
                file_options={"content-type": content_type, "upsert": "true"}
            )
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def processar():
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]
    if not arquivos:
        print(f"❌ Pasta '{PASTA_ENTRADA}' vazia!")
        return

    nome_pdf = arquivos[0]
    caminho_pdf = os.path.join(PASTA_ENTRADA, nome_pdf)
    
    # Data para organização (DD-MM-YYYY) e para Banco (YYYY-MM-DD)
    data_hoje_str = datetime.now().strftime('%d-%m-%Y')
    data_banco = datetime.now().strftime('%Y-%m-%d')
    
    nome_pdf_remoto = f"PDFs/{data_hoje_str}_{nome_pdf}"
    nome_html_remoto = f"INDICES/Indice_{data_hoje_str}_{nome_pdf.replace('.pdf', '.html')}"

    print(f"📄 Processando: {nome_pdf}")

    # 1. SOBE O PDF
    link_pdf_final = forcar_upload_correto(caminho_pdf, nome_pdf_remoto, "application/pdf")
    if not link_pdf_final: return

    # 2. LÊ OS DADOS
    dados = []
    print("🕵️  Lendo PDF...")
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for i, pagina in enumerate(pdf.pages):
                if (i+1) % 50 == 0: print(f"   Pag {i+1}...")
                texto = pagina.extract_text() or ""
                
                m_nome = re.search(r'Paciente\s*:\s*(.*?)\s*Prontuário', texto)
                m_aih = re.search(r'Num AIH\s*:\s*([\d-]+)', texto)
                m_pront = re.search(r'Prontuário\s*:\s*(\d+)', texto)

                if m_nome and m_aih:
                    dados.append({
                        'NOME': m_nome.group(1).strip(),
                        'AIH': m_aih.group(1).strip(),
                        'PRONTUARIO': m_pront.group(1).strip() if m_pront else "N/A",
                        'PAGINA': i + 1
                    })
    except Exception as e:
        print(f"❌ Erro leitura PDF: {e}")
        return

    print(f"✅ Extraído: {len(dados)} pacientes.")

    if dados:
        # 3. GERA HTML
        df = pd.DataFrame(dados)
        
        # HTML Conteúdo (Omitido o CSS longo para economizar espaço aqui, mas é o mesmo do seu script)
        # ... [MANTENHA A GERAÇÃO DO HTML IGUAL AO SEU SCRIPT ANTERIOR] ...
        html = f"""<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><title>Índice {data_hoje_str}</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <style>body{{font-family:sans-serif;padding:20px;background:#f4f6f9}} table{{background:white}} .btn{{text-decoration:none;padding:5px 10px;background:#007bff;color:white;border-radius:4px}}</style>
        </head><body><h2>Índice: {nome_pdf} ({data_hoje_str})</h2>
        <table id="tabela" class="display"><thead><tr><th>Pág</th><th>Paciente</th><th>AIH</th><th>Prontuário</th><th>Ação</th></tr></thead><tbody>"""
        
        for _, row in df.iterrows():
            link_pag = f"{link_pdf_final}#page={row['PAGINA']}"
            html += f"<tr><td>{row['PAGINA']}</td><td>{row['NOME']}</td><td>{row['AIH']}</td><td>{row['PRONTUARIO']}</td><td><a href='{link_pag}' target='_blank' class='btn'>Abrir</a></td></tr>"
        
        html += "</tbody></table><script>$(document).ready(function(){$('#tabela').DataTable();});</script></body></html>"

        temp_file = os.path.join(BASE_DIR, "temp_indice.html")
        with open(temp_file, "w", encoding="utf-8") as f: f.write(html)
        
        # Sobe HTML
        link_html_final = forcar_upload_correto(temp_file, nome_html_remoto, "text/html; charset=utf-8")
        os.remove(temp_file)

        # 4. REGISTRA NO BANCO DE DADOS (A NOVIDADE)
        print("💾 Salvando links na tabela 'controle_simuladas'...")
        try:
            # Primeiro deleta registros do dia para evitar duplicidade
            supabase.table("controle_simuladas").delete().eq("data_arquivo", data_banco).execute()
            
            # Insere o novo
            supabase.table("controle_simuladas").insert({
                "data_arquivo": data_banco,
                "nome_original": nome_pdf,
                "link_pdf": link_pdf_final,
                "link_indice": link_html_final
            }).execute()
            print("✅ Banco atualizado!")
        except Exception as e:
            print(f"⚠️ Erro ao salvar no banco: {e}")

        print("\n🎉 FIM! O site já pode ler os links novos.")

if __name__ == "__main__":
    processar()