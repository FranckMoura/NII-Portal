# ==============================================================================
# SISTEMA DE REPASSES - RATEIO DE EQUIPE (V8.0 - TABELA FORMATADA)
# Autor: Franck Moura (Via NII Automation)
# Data: 29/12/2025
# Descrição: Lógica V7.5 + Novo Layout de Tabela (Com bordas e zebrado).
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
import glob
import difflib
from datetime import datetime

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
print(f"--- Processando Rateio de Equipe (V8.0 - Tabela Grid) ---")

pdf_receita = glob.glob(os.path.join(PASTA_SCRIPT, '*RATEIO*.pdf'))
pdf_producao = glob.glob(os.path.join(PASTA_SCRIPT, 'R_PRODUCAO*.pdf'))
csv_vinculos = glob.glob(os.path.join(PASTA_SCRIPT, '*vinculo*.csv')) + glob.glob(os.path.join(PASTA_SCRIPT, '*VINCULO*.csv'))

ARQUIVO_RECEITA = pdf_receita[0] if pdf_receita else None
ARQUIVO_PRODUCAO = pdf_producao[0] if pdf_producao else None
ARQUIVO_VINCULOS = csv_vinculos[0] if csv_vinculos else None

if ARQUIVO_RECEITA: print(f"   -> Arquivo Bolo: {os.path.basename(ARQUIVO_RECEITA)}")
else: print("   ❌ ERRO: Nenhum PDF com 'RATEIO' no nome encontrado!")

def extrair_competencia(nome_arquivo):
    if not nome_arquivo: return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo)
    if match:
        mes, ano = match.groups()
        meses = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril', '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
        return f"{meses.get(mes, 'Mês')}/20{ano}", f"{mes}20{ano}"
    return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")

def corrigir_nome_similar(nome_pdf, lista_nomes_oficiais, corte=0.85):
    if not nome_pdf or not lista_nomes_oficiais: return nome_pdf
    nome_upper = nome_pdf.upper().strip()
    if nome_upper in lista_nomes_oficiais: return nome_upper
    for oficial in lista_nomes_oficiais:
        if nome_upper.startswith(oficial) or oficial.startswith(nome_upper):
            if len(oficial) > 4: return oficial
    matches = difflib.get_close_matches(nome_upper, lista_nomes_oficiais, n=1, cutoff=corte)
    if matches: return matches[0]
    return nome_upper

def processar_receita_rateio(caminho):
    if not caminho or not os.path.exists(caminho): return 0.0, set()
    total_sp_acumulado = 0.0
    codigos_rateio = set()
    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                match_cod = re.search(r'^"?(\d{8,10})"?', line.strip())
                if match_cod:
                    codigos_rateio.add(match_cod.group(1))
                    valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', line)
                    if len(valores) >= 2:
                        try:
                            val_sp_str = valores[-2]
                            val_limpo = val_sp_str.replace('.', '').replace(',', '.')
                            total_sp_acumulado += float(val_limpo)
                        except: pass
    print(f"   -> Total SP Receita: R$ {total_sp_acumulado:,.2f}")
    return total_sp_acumulado, codigos_rateio

