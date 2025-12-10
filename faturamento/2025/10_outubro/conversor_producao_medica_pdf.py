# ==============================================================================
# SCRIPT DE PROCESSAMENTO DE PRODUÇÃO MÉDICA (PDF -> HTML)
# Autor: Franck Moura (Via NII Portal)
# Data: 2025-04-10
# Descrição: Lê o PDF de Produtividade Médica (Conta), extrai valores de repasse
#            e gera Dashboard HTML no padrão NII.
# ==============================================================================

import pdfplumber
import pandas as pd
import re
import os

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ENTRADA = os.path.join(PASTA_SCRIPT, 'R_PRODUCAO_MEDICA_CONTA_1025.pdf')
NOME_ARQUIVO_SAIDA = os.path.join(PASTA_SCRIPT, 'painel_producao_medica.html')

print(f"--- Iniciando Processamento de Produção Médica ---")
print(f"Lendo arquivo: {ARQUIVO_ENTRADA}")

# ==============================================================================
# 2. EXTRAÇÃO DE DADOS DO PDF
# ==============================================================================

def extrair_dados_pdf(caminho):
    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        return pd.DataFrame()

    dados = []
    prestador_atual = "DESCONHECIDO"
    
    # Regex para identificar cabeçalho de prestador: NOME (CODIGO)
    # Ex: ADILSON JOAO MASSONI (345)
    regex_prestador = re.compile(r'^([A-Z\s\.]+)\s+\(\d+\)$')
    
    with pdfplumber.open(caminho) as pdf:
        total_paginas = len(pdf.pages)
        print(f"O arquivo possui {total_paginas} páginas. Processando...")
        
        for i, page in enumerate(pdf.pages):
            # Extrai texto linha a linha mantendo layout aproximado
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 1. Identificar Prestador
                match_prestador = regex_prestador.match(line)
                if match_prestador:
                    # Verifica se não é um falso positivo (cabeçalhos do sistema)
                    if "HOSPITAL" not in line and "SISTEMA" not in line:
                        prestador_atual = match_prestador.group(1).strip()
                        continue
                
                # 2. Identificar Linhas de Procedimento/AIH
                # O layout parece ter a AIH (13 digitos) no inicio ou data/codigo
                # O valor do prestador costuma ser o último número da linha
                
                # Tentativa de capturar linhas de dados relevantes
                # Ex de linha útil: "5125... 26/09 ... 27,86"
                
                # Vamos procurar linhas que terminam com um valor monetário e tem dados no meio
                if re.search(r'\d+,\d{2}$', line):
                    parts = line.split()
                    
                    # Logica heurística para extrair o valor final (Vl. Prestador)
                    # Geralmente é o último item da linha
                    try:
                        valor_str = parts[-1]
                        valor = float(valor_str.replace('.', '').replace(',', '.'))
                        
                        # Tenta pegar AIH (primeiro item numérico longo)
                        aih = "N/D"
                        for p in parts:
                            if len(p) == 13 and p.isdigit():
                                aih = p
                                break
                        
                        # Se achou valor e tem um contexto de prestador, salva
                        if valor > 0 and prestador_atual != "DESCONHECIDO":
                            # Tenta limpar o "Lixo" da linha para pegar uma descrição aproximada
                            desc = line
                            # Remove o valor do fim
                            desc = desc.replace(valor_str, "")
                            # Remove AIH
                            if aih != "N/D": desc = desc.replace(aih, "")
                            
                            dados.append({
                                'Prestador': prestador_atual,
                                'AIH': aih,
                                'Linha_Raw': desc.strip(), # Descrição bruta para referência
                                'Valor_Repasse': valor
                            })
                    except:
                        pass
    
    return pd.DataFrame(dados)

# ==============================================================================
# 3. GERAÇÃO DO DASHBOARD HTML
# ==============================================================================

