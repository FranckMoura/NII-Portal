import json
import os
import pandas as pd
from datetime import datetime

print("--- GERANDO DASHBOARD (V2.1 - CORREÇÃO DE CHAVES) ---")

PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
ARQUIVO_JSON_SISREG = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")
ARQUIVO_JSON_TABNET = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")
PASTA_SITE = r"C:\Users\DELL\OneDrive\NII-Portal-1"

# --- FUNÇÃO AUXILIAR: CARREGAR DADOS ---
def carregar_dados(caminho):
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

dados_sisreg = carregar_dados(ARQUIVO_JSON_SISREG)
dados_tabnet = carregar_dados(ARQUIVO_JSON_TABNET)

# --- 1. GERAR PÁGINA INDICADORES (TABNET) ---
def gerar_html_indicadores(dados):
    if not dados:
        print("⚠️ Sem dados do TabNet para gerar gráficos.")
        return

    print(f"   Gerando indicadores.html com {len(dados)} meses de histórico...")
    
    # --- DESCOBRIR O NOME DAS COLUNAS (Importante para evitar KeyErrors) ---
    primeiro_item = dados[0]
    
    # Tenta achar a chave que guarda o texto do período (ex: "Jan/2024")
    chave_periodo = 'ano_mes_processament' # Padrão novo
    if 'periodo_txt' in primeiro_item: chave_periodo = 'periodo_txt'
    elif 'competencia' in primeiro_item: chave_periodo = 'competencia'
    
    # Tenta achar a chave de valor total
    chave_valor = 'valor_total'
    
    print(f"   (Mapeamento: Período='{chave_periodo}', Valor='{chave_valor}')")

    # Prepara os dados (Listas)
    labels = [d.get(chave_periodo, '-') for d in dados]
    internacoes = [d.get('internacoes', d.get('qtd_aih', 0)) for d in dados]
    obitos = [d.get('obitos', 0) for d in dados]
    valor_total = [d.get(chave_valor, 0) for d in dados]
    media_perm = [d.get('media_permanencia', 0) for d in dados]
    taxa_mort = [d.get('taxa_mortalidade', 0) for d in dados]
    
    # Calcula totais
    total_internacoes = sum(internacoes)
    total_faturamento = sum(valor_total)
    media_mortalidade = sum(taxa_mort)/len(dados) if dados else 0

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NII - Indicadores Hospitalares</title>
        <link rel="stylesheet" href="css/style.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            .kpi-container {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
            .kpi-card {{ flex: 1; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; min-width: 200px; }}
            .kpi-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
            .kpi-label {{ color: #7f8c8d; font-size: 0.9em; text-transform: uppercase; }}
            
            .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
            .chart-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            
            @media (max-width: 768px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: right; }}
            th {{ background-color: #f4f4f4; text-align: center; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="container">
                <a href="index.html" class="navbar-brand-link">
                    <span class="navbar-brand-text">NII - HBSH</span>
                </a>
                <ul class="navbar-nav">
                    <li><a href="index.html">Início</a></li>
                    <li><a href="faturamento.html">Faturamento</a></li>
                    <li><a href="indicadores.html" class="active">Indicadores</a></li>
                    <li><a href="manuais.html">Manuais</a></li>
                </ul>
            </div>
        </nav>

        <header class="page-header">
            <div class="container">
                <h1>Indicadores Históricos (TabNet/SIHSUS)</h1>
                <p>Análise da evolução hospitalar baseada no arquivo SIH importado.</p>
            </div>
        </header>

        <main class="container">
            
            <section class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-value">{len(dados)}</div>
                    <div class="kpi-label">Meses Analisados</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{total_internacoes:,.0f}</div>
                    <div class="kpi-label">Total Internações</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">R$ {total_faturamento:,.2f}</div>
                    <div class="kpi-label">Faturamento Histórico</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{media_mortalidade:.2f}%</div>
                    <div class="kpi-label">Mortalidade Média</div>
                </div>
            </section>

            <section class="chart-grid">
                <div class="chart-card">
                    <h3>Evolução: Internações vs Óbitos</h3>
                    <canvas id="chartInternacoes"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Faturamento (Produção Aprovada)</h3>
                    <canvas id="chartFinanceiro"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Média de Permanência (Dias)</h3>
                    <canvas id="chartPermanencia"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Taxa de Mortalidade (%)</h3>
                    <canvas id="chartMortalidade"></canvas>
                </div>
            </section>

            <section>
                <h2>Histórico Detalhado</h2>
                <div style="overflow-x:auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Período</th>
                                <th>Internações</th>
                                <th>Valor Total</th>
                                <th>Média Perm. (Dias)</th>
                                <th>Óbitos</th>
                                <th>Mortalidade (%)</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    for d in reversed(dados):
        # Usa .get() para evitar erro se faltar alguma coluna
        p_txt = d.get(chave_periodo, '-')
        inter = d.get('internacoes', d.get('qtd_aih', 0))
        val = d.get(chave_valor, 0)
        perm = d.get('media_permanencia', 0)
        obt = d.get('obitos', 0)
        mort = d.get('taxa_mortalidade', 0)

        html += f"""
            <tr>
                <td style="text-align:center">{p_txt}</td>
                <td>{inter}</td>
                <td>R$ {val:,.2f}</td>
                <td>{perm:.1f}</td>
                <td>{obt}</td>
                <td>{mort:.2f}%</td>
            </tr>
        """

    html += """
                        </tbody>
                    </table>
                </div>
            </section>

        </main>

        <script>
            const labels = """ + str(labels) + """;
            const dataInternacoes = """ + str(internacoes) + """;
            const dataObitos = """ + str(obitos) + """;
            const dataValor = """ + str(valor_total) + """;
            const dataPerm = """ + str(media_perm) + """;
            const dataMort = """ + str(taxa_mort) + """;

            new Chart(document.getElementById('chartInternacoes'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Internações',
                        data: dataInternacoes,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        yAxisID: 'y'
                    }, {
                        label: 'Óbitos',
                        data: dataObitos,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        fill: true,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        y: { type: 'linear', display: true, position: 'left' },
                        y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
                    }
                }
            });

            new Chart(document.getElementById('chartFinanceiro'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Valor Total (R$)',
                        data: dataValor,
                        backgroundColor: '#2ecc71'
                    }]
                }
            });

            new Chart(document.getElementById('chartPermanencia'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Dias de Permanência',
                        data: dataPerm,
                        borderColor: '#f39c12',
                        tension: 0.1
                    }]
                }
            });
            
            new Chart(document.getElementById('chartMortalidade'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Taxa (%)',
                        data: dataMort,
                        borderColor: '#8e44ad',
                        tension: 0.1
                    }]
                }
            });
        </script>
    </body>
    </html>
    """
    
    with open(os.path.join(PASTA_SITE, "indicadores.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Página indicadores.html recriada com sucesso!")

# --- EXECUÇÃO ---
if dados_tabnet:
    gerar_html_indicadores(dados_tabnet)
else:
    print("⚠️ JSON do TabNet vazio ou não encontrado.")
    # Se não tiver tabnet, mas tiver sisreg, gera pelo menos o index
    pass