def carregar_vinculos(caminho):
    if not caminho or not os.path.exists(caminho): return pd.DataFrame()
    try:
        try: df = pd.read_csv(caminho, sep=';', encoding='latin-1')
        except: df = pd.read_csv(caminho, sep=',', encoding='utf-8')
        mapa = {}
        for c in df.columns:
            if c.upper().strip() in ['PRESTADOR', 'NOME', 'MEDICO']: mapa[c] = 'Prestador'
            elif c.upper().strip() in ['VINCULO', 'PESO', 'QTD', 'COTAS']: mapa[c] = 'Vinculo'
        df = df.rename(columns=mapa)
        if 'Prestador' not in df.columns: return pd.DataFrame()
        if 'Vinculo' not in df.columns: df['Vinculo'] = 1
        df['Prestador'] = df['Prestador'].astype(str).str.upper().str.strip()
        df = df[~df['Prestador'].str.contains('HOSPITAL', case=False, na=False)]
        df['Vinculo'] = pd.to_numeric(df['Vinculo'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df = df[df['Vinculo'] > 0]
        return df[['Prestador', 'Vinculo']]
    except: return pd.DataFrame()

def calcular_rateio(valor_total, df_vinculos):
    if df_vinculos.empty or valor_total <= 0: return pd.DataFrame()
    total_cotas = df_vinculos['Vinculo'].sum()
    if total_cotas == 0: return pd.DataFrame()
    valor_ponto = valor_total / total_cotas
    df_vinculos['Valor_Rateio'] = df_vinculos['Vinculo'] * valor_ponto
    return df_vinculos

def ler_producao_individual(caminho, codigos_blacklist, lista_nomes_validos=None):
    if not caminho or not os.path.exists(caminho): return pd.DataFrame()
    dados = []
    medico_atual = "DESCONHECIDO"
    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                if re.search(r'\(\d+\)', line) and not "Competência" in line:
                    nome_cru = re.sub(r'\(\d+\)', '', line).strip()
                    if len(nome_cru) > 3:
                        if lista_nomes_validos:
                            match_nome = corrigir_nome_similar(nome_cru, lista_nomes_validos)
                            medico_atual = match_nome if match_nome else nome_cru.upper()
                        else:
                            medico_atual = nome_cru.upper()
                match_cod = re.search(r'\b(\d{8,10})\b', line)
                if not match_cod: continue 
                if "HOSPITAL" in medico_atual.upper(): continue
                codigo_encontrado = match_cod.group(1)
                if codigo_encontrado in codigos_blacklist: continue 
                valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', line)
                eh_item_valido = ("Anestesista" in line or "Auxiliar" in line or "Cirurgião" in line or "Próprio" in line or "Clínico" in line)
                if valores and eh_item_valido:
                    val_str = valores[-1].replace('.', '').replace(',', '.')
                    valor = float(val_str)
                    dados.append({'Prestador': medico_atual, 'Valor_Producao': valor})
    if not dados: return pd.DataFrame()
    df = pd.DataFrame(dados)
    df = df[~df['Prestador'].str.contains('HOSPITAL', case=False, na=False)]
    return df.groupby('Prestador')['Valor_Producao'].sum().reset_index()

def gerar_relatorio_final(df_rateio, df_producao, receita_total, nome_arquivo):
    if not df_producao.empty: prod_agrupada = df_producao
    else: prod_agrupada = pd.DataFrame(columns=['Prestador', 'Valor_Producao'])
    if not df_rateio.empty: df_final = pd.merge(df_rateio, prod_agrupada, on='Prestador', how='outer').fillna(0)
    else:
        df_final = prod_agrupada.copy()
        df_final['Valor_Rateio'] = 0
        df_final['Vinculo'] = 0
    df_final = df_final[~df_final['Prestador'].str.contains('HOSPITAL', case=False, na=False)]
    df_final['Total_Receber'] = df_final['Valor_Rateio'] + df_final['Valor_Producao']
    df_final = df_final.sort_values(by='Total_Receber', ascending=False)
    
    total_rateio_dist = df_final['Valor_Rateio'].sum()
    total_producao_dist = df_final['Valor_Producao'].sum()
    total_geral = df_final['Total_Receber'].sum()
    comp_label, _ = extrair_competencia(ARQUIVO_PRODUCAO if ARQUIVO_PRODUCAO else ARQUIVO_RECEITA)

    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Rateio Equipe - {comp_label}</title>
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

            /* ALTO CONTRASTE IMPRESSÃO */
            @media print {{
                @page {{ margin: 10mm; size: A4 portrait; }}
                body {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: white !important; font-size: 10px !important; color: #000 !important; }}
                .no-print, .dataTables_filter, .dataTables_length, .dataTables_info, .dataTables_paginate {{ display: none !important; }}
                .header-bg {{ padding: 10px !important; margin-bottom: 10px !important; }}
                .header-bg h1, .header-bg p, .header-bg i {{ color: white !important; -webkit-text-fill-color: white !important; }}
                .grid-print-row {{ display: grid !important; grid-template-columns: 1fr 1fr 1fr !important; gap: 10px !important; margin-bottom: 10px !important; }}
                .card {{ padding: 8px !important; box-shadow: none !important; border: 1px solid #000 !important; break-inside: avoid !important; }}
                .text-green-600, .text-blue-600, .text-purple-600, .text-orange-600 {{ color: #000 !important; font-weight: 800 !important; }}
                
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
                    <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-users-between-lines text-3xl"></i></div>
                    <div><h1 class='text-3xl font-bold'>Relatório de Repasse de Equipe</h1><p class='text-blue-100'>Competência: {comp_label} | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</p></div>
                </div>
            </div>
        </div>
        <div class='max-w-7xl mx-auto px-4'>
            <div class='grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 grid-print-row'>
                <div class='card border-l-4 border-blue-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Receita Rateio (SP)</h3><p class='text-2xl font-bold text-gray-800'>R$ {receita_total:,.2f}</p></div><i class="fa-solid fa-chart-pie text-blue-200 text-3xl"></i></div>
                <div class='card border-l-4 border-orange-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Produção Extra</h3><p class='text-2xl font-bold text-orange-600'>R$ {total_producao_dist:,.2f}</p></div><i class="fa-solid fa-user-doctor text-orange-200 text-3xl"></i></div>
                 <div class='card border-l-4 border-green-500 flex items-center justify-between'><div><h3 class='text-gray-500 text-sm font-medium'>Total a Repassar</h3><p class='text-2xl font-bold text-green-600'>R$ {total_geral:,.2f}</p></div><i class="fa-solid fa-money-check-dollar text-green-200 text-3xl"></i></div>
            </div>
            <div class="bg-white rounded-t-lg shadow-sm border-b px-6 pt-4 flex gap-4 no-print">
                <button id="btn-geral" class="tab-btn active" onclick="verTab('geral')"><i class="fa-solid fa-list-check mr-2"></i> Visão Geral</button>
                <button id="btn-rateio" class="tab-btn" onclick="verTab('rateio')"><i class="fa-solid fa-users mr-2"></i> Memória Rateio</button>
                 <button id="btn-prod" class="tab-btn" onclick="verTab('prod')"><i class="fa-solid fa-notes-medical mr-2"></i> Prod. Individual</button>
            </div>
            <div class="bg-white rounded-b-lg shadow p-6 min-h-[500px]">
                <div id="tab-geral" class="view-tab">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Resumo Final de Pagamento</h2>
                    <table id='tbl-geral'>
                        <thead><tr><th>Profissional</th><th class='text-right'>V. Rateio</th><th class='text-right'>V. Prod. Extra</th><th class='text-right'>TOTAL (R$)</th></tr></thead>
                        <tbody>"""
    for _, row in df_final.iterrows():
        html += f"<tr><td class='font-bold'>{row['Prestador']}</td><td class='text-right'>{row['Valor_Rateio']:,.2f}</td><td class='text-right'>{row['Valor_Producao']:,.2f}</td><td class='text-right font-bold text-green-600'>{row['Total_Receber']:,.2f}</td></tr>"
    html += f"""</tbody><tfoot><tr class="bg-gray-200 font-bold"><td>TOTAIS</td><td class="text-right">{total_rateio_dist:,.2f}</td><td class="text-right">{total_producao_dist:,.2f}</td><td class="text-right text-green-800">R$ {total_geral:,.2f}</td></tr></tfoot></table></div>
                <div id="tab-rateio" class="view-tab hidden">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Memória de Cálculo do Rateio</h2>
                    <table id='tbl-rateio'>
                        <thead><tr><th>Profissional</th><th class='text-center'>Peso/Cotas</th><th class='text-right'>Valor Rateio (R$)</th></tr></thead>
                        <tbody>"""
    if not df_rateio.empty:
        for _, row in df_rateio.iterrows(): html += f"<tr><td>{row['Prestador']}</td><td class='text-center'>{row['Vinculo']}</td><td class='text-right font-bold'>{row['Valor_Rateio']:,.2f}</td></tr>"
    html += """</tbody></table></div>
                <div id="tab-prod" class="view-tab hidden">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Produção Individual (Exceto Itens do Rateio)</h2>
                    <table id='tbl-prod'>
                        <thead><tr><th>Profissional</th><th class='text-right'>Valor Produção (R$)</th></tr></thead>
                        <tbody>"""
    if not df_producao.empty:
        for _, row in prod_agrupada.iterrows(): html += f"<tr><td>{row['Prestador']}</td><td class='text-right'>{row['Valor_Producao']:,.2f}</td></tr>"
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
                $('#tbl-geral').DataTable(config); $('#tbl-rateio').DataTable(config); $('#tbl-prod').DataTable(config);
            });
            function verTab(id) { $('.view-tab').addClass('hidden'); $('#tab-' + id).removeClass('hidden'); $('.tab-btn').removeClass('active'); $('#btn-' + id).addClass('active'); }
        </script>
    </body></html>"""
    with open(nome_arquivo, 'w', encoding='utf-8') as f: f.write(html)
    print(f"✅ Relatório HTML gerado: {os.path.basename(nome_arquivo)}")
    return total_geral

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
    receita_total, codigos_blacklist = processar_receita_rateio(ARQUIVO_RECEITA)
    df_vinculos = carregar_vinculos(ARQUIVO_VINCULOS)
    df_rateio = calcular_rateio(receita_total, df_vinculos)
    lista_oficial_nomes = []
    if not df_vinculos.empty: lista_oficial_nomes = df_vinculos['Prestador'].unique().tolist()
    df_producao = ler_producao_individual(ARQUIVO_PRODUCAO, codigos_blacklist, lista_oficial_nomes)
    comp_label, comp_sufixo = extrair_competencia(ARQUIVO_PRODUCAO if ARQUIVO_PRODUCAO else ARQUIVO_RECEITA)
    nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_rateio_{comp_sufixo}.html")
    total_geral = gerar_relatorio_final(df_rateio, df_producao, receita_total, nome_html)
    caminho_web = os.path.relpath(nome_html, r"C:\Users\DELL\OneDrive\NII-Portal-1").replace("\\", "/")
    reg = { "titulo": f"Repasse de Equipe - {comp_label}", "competencia": comp_label, "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"), "valor_total": f"R$ {total_geral:,.2f}", "arquivo": caminho_web }
    atualizar_portal(reg)