def gerar_dashboard(df, caminho_saida):
    if df.empty:
        print("Nenhum dado encontrado. Verifique se o PDF está no padrão esperado.")
        return

    # Cálculos
    total_geral = df['Valor_Repasse'].sum()
    qtd_itens = len(df)
    qtd_medicos = df['Prestador'].nunique()
    
    # Agrupamento por Prestador (Ranking)
    df_resumo = df.groupby('Prestador').agg(
        Qtd_Itens=('Valor_Repasse', 'count'),
        Valor_Total=('Valor_Repasse', 'sum')
    ).reset_index().sort_values(by='Valor_Total', ascending=False)

    # HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NII - Produção Médica</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
        
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; background-color: #f8f9fa; color: #333; }}
            .nii-header {{ background-color: #ffffff; border-bottom: 1px solid #e0e0e0; padding: 1rem 0; margin-bottom: 2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .metric-card {{ background: white; border: 1px solid #dee2e6; border-radius: 8px; padding: 1.5rem; }}
            .tab-btn {{ padding: 10px 20px; border-radius: 8px; font-weight: 500; margin-right: 0.5rem; transition: 0.3s; }}
            .tab-btn.active {{ background-color: #10b981; color: white; }} /* Verde para diferenciar do outro relatório */
            .tab-btn.inactive {{ background-color: #e9ecef; color: #495057; }}
        </style>
    </head>
    <body>
        <header class="nii-header">
            <div class="max-w-7xl mx-auto px-4 flex justify-between items-center">
                <div class="flex items-center gap-2 text-xl font-bold text-gray-700">
                    <i class="fa-solid fa-user-md text-green-600"></i>
                    <span>NII - Produção Médica (Contas)</span>
                </div>
                <div class="text-right text-sm">
                    <div class="font-bold">Hospital Beneficente Santa Helena</div>
                    <div class="text-gray-500">Repasse Médico</div>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-4 pb-12">
            <!-- Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="metric-card border-l-4 border-green-500">
                    <div class="text-sm text-gray-500 uppercase">Total a Repassar</div>
                    <div class="text-3xl font-bold text-gray-800">R$ {total_geral:,.2f}</div>
                </div>
                <div class="metric-card border-l-4 border-blue-500">
                    <div class="text-sm text-gray-500 uppercase">Itens Produzidos</div>
                    <div class="text-3xl font-bold text-gray-800">{qtd_itens}</div>
                </div>
                <div class="metric-card border-l-4 border-purple-500">
                    <div class="text-sm text-gray-500 uppercase">Médicos Listados</div>
                    <div class="text-3xl font-bold text-gray-800">{qtd_medicos}</div>
                </div>
            </div>

            <!-- Navegação -->
            <div class="flex mb-4">
                <button onclick="switchTab('resumo')" id="btn-resumo" class="tab-btn active">Resumo por Médico</button>
                <button onclick="switchTab('analitico')" id="btn-analitico" class="tab-btn inactive">Detalhamento (AIH)</button>
            </div>

            <!-- Tabela Resumo -->
            <div id="view-resumo" class="bg-white rounded-lg shadow border p-4">
                <table id="table-resumo" class="w-full text-sm hover">
                    <thead>
                        <tr class="text-left bg-gray-100"><th>Médico / Prestador</th><th class="text-right">Qtd Itens</th><th class="text-right">Valor Total (R$)</th></tr>
                    </thead>
                    <tbody>
    """
    for _, row in df_resumo.iterrows():
        html += f"<tr><td class='font-bold'>{row['Prestador']}</td><td class='text-right'>{row['Qtd_Itens']}</td><td class='text-right font-bold text-green-600'>{row['Valor_Total']:,.2f}</td></tr>"

    html += """
                    </tbody>
                </table>
            </div>

            <!-- Tabela Analitica -->
            <div id="view-analitico" class="hidden bg-white rounded-lg shadow border p-4">
                <table id="table-analitico" class="w-full text-sm hover">
                    <thead>
                        <tr class="text-left bg-gray-100"><th>Médico</th><th>AIH / Ref</th><th>Detalhes (Extraído)</th><th class="text-right">Valor Item (R$)</th></tr>
                    </thead>
                    <tbody>
    """
    for _, row in df.iterrows():
        html += f"<tr><td>{row['Prestador']}</td><td class='font-mono'>{row['AIH']}</td><td class='text-xs text-gray-500'>{row['Linha_Raw'][:50]}...</td><td class='text-right'>{row['Valor_Repasse']:,.2f}</td></tr>"

    html += """
                    </tbody>
                </table>
            </div>
        </main>

        <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>

        <script>
            $(document).ready(function() {
                var conf = { 
                    language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' },
                    dom: 'Bfrtip',
                    buttons: ['excel', 'print']
                };
                $('#table-resumo').DataTable(conf);
                $('#table-analitico').DataTable(conf);
            });
            function switchTab(t) {
                $('#view-resumo, #view-analitico').addClass('hidden');
                $('#view-'+t).removeClass('hidden');
                $('.tab-btn').removeClass('active').addClass('inactive');
                $('#btn-'+t).removeClass('inactive').addClass('active');
            }
        </script>
    </body>
    </html>
    """

    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Sucesso! Painel gerado em: {caminho_saida}")

if __name__ == "__main__":
    df = extrair_dados_pdf(ARQUIVO_ENTRADA)
    gerar_dashboard(df, NOME_ARQUIVO_SAIDA)