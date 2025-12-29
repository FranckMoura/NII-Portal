# ==============================================================================
# SISTEMA DE REPASSES - TERCEIROS E FORNECEDORES (V2.6 - HEMODIÁLISE RESTRITA)
# Autor: Franck Moura (Via NII Automation)
# Data: 26/12/2025
# Descrição: Processa receita SADT.
#            AGRUPAMENTO: Hemodiálise restrita ao cód 0305010131.
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
import glob
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

print(f"--- Processando Repasse de Terceiros/SADT (V2.6 - Ajuste Fino) ---")

# Busca automática
pdf_geral = glob.glob(os.path.join(PASTA_SCRIPT, 'R_RECEITA_PROCEDIMENTO_GERAL*.pdf'))
if not pdf_geral:
    pdf_geral = glob.glob(os.path.join(PASTA_SCRIPT, 'R_PROC_LANCAMENTOS*.pdf'))

ARQUIVO_ENTRADA = pdf_geral[0] if pdf_geral else None

# ==============================================================================
# 2. MAPA DE GRUPOS SUS (REGRA DE NEGÓCIO PERSONALIZADA)
# ==============================================================================
def definir_grupo_macro(codigo, descricao):
    """
    Classifica o procedimento com base em CÓDIGOS ESPECÍFICOS ou PALAVRAS-CHAVE.
    A ordem das verificações define a prioridade.
    """
    c = str(codigo).strip()
    d = str(descricao).upper().strip()
    
    # --- 1. REGRAS ESPECÍFICAS (EXCEÇÕES E CÓDIGOS DIRETOS) ---
    
    # UTIs
    if c == '0802010083': return "UTI ADULTO"
    if c == '0802010121': return "UTI NEONATAL"

    # HEMODIÁLISE (Regra Restrita - Apenas Agudos)
    if c == '0305010131': return "HEMODIALISE"

    # MATERIAIS E MEDICAMENTOS (Códigos Específicos)
    if c in ['0603030017', '0603040012', '0603060013', '0603070019']:
        return "MATERIAIS E MEDICAMENTOS"
    
    # CORREÇÃO: Embolectomia -> Grupo Cirúrgico (Sai da Hemodinâmica)
    if c == '0406020124': 
        return "04 - PROCEDIMENTOS CIRÚRGICOS (GERAL)"

    # HEMOTERAPIA (Exames Pré-Transfusionais Específicos)
    if c in ['0212010026', '0212010034']:
        return "HEMOTERAPIA"

    # --- 2. REGRAS POR PALAVRA-CHAVE E PREFIXOS ESPECIAIS ---

    # Materiais (Curativos)
    if "CURATIVO GRAU II" in d: 
        return "MATERIAIS E MEDICAMENTOS"

    # ANESTESIA / SEDAÇÃO (Prefixo 0417 ou Palavras-Chave)
    if c.startswith('0417') or "ANESTESIA" in d or "SEDACAO" in d or "SEDAÇÃO" in d:
        return "ANESTESIA/SEDAÇÃO/ANALGESIA"

    # Ecocardiografia -> Outros
    if "ECOCARDIOGRAFIA" in d: 
        return "OUTROS PROCEDIMENTOS"

    # Fisioterapia
    if "FISIOTERAP" in d: 
        return "FISIOTERAPIA"
    
    # Hemoterapia (Geral)
    if "TRANSFUSAO" in d or "TRANSFUSÃO" in d or "TRANSFUSIONAL" in d or c.startswith('0306'):
        return "HEMOTERAPIA"
    
    # Hemodinâmica (Geral - exceto o que já foi filtrado acima)
    if "CATETERISMO" in d or "ANGIOPLASTIA" in d or c.startswith('0406'):
        return "HEMODINAMICA"
    
    # Hemodiálise (Backup por nome, caso o código mude, mas sem pegar DRC/Pielonefrite)
    if ("HEMODIALISE" in d or "HEMODIÁLISE" in d) and not "DOENÇA RENAL" in d:
        return "HEMODIALISE"

    # --- 3. REGRAS PADRÃO SUS (SIGTAP) ---
    if c.startswith('0201'): return "0201 - COLETA DE MATERIAL"
    if c.startswith('0202'): return "0202 - LABORATÓRIO CLÍNICO"
    if c.startswith('0203'): return "0203 - ANATOMOPATOLÓGICO"
    if c.startswith('0204'): return "0204 - RADIOLOGIA / RAIO-X"
    if c.startswith('0205'): return "0205 - ULTRASSONOGRAFIA"
    if c.startswith('0206'): return "0206 - TOMOGRAFIA COMPUTADORIZADA"
    if c.startswith('0207'): return "0207 - RESSONÂNCIA MAGNÉTICA"
    if c.startswith('0208'): return "0208 - MEDICINA NUCLEAR"
    if c.startswith('0209'): return "0209 - ENDOSCOPIA / VIDEO"
    if c.startswith('0211'): return "0211 - MÉT. DIAG. ESPECIALIDADES (ECG/EEG)"
    
    # Os códigos 0305... que não são hemodiálise cairão aqui em PROCEDIMENTOS CLÍNICOS
    if c.startswith('03'): return "03 - PROCEDIMENTOS CLÍNICOS (GERAL)"
    if c.startswith('04'): return "04 - PROCEDIMENTOS CIRÚRGICOS (GERAL)"
    if c.startswith('07'): return "07 - ÓRTESES, PRÓTESES E MATERIAIS (OPME)"
    if c.startswith('08'): return "08 - DIÁRIAS E TAXAS"
    
    return "OUTROS PROCEDIMENTOS"

