import pandas as pd
import json
import os

print("--- 👶 GERADOR DE DASHBOARD PRO (DataTables + Export) ---")

# --- CONFIGURAÇÕES ---
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_EXCEL = os.path.join(PASTA_ATUAL, "Relatorio_Natalidade_Consolidado.xlsx")
ARQUIVO_HTML = os.path.join(PASTA_ATUAL, "painel_natalidade_pro.html")

# --- 1. CARREGAR E LIMPAR DADOS ---
if not os.path.exists(ARQUIVO_EXCEL):
    print(f"❌ Erro: Arquivo Excel não encontrado: {ARQUIVO_EXCEL}")
    exit()

print(">> Lendo e processando dados...")
df = pd.read_excel(ARQUIVO_EXCEL)

# Limpeza e Categorização
def categorizar_parto(texto):
    texto = str(texto).upper()
    if "CESARIANA" in texto: return "PARTO CESARIANO"
    elif "NORMAL" in texto: return "PARTO NORMAL"
    elif "FÓRCEPS" in texto: return "PARTO FÓRCEPS"
    elif "TOTAL" in texto: return "IGNORAR" # Remove linhas de total do Excel se houver
    else: return "OUTROS"

# Remove linhas vazias ou de total/espaçamento do Excel anterior
df = df.dropna(subset=['Nascidos Vivos']) 
df['Categoria'] = df['Procedimento'].apply(categorizar_parto)
df = df[df['Categoria'] != "IGNORAR"]

# Agrupa dados
df_agrupado = df.groupby(['Competência', 'Categoria'])[[
    'Nascidos Vivos', 'Nascidos Mortos', 'Óbitos Neo'
]].sum().reset_index()

# Ordena cronologicamente
df_agrupado['DataSort'] = pd.to_datetime(df_agrupado['Competência'], format='%m/%Y', errors='coerce')
df_agrupado = df_agrupado.sort_values(['DataSort', 'Categoria'])

# Prepara JSON
dados_json = []
meses_unicos = sorted(list(df_agrupado['Competência'].unique()), 
                      key=lambda x: pd.to_datetime(x, format='%m/%Y'))

for index, row in df_agrupado.iterrows():
    dados_json.append({
        "mes": row['Competência'],
        "tipo": row['Categoria'],
        "vivos": int(row['Nascidos Vivos']),
        "mortos": int(row['Nascidos Mortos']),
        "obitos": int(row['Óbitos Neo']),
        "total": int(row['Nascidos Vivos'] + row['Nascidos Mortos'])
    })

json_string = json.dumps(dados_json, ensure_ascii=False)

