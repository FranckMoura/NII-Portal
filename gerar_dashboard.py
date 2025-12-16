import json
import os

print("--- GERANDO DASHBOARD (V3.0 - COM FILTRO DE DATAS) ---")

PASTA_BASE = r"C:\Users\DELL\OneDrive\NII-Portal-1"
ARQUIVO_JSON = os.path.join(PASTA_BASE, "arquivos", "dados_tabnet.json")

def carregar_dados():
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

dados = carregar_dados()

if not dados:
    print("⚠️ ERRO: Sem dados para gerar o dashboard. Rode o importar_tabnet.py primeiro.")
    exit()

# Pega o primeiro registro para mapear colunas (garantia contra keyerror)
ref = dados[0]
k_periodo = 'periodo_txt' if 'periodo_txt' in ref else 'ano_mes_processament'
k_valor = 'valor_total'

# Prepara o JSON inteiro para ser embutido no HTML (o Javascript vai filtrar depois)
dados_json_str = json.dumps(dados)

html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NII - Histórico Interativo</title>
    <link rel="stylesheet" href="css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Estilos do Filtro */
        .filter-bar {{
            background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; align-items: flex-end; gap: 15px; flex-wrap: wrap;
        }}
        .filter-group {{ display: flex; flex-direction: column; }}
        .filter-group label {{ font-size: 0.85em; color: #7f8c8d; margin-bottom: 5px; font-weight: bold; }}
        .filter-group input {{ padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 1em; }}
        .btn-filter {{
            background-color: #3498db; color: white; border: none; padding: 10px 20px;
            border-radius: 4px; cursor: pointer; font-weight: bold; transition: background 0.3s;
            height: 40px;
        }}
        .btn-filter:hover {{ background-color: #2980b9; }}

        /* KPIs e Gráficos */
        .kpi-container {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .kpi-card {{ flex: 1; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }}
        .kpi-value {{ font-size: 1.8em; font-weight: bold; color: #2c3e50; }}
        
        .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #eee; text-align: right; }}
        th {{ background-color: #f8f9fa; text-align: center; }}
        .td-center {{ text-align: center; }}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="index.html" class="navbar-brand-link"><span class="navbar-brand-text">NII - HBSH</span></a>
            <ul class="navbar-nav">
                <li><a href="index.html">Início</a></li>
                <li><a href="faturamento.html">Faturamento</a></li>
                <li><a href="indicadores.html" class="active">Indicadores</a></li>
            </ul>
        </div>
    </nav>

    <header class="page-header">
        <div class="container">
            <h1>Indicadores Históricos (TabNet)</h1>
            <p>Selecione um período abaixo para filtrar os dados.</p>
        </div>
    </header>

    <main class="container">
        
        <section class="filter-bar">
            <div class="filter-group">
                <label>Data Início:</label>
                <input type="month" id="startDate">
            </div>
            <div class="filter-group">
                <label>Data Fim:</label>
                <input type="month" id="endDate">
            </div>
            <button class="btn-filter" onclick="aplicarFiltro()">Filtrar Dados</button>
            <button class="btn-filter" style="background:#95a5a6" onclick="resetarFiltro()">Limpar</button>
        </section>

        <section class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-value" id="kpi-meses">-</div>
                <div class="kpi-label">Meses Filtrados</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" id="kpi-internacoes">-</div>
                <div class="kpi-label">Total Internações</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" id="kpi-faturamento">-</div>
                <div class="kpi-label">Faturamento Período</div>
            </div>
        </section>

        <section class="chart-grid">
            <div class="chart-card">
                <h3>Internações vs Óbitos</h3>
                <canvas id="chart1"></canvas>
            </div>
            <div class="chart-card">
                <h3>Evolução do Faturamento</h3>
                <canvas id="chart2"></canvas>
            </div>
        </section>

        <section style="background:white; padding:20px; border-radius:8px;">
            <h3>Detalhamento do Período</h3>
            <div style="overflow-x:auto; max-height: 400px; overflow-y: auto;">
                <table id="tabelaDados">
                    <thead>
                        <tr>
                            <th>Período</th>
                            <th>Internações</th>
                            <th>Valor Total</th>
                            <th>Média Perm.</th>
                            <th>Óbitos</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </section>

    </main>

    <script>
        // DADOS BRUTOS VINDO DO PYTHON
        const rawData = {dados_json_str};

        // Variáveis globais dos gráficos
        let chart1 = null;
        let chart2 = null;

        // Ao carregar a página
        window.onload = function() {{
            // Define datas padrão (últimos 12 meses)
            if (rawData.length > 0) {{
                const ultimo = rawData[rawData.length - 1].data_iso.substring(0, 7); // YYYY-MM
                document.getElementById('endDate').value = ultimo;
                
                // Tenta pegar 12 meses atrás
                const idxInicio = Math.max(0, rawData.length - 12);
                const inicio = rawData[idxInicio].data_iso.substring(0, 7);
                document.getElementById('startDate').value = inicio;
            }}
            aplicarFiltro();
        }};

        function formatMoeda(val) {{ return "R$ " + val.toLocaleString('pt-BR', {{minimumFractionDigits: 2}}); }}

        function aplicarFiltro() {{
            const start = document.getElementById('startDate').value;
            const end = document.getElementById('endDate').value;

            // Filtra o Array
            const filtered = rawData.filter(d => {{
                const dIso = d.data_iso.substring(0, 7);
                return dIso >= start && dIso <= end;
            }});

            atualizarDashboard(filtered);
        }}

        function resetarFiltro() {{
            if (rawData.length > 0) {{
                document.getElementById('startDate').value = rawData[0].data_iso.substring(0, 7);
                document.getElementById('endDate').value = rawData[rawData.length-1].data_iso.substring(0, 7);
                aplicarFiltro();
            }}
        }}

        function atualizarDashboard(dados) {{
            // 1. Atualiza KPIs
            let totalInt = 0, totalFat = 0;
            dados.forEach(d => {{
                totalInt += (d.internacoes || d.qtd_aih || 0);
                totalFat += (d['{k_valor}'] || 0);
            }});

            document.getElementById('kpi-meses').innerText = dados.length;
            document.getElementById('kpi-internacoes').innerText = totalInt.toLocaleString('pt-BR');
            document.getElementById('kpi-faturamento').innerText = formatMoeda(totalFat);

            // 2. Prepara dados para Gráficos
            const labels = dados.map(d => d['{k_periodo}']);
            const dataInt = dados.map(d => d.internacoes || d.qtd_aih || 0);
            const dataObt = dados.map(d => d.obitos || 0);
            const dataFat = dados.map(d => d['{k_valor}'] || 0);

            // 3. Renderiza/Atualiza Gráfico 1 (Linha)
            const ctx1 = document.getElementById('chart1').getContext('2d');
            if (chart1) chart1.destroy();
            chart1 = new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Internações', data: dataInt, borderColor: '#3498db', fill: false }},
                        {{ label: 'Óbitos', data: dataObt, borderColor: '#e74c3c', fill: false }}
                    ]
                }}
            }});

            // 4. Renderiza/Atualiza Gráfico 2 (Barra)
            const ctx2 = document.getElementById('chart2').getContext('2d');
            if (chart2) chart2.destroy();
            chart2 = new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Faturamento', data: dataFat, backgroundColor: '#2ecc71' }}
                    ]
                }}
            }});

            // 5. Atualiza Tabela
            const tbody = document.querySelector("#tabelaDados tbody");
            tbody.innerHTML = "";
            // Inverte para tabela mostrar mais recente no topo
            [...dados].reverse().forEach(d => {{
                const row = `<tr>
                    <td class="td-center">${{d['{k_periodo}']}}</td>
                    <td>${{(d.internacoes || d.qtd_aih || 0)}}</td>
                    <td>${{formatMoeda(d['{k_valor}'] || 0)}}</td>
                    <td>${{(d.media_permanencia || 0).toFixed(1)}}</td>
                    <td>${{(d.obitos || 0)}}</td>
                </tr>`;
                tbody.innerHTML += row;
            }});
        }}
    </script>
</body>
</html>
"""

with open(os.path.join(PASTA_BASE, "indicadores.html"), "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Dashboard interativo gerado com sucesso!")