# ==============================================================================
# 3. EXTRAÇÃO DE DADOS
# ==============================================================================

def extrair_competencia(nome_arquivo):
    if not nome_arquivo: return datetime.now().strftime("%B/%Y"), datetime.now().strftime("%m%Y")
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

def ler_dados_terceiros(caminho):
    if not caminho or not os.path.exists(caminho): 
        print("❌ Arquivo PDF não encontrado.")
        return pd.DataFrame()
    
    dados = []
    
    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                if "Total" in line or "TOTAL" in line: continue
                match_cod = re.search(r'^"?(\d{8,10})"?', line.strip())

                if match_cod:
                    codigo = match_cod.group(1)
                    resto_linha = line.replace(codigo, "").strip()
                    match_desc = re.split(r'\d{1,3}(?:\.\d{3})*,', resto_linha)
                    descricao = match_desc[0].strip().replace('"', '') if match_desc else "ITEM"
                    valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', line)
                    
                    if valores:
                        try:
                            val_total_str = valores[-1].replace('.', '').replace(',', '.')
                            val_total = float(val_total_str)
                            qtd = 1
                            numeros_inteiros = re.findall(r'\s(\d+)\s', line)
                            if numeros_inteiros: qtd = int(numeros_inteiros[-1])

                            grupo_macro = definir_grupo_macro(codigo, descricao)

                            dados.append({
                                'Grupo_Macro': grupo_macro,
                                'Codigo': codigo,
                                'Descricao': descricao,
                                'Qtd': qtd,
                                'Valor_Total': val_total
                            })
                        except: pass

    if not dados: return pd.DataFrame()
    return pd.DataFrame(dados)

# ==============================================================================
# 4. GERAÇÃO DO HTML (VISUAL LIMPO - 3 CARDS)
# ==============================================================================

