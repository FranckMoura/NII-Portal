# ==============================================================================
# SISTEMA DE REPASSES - VERSÃO FILA ZERO (COM DETALHAMENTO)
# Autor: Franck Moura (Via NII Automation)
# Data: 26/12/2025
# Descrição: Processa produção médica e gera relatório com abas (Resumo/Detalhado).
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
import glob
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÕES AUTOMÁTICAS
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Busca automática dos PDFs na pasta atual
pdf_receita = glob.glob(os.path.join(PASTA_SCRIPT, 'R_RECEITA*.pdf'))
pdf_producao = glob.glob(os.path.join(PASTA_SCRIPT, 'R_PRODUCAO*.pdf'))

ARQUIVO_PDF_RATEIO_RECEITA = pdf_receita[0] if pdf_receita else "NAO_ENCONTRADO"
ARQUIVO_PDF_PRODUCAO_CONTA = pdf_producao[0] if pdf_producao else "NAO_ENCONTRADO"

print(f"--- Processando Fila Zero (Com Detalhes) na pasta: {os.path.basename(PASTA_SCRIPT)} ---")

# ==============================================================================
# 2. FUNÇÕES DE EXTRAÇÃO
# ==============================================================================

def extrair_competencia(nome_arquivo):
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo)
    if match:
        mes, ano = match.groups()
        meses = {
            '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
            '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
            '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
        }
        return f"{meses.get(mes, 'Mês')}/20{ano}", f"{mes}20{ano}"
    return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")

def ler_valor_total_receita(caminho_pdf):
    if not os.path.exists(caminho_pdf): return 0.0
    total = 0.0
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                if "Total" in line or "TOTAL" in line:
                    valores = re.findall(r'[\d\.]*[\d]\,\d{2}', line)
                    if valores:
                        v_str = valores[-1].replace('.', '').replace(',', '.')
                        try:
                            v = float(v_str)
                            if v > total: total = v
                        except: pass
    return total

def processar_producao_detalhada():
    """
    Lê o PDF e extrai linha a linha para criar o detalhamento.
    Tenta capturar AIH e Procedimento do contexto.
    """
    if not os.path.exists(ARQUIVO_PDF_PRODUCAO_CONTA):
        print("❌ Arquivo de Produção não encontrado.")
        return pd.DataFrame()

    dados_detalhados = []
    
    # Variáveis de Estado (Memória do loop)
    medico_atual = "DESCONHECIDO"
    aih_atual = "-"
    proc_atual = "-"
    data_atual = "-"

    with pdfplumber.open(ARQUIVO_PDF_PRODUCAO_CONTA) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            lines = text.split('\n')
            
            for line in lines:
                # 1. Detecta Médico (Nome seguido de CRM/Código entre parênteses)
                # Ex: DEBORAH MARIA (306)
                if re.search(r'\(\d+\)', line) and not "Competência" in line and not "Página" in line and not "Total" in line:
                     medico_atual = re.sub(r'\(\d+\)', '', line).strip()
                
                # 2. Detecta AIH (13 dígitos começando com 5, comum no MT)
                match_aih = re.search(r'\b(5\d{12})\b', line)
                if match_aih:
                    aih_atual = match_aih.group(1)
                    
                    # Tenta pegar data na mesma linha (dd/mm)
                    match_data = re.search(r'\d{2}/\d{2}', line)
                    if match_data: data_atual = match_data.group(0)

                # 3. Detecta Procedimento (Geralmente texto maiúsculo com código antes)
                # Ex: 0408050160 RECONSTRUCAO...
                match_proc = re.search(r'\d{10}\s+(.*)', line)
                if match_proc:
                    # Pega o texto do procedimento, limpando valores no final se houver
                    proc_temp = match_proc.group(1)
                    proc_atual = re.split(r'\d{1,3}[\.,]', proc_temp)[0].strip() # Corta antes do valor

                # 4. Detecta Linha de Valor (Onde ocorre o pagamento)
                # Procura valor monetário no final da linha
                match_valor = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*$', line)
                
                # Filtros para garantir que é linha de produção médica válida
                eh_item_pagamento = ("Anestesista" in line or "Auxiliar" in line or "Cirurgião" in line or "Próprio" in line or "Clínico" in line)
                
                if match_valor and eh_item_pagamento:
                    valor_str = match_valor.group(1).replace('.', '').replace(',', '.')
                    valor = float(valor_str)
                    
                    # Adiciona ao relatório detalhado
                    dados_detalhados.append({
                        'Prestador': medico_atual,
                        'Data': data_atual,
                        'AIH': aih_atual,
                        'Procedimento': proc_atual if len(proc_atual) > 3 else "PROCEDIMENTO PADRÃO",
                        'Valor': valor
                    })

    if not dados_detalhados:
        return pd.DataFrame()

    return pd.DataFrame(dados_detalhados)

