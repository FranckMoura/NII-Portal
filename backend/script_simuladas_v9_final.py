import os
import pdfplumber
import pandas as pd
import re
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR SIMULADAS V20: GRAVAÇÃO EM BLOCOS (À PROVA DE FALHAS) ---")

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
    print(f"☁️  Subindo para a nuvem: {nome_remoto}...")
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

    link_pdf_final = forcar_upload_correto(caminho_pdf, nome_pdf_remoto, "application/pdf")
    if not link_pdf_final: return

    dados_extraidos = []
    
    ultimo_paciente_valido = {
        'NOME': None, 'AIH': None, 'PRONTUARIO': None,
        'ESPEC': None, 'CNS': None, 'PROC': None,
        'DT_INT': None, 'DT_SAI': None
    }
    
    print("🕵️  Lendo PDF (Ativando Limpeza Profunda)...")
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            total_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                num_pag = i + 1
                if num_pag % 50 == 0: print(f"   Pag {num_pag}/{total_paginas}...")
                
                texto = pagina.extract_text() or ""
                texto_sq = re.sub(r'\s+', '', texto).lower()
                
                # 1. CAMPOS DE TEXTO LIVRE
                m_nome = re.search(r'Paciente\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                nome_bruto = m_nome.group(1).replace('Prontuário', '').replace('Data Nasc', '').replace('Sexo', '').strip() if m_nome else None
                
                # LIMPEZA DO NOME: Remove prontuários grudados no final do nome
                nome = re.sub(r'[:\-\.]*\s*\d+$', '', nome_bruto).strip() if nome_bruto else None
                
                m_proc = re.search(r'Procedimento principal\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                proc = m_proc.group(1).replace('Diag. principal', '').strip() if m_proc else "-"
                
                # 2. CAMPOS ESTRUTURADOS (Squash)
                m_aih = re.search(r'aih:([\d\-]+)', texto_sq)
                aih = m_aih.group(1).strip() if m_aih else None
                
                m_pront = re.search(r'prontu.rio:(\d+)', texto_sq)
                pront = m_pront.group(1).strip() if m_pront else "N/A"
                
                m_espec = re.search(r'especialidade:(\d+-[a-z]+)', texto_sq)
                espec = m_espec.group(1).upper().replace('-', ' - ') if m_espec else "-"
                
                m_cns = re.search(r'cns/cpf:([\d\.\-]+)', texto_sq)
                if not m_cns: m_cns = re.search(r'cns:([\d\.\-]+)', texto_sq)
                cns = m_cns.group(1).upper() if m_cns else "-"
                
                m_dt_int = re.search(r'interna..o:?(\d{2}/\d{2}/\d{4})', texto_sq)
                dt_int = m_dt_int.group(1) if m_dt_int else "-"
                
                m_dt_sai = re.search(r'(?:sa.da|alta):?(\d{2}/\d{2}/\d{4})', texto_sq)
                dt_sai = m_dt_sai.group(1) if m_dt_sai else "-"

                todas_datas = re.findall(r'\d{2}/\d{2}/\d{4}', texto_sq)
                if dt_int == "-" and len(todas_datas) >= 3: dt_int = todas_datas[-2]
                if dt_sai == "-" and len(todas_datas) >= 4: dt_sai = todas_datas[-1]

                if nome and aih:
                    registro = {
                        'NOME': nome, 'AIH': aih, 'PRONTUARIO': pront, 
                        'ESPEC': espec, 'CNS': cns, 'PROC': proc,
                        'DT_INT': dt_int, 'DT_SAI': dt_sai, 'PAGINA': num_pag
                    }
                    ultimo_paciente_valido = registro.copy()
                    dados_extraidos.append(registro)
                        
                elif not nome and aih:
                    if ultimo_paciente_valido['AIH'] == aih:
                        registro = ultimo_paciente_valido.copy()
                        registro['NOME'] = registro['NOME'] + " (Cont.)"
                        registro['PAGINA'] = num_pag
                        dados_extraidos.append(registro)
                        
    except Exception as e:
        print(f"❌ Erro leitura PDF: {e}")
        return

    print(f"✅ Extraído: {len(dados_extraidos)} registros detalhados.")

    if dados_extraidos:
        df = pd.DataFrame(dados_extraidos)
        
        html_top = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Índice de Simuladas - NII</title>
    
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>

    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        body { font-family: 'Roboto', sans-serif; background: #f3f4f6; color: #1e293b; padding: 0; margin: 0; min-height: 100vh; padding-bottom: 90px; }
        
        .header-bg { background: linear-gradient(135deg, #000428 0%, #004e92 100%) !important; color: white !important; padding: 20px 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); margin-bottom: 25px; }
        .header-mini-logo { height: 40px; margin-right: 15px; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.3)); }
        .container { max-width: 1500px; margin: 0 auto; padding: 0 15px; }

        .btn-back { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; display: flex; align-items: center; gap: 8px; text-decoration: none; }
        .btn-back:hover { background: rgba(255,255,255,0.3); color: white; }

        .table-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; overflow-x: auto; }
        
        table.dataTable { width: 100% !important; border-collapse: collapse !important; }
        table.dataTable thead th { background-color: #004e92 !important; color: white !important; font-weight: 700 !important; text-transform: uppercase; border: none !important; padding: 10px 8px !important; font-size: 0.75rem; white-space: nowrap; }
        table.dataTable tbody td { padding: 6px 8px !important; border-bottom: 1px solid #f1f5f9; color: #334155; font-size: 0.75rem; vertical-align: middle; }
        
        /* Protege as colunas numéricas contra quebra de linha na tela */
        .nowrap-col { white-space: nowrap !important; }

        .dt-button { background: #10b981 !important; color: white !important; border: none !important; border-radius: 6px !important; padding: 6px 12px !important; font-weight: 600 !important; font-size: 0.75rem !important; }
        .dt-button:hover { background: #059669 !important; }

        .badge-proc { background: #e2e8f0; color: #1e293b; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; white-space: nowrap; }
        .badge-dt { background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; white-space: nowrap; }

        .btn-action { border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.7rem; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; color: white; font-weight: 600; transition: 0.2s; }
        .btn-add { background: #10b981; } .btn-add:hover { background: #059669; }
        .btn-added { background: #94a3b8; cursor: not-allowed; }
        .btn-open { background: #0ea5e9; } .btn-open:hover { background: #0284c7; }

        .collection-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: #0f172a; color: white; padding: 15px 30px; box-shadow: 0 -4px 15px rgba(0,0,0,0.3); z-index: 1000; display: flex; justify-content: space-between; align-items: center; }
        .pages-display { font-family: monospace; color: #fbbf24; font-size: 1rem; margin-left: 10px; font-weight:bold; }
        .btn-copy { background: #3b82f6; color: white; border: none; padding: 8px 20px; border-radius: 50px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-copy:hover { transform: scale(1.05); }
        .btn-clear { background: transparent; border: none; color: #94a3b8; margin-right: 15px; cursor:pointer; text-decoration: underline; font-size: 0.8rem; }

        /* IMPRESSÃO OFICIAL */
        .header-print { display: none; }
        #print-footer { display: none; }
        @media print {
            @page { margin: 10mm; size: A4 landscape; }
            body { background: white !important; font-size: 8pt !important; padding: 0 !important; color: #000 !important; font-family: 'Arial', sans-serif !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
            .no-print, .collection-bar, .dataTables_filter, .dataTables_length, .dataTables_info, .dt-buttons, .table-search { display: none !important; }
            .header-bg { display: none !important; }
            
            .header-print { display: flex !important; align-items: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; }
            .header-print img { height: 40px; margin-right: 15px; }
            .header-info { flex: 1; text-align: center; }
            .header-info h1 { margin: 0; font-size: 14pt; font-weight: 900; text-transform: uppercase; color: #000;}
            .header-info h2 { margin: 2px 0; font-size: 11pt; font-weight: bold; color: #000;}
            .header-meta { font-size: 8pt; text-align: right; line-height: 1.2; color: #000;}
            
            .table-card { box-shadow: none !important; border: none !important; padding: 0 !important; }
            table.dataTable { border: 1px solid #000 !important; width: 100% !important; }
            table.dataTable th { background-color: #eee !important; color: #000 !important; font-weight: 900 !important; border: 1px solid #000 !important; font-size: 8pt !important; padding: 4px !important; }
            table.dataTable td { border: 1px solid #000 !important; padding: 4px !important; font-size: 8pt !important; color: #000 !important; }
            .badge-proc, .badge-dt { background: none !important; color: #000 !important; padding: 0 !important; font-weight: normal; }
            
            #print-footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 7pt; border-top: 1px solid #000; padding-top: 5px; display: block !important; color: #000; }
        }
    </style>
</head>
<body>

    <div class='header-bg no-print'>
        <div class='max-w-7xl mx-auto flex justify-between items-center px-4'>
            <div class="flex items-center gap-4">
                <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-file-medical text-3xl"></i></div>
                <div>
                    <h1 class='text-3xl font-bold'>Índice de Faturamento</h1>
                    <p class='text-gray-300'>Prévia de Simuladas: VAR_NOME_PDF</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <img src="https://voweywtzoldwfhgkniup.supabase.co/storage/v1/object/public/arquivos-faturamento/logo.png" alt="Logo HSH" class="header-mini-logo">
                <a href="../index_v2.html" class="btn-back"><i class="fas fa-arrow-left"></i> Voltar</a>
            </div>
        </div>
    </div>

    <div class="header-print">
        <img src="https://voweywtzoldwfhgkniup.supabase.co/storage/v1/object/public/arquivos-faturamento/logo.png" alt="Logo">
        <div class="header-info">
            <h1>Hospital Beneficente Santa Helena</h1>
            <h2>Índice de Faturamento (Prévia Simuladas)</h2>
            <p style="font-size:10pt; margin:0;">Portal NII - Núcleo Interno de Informação</p>
        </div>
        <div class="header-meta">
            <div><b>Arquivo:</b> VAR_NOME_PDF</div>
            <div><b>Emissão:</b> VAR_DATA_HOJE</div>
        </div>
    </div>

    <div class="container">
        <div class="table-card">
            <table id="tabelaPacientes" class="display compact w-full">
                <thead>
                    <tr>
                        <th style="width: 30px;">Pág</th>
                        <th>Paciente</th>
                        <th>CNS/CPF</th>
                        <th>AIH</th>
                        <th style="width: 60px;">Prontuário</th>
                        <th>Especialidade</th>
                        <th>Procedimento Principal</th>
                        <th style="width: 60px;">Internação</th>
                        <th style="width: 60px;">Saída</th>
                        <th class="no-print" style="width: 120px; text-align:center;">Ações</th>
                    </tr>
                    <tr class="table-search no-print">
                        </tr>
                </thead>
                <tbody>
"""
        print(f"⚙️  Construindo tabela HTML com {len(df)} pacientes...")
        html_rows = ""
        for _, row in df.iterrows():
            link_remoto = f"{link_pdf_final}#page={row['PAGINA']}"
            proc_curto = str(row['PROC'])[:35] + "..." if len(str(row['PROC'])) > 35 else row['PROC']
            
            html_rows += f"""
                <tr>
                    <td class="nowrap-col"><b class="text-blue-700 text-sm">{row['PAGINA']}</b></td>
                    <td><b class="text-gray-800 uppercase">{row['NOME']}</b></td>
                    <td class="nowrap-col text-gray-500 font-medium">{row['CNS']}</td>
                    <td class="nowrap-col"><span class="badge-proc">{row['AIH']}</span></td>
                    <td class="nowrap-col font-bold">{row['PRONTUARIO']}</td>
                    <td class="nowrap-col text-gray-600 text-[0.7rem] uppercase">{row['ESPEC']}</td>
                    <td title="{row['PROC']}">{proc_curto}</td>
                    <td class="nowrap-col"><span class="badge-dt text-green-700">{row['DT_INT']}</span></td>
                    <td class="nowrap-col"><span class="badge-dt text-red-600">{row['DT_SAI']}</span></td>
                    <td class="nowrap-col no-print text-center">
                        <div class="btn-group flex gap-1 justify-center">
                            <a href="{link_remoto}" target="_blank" class="btn-action btn-open" title="Visualizar">
                                <i class="fas fa-external-link-alt"></i> Abrir
                            </a>
                            <button class="btn-action btn-add" onclick="addPage({row['PAGINA']}, this)">
                                <i class="fas fa-plus"></i> Imprimir
                            </button>
                        </div>
                    </td>
                </tr>
            """

        html_bottom = """
                </tbody>
            </table>
        </div>
    </div>

    <div class="collection-bar no-print">
        <div>
            <i class="fas fa-print text-gray-400 mr-2"></i>
            <strong>Fila de Impressão:</strong>
            <span id="pageList" class="pages-display">Nenhuma página</span>
        </div>
        <div>
            <button class="btn-clear" onclick="clearPages()">Limpar Tudo</button>
            <button class="btn-copy" onclick="copyAllPages()" id="btnCopy"><i class="fas fa-copy mr-1"></i> COPIAR LISTA</button>
        </div>
    </div>

    <div id="print-footer">
        Relatório gerado pelo Portal NII em VAR_DATA_HOJE.
    </div>

    <script>
        $(document).ready(function() {
            $('#tabelaPacientes thead tr:eq(0) th').each( function (i) {
                if(i === 9) { 
                    $('.table-search').append('<th></th>');
                } else {
                    $('.table-search').append('<th><input type="text" placeholder="Filtrar..." class="w-full p-1 text-[0.65rem] border rounded text-gray-700 outline-none focus:ring-1 focus:ring-blue-500 font-normal" /></th>');
                }
            });

            var table = $('#tabelaPacientes').DataTable({
                language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" },
                dom: 'Bfrtip',
                pageLength: 20,
                order: [[0, 'asc']],
                buttons: [
                    { extend: 'csvHtml5', text: '<i class="fas fa-file-csv"></i> CSV', className: 'dt-button bg-green-600 hover:bg-green-700' },
                    { extend: 'excelHtml5', text: '<i class="fas fa-file-excel"></i> Excel', className: 'dt-button bg-blue-600 hover:bg-blue-700' },
                    { extend: 'print', text: '<i class="fas fa-print"></i> Relatório Oficial', className: 'dt-button bg-gray-600 hover:bg-gray-700', action: function () { window.print(); } }
                ],
                orderCellsTop: true,
                initComplete: function () {
                    this.api().columns().every( function () {
                        var that = this;
                        $('input', $('.table-search th').eq(this.index())).on('keyup change clear', function () {
                            if (that.search() !== this.value) { that.search(this.value).draw(); }
                        });
                    });
                }
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
                btn.innerHTML = '<i class="fas fa-check"></i> Fila';
            }
        }

        function updateDisplay() {
            pageListElement.textContent = collectedPages.length === 0 ? "Nenhuma página" : collectedPages.join(', ');
        }

        function clearPages() {
            collectedPages = [];
            updateDisplay();
            $('.btn-added').html('<i class="fas fa-plus"></i> Imprimir').removeClass('btn-added');
        }

        function copyAllPages() {
            if (collectedPages.length > 0) {
                var textToCopy = collectedPages.join(',');
                navigator.clipboard.writeText(textToCopy).then(function() {
                    var btn = document.getElementById('btnCopy');
                    var originalText = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check-double"></i> COPIADO!';
                    btn.style.background = '#10b981';
                    setTimeout(function() { btn.innerHTML = originalText; btn.style.background = '#3b82f6'; }, 2000);
                }, function(err) { alert('Erro: ' + err); });
            } else { alert('Adicione páginas à fila de impressão primeiro.'); }
        }
    </script>
</body>
</html>
"""
        data_print = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        print("💾 Gravando arquivo HTML no disco em blocos (À prova de falhas)...")
        temp_file = os.path.join(BASE_DIR, "temp_indice.html")
        
        # O SEGREDO: SALVAR BLOCO POR BLOCO COM f.write()
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(html_top.replace("VAR_DATA_HOJE", data_print).replace("VAR_NOME_PDF", nome_pdf))
            f.write(html_rows)
            f.write(html_bottom)
        
        link_html_final = forcar_upload_correto(temp_file, nome_html_remoto, "text/html; charset=utf-8")
        os.remove(temp_file)

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

        print("\n🎉 FIM! O índice premium FINAL está no ar.")

if __name__ == "__main__":
    processar()