# --- 2. GERAR O HTML (COM DATATABLES & EXPORT) ---
html_content = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Indicadores Obstétricos - HSH</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.bootstrap5.min.css">

    <style>
        body {{ background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }}
        .header {{ background: linear-gradient(to right, #6f42c1, #d63384); color: white; padding: 25px 0; margin-bottom: 30px; }}
        .card-kpi {{ border: none; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); transition: transform 0.3s; }}
        .card-kpi:hover {{ transform: translateY(-5px); }}
        .chart-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        .table-container {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        
        /* Badges Personalizados */
        .badge-cesaria {{ background-color: #fd7e14; color: white; }}
        .badge-normal {{ background-color: #198754; color: white; }}
        .badge-outros {{ background-color: #6c757d; color: white; }}

        /* Botões DataTables */
        .dt-buttons .btn {{ margin-right: 5px; border-radius: 5px !important; }}
    </style>
</head>
<body>

    <div class="header shadow">
        <div class="container d-flex justify-content-between align-items-center">
            <div>
                <h2 class="mb-0"><i class="fas fa-baby"></i> Painel de Natalidade</h2>
                <small class="opacity-75">Hospital Beneficente Santa Helena</small>
            </div>
            <div>
                <button class="btn btn-light btn-sm text-primary fw-bold" onclick="window.print()">
                    <i class="fas fa-print"></i> Imprimir Página
                </button>
            </div>
        </div>
    </div>

    <div class="container mb-5">
        
        <div class="row mb-4">
            <div class="col-md-4 offset-md-4">
                <div class="input-group shadow-sm">
                    <span class="input-group-text bg-white"><i class="fas fa-calendar-alt text-primary"></i></span>
                    <select id="filtroMes" class="form-select border-start-0" onchange="atualizarDashboard()">
                        {''.join([f'<option value="{m}">{m}</option>' for m in meses_unicos])}
                        <option value="TODOS" selected>VISÃO GERAL (TODOS OS MESES)</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="row mb-4 text-center">
            <div class="col-md-3 mb-2">
                <div class="card card-kpi h-100 py-3 border-start border-5 border-success">
                    <div class="card-body">
                        <div class="text-success mb-2"><i class="fas fa-smile fa-2x"></i></div>
                        <h1 class="fw-bold mb-0" id="kpiVivos">0</h1>
                        <small class="text-muted fw-bold text-uppercase">Nascidos Vivos</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-2">
                <div class="card card-kpi h-100 py-3 border-start border-5 border-primary">
                    <div class="card-body">
                        <div class="text-primary mb-2"><i class="fas fa-clipboard-list fa-2x"></i></div>
                        <h1 class="fw-bold mb-0" id="kpiTotal">0</h1>
                        <small class="text-muted fw-bold text-uppercase">Total Partos</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-2">
                <div class="card card-kpi h-100 py-3 border-start border-5 border-warning">
                    <div class="card-body">
                        <div class="text-warning mb-2"><i class="fas fa-percentage fa-2x"></i></div>
                        <h1 class="fw-bold mb-0" id="kpiCesaria">0%</h1>
                        <small class="text-muted fw-bold text-uppercase">Taxa Cesárea</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-2">
                <div class="card card-kpi h-100 py-3 border-start border-5 border-danger">
                    <div class="card-body">
                        <div class="text-danger mb-2"><i class="fas fa-heart-broken fa-2x"></i></div>
                        <h1 class="fw-bold mb-0" id="kpiObitos">0</h1>
                        <small class="text-muted fw-bold text-uppercase">Natimortos + Óbitos</small>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="chart-box">
                    <div class="d-flex justify-content-between mb-3">
                        <h5 class="text-secondary">Tipo de Parto</h5>
                        <button class="btn btn-sm btn-outline-secondary" onclick="baixarGrafico('chartPizza', 'grafico_tipo_parto')"><i class="fas fa-download"></i> Imagem</button>
                    </div>
                    <div style="height: 300px;">
                        <canvas id="chartPizza"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="chart-box">
                    <div class="d-flex justify-content-between mb-3">
                        <h5 class="text-secondary">Evolução de Nascimentos</h5>
                        <button class="btn btn-sm btn-outline-secondary" onclick="baixarGrafico('chartLinha', 'grafico_evolucao')"><i class="fas fa-download"></i> Imagem</button>
                    </div>
                    <div style="height: 300px;">
                        <canvas id="chartLinha"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <div class="table-container">
            <h4 class="text-secondary mb-4"><i class="fas fa-table"></i> Detalhamento dos Dados</h4>
            <table id="tabelaDados" class="table table-striped table-hover w-100">
                <thead class="table-dark">
                    <tr>
                        <th>Competência</th>
                        <th>Tipo de Procedimento</th>
                        <th class="text-center">Vivos</th>
                        <th class="text-center">Natimortos</th>
                        <th class="text-center">Óbitos Neo</th>
                        <th class="text-center">Total</th>
                    </tr>
                </thead>
                <tbody>
                    </tbody>
                <tfoot>
                    <tr class="bg-light fw-bold">
                        <th colspan="2" class="text-end">TOTAIS:</th>
                        <th class="text-center"></th>
                        <th class="text-center"></th>
                        <th class="text-center"></th>
                        <th class="text-center"></th>
                    </tr>
                </tfoot>
            </table>
        </div>

    </div>

    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.bootstrap5.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.53/pdfmake.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.53/vfs_fonts.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>

    <script>
        const dadosRaw = {json_string};
        let table = null;
        let chartPizza = null;
        let chartLinha = null;

        // Função para Inicializar DataTables
        function initTable(dados) {{
            if (table) {{
                table.clear();
                table.rows.add(dados);
                table.draw();
                return;
            }}

            table = $('#tabelaDados').DataTable({{
                data: dados,
                columns: [
                    {{ data: 'mes' }},
                    {{ 
                        data: 'tipo',
                        render: function(data) {{
                            let cor = 'badge-outros';
                            if(data.includes('CESARIANO')) cor = 'badge-cesaria';
                            if(data.includes('NORMAL')) cor = 'badge-normal';
                            return `<span class="badge ${{cor}} p-2">${{data}}</span>`;
                        }}
                    }},
                    {{ data: 'vivos', className: 'text-center fw-bold text-success' }},
                    {{ data: 'mortos', className: 'text-center' }},
                    {{ data: 'obitos', className: 'text-center text-danger' }},
                    {{ data: 'total', className: 'text-center fw-bold' }}
                ],
                dom: 'Bfrtip',
                buttons: [
                    {{ extend: 'copy', text: '<i class="fas fa-copy"></i> Copiar', className: 'btn-secondary' }},
                    {{ extend: 'excel', text: '<i class="fas fa-file-excel"></i> Excel', className: 'btn-success' }},
                    {{ extend: 'pdf', text: '<i class="fas fa-file-pdf"></i> PDF', className: 'btn-danger' }},
                    {{ extend: 'print', text: '<i class="fas fa-print"></i> Imprimir Tabela', className: 'btn-info' }}
                ],
                language: {{
                    url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json"
                }},
                pageLength: 25,
                footerCallback: function (row, data, start, end, display) {{
                    var api = this.api();
                    // Função para limpar e somar
                    var intVal = function (i) {{ return typeof i === 'string' ? i.replace(/[\$,]/g, '')*1 : typeof i === 'number' ? i : 0; }};
                    
                    // Totalizar colunas
                    $(api.column(2).footer()).html(api.column(2).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                    $(api.column(3).footer()).html(api.column(3).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                    $(api.column(4).footer()).html(api.column(4).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                    $(api.column(5).footer()).html(api.column(5).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                }}
            }});
        }}

        function atualizarDashboard() {{
            const mesSel = document.getElementById('filtroMes').value;
            
            // 1. Filtrar Dados
            let dadosFiltrados = dadosRaw;
            if (mesSel !== "TODOS") {{
                dadosFiltrados = dadosRaw.filter(d => d.mes === mesSel);
            }}

            // 2. Calcular KPIs
            let tVivos = 0, tMortos = 0, tObitos = 0, tPartos = 0;
            let qtdNormal = 0, qtdCesaria = 0;

            dadosFiltrados.forEach(d => {{
                tVivos += d.vivos;
                tMortos += d.mortos;
                tObitos += d.obitos;
                tPartos += d.total;
                
                if(d.tipo.includes('NORMAL')) qtdNormal += d.total;
                if(d.tipo.includes('CESARIANO')) qtdCesaria += d.total;
            }});

            // Atualiza Texto KPI
            document.getElementById('kpiVivos').innerText = tVivos;
            document.getElementById('kpiTotal').innerText = tPartos;
            document.getElementById('kpiObitos').innerText = tMortos + tObitos;
            
            let taxaCesaria = tPartos > 0 ? ((qtdCesaria / tPartos) * 100).toFixed(1) : 0;
            document.getElementById('kpiCesaria').innerText = taxaCesaria + '%';

            // 3. Atualizar Tabela (DataTables)
            initTable(dadosFiltrados);

            // 4. Atualizar Gráficos
            atualizarGraficos(qtdNormal, qtdCesaria);
        }}

        function atualizarGraficos(normal, cesaria) {{
            // Gráfico Pizza
            const ctx1 = document.getElementById('chartPizza').getContext('2d');
            if(chartPizza) chartPizza.destroy();
            
            chartPizza = new Chart(ctx1, {{
                type: 'doughnut',
                data: {{
                    labels: ['Normal', 'Cesariana'],
                    datasets: [{{ data: [normal, cesaria], backgroundColor: ['#198754', '#fd7e14'] }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});

            // Gráfico Linha (Sempre mostra evolução do ANO TODO para contexto)
            // Agrupar por mês
            const mesesMap = {{}};
            dadosRaw.forEach(d => {{
                if(!mesesMap[d.mes]) mesesMap[d.mes] = 0;
                mesesMap[d.mes] += d.vivos;
            }});
            
            // Ordenar meses (gambiarra simples para ordenar string data)
            // Assumindo que dadosRaw já vem ordenado do Python, podemos pegar as keys
            const labels = Object.keys(mesesMap); 
            const data = Object.values(mesesMap);

            const ctx2 = document.getElementById('chartLinha').getContext('2d');
            if(chartLinha) chartLinha.destroy();

            chartLinha = new Chart(ctx2, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'Nascidos Vivos',
                        data: data,
                        borderColor: '#6f42c1',
                        backgroundColor: 'rgba(111, 66, 193, 0.1)',
                        fill: true,
                        tension: 0.3
                    }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});
        }}

        function baixarGrafico(canvasId, nomeArquivo) {{
            const canvas = document.getElementById(canvasId);
            const link = document.createElement('a');
            link.download = nomeArquivo + '.png';
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();
        }}

        // Inicialização
        document.addEventListener('DOMContentLoaded', () => {{
            atualizarDashboard();
        }});
    </script>
</body>
</html>
"""

# Salvar Arquivo
try:
    with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("\n" + "="*50)
    print(f"✅ DASHBOARD PRO GERADO!")
    print(f"📂 Arquivo: {ARQUIVO_HTML}")
    print("="*50)
except Exception as e:
    print(f"❌ Erro ao salvar HTML: {e}")