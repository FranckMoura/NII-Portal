# ==============================================================================
# SCRIPT DE CÁLCULO DE RATEIO DE EQUIPE (POOL) - NII PORTAL
# Autor: Franck Moura (Via NII Automation)
# Data: 2025-04-10
# Descrição: 
#   1. Lê PDF de Receita (SADT/Procedimentos) para obter o Montante Total (Vl. SP).
#   2. Lê CSV de Vínculos para obter os pesos de cada médico.
#   3. Calcula o valor do ponto e o repasse individual.
#   4. Gera Dashboard HTML (Ordenado Alfabeticamente).
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import csv
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Arquivos de Entrada
ARQUIVO_PDF_RECEITA = os.path.join(PASTA_SCRIPT, 'R_RECEITA_PROCEDIMENTO_RATEIO_1025.pdf')
ARQUIVO_CSV_VINCULOS = os.path.join(PASTA_SCRIPT, 'vinculos.csv')

# Arquivo de Saída
ARQUIVO_HTML_SAIDA = os.path.join(PASTA_SCRIPT, 'painel_rateio_equipe.html')

print("--- Iniciando Cálculo de Rateio de Equipe ---")

# ==============================================================================
# 2. FUNÇÕES DE LEITURA E EXTRAÇÃO
# ==============================================================================

def limpar_valor_monetario(valor_str):
    """
    Converte strings como '2.468,80' ou '355.94' para float.
    Tenta lidar com diferentes formatos de separadores.
    """
    if not valor_str: return 0.0
    
    # Remove aspas e espaços
    v = valor_str.replace('"', '').replace("'", "").strip()
    
    try:
        # Padrão Brasileiro (tem vírgula como decimal)
        if ',' in v:
            v = v.replace('.', '') # Remove milhar
            v = v.replace(',', '.') # Troca vírgula por ponto
        # Padrão Americano ou erro de OCR (apenas ponto)
        elif v.count('.') == 1:
            pass # Já está pronto (ex: 355.94)
        
        return float(v)
    except:
        return 0.0

def extrair_montante_sp_do_pdf(caminho_pdf):
    """
    Lê o PDF e soma a coluna 'Vl. SP'.
    """
    if not os.path.exists(caminho_pdf):
        print(f"[ERRO] PDF não encontrado: {caminho_pdf}")
        return 0.0

    total_sp = 0.0
    linhas_processadas = 0
    
    print(f"Lendo PDF de Receita: {os.path.basename(caminho_pdf)}...")
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            # O PDF parece ter linhas formatadas como CSV (ex: "cod","desc","val"...)
            # Vamos tentar identificar essas linhas
            for line in text.split('\n'):
                # Verifica se a linha tem cara de dados (começa com número entre aspas ou não)
                # Ex: "0303100010"
                if re.match(r'^"?\d{8,10}"?', line.strip()):
                    try:
                        # Tenta separar por vírgula respeitando aspas (csv reader logic simples)
                        # Como o extract_text pode não trazer as aspas perfeitas, vamos usar split inteligente
                        # Mas o snippet mostrava aspas. Vamos tentar parsear.
                        
                        # Estratégia Robusta: Pegar os últimos valores numéricos da linha
                        # O layout é: ..., Vl. SH, (Vazio?), Vl. SP, Total
                        # Vl. SP é geralmente o penúltimo valor monetário
                        
                        # Regex para encontrar valores monetários na linha (ex: "1.200,00" ou "355.94")
                        valores = re.findall(r'"?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"?', line)
                        
                        if len(valores) >= 2:
                            # Assumindo que a estrutura é [..., Vl_SH, Vl_SP, Total]
                            # O Vl_SP seria o penúltimo encontrado (antes do Total)
                            # Se houver Vl_Proced lá atrás, precisamos cuidar.
                            
                            # No snippet: "2.468,80"(Proced), "2.110.24"(SH), "355.94"(SP), "2.466.18"(Total) -> 4 valores
                            # Então Vl. SP é o índice -2 (penúltimo)
                            str_sp = valores[-2]
                            valor = limpar_valor_monetario(str_sp)
                            
                            total_sp += valor
                            linhas_processadas += 1
                    except Exception as e:
                        # print(f"Erro na linha: {line} | {e}")
                        pass

    print(f"  -> Linhas de procedimento somadas: {linhas_processadas}")
    print(f"  -> Montante Total SP Apurado: R$ {total_sp:,.2f}")
    return total_sp