# ==============================================================================
# 3. GERAÇÃO DO HTML (COM ABAS)
# ==============================================================================

def gerar_html_com_abas(df_detalhado, nome_arquivo, competencia_label, total_receita):
    
    # Cria o DataFrame de Resumo (Agrupado)
    df_resumo = df_detalhado.groupby('Prestador')['Valor'].sum().reset_index()
    df_resumo = df_resumo.sort_values(by='Valor', ascending=False)
    
    total_repassar = df_resumo['Valor'].sum()

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
            .header-bg {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 1.5rem; margin-bottom: 2rem; }}
            .tab-btn {{ cursor: pointer; padding: 10px 20px; font-weight: 600; border-bottom: 2px solid transparent; color: #6b7280; transition: all 0.3s; }}
            .tab-btn:hover {{ color: #1d4ed8; }}
            .tab-btn.active {{ border-bottom: 2px solid #2563eb; color: #2563eb; }}
            .hidden {{ display: none; }}
        </style>
    </head>
    <body class='text-gray-800'>
        
        <div class='header-bg p-8 shadow-lg mb-8'>
            <div class='max-w-7xl mx-auto'>
                <div class="flex items-center gap-4">
                    <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-file-invoice-dollar text-3xl"></i></div>
                    <div>
                        <h1 class='text-3xl font-bold'>Relatório Fila Zero</h1>
                        <p class='text-blue-100'>Competência: {competencia_label} | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</p>
                    </div>
                </div>
            </div>
        </div>

        <div class='max-w-7xl mx-auto px-4'>
            
            <div class='grid grid-cols-1 md:grid-cols-3 gap-6 mb-8'>
                <div class='card border-l-4 border-blue-500 flex items-center justify-between'>
                    <div>
                        <h3 class='text-gray-500 text-sm font-medium'>Receita Total (Procedimentos)</h3>
                        <p class='text-2xl font-bold text-gray-800'>R$ {total_receita:,.2f}</p>
                    </div>
                    <i class="fa-solid fa-money-bill-wave text-blue-200 text-3xl"></i>
                </div>
                <div class='card border-l-4 border-green-500 flex items-center justify-between'>
                    <div>
                        <h3 class='text-gray-500 text-sm font-medium'>Total a Repassar (Produção)</h3>
                        <p class='text-2xl font-bold text-green-600'>R$ {total_repassar:,.2f}</p>
                    </div>
                    <i class="fa-solid fa-hand-holding-dollar text-green-200 text-3xl"></i>
                </div>
                 <div class='card border-l-4 border-purple-500 flex items-center justify-between'>
                    <div>
                        <h3 class='text-gray-500 text-sm font-medium'>Total de Procedimentos</h3>
                        <p class='text-2xl font-bold text-purple-600'>{len(df_detalhado)}</p>
                    </div>
                    <i class="fa-solid fa-notes-medical text-purple-200 text-3xl"></i>
                </div>
            </div>

            <div class="bg-white rounded-t-lg shadow-sm border-b px-6 pt-4 flex gap-4">
                <button id="btn-resumo" class="tab-btn active" onclick="verTab('resumo')">
                    <i class="fa-solid fa-list mr-2"></i> Visão Resumida
                </button>
                <button id="btn-detalhado" class="tab-btn" onclick="verTab('detalhado')">
                    <i class="fa-solid fa-table-list mr-2"></i> Detalhamento dos Procedimentos
                </button>
            </div>

            <div class="bg-white rounded-b-lg shadow p-6 min-h-[500px]">
                
                <div id="tab-resumo" class="view-tab">
                    <h2 class='text-xl font-bold mb-4 text-gray-700'>Resumo por Profissional</h2>
                    <table id='tbl-resumo' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'>
                            <tr>
                                <th>Profissional</th>
                                <th class='text-right'>Valor Total (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    for _, row in df_resumo.iterrows():
        html += f"""
            <tr>
                <td class='font-medium text-gray-900'>{row['Prestador']}</td>
                <td class='text-right font-bold text-blue-600'>{row['Valor']:,.2f}</td>
            </tr>
        """
    
    html += """
                        </tbody>
                        <tfoot>
                            <tr class="bg-gray-100 font-bold"><td>TOTAL</td><td class="text-right">R$ """ + f"{total_repassar:,.2f}" + """</td></tr>
                        </tfoot>
                    </table>
                </div>

                <div id="tab-detalhado" class="view-tab hidden">
                    <h2 class='text-xl font-bold mb-4 text-gray-700'>Detalhamento Completo</h2>
                    <table id='tbl-detalhado' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'>
                            <tr>
                                <th>Data</th>
                                <th>AIH</th>
                                <th>Profissional</th>
                                <th>Procedimento</th>
                                <th class='text-right'>Valor (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    for _, row in df_detalhado.iterrows():
        html += f"""
            <tr>
                <td>{row['Data']}</td>
                <td>{row['AIH']}</td>
                <td class='font-medium'>{row['Prestador']}</td>
                <td>{row['Procedimento']}</td>
                <td class='text-right'>{row['Valor']:,.2f}</td>
            </tr>
        """

    html += """
                        </tbody>
                    </table>
                </div>

            </div>
        </div>

        <script src='https://code.jquery.com/jquery-3.7.0.js'></script>
        <script src='https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js'></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
        <script>
            $(document).ready(function() {
                var config = {
                    language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' },
                    dom: 'Bfrtip',
                    buttons: [
                        { extend: 'excel', text: '<i class="fa-solid fa-file-excel"></i> Excel', className: 'bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700' },
                        { extend: 'print', text: '<i class="fa-solid fa-print"></i> Imprimir', className: 'bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700' }
                    ],
                    pageLength: 25
                };
                
                $('#tbl-resumo').DataTable(config);
                $('#tbl-detalhado').DataTable(config);
            });

            function verTab(id) {
                $('.view-tab').addClass('hidden');
                $('#tab-' + id).removeClass('hidden');
                $('.tab-btn').removeClass('active');
                $('#btn-' + id).addClass('active');
            }
        </script>
    </body>
    </html>
    """
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Relatório HTML gerado com abas: {os.path.basename(nome_arquivo)}")

# ==============================================================================
# 4. ATUALIZAÇÃO DO PORTAL (JSON)
# ==============================================================================

def atualizar_portal(novo_registro):
    caminho_atual = PASTA_SCRIPT
    caminho_json = None
    for _ in range(4):
        teste = os.path.join(caminho_atual, 'arquivos', 'dados_financeiro.json')
        if os.path.exists(teste):
            caminho_json = teste
            break
        caminho_atual = os.path.dirname(caminho_atual)
    
    if not caminho_json:
        caminho_json = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos\dados_financeiro.json"
    
    print(f"   -> Atualizando JSON do portal em: {caminho_json}")

    try:
        if os.path.exists(caminho_json):
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        else:
            dados = []

        dados = [d for d in dados if d['titulo'] != novo_registro['titulo']]
        dados.insert(0, novo_registro)

        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print("   -> JSON do Portal atualizado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao atualizar JSON do portal: {e}")

# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    receita_total = ler_valor_total_receita(ARQUIVO_PDF_RATEIO_RECEITA)
    
    print("   -> Lendo produção detalhada (AIH, Procedimento, Valor)...")
    df_detalhado = processar_producao_detalhada()
    
    if not df_detalhado.empty:
        total_prod = df_detalhado['Valor'].sum()
        print(f"   -> Produção identificada: R$ {total_prod:,.2f}")
        
        comp_label, comp_sufixo = extrair_competencia(os.path.basename(ARQUIVO_PDF_PRODUCAO_CONTA))
        nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_fila_zero_{comp_sufixo}.html")
        
        gerar_html_com_abas(df_detalhado, nome_html, comp_label, receita_total)
        
        caminho_relativo = os.path.relpath(nome_html, r"C:\Users\DELL\OneDrive\NII-Portal-1")
        caminho_web = caminho_relativo.replace("\\", "/")
        
        reg = {
            "titulo": f"Fila Zero - {comp_label}",
            "competencia": comp_label,
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "valor_total": f"R$ {total_prod:,.2f}",
            "arquivo": caminho_web 
        }
        atualizar_portal(reg)
        
    else:
        print("❌ Nenhuma produção encontrada nos PDFs.")