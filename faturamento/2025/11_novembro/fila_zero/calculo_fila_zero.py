# ==============================================================================
# SISTEMA DE REPASSES - VERSÃO FILA ZERO (ADAPTADO)
# Autor: Franck Moura (Via NII Automation)
# Data: 26/12/2025
# Descrição: Processa produção médica sem exigir arquivo de vínculos (rateio).
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

print(f"--- Processando Fila Zero na pasta: {os.path.basename(PASTA_SCRIPT)} ---")

# ==============================================================================
# 2. FUNÇÕES DE EXTRAÇÃO (ADAPTADAS)
# ==============================================================================

def extrair_competencia(nome_arquivo):
    """Tenta extrair mês/ano do nome do arquivo (ex: 1125 -> Novembro/2025)"""
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
    """Lê o valor total do PDF de Receita (apenas informativo no Fila Zero)"""
    if not os.path.exists(caminho_pdf): return 0.0
    
    total = 0.0
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                if "Total" in line or "TOTAL" in line:
                    # Procura valores monetários na linha de total
                    valores = re.findall(r'[\d\.]*[\d]\,\d{2}', line)
                    if valores:
                        # Pega o último valor da linha (geralmente é o total geral)
                        v_str = valores[-1].replace('.', '').replace(',', '.')
                        try:
                            v = float(v_str)
                            if v > total: total = v
                        except: pass
    return total

def processar_producao_individual():
    """Lê o PDF de produção por conta e soma por médico"""
    if not os.path.exists(ARQUIVO_PDF_PRODUCAO_CONTA):
        print("❌ Arquivo de Produção não encontrado.")
        return pd.DataFrame()

    dados = []
    medico_atual = "DESCONHECIDO"
    
    with pdfplumber.open(ARQUIVO_PDF_PRODUCAO_CONTA) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            
            for line in lines:
                # Detecta nome do médico (geralmente linhas que não começam com data/número e têm nome)
                # No padrão SoulMV, o nome do médico vem no cabeçalho ou antes da tabela
                # Vamos tentar uma heurística simples: se a linha tem nome e (CRM ou código)
                if re.search(r'\(\d+\)', line) and not "Competência" in line and not "Página" in line:
                     # Remove números entre parênteses para limpar o nome
                     medico_atual = re.sub(r'\(\d+\)', '', line).strip()

                # Detecta linha de procedimento com valor (ex: "484,42")
                # Procura padrão de valor no fim da linha
                match_valor = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*$', line)
                
                # Para evitar pegar linhas de totalização parcial, verificamos se tem código de proc
                # ou se parece uma linha de item.
                if match_valor and ("Anestesista" in line or "Auxiliar" in line or "Cirurgião" in line or "Próprio" in line):
                    valor_str = match_valor.group(1).replace('.', '').replace(',', '.')
                    valor = float(valor_str)
                    
                    dados.append({
                        'Prestador': medico_atual,
                        'Valor_Producao': valor
                    })

    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)
    # Agrupa por médico e soma
    df_agrupado = df.groupby('Prestador')['Valor_Producao'].sum().reset_index()
    return df_agrupado

# ==============================================================================
# 3. GERAÇÃO DO HTML
# ==============================================================================

