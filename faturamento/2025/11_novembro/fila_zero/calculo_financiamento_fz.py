# ==============================================================================
# SISTEMA DE REPASSES - PRODUÇÃO POR FINANCIAMENTO FILA ZERO (V1.0)
# Autor: Franck Moura (Via NII Automation)
# Data: 29/12/2025
# Descrição: Processa R_PROD_FINANCIAMENTO (Fila Zero).
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
import glob
from datetime import datetime

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
print(f"--- Processando Produção por Financiamento (Fila Zero) ---")

# Busca: Arquivos que TEM "FINANCIAMENTO" E TEM "FILAZERO"
arquivos_todos = glob.glob(os.path.join(PASTA_SCRIPT, 'R_PROD_FINANCIAMENTO*.pdf'))
pdf_financiamento = [f for f in arquivos_todos if "FILAZERO" in f.upper()]

ARQUIVO_ENTRADA = pdf_financiamento[0] if pdf_financiamento else None

# ... [O RESTO DO CÓDIGO É EXATAMENTE IGUAL AO SCRIPT ACIMA] ...
# ... [APENAS MUDA O TÍTULO NO FINAL E O NOME DO ARQUIVO HTML] ...

# ==============================================================================
# COPIAR AS MESMAS FUNÇÕES DO SCRIPT ANTERIOR AQUI (extrair, ler, gerar, atualizar)
# ==============================================================================
# (Para economizar espaço, vou colocar apenas o BLOCO FINAL diferente aqui, 
#  mas você deve copiar as funções def do script anterior para este também)

def extrair_competencia(nome_arquivo):
    if not nome_arquivo: return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo)
    if match:
        mes, ano = match.groups()
        meses = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril', '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
        return f"{meses.get(mes, 'Mês')}/20{ano}", f"{mes}20{ano}"
    return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")

def ler_dados_financiamento(caminho):
    # ... (Copiar função ler_dados_financiamento do script anterior) ...
    if not caminho or not os.path.exists(caminho): return pd.DataFrame()
    dados = []
    grupo_atual = "GERAL"
    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                if "Financiamento:" in line or "FINANCIAMENTO:" in line:
                    partes = line.split(":")
                    if len(partes) > 1: grupo_atual = partes[1].strip().upper()
                    continue
                match_cod = re.search(r'^"?(\d{8,10})"?', line.strip())
                if "Total" in line or "TOTAL" in line: continue
                if match_cod:
                    codigo = match_cod.group(1)
                    resto_linha = line.replace(codigo, "").strip()
                    match_desc = re.split(r'\d{1,3}(?:\.\d{3})*,', resto_linha)
                    descricao = match_desc[0].strip().replace('"', '') if match_desc else "ITEM"
                    valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', line)
                    if valores:
                        try:
                            val_str = valores[-1].replace('.', '').replace(',', '.')
                            valor = float(val_str)
                            qtd = 1
                            nums = re.findall(r'\s(\d+)\s', line)
                            if nums: qtd = int(nums[-1])
                            dados.append({'Financiamento': grupo_atual, 'Codigo': codigo, 'Descricao': descricao, 'Qtd': qtd, 'Valor': valor})
                        except: pass
    if not dados: return pd.DataFrame()
    return pd.DataFrame(dados)

