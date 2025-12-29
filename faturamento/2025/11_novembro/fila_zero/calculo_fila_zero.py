# ==============================================================================
# SISTEMA DE REPASSES - FILA ZERO (V5.0 - TABELA FORMATADA)
# ==============================================================================
import pdfplumber
import pandas as pd
import os
import re
import json
import glob
from datetime import datetime

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
print(f"--- Processando Fila Zero (V5.0 - Tabela Grid) ---")

pdf_receita = glob.glob(os.path.join(PASTA_SCRIPT, 'R_RECEITA*.pdf'))
pdf_producao = glob.glob(os.path.join(PASTA_SCRIPT, 'R_PRODUCAO*.pdf'))
ARQUIVO_PDF_RECEITA = pdf_receita[0] if pdf_receita else "NAO_ENCONTRADO"
ARQUIVO_PDF_PRODUCAO = pdf_producao[0] if pdf_producao else "NAO_ENCONTRADO"

def extrair_competencia(nome_arquivo):
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo)
    if match: return f"{match.group(1)}/{'20'+match.group(2)}", f"{match.group(1)}{'20'+match.group(2)}"
    return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")

def ler_valor_total_receita(caminho_pdf):
    if not os.path.exists(caminho_pdf): return 0.0
    total = 0.0
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                if "Total" in line or "TOTAL" in line:
                    valores = re.findall(r'[\d\.]*[\d]\,\d{2}', line)
                    if valores:
                        try: total = max(total, float(valores[-1].replace('.', '').replace(',', '.')))
                        except: pass
    return total

def processar_producao_detalhada():
    if not os.path.exists(ARQUIVO_PDF_PRODUCAO): return pd.DataFrame()
    dados_detalhados = []
    medico_atual = "DESCONHECIDO"
    aih_atual = "-"
    proc_atual = "-"
    data_atual = "-"
    with pdfplumber.open(ARQUIVO_PDF_PRODUCAO) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            lines = text.split('\n')
            for line in lines:
                if "Total" in line or "TOTAL" in line or "Prestador:" in line or "Rateio:" in line: continue
                if re.search(r'\(\d+\)', line) and not "Competência" in line: medico_atual = re.sub(r'\(\d+\)', '', line).strip()
                match_aih = re.search(r'\b(5\d{12})\b', line)
                if match_aih:
                    aih_atual = match_aih.group(1)
                    match_data = re.search(r'\d{2}/\d{2}', line)
                    if match_data: data_atual = match_data.group(0)
                match_proc = re.search(r'\d{10}\s+(.*)', line)
                if match_proc:
                    proc_temp = match_proc.group(1)
                    proc_atual = re.split(r'\d{1,3}[\.,]', proc_temp)[0].strip()
                valores_encontrados = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', line)
                eh_item_pagamento = ("Anestesista" in line or "Auxiliar" in line or "Cirurgião" in line or "Próprio" in line or "Clínico" in line)
                if valores_encontrados and eh_item_pagamento:
                    valor_str = valores_encontrados[-1].replace('.', '').replace(',', '.')
                    dados_detalhados.append({'Prestador': medico_atual, 'Data': data_atual, 'AIH': aih_atual, 'Procedimento': proc_atual if len(proc_atual) > 3 else "PROCEDIMENTO", 'Valor': float(valor_str)})
    if not dados_detalhados: return pd.DataFrame()
    return pd.DataFrame(dados_detalhados)