def gerar_html_fila_zero(df_indiv, nome_arquivo, competencia_label, total_receita):
    total_repassar = df_indiv['Valor_Producao'].sum()
    
    # Ordena por valor
    df_indiv = df_indiv.sort_values(by='Valor_Producao', ascending=False)

    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Repasse Fila Zero - {competencia_label}</title>
        <script src='https://cdn.tailwindcss.com'></script>
        <link rel='stylesheet' href='https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css'>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; background-color: #f3f4f6; }}
            .header-bg {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 1.5rem; }}
        </style>
    </head>
    <body class='text-gray-800'>
        
        <div class='header-bg p-6 shadow-lg mb-8'>
            <div class='max-w-7xl mx-auto'>
                <h1 class='text-3xl font-bold'>Relatório de Repasse - FILA ZERO</h1>
                <p class='text-blue-100 mt-2'>Competência: {competencia_label} | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</p>
            </div>
        </div>

        <div class='max-w-7xl mx-auto px-4'>
            
            <div class='grid grid-cols-1 md:grid-cols-2 gap-6 mb-8'>
                <div class='card border-l-4 border-blue-500'>
                    <h3 class='text-gray-500 text-sm font-medium'>Receita Total (Procedimentos)</h3>
                    <p class='text-2xl font-bold text-gray-800'>R$ {total_receita:,.2f}</p>
                </div>
                <div class='card border-l-4 border-green-500'>
                    <h3 class='text-gray-500 text-sm font-medium'>Total a Repassar (Produção)</h3>
                    <p class='text-2xl font-bold text-green-600'>R$ {total_repassar:,.2f}</p>
                    <p class='text-xs text-gray-400'>Soma da produção individual identificada</p>
                </div>
            </div>

            <div class='card mb-8'>
                <h2 class='text-xl font-bold mb-4 text-gray-700 border-b pb-2'>Detalhamento por Profissional</h2>
                <div class='overflow-x-auto'>
                    <table id='tbl-fila-zero' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'>
                            <tr>
                                <th>Profissional</th>
                                <th class='text-right'>Valor Produção (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    for _, row in df_indiv.iterrows():
        html += f"""
            <tr class='bg-white border-b hover:bg-gray-50'>
                <td class='font-medium text-gray-900'>{row['Prestador']}</td>
                <td class='text-right font-bold text-blue-600'>{row['Valor_Producao']:,.2f}</td>
            </tr>
        """

    html += """
                        </tbody>
                        <tfoot>
                            <tr class='font-bold bg-gray-100'>
                                <td>TOTAL GERAL</td>
                                <td class='text-right'>R$ """ + f"{total_repassar:,.2f}" + """</td>
                            </tr>
                        </tfoot>
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
                $('#tbl-fila-zero').DataTable({
                    language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' },
                    dom: 'Bfrtip',
                    buttons: [
                        { extend: 'excel', text: 'Exportar Excel', className: 'bg-green-500 text-white px-4 py-2 rounded' },
                        { extend: 'print', text: 'Imprimir', className: 'bg-blue-500 text-white px-4 py-2 rounded' }
                    ],
                    pageLength: 50,
                    order: [[1, 'desc']]
                });
            });
        </script>
    </body>
    </html>
    """
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Relatório HTML gerado: {os.path.basename(nome_arquivo)}")

# ==============================================================================
# 4. ATUALIZAÇÃO DO PORTAL (JSON)
# ==============================================================================

def atualizar_portal(novo_registro):
    # Procura a pasta 'arquivos' subindo níveis
    caminho_atual = PASTA_SCRIPT
    caminho_json = None
    
    # Tenta subir até 4 níveis para achar a pasta "arquivos"
    for _ in range(4):
        teste = os.path.join(caminho_atual, 'arquivos', 'dados_financeiro.json')
        if os.path.exists(teste):
            caminho_json = teste
            break
        caminho_atual = os.path.dirname(caminho_atual) # Sobe um nível
    
    if not caminho_json:
        # Tenta hardcoded se a busca falhar (baseado no seu padrão)
        # c:/Users/DELL/OneDrive/NII-Portal-1/arquivos/dados_financeiro.json
        caminho_json = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos\dados_financeiro.json"
    
    print(f"   -> Atualizando JSON do portal em: {caminho_json}")

    try:
        if os.path.exists(caminho_json):
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        else:
            dados = []

        # Remove duplicatas se já existir (mesmo título)
        dados = [d for d in dados if d['titulo'] != novo_registro['titulo']]
        
        # Adiciona o novo no topo
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
    # 1. Dados Básicos
    receita_total = ler_valor_total_receita(ARQUIVO_PDF_RATEIO_RECEITA)
    
    # 2. Produção Individual
    print("   -> Lendo produção individual...")
    df_indiv = processar_producao_individual()
    
    if not df_indiv.empty:
        total_prod = df_indiv['Valor_Producao'].sum()
        print(f"   -> Produção identificada: R$ {total_prod:,.2f}")
        
        # 3. Gerar Relatório
        comp_label, comp_sufixo = extrair_competencia(os.path.basename(ARQUIVO_PDF_PRODUCAO_CONTA))
        nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_fila_zero_{comp_sufixo}.html")
        
        gerar_html_fila_zero(df_indiv, nome_html, comp_label, receita_total)
        
        # 4. Registrar no Portal
        # O caminho do arquivo no JSON deve ser relativo à raiz do site
        # Ex: faturamento/2025/11_novembro/fila zero/relatorio...
        
        # Pega o caminho relativo a partir da pasta raiz do projeto (NII-Portal-1)
        caminho_relativo = os.path.relpath(nome_html, r"C:\Users\DELL\OneDrive\NII-Portal-1")
        # Corrige barras para web (/)
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