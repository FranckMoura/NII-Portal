import os
import pdfplumber
import pandas as pd
import re
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR V8: HTML PREMIUM COM COLEÇÃO DE PÁGINAS ---")

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
        try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except: pass

        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto,
                file=f,
                file_options={"content-type": content_type, "upsert": "true", "cache-control": "3600"}
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
    
    data_hoje_str = datetime.now().strftime('%d-%m-%Y')
    data_banco = datetime.now().strftime('%Y-%m-%d')
    
    nome_pdf_remoto = f"PDFs/{data_hoje_str}_{nome_pdf}"
    nome_html_remoto = f"INDICES/Indice_{data_hoje_str}_{nome_pdf.replace('.pdf', '.html')}"

    print(f"📄 Processando: {nome_pdf}")

    # 1. SOBE O PDF PRIMEIRO (Para termos o link)
    link_pdf_final = forcar_upload_correto(caminho_pdf, nome_pdf_remoto, "application/pdf")
    if not link_pdf_final: return

    # 2. LÊ OS DADOS (Lógica Inteligente com Continuação)
    dados_extraidos = []
    ultimo_paciente_valido = {'nome': None, 'aih': None, 'prontuario': None}
    
    print("🕵️  Lendo PDF...")
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            total_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                num_pag = i + 1
                if num_pag % 50 == 0: print(f"   Pag {num_pag}/{total_paginas}...")
                
                texto = pagina.extract_text(x_tolerance=2) or ""
                
                m_nome = re.search(r'Paciente\s*:\s*(.*?)\s*Prontuário', texto)
                m_aih = re.search(r'Num AIH\s*:\s*([\d-]+)', texto)
                m_pront = re.search(r'Prontuário\s*:\s*(\d+)', texto)

                nome = m_nome.group(1).strip() if m_nome else None
                aih = m_aih.group(1).strip() if m_aih else None
                pront = m_pront.group(1).strip() if m_pront else None

                if nome and aih:
                    registro = {'NOME': nome, 'AIH': aih, 'PRONTUARIO': pront or "N/A", 'PAGINA': num_pag}
                    ultimo_paciente_valido = {'nome': nome, 'aih': aih, 'prontuario': pront}
                    dados_extraidos.append(registro)
                elif not nome and aih:
                    # Tenta recuperar do anterior se for a mesma AIH
                    if ultimo_paciente_valido['aih'] == aih:
                        registro = {
                            'NOME': ultimo_paciente_valido['nome'] + " (Cont.)",
                            'AIH': aih,
                            'PRONTUARIO': ultimo_paciente_valido['prontuario'],
                            'PAGINA': num_pag
                        }
                        dados_extraidos.append(registro)
    except Exception as e:
        print(f"❌ Erro leitura PDF: {e}")
        return

    print(f"✅ Extraído: {len(dados_extraidos)} registros.")

    if dados_extraidos:
        # 3. GERA HTML (VERSÃO PREMIUM IGUAL AO SEU SCRIPT LOCAL)
        df = pd.DataFrame(dados_extraidos)
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Índice {data_hoje_str}</title>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {{ --primary: #0056b3; --success: #28a745; --info: #17a2b8; --dark: #343a40; }}
        body {{ font-family: 'Roboto', sans-serif; background: #f4f6f9; padding: 20px; padding-bottom: 80px; }}
        .header {{ background: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ margin: 0; font-size: 20px; color: var(--primary); }}
        .header small {{ color: #666; font-size: 14px; }}
        .table-container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        table.dataTable tbody td {{ padding: 6px 10px; font-size: 13px; vertical-align: middle; }}
        table.dataTable thead th {{ background-color: var(--primary); color: white; padding: 8px 10px; font-size: 14px; }}
        .btn-group {{ display: flex; gap: 5px; justify-content: center; }}
        .btn-action {{ border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; color: white; font-weight: 500; transition: 0.2s; }}
        .btn-add {{ background: var(--success); }}
        .btn-add:hover {{ background: #218838; }}
        .btn-added {{ background: #6c757d; cursor: not-allowed; }}
        .btn-open {{ background: var(--info); }}
        .btn-open:hover {{ background: #117a8b; }}
        .collection-bar {{ position: fixed; bottom: 0; left: 0; width: 100%; background: var(--dark); color: white; padding: 15px 20px; box-shadow: 0 -2px 10px rgba(0,0,0,0.2); z-index: 1000; display: flex; justify-content: space-between; align-items: center; }}
        .pages-display {{ font-family: monospace; color: #ffc107; font-size: 14px; max-width: 70%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
        .btn-copy {{ background: #007bff; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold; cursor: pointer; }}
        .btn-clear {{ background: transparent; border: 1px solid #6c757d; color: #ccc; margin-left: 10px; padding: 8px; border-radius: 4px; cursor:pointer; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1><i class="fas fa-file-medical"></i> Índice de Pacientes (Nuvem)</h1>
            <small>Arquivo Original: {nome_pdf}</small>
        </div>
        <div>
            <button onclick="window.close()" style="background:#dc3545; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Fechar</button>
        </div>
    </div>

    <div class="table-container">
        <table id="tabelaPacientes" class="display" style="width:100%">
            <thead><tr><th>Página</th><th>Paciente</th><th>AIH</th><th>Prontuário</th><th style="width:160px; text-align:center;">Ações</th></tr></thead>
            <tbody>
"""
        # INSERE AS LINHAS DA TABELA
        for _, row in df.iterrows():
            # Aqui usamos o link_pdf_final que veio do Supabase
            link_remoto = f"{link_pdf_final}#page={row['PAGINA']}"
            
            html += f"""
                <tr>
                    <td><span style="font-weight:bold; color:#0056b3;">{row['PAGINA']}</span></td>
                    <td>{row['NOME']}</td>
                    <td>{row['AIH']}</td>
                    <td>{row['PRONTUARIO']}</td>
                    <td style="text-align:center;">
                        <div class="btn-group">
                            <a href="{link_remoto}" target="_blank" class="btn-action btn-open" title="Ver Folha">
                                <i class="fas fa-external-link-alt"></i> Abrir
                            </a>
                            <button class="btn-action btn-add" onclick="addPage({row['PAGINA']}, this)">
                                <i class="fas fa-plus"></i> Incluir
                            </button>
                        </div>
                    </td>
                </tr>
            """

        html += """
            </tbody>
        </table>
    </div>

    <div class="collection-bar">
        <div>
            <strong>Páginas:</strong>
            <span id="pageList" class="pages-display">Nenhuma</span>
        </div>
        <div>
            <button class="btn-clear" onclick="clearPages()" title="Limpar"><i class="fas fa-trash"></i></button>
            <button class="btn-copy" onclick="copyAllPages()" id="btnCopy"><i class="fas fa-copy"></i> COPIAR</button>
        </div>
    </div>

    <script>
        $(document).ready(function() {
            $('#tabelaPacientes').DataTable({
                language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" },
                pageLength: 15,
                order: [[0, 'asc']]
            });
        });

        var collectedPages = [];
        var pageListElement = document.getElementById('pageList');

        function addPage(pageNumber, btn) {
            if (!collectedPages.includes(pageNumber)) {
                collectedPages.push(pageNumber);
                collectedPages.sort(function(a, b){return a - b});
                updateDisplay();
                btn.classList.add('btn-added');
                btn.innerHTML = '<i class="fas fa-check"></i>';
            }
        }

        function updateDisplay() {
            if(collectedPages.length === 0) {
                pageListElement.textContent = "Nenhuma";
            } else {
                pageListElement.textContent = collectedPages.join(', ');
            }
        }

        function clearPages() {
            collectedPages = [];
            updateDisplay();
            $('.btn-added').html('<i class="fas fa-plus"></i> Incluir').removeClass('btn-added');
        }

        function copyAllPages() {
            if (collectedPages.length > 0) {
                var textToCopy = collectedPages.join(',');
                navigator.clipboard.writeText(textToCopy).then(function() {
                    var btn = document.getElementById('btnCopy');
                    var originalText = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check-double"></i> COPIADO!';
                    btn.style.background = '#28a745';
                    setTimeout(function() { 
                        btn.innerHTML = originalText; 
                        btn.style.background = '#007bff'; 
                    }, 2000);
                }, function(err) { alert('Erro: ' + err); });
            } else { alert('Selecione páginas primeiro.'); }
        }
    </script>
</body>
</html>
"""
        # Salva e Sobe
        temp_file = os.path.join(BASE_DIR, "temp_indice.html")
        with open(temp_file, "w", encoding="utf-8") as f: f.write(html)
        
        link_html_final = forcar_upload_correto(temp_file, nome_html_remoto, "text/html; charset=utf-8")
        os.remove(temp_file)

        # 4. ATUALIZA BANCO
        print("💾 Salvando links na tabela 'controle_simuladas'...")
        try:
            supabase.table("controle_simuladas").delete().eq("data_arquivo", data_banco).execute()
            supabase.table("controle_simuladas").insert({
                "data_arquivo": data_banco,
                "nome_original": nome_pdf,
                "link_pdf": link_pdf_final,
                "link_indice": link_html_final
            }).execute()
            print("✅ Banco atualizado!")
        except Exception as e:
            print(f"⚠️ Erro ao salvar no banco: {e}")

        print("\n🎉 FIM! O índice premium está no ar.")

if __name__ == "__main__":
    processar()