def ler_pesos_vinculos(caminho_csv):
    """
    Lê o CSV de vínculos e retorna um DataFrame.
    """
    if not os.path.exists(caminho_csv):
        print(f"[ERRO] CSV de Vínculos não encontrado: {caminho_csv}")
        return pd.DataFrame()
    
    try:
        # Lê com separador ponto e vírgula (padrão do seu arquivo)
        df = pd.read_csv(caminho_csv, sep=';', encoding='latin1')
        
        # Limpa nomes de colunas
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Garante que o vínculo é numérico (troca vírgula por ponto se houver)
        if df['vinculo'].dtype == object:
             df['vinculo'] = df['vinculo'].astype(str).str.replace(',', '.').astype(float)
             
        return df
    except Exception as e:
        print(f"[ERRO] Falha ao ler CSV: {e}")
        return pd.DataFrame()

# ==============================================================================
# 3. GERAÇÃO DO DASHBOARD HTML
# ==============================================================================

def gerar_dashboard_rateio(df, total_bolo, total_pesos, valor_ponto, caminho_saida):
    if df.empty: return

    # HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NII - Rateio de Equipe</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; background-color: #f0f2f5; color: #1f2937; }}
            .nii-header {{ background: white; border-bottom: 1px solid #e5e7eb; padding: 1.5rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .metric-card {{ background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%); border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.5rem; }}
        </style>
    </head>
    <body>
        <header class="nii-header">
            <div class="max-w-7xl mx-auto px-4 flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="bg-blue-600 text-white p-2 rounded-lg"><i class="fa-solid fa-users-gear"></i></div>
                    <div>
                        <h1 class="text-xl font-bold text-gray-800">Cálculo de Rateio (Pool)</h1>
                        <p class="text-xs text-gray-500">Núcleo Interno de Informação - HBSH</p>
                    </div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-semibold text-gray-600">{datetime.now().strftime('%d/%m/%Y')}</div>
                    <div class="text-xs text-green-600 font-bold">Cálculo Automático</div>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-4 py-8">
            <!-- Cards de Métricas -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <!-- Card 1: O Bolo -->
                <div class="metric-card border-l-4 border-blue-500 shadow-sm">
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-sm font-medium text-gray-500 uppercase tracking-wider">Montante Total (SP)</p>
                            <h3 class="text-3xl font-bold text-gray-900 mt-1">R$ {total_bolo:,.2f}</h3>
                        </div>
                        <div class="p-2 bg-blue-100 rounded-full text-blue-600"><i class="fa-solid fa-sack-dollar"></i></div>
                    </div>
                    <p class="text-xs text-gray-400 mt-2">Soma extraída do PDF de Receita</p>
                </div>

                <!-- Card 2: Os Pesos -->
                <div class="metric-card border-l-4 border-orange-500 shadow-sm">
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-sm font-medium text-gray-500 uppercase tracking-wider">Total de Vínculos</p>
                            <h3 class="text-3xl font-bold text-gray-900 mt-1">{total_pesos:.2f}</h3>
                        </div>
                        <div class="p-2 bg-orange-100 rounded-full text-orange-600"><i class="fa-solid fa-scale-balanced"></i></div>
                    </div>
                    <p class="text-xs text-gray-400 mt-2">Soma dos pesos da equipe</p>
                </div>

                <!-- Card 3: O Ponto -->
                <div class="metric-card border-l-4 border-green-500 shadow-sm">
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-sm font-medium text-gray-500 uppercase tracking-wider">Valor do Ponto (1.0)</p>
                            <h3 class="text-3xl font-bold text-green-600 mt-1">R$ {valor_ponto:,.2f}</h3>
                        </div>
                        <div class="p-2 bg-green-100 rounded-full text-green-600"><i class="fa-solid fa-money-bill-trend-up"></i></div>
                    </div>
                    <p class="text-xs text-gray-400 mt-2">Montante / Vínculos</p>
                </div>
            </div>

            <!-- Tabela de Repasse -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="p-6 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                    <h3 class="text-lg font-bold text-gray-800">Distribuição por Profissional</h3>
                    <button onclick="window.print()" class="text-sm text-gray-500 hover:text-gray-800"><i class="fa-solid fa-print mr-1"></i> Imprimir</button>
                </div>
                
                <div class="p-0">
                    <table id="tabela-rateio" class="w-full text-left border-collapse">
                        <thead class="bg-gray-100 text-gray-600 uppercase text-xs font-bold">
                            <tr>
                                <th class="p-4 border-b">Profissional / Prestador</th>
                                <th class="p-4 border-b text-center">Peso (Vínculo)</th>
                                <th class="p-4 border-b text-right">Valor a Receber (R$)</th>
                                <th class="p-4 border-b text-right text-gray-400">% do Bolo</th>
                            </tr>
                        </thead>
                        <tbody class="text-sm text-gray-700">
    """
    
    for _, row in df.iterrows():
        percentual = (row['valor_receber'] / total_bolo * 100) if total_bolo > 0 else 0
        
        # Destaque visual para pesos maiores
        peso_style = "font-bold text-blue-600" if row['vinculo'] >= 1 else "text-gray-600"
        
        html += f"""
                            <tr class="hover:bg-gray-50 border-b last:border-0 transition-colors">
                                <td class="p-4 font-medium">{row['prestador']}</td>
                                <td class="p-4 text-center {peso_style}">{row['vinculo']}</td>
                                <td class="p-4 text-right font-bold text-green-700 bg-green-50/50">R$ {row['valor_receber']:,.2f}</td>
                                <td class="p-4 text-right text-xs text-gray-400">{percentual:.1f}%</td>
                            </tr>
        """

    html += """
                        </tbody>
                        <tfoot class="bg-gray-100 font-bold text-gray-800">
                            <tr>
                                <td class="p-4">TOTAL GERAL</td>
                                <td class="p-4 text-center">""" + f"{total_pesos:.2f}" + """</td>
                                <td class="p-4 text-right text-green-800">""" + f"R$ {total_bolo:,.2f}" + """</td>
                                <td></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </main>

        <!-- Scripts -->
        <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script>
            $(document).ready(function() {
                $('#tabela-rateio').DataTable({
                    language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' },
                    dom: 't', // Apenas a tabela, sem pesquisa/paginação (lista completa é melhor para rateio)
                    paging: false,
                    order: [[ 0, 'asc' ]] // Ordenar por Profissional (A-Z)
                });
            });
        </script>
    </body>
    </html>
    """

    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Sucesso! Painel gerado em: {caminho_saida}")

# ==============================================================================
# 4. EXECUÇÃO PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    # 1. Obter o Bolo (Total SP)
    total_sp = extrair_montante_sp_do_pdf(ARQUIVO_PDF_RECEITA)
    
    if total_sp > 0:
        # 2. Obter a Equipe (Vínculos)
        df_equipe = ler_pesos_vinculos(ARQUIVO_CSV_VINCULOS)
        
        if not df_equipe.empty:
            # 3. Calcular
            total_pesos = df_equipe['vinculo'].sum()
            
            if total_pesos > 0:
                valor_ponto = total_sp / total_pesos
                
                print(f"  -> Soma dos Pesos: {total_pesos}")
                print(f"  -> Valor do Ponto (1.0): R$ {valor_ponto:,.2f}")
                
                # Aplica o cálculo linha a linha
                df_equipe['valor_receber'] = df_equipe['vinculo'] * valor_ponto
                
                # Ordena por Nome (Ordem Alfabética)
                df_equipe = df_equipe.sort_values(by='prestador')
                
                # 4. Gerar Relatório
                gerar_dashboard_rateio(df_equipe, total_sp, total_pesos, valor_ponto, ARQUIVO_HTML_SAIDA)
                
            else:
                print("[ERRO] A soma dos vínculos no CSV é zero.")
        else:
            print("[ERRO] CSV de vínculos vazio ou inválido.")
    else:
        print("[ERRO] Não foi possível extrair valores do PDF ou valor é zero.")