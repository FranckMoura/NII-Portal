import os
import pdfplumber
import re
import json
import time
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR SIMULADAS V27: ANTI-QUEDAS E CONTINUAÇÃO POR AIH ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ENTRADA = os.path.join(BASE_DIR, "entradas_pdf")
if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)

try: supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e: print(f"❌ Erro de conexão: {e}"); exit()

# --- FUNÇÕES DE LIMPEZA E UPLOAD ---
def desamassar_linha_procedimento(linha_texto):
    m_data = re.search(r'(\d{2}/\d{4})', linha_texto)
    if not m_data: return None
    cmpt = m_data.group(1)
    desc = linha_texto[m_data.end():].strip()
    resto_antes = linha_texto[:m_data.start()].strip()
    partes = resto_antes.split()
    if partes:
        ultimo_bloco = partes[-1]
        m_qtd = re.search(r'(\d+)$', ultimo_bloco)
        if m_qtd:
            qtd = m_qtd.group(1)
            partes[-1] = ultimo_bloco[:m_qtd.start()]
            if not partes[-1]: partes.pop()
        else: qtd = "1"
    else: qtd = "1"
    bloco_esq = "".join(partes) 
    if len(bloco_esq) >= 10:
        codigo = bloco_esq[:10]
        docs_str = bloco_esq[10:]
    else:
        codigo = bloco_esq; docs_str = ""
    docs_sep = []
    if docs_str:
        if len(docs_str) == 21 and docs_str.startswith('7'): 
            docs_sep.extend([docs_str[:15], docs_str[15:]])
        elif len(docs_str) > 15 and docs_str.startswith('7'):
            docs_sep.append(docs_str[:15])
            resto = docs_str[15:]
            if len(resto) == 13: docs_sep.extend([resto[:7], resto[7:]]) 
            elif len(resto) > 0: docs_sep.append(resto)
        elif len(docs_str) == 14: 
             docs_sep.extend([docs_str[:7], docs_str[7:]])
        else: docs_sep.append(docs_str)
    return {"codigo": codigo, "qtde": qtd, "cmpt": cmpt, "descricao": desc, "doc_cnes": " / ".join(docs_sep) if docs_sep else "-"}

def forcar_upload_correto(caminho_local, nome_remoto, content_type):
    print(f"☁️  Subindo para a nuvem: {nome_remoto}...")
    for tentativa in range(3):
        try:
            try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
            except: pass
            with open(caminho_local, 'rb') as f:
                supabase.storage.from_(NOME_BUCKET).upload(path=nome_remoto, file=f, file_options={"content-type": content_type, "upsert": "true", "cache-control": "3600"})
            return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
        except Exception as e:
            print(f"   ⚠️ Falha no upload (T{tentativa+1}/3). Aguardando... Erro: {e}")
            time.sleep(3)
    return None

def inserir_com_tentativas(tabela, dados, tamanho_lote=100):
    total = len(dados)
    for i in range(0, total, tamanho_lote):
        lote = dados[i:i+tamanho_lote]
        sucesso = False
        for tentativa in range(1, 4):
            try:
                supabase.table(tabela).insert(lote).execute()
                sucesso = True
                break
            except Exception as e:
                print(f"\n   ⚠️ Falha no lote {i} da tabela {tabela} (Tentativa {tentativa}/3). Reconectando...")
                time.sleep(3)
        if not sucesso:
            raise Exception(f"Falha de conexão definitiva ao inserir na tabela {tabela}.")