def gerar_html_fila_zero(df_detalhado, nome_arquivo, competencia_label, total_receita):
    df_resumo = df_detalhado.groupby('Prestador')['Valor'].sum().reset_index()
    df_resumo = df_resumo.sort_values(by='Valor', ascending=False)
    total_repassar = df_resumo['Valor'].sum()
    aihs_validas = df_detalhado[df_detalhado['AIH'] != '-']['AIH'].unique()
    qtd_procedimentos_reais = len(aihs_validas) if len(aihs_validas) > 0 else len(df_detalhado)

    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Fila Zero - {competencia_label}</title>
        <script src='https://cdn.tailwindcss.com'></script>
        <link rel='stylesheet' href='https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css'>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; background-color: #f3f4f6; }}
            .header-bg {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 1.5rem; border: 1px solid #e5e7eb; }}
            .tab-btn {{ cursor: pointer; padding: 10px 20px; font-weight: 600; border-bottom: 2px solid transparent; color: #6b7280; transition: all 0.3s; }}
            .tab-btn.active {{ border-bottom: 2px solid #2563eb; color: #2563eb; }}
            .hidden {{ display: none !important; }}

            /* ESTILO TABELA EXECUTIVA */
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
            th {{ background-color: #e2e8f0; color: #1e293b; font-weight: bold; text-transform: uppercase; padding: 10px; border: 1px solid #cbd5e1; text-align: left; }}
            td {{ padding: 8px; border: 1px solid #e2e8f0; color: #334155; vertical-align: middle; }}
            tr:nth-child(even) {{ background-color: #f8fafc; }}
            .text-right {{ text-align: right; }}
            .text-center {{ text-align: center; }}
            .font-bold {{ font-weight: 700; }}

            @media print {{
                @page {{ margin: 10mm; size: A4 portrait; }}
                body {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: white !important; font-size: 10px !important; color: #000 !important; }}
                .no-print, .dataTables_filter, .dataTables_length, .dataTables_info, .dataTables_paginate {{ display: none !important; }}
                .header-bg {{ padding: 10px !important; margin-bottom: 10px !important; }}
                .header-bg h1, .header-bg p, .header-bg i {{ color: white !important; -webkit-text-fill-color: white !important; }}
                .grid-print-row {{ display: grid !important; grid-template-columns: 1fr 1fr 1fr !important; gap: 10px !important; margin-bottom: 20px !important; }}
                .card {{ padding: 8px !important; box-shadow: none !important; border: 1px solid #000 !important; break-inside: avoid !important; }}
                .text-green-600, .text-blue-600, .text-purple-600 {{ color: #000 !important; font-weight: 800 !important; }}
                /* Bordas Pretas na Impressão */
                th {{ background-color: #ddd !important; border: 1px solid #000 !important; color: #000 !important; }}
                td {{ border: 1px solid #000 !important; color: #000 !important; }}
                tr:nth-child(even) {{ background-color: #eee !important; }}
                .max-w-7xl {{ max-width: 100% !important; padding: 0 !important; }}
                .bg-white {{ box-shadow: none !important; }}
            }}
        </style>
    </head>
    <body class='text-gray-800'>
        <div class='header-bg p-8 shadow-lg mb-8'>
            <div class='max-w-7xl mx-auto'>
                <div class="flex items-center gap-4">
                    <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-file-invoice-dollar text-3xl"></i></div>
                    <div><h1 class='text-3xl font-bold'>Relatório Fila Zero</h1><p class='text-blue-100'>Competência: {competencia_label} | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</p></div>
                </div>
            </div>
        </div>
        <div class='max-w-7xl mx-auto px-4'>
            <div class='grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 grid-print-row'>
                <div class='card border-l-4 border-blue-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Receita Total</h3><p class='text-2xl font-bold text-gray-800'>R$ {total_receita:,.2f}</p></div><i class="fa-solid fa-money-bill-wave text-blue-200 text-3xl"></i></div>
                <div class='card border-l-4 border-green-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Total a Repassar</h3><p class='text-2xl font-bold text-green-600'>R$ {total_repassar:,.2f}</p></div><i class="fa-solid fa-hand-holding-dollar text-green-200 text-3xl"></i></div>
                 <div class='card border-l-4 border-purple-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Procedimentos (AIH)</h3><p class='text-2xl font-bold text-purple-600'>{qtd_procedimentos_reais}</p></div><i class="fa-solid fa-notes-medical text-purple-200 text-3xl"></i></div>
            </div>
            <div class="bg-white rounded-t-lg shadow-sm border-b px-6 pt-4 flex gap-4 no-print">
                <button id="btn-resumo" class="tab-btn active" onclick="verTab('resumo')"><i class="fa-solid fa-list mr-2"></i> Visão Resumida</button>
                <button id="btn-detalhado" class="tab-btn" onclick="verTab('detalhado')"><i class="fa-solid fa-table-list mr-2"></i> Detalhamento</button>
            </div>
            <div class="bg-white rounded-b-lg shadow p-6 min-h-[500px]">
                <div id="tab-resumo" class="view-tab">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Resumo por Profissional</h2>
                    <table id='tbl-resumo'>
                        <thead><tr><th>Profissional</th><th class='text-right'>Valor Total (R$)</th></tr></thead>
                        <tbody>"""
    for _, row in df_resumo.iterrows(): html += f"<tr><td class='font-bold'>{row['Prestador']}</td><td class='text-right font-bold text-blue-600'>{row['Valor']:,.2f}</td></tr>"
    html += f"""</tbody><tfoot><tr class="bg-gray-200 font-bold"><td>TOTAL</td><td class="text-right">R$ {total_repassar:,.2f}</td></tr></tfoot></table></div>
                <div id="tab-detalhado" class="view-tab hidden">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Detalhamento Completo</h2>
                    <table id='tbl-detalhado'>
                        <thead><tr><th>Data</th><th>AIH</th><th>Profissional</th><th>Procedimento</th><th class='text-right'>Valor (R$)</th></tr></thead>
                        <tbody>"""
    for _, row in df_detalhado.iterrows(): html += f"<tr><td>{row['Data']}</td><td>{row['AIH']}</td><td class='font-medium'>{row['Prestador']}</td><td>{row['Procedimento']}</td><td class='text-right'>{row['Valor']:,.2f}</td></tr>"
    html += """</tbody></table></div></div></div>
        <script src='https://code.jquery.com/jquery-3.7.0.js'></script>
        <script src='https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js'></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
        <script>
            $(document).ready(function() {
                var config = { language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' }, dom: 'Bfrtip', buttons: [ { extend: 'excel', text: 'Excel', className: 'bg-green-600 text-white px-3 py-1 rounded' }, { text: 'Imprimir Página', className: 'bg-blue-600 text-white px-3 py-1 rounded', action: function ( e, dt, node, config ) { window.print(); } } ], paging: false };
                $('#tbl-resumo').DataTable(config); $('#tbl-detalhado').DataTable(config);
            });
            function verTab(id) { $('.view-tab').addClass('hidden'); $('#tab-' + id).removeClass('hidden'); $('.tab-btn').removeClass('active'); $('#btn-' + id).addClass('active'); }
        </script>
    </body></html>"""
    with open(nome_arquivo, 'w', encoding='utf-8') as f: f.write(html)
    print(f"✅ Relatório HTML gerado: {os.path.basename(nome_arquivo)}")

def atualizar_portal(novo_registro):
    caminho_atual = PASTA_SCRIPT
    caminho_json = None
    for _ in range(4):
        teste = os.path.join(caminho_atual, 'arquivos', 'dados_financeiro.json')
        if os.path.exists(teste): caminho_json = teste; break
        caminho_atual = os.path.dirname(caminho_atual)
    if not caminho_json: caminho_json = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos\dados_financeiro.json"
    try:
        if os.path.exists(caminho_json):
            with open(caminho_json, 'r', encoding='utf-8') as f: dados = json.load(f)
        else: dados = []
        dados = [d for d in dados if d['titulo'] != novo_registro['titulo']]
        dados.insert(0, novo_registro)
        with open(caminho_json, 'w', encoding='utf-8') as f: json.dump(dados, f, indent=4, ensure_ascii=False)
        print("   -> JSON do Portal atualizado com sucesso!")
    except Exception as e: print(f"❌ Erro JSON: {e}")

if __name__ == "__main__":
    receita_total = ler_valor_total_receita(ARQUIVO_PDF_RECEITA)
    df_detalhado = processar_producao_detalhada()
    if not df_detalhado.empty:
        total_prod = df_detalhado['Valor'].sum()
        comp_label, comp_sufixo = extrair_competencia(os.path.basename(ARQUIVO_PDF_PRODUCAO))
        nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_fila_zero_{comp_sufixo}.html")
        gerar_html_fila_zero(df_detalhado, nome_html, comp_label, receita_total)
        caminho_web = os.path.relpath(nome_html, r"C:\Users\DELL\OneDrive\NII-Portal-1").replace("\\", "/")
        reg = { "titulo": f"Fila Zero - {comp_label}", "competencia": comp_label, "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"), "valor_total": f"R$ {total_prod:,.2f}", "arquivo": caminho_web }
        atualizar_portal(reg)
    else: print("❌ Nenhuma produção encontrada.")