def gerar_html(df, nome_arquivo, competencia_label, titulo_relatorio):
    # ... (Copiar função gerar_html do script anterior) ...
    df_resumo = df.groupby('Financiamento').agg({'Qtd': 'sum', 'Valor': 'sum'}).reset_index()
    df_resumo = df_resumo.sort_values(by='Valor', ascending=False)
    total_valor = df['Valor'].sum()
    total_qtd = df['Qtd'].sum()
    maior_fonte = df_resumo.iloc[0]['Financiamento'] if not df_resumo.empty else "-"
    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>{titulo_relatorio} - {competencia_label}</title>
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
            @media print {{
                @page {{ margin: 5mm; size: A4 portrait; }}
                body {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: white !important; font-size: 10px !important; color: #000 !important; }}
                .no-print, .dataTables_filter, .dataTables_length, .dataTables_info, .dataTables_paginate {{ display: none !important; }}
                .header-bg {{ padding: 10px !important; margin-bottom: 10px !important; }}
                .header-bg h1, .header-bg p, .header-bg i {{ color: white !important; -webkit-text-fill-color: white !important; }}
                .grid-print-row {{ display: grid !important; grid-template-columns: 1fr 1fr 1fr !important; gap: 10px !important; margin-bottom: 20px !important; }}
                .card {{ padding: 8px !important; box-shadow: none !important; border: 1px solid #000 !important; break-inside: avoid !important; }}
                .text-green-600, .text-blue-600, .text-purple-600 {{ color: #000 !important; font-weight: 800 !important; }}
                table {{ width: 100% !important; border-collapse: collapse !important; }}
                th {{ background-color: #ddd !important; color: #000 !important; border: 1px solid #000 !important; }}
                td {{ border-bottom: 1px solid #000 !important; color: #000 !important; }}
                .max-w-7xl {{ max-width: 100% !important; padding: 0 !important; }}
                .bg-white {{ box-shadow: none !important; }}
            }}
        </style>
    </head>
    <body class='text-gray-800'>
        <div class='header-bg p-8 shadow-lg mb-8'>
            <div class='max-w-7xl mx-auto'>
                <div class="flex items-center gap-4">
                    <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-chart-column text-3xl"></i></div>
                    <div><h1 class='text-3xl font-bold'>{titulo_relatorio}</h1><p class='text-blue-100'>Competência: {competencia_label} | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</p></div>
                </div>
            </div>
        </div>
        <div class='max-w-7xl mx-auto px-4'>
            <div class='grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 grid-print-row'>
                <div class='card border-l-4 border-blue-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Produção Total</h3><p class='text-2xl font-bold text-gray-800'>R$ {total_valor:,.2f}</p></div><i class="fa-solid fa-sack-dollar text-blue-200 text-3xl"></i></div>
                <div class='card border-l-4 border-purple-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Qtd. Procedimentos</h3><p class='text-2xl font-bold text-purple-600'>{total_qtd}</p></div><i class="fa-solid fa-layer-group text-purple-200 text-3xl"></i></div>
                <div class='card border-l-4 border-green-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Principal Fonte</h3><p class='text-sm font-bold text-green-700 truncate w-32' title="{maior_fonte}">{maior_fonte}</p></div><i class="fa-solid fa-ranking-star text-green-200 text-3xl"></i></div>
            </div>
            <div class="bg-white rounded-t-lg shadow-sm border-b px-6 pt-4 flex gap-4 no-print">
                <button id="btn-resumo" class="tab-btn active" onclick="verTab('resumo')"><i class="fa-solid fa-pie-chart mr-2"></i> Por Fonte de Financiamento</button>
                <button id="btn-detalhe" class="tab-btn" onclick="verTab('detalhe')"><i class="fa-solid fa-list mr-2"></i> Detalhado</button>
            </div>
            <div class="bg-white rounded-b-lg shadow p-6 min-h-[500px]">
                <div id="tab-resumo" class="view-tab">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Resumo por Bloco de Financiamento</h2>
                    <table id='tbl-resumo' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'><tr><th>Financiamento</th><th class='text-center'>Qtd</th><th class='text-right'>Valor Total (R$)</th></tr></thead>
                        <tbody>"""
    for _, row in df_resumo.iterrows(): html += f"<tr><td class='font-medium text-gray-900'>{row['Financiamento']}</td><td class='text-center'>{row['Qtd']}</td><td class='text-right font-bold text-blue-600'>{row['Valor']:,.2f}</td></tr>"
    html += f"""</tbody><tfoot><tr class="bg-gray-100 font-bold"><td>TOTAL</td><td class="text-center">{total_qtd}</td><td class="text-right">R$ {total_valor:,.2f}</td></tr></tfoot></table></div>
                <div id="tab-detalhe" class="view-tab hidden">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Detalhamento Completo</h2>
                    <table id='tbl-detalhe' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'><tr><th>Fonte</th><th>Código</th><th>Descrição</th><th class='text-center'>Qtd</th><th class='text-right'>Valor (R$)</th></tr></thead>
                        <tbody>"""
    for _, row in df.iterrows(): html += f"<tr><td class='text-xs'>{row['Financiamento']}</td><td>{row['Codigo']}</td><td class='font-medium'>{row['Descricao']}</td><td class='text-center'>{row['Qtd']}</td><td class='text-right'>{row['Valor']:,.2f}</td></tr>"
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
                $('#tbl-resumo').DataTable(config); $('#tbl-detalhe').DataTable(config);
            });
            function verTab(id) { $('.view-tab').addClass('hidden'); $('#tab-' + id).removeClass('hidden'); $('.tab-btn').removeClass('active'); $('#btn-' + id).addClass('active'); }
        </script>
    </body></html>"""
    with open(nome_arquivo, 'w', encoding='utf-8') as f: f.write(html)
    print(f"✅ Relatório HTML gerado: {os.path.basename(nome_arquivo)}")
    return total_valor

def atualizar_portal(novo_registro):
    # ... (Mesma função de antes) ...
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
    if ARQUIVO_ENTRADA:
        print(f"   -> Lendo arquivo: {os.path.basename(ARQUIVO_ENTRADA)}")
        df_dados = ler_dados_financiamento(ARQUIVO_ENTRADA)
        if not df_dados.empty:
            comp_label, comp_sufixo = extrair_competencia(os.path.basename(ARQUIVO_ENTRADA))
            nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_financiamento_fz_{comp_sufixo}.html")
            total = gerar_html(df_dados, nome_html, comp_label, "Produção por Financiamento (Fila Zero)")
            caminho_web = os.path.relpath(nome_html, r"C:\Users\DELL\OneDrive\NII-Portal-1").replace("\\", "/")
            reg = { "titulo": f"Financiamento Fila Zero - {comp_label}", "competencia": comp_label, "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"), "valor_total": f"R$ {total:,.2f}", "arquivo": caminho_web }
            atualizar_portal(reg)
        else: print("⚠️ Nenhum dado encontrado no PDF.")
    else: print("❌ Arquivo 'R_PROD_FINANCIAMENTO' (Fila Zero) não encontrado.")