# --- PROCESSAMENTO PRINCIPAL ---
def processar():
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]
    if not arquivos: print(f"❌ Pasta '{PASTA_ENTRADA}' vazia!"); return

    nome_pdf = arquivos[0]
    caminho_pdf = os.path.join(PASTA_ENTRADA, nome_pdf)
    competencia_global = "02/2026"
    data_banco = datetime.now().strftime('%Y-%m-%d')
    data_print = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    nome_pdf_remoto = f"PDFs/{datetime.now().strftime('%d-%m-%Y')}_{nome_pdf}"
    nome_html_remoto = f"INDICES/Indice_{datetime.now().strftime('%d-%m-%Y')}_{nome_pdf.replace('.pdf', '.html')}"

    print(f"📄 Processando Megarquivo: {nome_pdf}")
    link_pdf_final = forcar_upload_correto(caminho_pdf, nome_pdf_remoto, "application/pdf")
    if not link_pdf_final: return

    pacientes_map = {} 
    lista_procedimentos_banco = []
    lista_valores_banco = []
    
    ultimo_paciente_valido = None
    chave_ativa = None
    
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            total_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                num_pag = i + 1
                if num_pag % 20 == 0: print(f"   Lendo Pag {num_pag}/{total_paginas}...")
                
                texto = pagina.extract_text() or ""
                texto_sq = re.sub(r'\s+', '', texto).lower()
                texto_flat = re.sub(r'\s+', ' ', texto) 
                
                m_nome = re.search(r'Paciente\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                nome = m_nome.group(1).replace('Prontuário', '').replace('Data Nasc', '').replace('Sexo', '').strip() if m_nome else None
                nome = re.sub(r'[:\-\.]*\s*\d+$', '', nome).strip() if nome else None
                
                m_proc = re.search(r'Procedimento principal\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                proc = m_proc.group(1).replace('Diag. principal', '').strip() if m_proc else "-"
                
                m_aih = re.search(r'aih:([\d\-]+)', texto_sq)
                aih = m_aih.group(1).strip() if m_aih else None
                
                pront = (re.search(r'prontu.rio:(\d+)', texto_sq) or re.search(r'', '')).group(1) if re.search(r'prontu.rio:(\d+)', texto_sq) else "N/A"
                espec = (re.search(r'especialidade:(\d+-[a-z]+)', texto_sq) or re.search(r'', '')).group(1).upper().replace('-', ' - ') if re.search(r'especialidade:(\d+-[a-z]+)', texto_sq) else "-"
                m_cns = re.search(r'cns/cpf:([\d\.\-]+)', texto_sq) or re.search(r'cns:([\d\.\-]+)', texto_sq)
                cns = m_cns.group(1).upper() if m_cns else "-"
                
                dt_int = (re.search(r'interna..o:?(\d{2}/\d{2}/\d{4})', texto_sq) or re.search(r'', '')).group(1) if re.search(r'interna..o:?(\d{2}/\d{2}/\d{4})', texto_sq) else "-"
                dt_sai = (re.search(r'(?:sa.da|alta):?(\d{2}/\d{2}/\d{4})', texto_sq) or re.search(r'', '')).group(1) if re.search(r'(?:sa.da|alta):?(\d{2}/\d{2}/\d{4})', texto_sq) else "-"

                # === A REGRA DE OURO DA AIH ===
                is_continuation = (aih and ultimo_paciente_valido and aih == ultimo_paciente_valido['AIH'])

                if is_continuation:
                    nome_base = ultimo_paciente_valido['NOME'].replace(" (Cont.)", "")
                    nome_cont = f"{nome_base} (Cont.)"
                    chave_ativa = f"{nome_cont}_{aih}_{num_pag}"
                    
                    pacientes_map[chave_ativa] = {
                        'NOME': nome_cont, 'AIH': aih, 'PRONTUARIO': ultimo_paciente_valido['PRONTUARIO'], 
                        'ESPEC': ultimo_paciente_valido['ESPEC'], 'CNS': ultimo_paciente_valido['CNS'], 
                        'PROC': ultimo_paciente_valido['PROC'], 'DT_INT': dt_int if dt_int != "-" else ultimo_paciente_valido['DT_INT'], 
                        'DT_SAI': dt_sai if dt_sai != "-" else ultimo_paciente_valido['DT_SAI'], 
                        'PAGINA': num_pag, 'procedimentos': [], 'valores': [], 'valor_total': "0,00"
                    }
                    ultimo_paciente_valido = pacientes_map[chave_ativa].copy()

                elif nome and aih:
                    chave_ativa = f"{nome}_{aih}_{num_pag}"
                    pacientes_map[chave_ativa] = { 'NOME': nome, 'AIH': aih, 'PRONTUARIO': pront, 'ESPEC': espec, 'CNS': cns, 'PROC': proc, 'DT_INT': dt_int, 'DT_SAI': dt_sai, 'PAGINA': num_pag, 'procedimentos': [], 'valores': [], 'valor_total': "0,00" }
                    ultimo_paciente_valido = pacientes_map[chave_ativa].copy()
                else:
                    continue # Página sem AIH é inútil

                # 2. TABELA DE PROCEDIMENTOS
                m_bloco_proc = re.search(r'PROCEDIMENTOS\s+REALIZADOS(.*?)VALORES\s+DA\s+PR[EÉ]VIA', texto_flat, re.IGNORECASE)
                if m_bloco_proc:
                    bloco = m_bloco_proc.group(1)
                    bloco = re.sub(r'Linha\s+Procedimento.*?Descri[cç][aã]o', '', bloco, flags=re.IGNORECASE)
                    padrao = r'\b(\d{1,3})\s+(\d{10}\b.*?\d{2}/\d{4}.*?)(?=\s+\b\d{1,3}\s+\d{10}\b|$)'
                    for m in re.finditer(padrao, bloco):
                        lnh = m.group(1)
                        dados_proc = desamassar_linha_procedimento(m.group(2).strip())
                        if dados_proc:
                            dados_proc['linha'] = lnh
                            pacientes_map[chave_ativa]['procedimentos'].append(dados_proc)
                            lista_procedimentos_banco.append({
                                "competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": pacientes_map[chave_ativa]['NOME'],
                                "linha": lnh, "codigo": dados_proc["codigo"], "qtde": dados_proc["qtde"], "cmpt": dados_proc["cmpt"],
                                "documento_cnes": dados_proc["doc_cnes"], "descricao": dados_proc["descricao"]
                            })

                # 3. TABELA DE VALORES
                m_bloco_val = re.search(r'VALORES\s+DA\s+PR[EÉ]VIA(.*?)(?:SERVI[CÇ]O/CLASSIFICA|CNAER:|$)', texto_flat, re.IGNORECASE)
                if m_bloco_val:
                    b_val = m_bloco_val.group(1)
                    b_val = re.sub(r'Serviço Hospitalar.*?Terceiro', '', b_val, flags=re.IGNORECASE)
                    for m in re.finditer(r'(\d{2}\.\d{2}\.\d{2}\-[^\d].*?)(?=\s+\d{2}\.\d{2}\.\d{2}\-|\s+Total Geral:|$)', b_val, re.IGNORECASE):
                        item = m.group(1).strip()
                        m_sep = re.search(r'(.*?)\s+([\d\.\s,]+)$', item)
                        if m_sep:
                            vals = re.findall(r'[\d\.]*,\d{2}', m_sep.group(2))
                            val_ext = vals[-1] if vals else "0,00"
                            desc_ext = m_sep.group(1).strip()
                            pacientes_map[chave_ativa]['valores'].append({"descricao": desc_ext, "valor": val_ext})
                            lista_valores_banco.append({"competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": pacientes_map[chave_ativa]['NOME'], "grupo_consolidado": desc_ext, "valor_rs": val_ext})
                            
                    m_tot = re.search(r'Total Geral:\s*([\d\.\s,]+)', b_val, re.IGNORECASE)
                    if m_tot:
                        vals = re.findall(r'[\d\.]*,\d{2}', m_tot.group(1))
                        if vals: 
                            pacientes_map[chave_ativa]['valor_total'] = vals[-1]
                            lista_valores_banco.append({"competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": pacientes_map[chave_ativa]['NOME'], "grupo_consolidado": "TOTAL GERAL", "valor_rs": vals[-1]})

    except Exception as e: print(f"❌ Erro Crítico PDF: {e}"); return

    print(f"✅ Extrato concluído: {len(pacientes_map)} páginas validadas.")

    # --- 4. GERAR O HTML GIGANTE ---
    print("⚙️  Construindo o super HTML (Índice Standalone)...")
    
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
        .nowrap-col { white-space: nowrap !important; }
        .dt-button { background: #10b981 !important; color: white !important; border: none !important; border-radius: 6px !important; padding: 6px 12px !important; font-weight: 600 !important; font-size: 0.75rem !important; }
        .dt-button:hover { background: #059669 !important; }
        .badge-proc { background: #e2e8f0; color: #1e293b; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; white-space: nowrap; }
        .badge-dt { background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; white-space: nowrap; }
        .btn-action { border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.7rem; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; color: white; font-weight: 600; transition: 0.2s; }
        .btn-add { background: #10b981; } .btn-add:hover { background: #059669; }
        .btn-added { background: #94a3b8; cursor: not-allowed; }
        .btn-open { background: #0ea5e9; } .btn-open:hover { background: #0284c7; }
        .btn-fatura { background: #f59e0b; } .btn-fatura:hover { background: #d97706; }
        .collection-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: #0f172a; color: white; padding: 15px 30px; box-shadow: 0 -4px 15px rgba(0,0,0,0.3); z-index: 1000; display: flex; justify-content: space-between; align-items: center; }
        .pages-display { font-family: monospace; color: #fbbf24; font-size: 1rem; margin-left: 10px; font-weight:bold; }
        .btn-copy { background: #3b82f6; color: white; border: none; padding: 8px 20px; border-radius: 50px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-copy:hover { transform: scale(1.05); }
        .btn-clear { background: transparent; border: none; color: #94a3b8; margin-right: 15px; cursor:pointer; text-decoration: underline; font-size: 0.8rem; }
        .conta-modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(5px); z-index: 9999; display: none; justify-content: center; align-items: center; }
        .conta-modal-overlay.active { display: flex; }
        .conta-modal-content { background: white; width: 95%; max-width: 1000px; border-radius: 16px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); transform: scale(0.95); transition: 0.3s; display:flex; flex-direction:column; max-height: 90vh; }
        .conta-modal-overlay.active .conta-modal-content { transform: scale(1); }
        .conta-header { background: #004e92; color: white; padding: 20px 25px; display: flex; justify-content: space-between; align-items: center; flex-shrink:0; }
        .conta-body { padding: 25px; background: #f8fafc; overflow-y: auto; flex:1; }
        .tabela-itens { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .tabela-itens th { background: #e2e8f0; color: #475569; font-size: 0.75rem; text-transform: uppercase; padding: 10px; text-align: left; }
        .tabela-itens td { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.8rem; color: #1e293b; }
        .tabela-itens tr:last-child td { border-bottom: none; }
        .tabela-itens tbody tr:hover { background: #f8fafc; }
        @media print {
            @page { margin: 10mm; size: A4 landscape; }
            body { background: white !important; padding: 0 !important; }
            .no-print, .collection-bar, .dataTables_filter, .dataTables_length, .dataTables_info, .dt-buttons, .table-search { display: none !important; }
            .header-bg { display: none !important; }
            .header-print { display: flex !important; align-items: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; }
            .header-print img { height: 40px; margin-right: 15px; }
            .table-card { box-shadow: none !important; border: none !important; padding: 0 !important; }
            table.dataTable { border: 1px solid #000 !important; width: 100% !important; }
            table.dataTable th { background-color: #eee !important; color: #000 !important; border: 1px solid #000 !important; padding: 4px !important; }
            table.dataTable td { border: 1px solid #000 !important; padding: 4px !important; }
            #print-footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 7pt; border-top: 1px solid #000; padding-top: 5px; display: block !important; color: #000; }
        }
    </style>
</head>
<body>
    <div class="conta-modal-overlay no-print" id="contaModal">
        <div class="conta-modal-content">
            <div class="conta-header">
                <div>
                    <h2 class="text-2xl font-bold m-0 uppercase" id="contaNome">Nome do Paciente</h2>
                    <p class="text-sm text-blue-200 m-0 mt-1 font-mono" id="contaAih">AIH: 123456789</p>
                </div>
                <button onclick="document.getElementById('contaModal').classList.remove('active')" class="text-white text-4xl hover:text-red-400 leading-none">&times;</button>
            </div>
            <div class="conta-body">
                <div class="flex gap-4 mb-6 flex-wrap">
                   <div class="flex-1 bg-blue-50 border border-blue-200 p-4 rounded-xl">
                       <h4 class="text-blue-800 text-xs font-bold uppercase mb-1">Procedimento Principal</h4>
                       <p class="text-blue-900 font-bold text-sm" id="contaProcPrincipal"></p>
                   </div>
                   <div class="bg-green-50 border border-green-200 p-4 rounded-xl min-w-[200px] text-center shadow-sm">
                       <h4 class="text-green-800 text-xs font-bold uppercase mb-1">Total Faturado (Prévia)</h4>
                       <p class="text-green-700 font-black text-3xl" id="contaValorTotal">R$ 0,00</p>
                   </div>
                </div>
                <h4 class="font-bold text-gray-700 mb-2 uppercase text-sm border-b pb-2"><i class="fas fa-list-ol text-blue-600 mr-1"></i> Procedimentos Realizados</h4>
                <div class="overflow-x-auto mb-6 border border-gray-200 rounded-lg">
                    <table class="tabela-itens !mb-0">
                        <thead><tr><th style="width:30px">Lnh</th><th style="width:100px">Procedimento</th><th>Documento/CNES</th><th style="width:40px; text-align:center">Qtd</th><th style="width:60px">Cmpt</th><th>Descrição</th></tr></thead>
                        <tbody id="contaProcedimentosBody"></tbody>
                    </table>
                </div>
                <h4 class="font-bold text-gray-700 mb-2 uppercase text-sm border-b pb-2"><i class="fas fa-dollar-sign text-green-600 mr-1"></i> Resumo Financeiro</h4>
                <table class="tabela-itens">
                    <thead><tr><th>Grupo Consolidado (Tabela SIA/SIH)</th><th style="text-align: right; width:120px">Valor (R$)</th></tr></thead>
                    <tbody id="contaResumoBody"></tbody>
                </table>
            </div>
        </div>
    </div>

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
                <a href="../modulo_estrategico.html" class="btn-back"><i class="fas fa-arrow-left"></i> Voltar</a>
            </div>
        </div>
    </div>

    <div class="header-print">
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
                        <th class="no-print" style="width: 180px; text-align:center;">Ações</th>
                    </tr>
                    <tr class="table-search no-print"></tr>
                </thead>
                <tbody>
"""
    
    html_rows = ""
    for k, row in pacientes_map.items():
        link_remoto = f"{link_pdf_final}#page={row['PAGINA']}"
        proc_curto = str(row['PROC'])[:35] + "..." if len(str(row['PROC'])) > 35 else row['PROC']
        
        obj_dados = {
            "procedimento_principal": row['PROC'],
            "procedimentos": row['procedimentos'],
            "resumo_financeiro": row['valores']
        }
        json_seguro = json.dumps(obj_dados).replace('"', '&quot;').replace("'", "&#39;")
        nome_seguro = row['NOME'].replace("'", "\\'").replace('"', '&quot;')

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
                            <a href="{link_remoto}" target="_blank" class="btn-action btn-open" title="Visualizar PDF"><i class="fas fa-external-link-alt"></i> Abrir</a>
                            <button class="btn-action btn-add" onclick="addPage({row['PAGINA']}, this)"><i class="fas fa-plus"></i> Imprimir</button>
                            <button class="btn-action btn-fatura" onclick="abrirConta('{nome_seguro}', '{row['AIH']}', '{row['valor_total']}', '{json_seguro}')"><i class="fas fa-list-alt"></i> Detalhes</button>
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
        <div><i class="fas fa-print text-gray-400 mr-2"></i><strong>Fila de Impressão:</strong><span id="pageList" class="pages-display">Nenhuma página</span></div>
        <div><button class="btn-clear" onclick="clearPages()">Limpar Tudo</button><button class="btn-copy" onclick="copyAllPages()" id="btnCopy"><i class="fas fa-copy mr-1"></i> COPIAR LISTA</button></div>
    </div>

    <script>
        $(document).ready(function() {
            $('#tabelaPacientes thead tr:eq(0) th').each( function (i) {
                if(i === 9) { $('.table-search').append('<th></th>'); } 
                else { $('.table-search').append('<th><input type="text" placeholder="Filtrar..." class="w-full p-1 text-[0.65rem] border rounded text-gray-700 outline-none focus:ring-1 focus:ring-blue-500 font-normal" /></th>'); }
            });
            var table = $('#tabelaPacientes').DataTable({
                language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" },
                dom: 'lBrtip', pageLength: 20, order: [[0, 'asc']],
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

        function abrirConta(nome, aih, valorTotal, jsonString) {
            document.getElementById('contaNome').innerText = nome;
            document.getElementById('contaAih').innerText = "AIH: " + aih;
            document.getElementById('contaValorTotal').innerText = "R$ " + valorTotal;
            try {
                var dados = JSON.parse(jsonString);
                document.getElementById('contaProcPrincipal').innerText = dados.procedimento_principal || 'NÃO INFORMADO';
                
                var tBodyP = document.getElementById('contaProcedimentosBody'); tBodyP.innerHTML = "";
                if(dados.procedimentos && dados.procedimentos.length > 0) {
                    dados.procedimentos.forEach(function(p) {
                        tBodyP.innerHTML += `<tr><td class="font-bold text-gray-500">${p.linha}</td><td class="font-mono text-blue-700">${p.codigo}</td><td class="font-mono text-[0.7rem] text-gray-500">${p.doc_cnes}</td><td class="text-center font-bold text-gray-700">${p.qtde}</td><td class="text-gray-500 text-center">${p.cmpt}</td><td class="font-semibold uppercase">${p.descricao}</td></tr>`;
                    });
                } else { tBodyP.innerHTML = '<tr><td colspan="6" class="text-center text-gray-500 py-4">Nenhum procedimento registrado.</td></tr>'; }
                
                var tBodyV = document.getElementById('contaResumoBody'); tBodyV.innerHTML = "";
                if(dados.resumo_financeiro && dados.resumo_financeiro.length > 0) {
                    dados.resumo_financeiro.forEach(function(v) {
                        tBodyV.innerHTML += `<tr><td class="uppercase text-gray-700 font-semibold">${v.descricao}</td><td class="text-right font-mono font-bold text-blue-900">${v.valor}</td></tr>`;
                    });
                } else { tBodyV.innerHTML = '<tr><td colspan="2" class="text-center text-gray-500 py-4">Nenhum valor extraído.</td></tr>'; }
                
            } catch(e) { console.error("Erro no JSON", e); }
            
            document.getElementById('contaModal').classList.add('active');
        }

        var collectedPages = [];
        function addPage(pageNumber, btn) {
            if (!collectedPages.includes(pageNumber)) {
                collectedPages.push(pageNumber); collectedPages.sort(function(a, b){return a - b});
                document.getElementById('pageList').textContent = collectedPages.join(', ');
                btn.classList.add('btn-added'); btn.innerHTML = '<i class="fas fa-check"></i> Fila';
            }
        }
        function clearPages() {
            collectedPages = []; document.getElementById('pageList').textContent = "Nenhuma página";
            $('.btn-added').html('<i class="fas fa-plus"></i> Imprimir').removeClass('btn-added');
        }
        function copyAllPages() {
            if (collectedPages.length > 0) {
                navigator.clipboard.writeText(collectedPages.join(',')).then(function() {
                    var btn = document.getElementById('btnCopy'); var originalText = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check-double"></i> COPIADO!'; btn.style.background = '#10b981';
                    setTimeout(function() { btn.innerHTML = originalText; btn.style.background = '#3b82f6'; }, 2000);
                });
            } else { alert('Adicione páginas à fila primeiro.'); }
        }
    </script>
</body>
</html>
"""
    
    print("💾 Gravando super arquivo HTML no disco...")
    temp_file = os.path.join(BASE_DIR, "temp_indice.html")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(html_top.replace("VAR_DATA_HOJE", data_print).replace("VAR_NOME_PDF", nome_pdf))
        f.write(html_rows)
        f.write(html_bottom)
        
    link_html_final = forcar_upload_correto(temp_file, nome_html_remoto, "text/html; charset=utf-8")
    os.remove(temp_file)

    print("💾 Atualizando banco de dados...")
    try:
        supabase.table("controle_simuladas").delete().eq("data_arquivo", data_banco).execute()
        supabase.table("simuladas_procedimentos").delete().eq("competencia_arquivo", competencia_global).execute()
        supabase.table("simuladas_valores").delete().eq("competencia_arquivo", competencia_global).execute()

        supabase.table("controle_simuladas").insert({
            "data_arquivo": data_banco, "nome_original": nome_pdf,
            "link_pdf": link_pdf_final, "link_indice": link_html_final
        }).execute()

        print("💾 Enviando Procedimentos para o Supabase em Lotes...")
        inserir_com_tentativas("simuladas_procedimentos", lista_procedimentos_banco)
            
        print("💾 Enviando Valores para o Supabase em Lotes...")
        inserir_com_tentativas("simuladas_valores", lista_valores_banco)
            
        print("✅ Banco de dados sincronizado e atualizado!")
    except Exception as e: print(f"⚠️ Erro ao salvar no banco: {e}")

    print("\n🎉 FIM! O ÍNDICE STANDALONE (.HTML) E O BANCO DE DADOS ESTÃO PRONTOS.")

if __name__ == "__main__":
    processar()