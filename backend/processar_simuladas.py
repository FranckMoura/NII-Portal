import os
import pdfplumber
import pandas as pd
import re
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR NII: SIMULADAS ---")

# --- 1. CONFIGURAÇÕES E CAMINHOS ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

# Define pastas relativas a onde o script está
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ENTRADA = os.path.join(BASE_DIR, "entradas_pdf")
PASTA_TEMP = os.path.join(BASE_DIR, "temp")

# Cria pastas se não existirem
if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)
if not os.path.exists(PASTA_TEMP): os.makedirs(PASTA_TEMP)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão Supabase: {e}")
    exit()

def upload_sobrescrevendo(caminho_local, nome_remoto, content_type):
    """Remove antigo e sobe novo forçando o tipo correto"""
    print(f"☁️  Processando nuvem: {nome_remoto}...")
    try:
        # Tenta remover anterior (limpeza)
        try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except: pass

        # Upload novo
        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto, file=f,
                file_options={"content-type": content_type, "upsert": "true"}
            )
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def processar():
    # 1. Busca PDF
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]
    if not arquivos:
        print(f"❌ NENHUM PDF ENCONTRADO EM: {PASTA_ENTRADA}")
        print("👉 Mova o arquivo .pdf para a pasta 'entradas_pdf' e tente novamente.")
        return

    nome_pdf = arquivos[0]
    caminho_pdf = os.path.join(PASTA_ENTRADA, nome_pdf)
    
    # Define nomes na nuvem (usa data de hoje para manter organizado)
    data_hoje = datetime.now().strftime('%d-%m-%Y')
    
    # Nomes limpos para facilitar a leitura no portal
    nome_pdf_remoto = f"PDFs/{data_hoje}_{nome_pdf}"
    nome_html_remoto = f"INDICES/Indice_{data_hoje}_{nome_pdf.replace('.pdf', '.html')}"

    print(f"📄 Lendo: {nome_pdf}")

    # 2. Upload do PDF
    link_pdf = upload_sobrescrevendo(caminho_pdf, nome_pdf_remoto, "application/pdf")
    if not link_pdf: return

    # 3. Extração de Dados
    dados = []
    print("🕵️  Extraindo pacientes...")
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for i, pagina in enumerate(pdf.pages):
                if (i+1) % 50 == 0: print(f"   -> Pag {i+1}...")
                texto = pagina.extract_text()
                if not texto: continue

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
        print(f"❌ Erro ao ler PDF: {e}")
        return

    print(f"✅ Encontrados {len(dados)} registros.")

    # 4. Gera HTML
    if dados:
        df = pd.DataFrame(dados)
        
        # HTML template (Resumido para caber aqui, mas com sua lógica visual)
        html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Índice - {nome_pdf}</title>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {{ font-family: 'Roboto', sans-serif; background: #f4f6f9; padding: 20px; padding-bottom: 80px; }}
        .header {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; display:flex; justify-content:space-between; align-items:center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .btn-action {{ padding: 6px 12px; border-radius: 4px; color: white; text-decoration: none; font-size: 12px; font-weight: 500; margin-right: 5px; cursor: pointer; border: none; }}
        .btn-open {{ background: #17a2b8; }} 
        .btn-add {{ background: #28a745; }}
        .btn-added {{ background: #6c757d; cursor: not-allowed; }}
        .collection-bar {{ position: fixed; bottom: 0; left: 0; width: 100%; background: #343a40; color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; z-index: 1000; }}
        .btn-copy {{ background: #007bff; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold; cursor: pointer; }}
        .btn-clear {{ background: transparent; border: 1px solid #6c757d; color: #ccc; margin-left: 10px; padding: 8px; border-radius: 4px; cursor:pointer; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h3 style="margin:0; color:#0056b3;"><i class="fas fa-file-medical"></i> Índice: {nome_pdf}</h3>
            <small>Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small>
        </div>
        <button onclick="window.close()" style="background:#dc3545; color:white; border:none; padding:8px 15px; border-radius:5px;">Fechar</button>
    </div>
    
    <div style="background:white; padding:20px; border-radius:8px;">
        <table id="tabela" class="display" style="width:100%">
            <thead><tr><th>Pág</th><th>Paciente</th><th>AIH</th><th>Prontuário</th><th>Ações</th></tr></thead>
            <tbody>
"""
        for _, row in df.iterrows():
            link_remoto = f"{link_pdf}#page={row['PAGINA']}"
            html += f"""
                <tr>
                    <td>{row['PAGINA']}</td><td>{row['NOME']}</td><td>{row['AIH']}</td><td>{row['PRONTUARIO']}</td>
                    <td style="text-align:center;">
                        <a href="{link_remoto}" target="_blank" class="btn-action btn-open"><i class="fas fa-external-link-alt"></i> Abrir</a>
                        <button class="btn-action btn-add" onclick="addPage({row['PAGINA']}, this)"><i class="fas fa-plus"></i> Incluir</button>
                    </td>
                </tr>
            """

        html += """
            </tbody>
        </table>
    </div>
    <div class="collection-bar">
        <div><strong>Selecionadas:</strong> <span id="pageList" style="color:#ffc107">Nenhuma</span></div>
        <div><button class="btn-clear" onclick="clearPages()"><i class="fas fa-trash"></i></button> <button class="btn-copy" onclick="copyAllPages()" id="btnCopy">COPIAR LISTA</button></div>
    </div>
    <script>
        $(document).ready(function() { $('#tabela').DataTable({ language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" }, pageLength: 10 }); });
        var collectedPages = [];
        function addPage(p, btn) { if(!collectedPages.includes(p)) { collectedPages.push(p); collectedPages.sort((a,b)=>a-b); document.getElementById('pageList').innerText = collectedPages.join(', '); btn.classList.add('btn-added'); btn.innerHTML = '<i class="fas fa-check"></i>'; } }
        function clearPages() { collectedPages=[]; document.getElementById('pageList').innerText="Nenhuma"; $('.btn-added').html('<i class="fas fa-plus"></i> Incluir').removeClass('btn-added'); }
        function copyAllPages() { navigator.clipboard.writeText(collectedPages.join(',')); alert('Copiado!'); }
    </script>
</body>
</html>
"""
        # Salva temporário na pasta temp
        caminho_html_temp = os.path.join(PASTA_TEMP, "temp_indice.html")
        with open(caminho_html_temp, "w", encoding="utf-8") as f: f.write(html)
        
        # Upload
        upload_sobrescrevendo(caminho_html_temp, nome_html_remoto, "text/html; charset=utf-8")
        
        # Limpa temporário
        os.remove(caminho_html_temp)
        print("\n🎉 SUCESSO! Índice atualizado na nuvem.")
        print("👉 Vá ao portal e limpe o cache (Ctrl + F5).")

    else:
        print("⚠️ Nenhum dado extraído.")

if __name__ == "__main__":
    processar()