def gerar_html_terceiros(df, nome_arquivo, competencia_label):
    
    # --- CÁLCULOS ESPECIAIS (UTI) ---
    df_adulto = df[df['Grupo_Macro'] == 'UTI ADULTO']
    df_neo = df[df['Grupo_Macro'] == 'UTI NEONATAL']
    
    qtd_uti_adulto = df_adulto['Qtd'].sum()
    qtd_uti_neo = df_neo['Qtd'].sum()
    
    valor_sadt_adulto = qtd_uti_adulto * 50.00
    valor_sadt_neo = qtd_uti_neo * 70.00
    
    # --- AGRUPAMENTO GERAL ---
    df_macro = df.groupby('Grupo_Macro').agg({
        'Qtd': 'sum',
        'Valor_Total': 'sum'
    }).reset_index()
    df_macro = df_macro.sort_values(by='Valor_Total', ascending=False)
    
    total_geral = df['Valor_Total'].sum()
    total_itens = df['Qtd'].sum()
    
    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Repasse Terceiros - {competencia_label}</title>
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
                body {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: white !important; font-size: 10px !important; }}
                .no-print, .dataTables_filter, .dataTables_length, .dataTables_info, .dataTables_paginate {{ display: none !important; }}
                .header-bg {{ padding: 10px !important; margin-bottom: 10px !important; }}
                h1 {{ font-size: 16px !important; }}
                .header-bg p {{ font-size: 10px !important; }}
                
                .grid-print-row {{ display: grid !important; grid-template-columns: 1fr 1fr 1fr !important; gap: 10px !important; margin-bottom: 20px !important; }}
                
                .card {{ padding: 8px !important; box-shadow: none !important; border: 1px solid #ccc !important; break-inside: avoid !important; }}
                .card h3 {{ font-size: 8px !important; }}
                .card p {{ font-size: 12px !important; }}
                .card i {{ display: none !important; }}
                table {{ width: 100% !important; border-collapse: collapse !important; }}
                th {{ background-color: #eee !important; font-size: 9px !important; padding: 4px !important; border: 1px solid #ddd !important; }}
                td {{ font-size: 9px !important; padding: 4px !important; border-bottom: 1px solid #eee !important; }}
                .max-w-7xl {{ max-width: 100% !important; padding: 0 !important; }}
                .bg-white {{ box-shadow: none !important; }}
            }}
        </style>
    </head>
    <body class='text-gray-800'>
        
        <div class='header-bg p-8 shadow-lg mb-8'>
            <div class='max-w-7xl mx-auto'>
                <div class="flex items-center gap-4">
                    <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-truck-medical text-3xl"></i></div>
                    <div>
                        <h1 class='text-3xl font-bold'>Repasse Terceiros (SADT)</h1>
                        <p class='text-blue-100'>Competência: {competencia_label} | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</p>
                    </div>
                </div>
            </div>
        </div>

        <div class='max-w-7xl mx-auto px-4'>
            
            <div class='grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 grid-print-row'>
                
                <div class='card border-l-4 border-blue-500 flex items-center justify-between'>
                    <div>
                        <h3 class='text-gray-500 text-sm font-medium'>Faturamento Total</h3>
                        <p class='text-2xl font-bold text-gray-800'>R$ {total_geral:,.2f}</p>
                    </div>
                    <i class="fa-solid fa-file-invoice-dollar text-blue-200 text-3xl"></i>
                </div>
                
                <div class='card border-l-4 border-cyan-500 flex items-center justify-between'>
                    <div>
                        <h3 class='text-gray-500 text-sm font-medium'>SADT UTI ADULTO</h3>
                        <p class='text-2xl font-bold text-cyan-600'>R$ {valor_sadt_adulto:,.2f}</p>
                        <p class='text-xs text-gray-400'>{qtd_uti_adulto} diárias x R$ 50</p>
                    </div>
                    <i class="fa-solid fa-bed-pulse text-cyan-200 text-3xl"></i>
                </div>

                <div class='card border-l-4 border-pink-500 flex items-center justify-between'>
                    <div>
                        <h3 class='text-gray-500 text-sm font-medium'>SADT UTI NEONATAL</h3>
                        <p class='text-2xl font-bold text-pink-600'>R$ {valor_sadt_neo:,.2f}</p>
                        <p class='text-xs text-gray-400'>{qtd_uti_neo} diárias x R$ 70</p>
                    </div>
                    <i class="fa-solid fa-baby-carriage text-pink-200 text-3xl"></i>
                </div>
            </div>

            <div class="bg-white rounded-t-lg shadow-sm border-b px-6 pt-4 flex gap-4 no-print">
                <button id="btn-resumo" class="tab-btn active" onclick="verTab('resumo')">
                    <i class="fa-solid fa-layer-group mr-2"></i> Resumo por Grupo
                </button>
                <button id="btn-detalhe" class="tab-btn" onclick="verTab('detalhe')">
                    <i class="fa-solid fa-list-ul mr-2"></i> Detalhamento Completo
                </button>
            </div>

            <div class="bg-white rounded-b-lg shadow p-6 min-h-[500px]">
                
                <div id="tab-resumo" class="view-tab">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Consolidado por Grupo de Procedimento</h2>
                    <table id='tbl-resumo' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'>
                            <tr>
                                <th>Grupo / Tipo de Exame</th>
                                <th class='text-center'>Quantidade</th>
                                <th class='text-right'>Valor Faturado (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    for _, row in df_macro.iterrows():
        html += f"""
            <tr>
                <td class='font-medium text-gray-900'>{row['Grupo_Macro']}</td>
                <td class='text-center'>{row['Qtd']}</td>
                <td class='text-right font-bold text-blue-600'>{row['Valor_Total']:,.2f}</td>
            </tr>
        """
    
    html += """
                        </tbody>
                        <tfoot>
                            <tr class="bg-gray-100 font-bold">
                                <td>TOTAL GERAL</td>
                                <td class="text-center">""" + f"{total_itens}" + """</td>
                                <td class="text-right">R$ """ + f"{total_geral:,.2f}" + """</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <div id="tab-detalhe" class="view-tab hidden">
                    <h2 class='text-xl font-bold mb-4 text-gray-700 no-print'>Detalhamento de Itens</h2>
                    <table id='tbl-detalhe' class='display w-full text-sm text-left text-gray-500'>
                        <thead class='text-xs text-gray-700 uppercase bg-gray-50'>
                            <tr>
                                <th>Grupo</th>
                                <th>Código</th>
                                <th>Descrição</th>
                                <th class='text-center'>Qtd</th>
                                <th class='text-right'>Valor Total (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    for _, row in df.iterrows():
        html += f"""
            <tr>
                <td class='text-xs'>{row['Grupo_Macro']}</td>
                <td>{row['Codigo']}</td>
                <td class='font-medium'>{row['Descricao']}</td>
                <td class='text-center'>{row['Qtd']}</td>
                <td class='text-right'>{row['Valor_Total']:,.2f}</td>
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
                        { extend: 'excel', text: '<i class="fa-solid fa-file-excel"></i> Excel', className: 'bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 mr-2' },
                        { 
                            text: '<i class="fa-solid fa-print"></i> Imprimir Página', 
                            className: 'bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700',
                            action: function ( e, dt, node, config ) { window.print(); }
                        }
                    ],
                    paging: false
                };
                $('#tbl-resumo').DataTable(config);
                $('#tbl-detalhe').DataTable(config);
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
    print(f"✅ Relatório HTML gerado (V2.6 - Ajuste Fino): {os.path.basename(nome_arquivo)}")
    return total_geral

# ==============================================================================
# 5. ATUALIZAÇÃO DO PORTAL (JSON)
# ==============================================================================

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

        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print("   -> JSON do Portal atualizado com sucesso!")
    except Exception as e: print(f"❌ Erro JSON: {e}")

# ==============================================================================
# 6. EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    if ARQUIVO_ENTRADA:
        print(f"   -> Lendo arquivo: {os.path.basename(ARQUIVO_ENTRADA)}")
        df_dados = ler_dados_terceiros(ARQUIVO_ENTRADA)
        
        if not df_dados.empty:
            comp_label, comp_sufixo = extrair_competencia(os.path.basename(ARQUIVO_ENTRADA))
            nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_terceiros_{comp_sufixo}.html")
            
            total_geral = gerar_html_terceiros(df_dados, nome_html, comp_label)
            
            caminho_web = os.path.relpath(nome_html, r"C:\Users\DELL\OneDrive\NII-Portal-1").replace("\\", "/")
            reg = {
                "titulo": f"Terceiros/SADT - {comp_label}",
                "competencia": comp_label,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "valor_total": f"R$ {total_geral:,.2f}",
                "arquivo": caminho_web 
            }
            atualizar_portal(reg)
        else:
            print("⚠️ Nenhum dado encontrado no PDF.")
    else:
        print("❌ Erro: Nenhum arquivo 'R_RECEITA_PROCEDIMENTO_GERAL' ou 'LANCAMENTOS' encontrado.")