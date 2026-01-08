import pandas as pd
import json
import os
import re

print("--- 👶 GERADOR FINAL: DADOS LIMPOS + VISUAL PERFEITO ---")

# --- CONFIGURAÇÕES ---
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_EXCEL = os.path.join(PASTA_ATUAL, "Relatorio_Natalidade_Consolidado.xlsx")
ARQUIVO_HTML = os.path.join(PASTA_ATUAL, "painel_natalidade_final.html")

if not os.path.exists(ARQUIVO_EXCEL):
    print(f"❌ Erro: {ARQUIVO_EXCEL} não encontrado.")
    exit()

print(">> Processando dados...")
df = pd.read_excel(ARQUIVO_EXCEL)

# --- 1. LIMPEZA DE DADOS (A Lógica Nova que remove pacientes) ---
def limpar_nome_procedimento_v2(texto):
    texto = str(texto).upper().strip()
    if "TOTAL" in texto or ">>>" in texto: return "IGNORAR"

    # Encontra onde começa o procedimento real
    match_inicio = re.search(r'(PARTO\s|OPERAÇÃO\s|CESARIANA)', texto)
    if match_inicio:
        texto = texto[match_inicio.start():]
    else:
        # Remove códigos numéricos soltos no início se não achar palavras chave
        texto = re.sub(r'^[\w\d]+\s+', '', texto)

    # Remove idade/datas do final
    match_idade = re.search(r'\s\d{1,2}[aA]\s', texto)
    if match_idade:
        texto = texto[:match_idade.start()]
    
    # Remove CIDs iniciais (Ex: O800)
    texto = re.sub(r'^[A-Z0-9]{3,4}\s+', '', texto)

    return texto.strip()

def definir_grupo_macro(texto):
    if "CESARIANA" in texto: return "CESARIANA"
    if "NORMAL" in texto: return "NORMAL"
    return "OUTROS"

df = df.dropna(subset=['Nascidos Vivos'])
df['Procedimento_Limpo'] = df['Procedimento'].apply(limpar_nome_procedimento_v2)
df = df[df['Procedimento_Limpo'] != "IGNORAR"]
df = df[df['Procedimento_Limpo'].str.len() > 3]
df['Grupo'] = df['Procedimento_Limpo'].apply(definir_grupo_macro)

# Agrupamento
df_agrupado = df.groupby(['Competência', 'Procedimento_Limpo', 'Grupo'])[[
    'Nascidos Vivos', 'Nascidos Mortos', 'Óbitos Neo'
]].sum().reset_index()

# Ordenação
df_agrupado['DataSort'] = pd.to_datetime(df_agrupado['Competência'], format='%m/%Y', errors='coerce')
df_agrupado = df_agrupado.sort_values(['DataSort', 'Grupo', 'Procedimento_Limpo'])

# JSON
dados_json = []
meses_unicos = sorted(list(df_agrupado['Competência'].unique()), 
                      key=lambda x: pd.to_datetime(x, format='%m/%Y'))

for index, row in df_agrupado.iterrows():
    dados_json.append({
        "mes": row['Competência'],
        "procedimento": row['Procedimento_Limpo'],
        "grupo": row['Grupo'],
        "vivos": int(row['Nascidos Vivos']),
        "mortos": int(row['Nascidos Mortos']),
        "obitos": int(row['Óbitos Neo']),
        "total": int(row['Nascidos Vivos'] + row['Nascidos Mortos'])
    })

json_string = json.dumps(dados_json, ensure_ascii=False)

# --- 2. HTML COM O LAYOUT VISUAL (O "Bonito" do PDF 1125) ---
html_content = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Indicadores Obstétricos HSH</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.bootstrap5.min.css">

    <style>
        body {{ background-color: #f4f7f6; font-family: 'Segoe UI', sans-serif; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        
        .header {{ background: white; padding: 20px 0; border-bottom: 3px solid #6f42c1; margin-bottom: 25px; }}
        .card-kpi {{ border: none; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); transition: transform 0.2s; }}
        .card-kpi:hover {{ transform: translateY(-5px); }}
        
        .badge-cesaria {{ background-color: #fd7e14 !important; color: white; }}
        .badge-normal {{ background-color: #20c997 !important; color: white; }}
        
        .chart-box {{ background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        .table-container {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}

        /* --- AJUSTES DE IMPRESSÃO (Mantendo o visual colorido) --- */
        @media print {{
            @page {{ size: A4 landscape; margin: 1cm; }} /* Força Paisagem para caber melhor */
            
            body {{ background-color: white !important; font-size: 11px; }}
            .container {{ max-width: 100% !important; width: 100% !important; padding: 0 !important; }}
            
            /* Esconder controles */
            .no-print, .dataTables_filter, .dataTables_length, .dataTables_paginate, .dataTables_info, select, button {{ display: none !important; }}
            
            /* Ajuste Cards */
            .card-kpi {{ border: 1px solid #ddd !important; box-shadow: none !important; margin-bottom: 10px; page-break-inside: avoid; }}
            
            /* Ajuste Gráficos */
            .chart-box {{ border: 1px solid #ddd !important; box-shadow: none !important; height: 220px !important; page-break-inside: avoid; }}
            
            /* Tabela Bonita mas Compacta */
            table {{ width: 100% !important; border-collapse: collapse !important; font-size: 10px !important; }}
            th {{ background-color: #f8f9fa !important; color: black !important; border-bottom: 2px solid #666 !important; }}
            td {{ border-bottom: 1px solid #eee !important; padding: 4px 8px !important; }}
            
            /* Forçar impressão de cores de fundo (badges) */
            .badge {{ color: white !important; border: none !important; -webkit-print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>

    <div class="header">
        <div class="container d-flex justify-content-between align-items-center">
            <div>
                <h3 class="fw-bold mb-0 text-primary"><i class="fas fa-hospital-user"></i> Indicadores Obstétricos</h3>
                <p class="text-muted mb-0 small">Hospital Beneficente Santa Helena - Núcleo de Informação</p>
            </div>
            <button class="btn btn-dark btn-sm no-print" onclick="window.print()"><i class="fas fa-print"></i> Imprimir / Salvar PDF</button>
        </div>
    </div>

    <div class="container mb-5">
        
        <div class="row mb-4 no-print">
            <div class="col-md-4">
                <label class="fw-bold text-secondary">Selecione o Mês:</label>
                <select id="filtroMes" class="form-select shadow-sm" onchange="atualizarDashboard()">
                    {''.join([f'<option value="{m}">{m}</option>' for m in meses_unicos])}
                    <option value="TODOS" selected>VISÃO GERAL (ANO COMPLETO)</option>
                </select>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-3 col-6 mb-2">
                <div class="card card-kpi bg-white h-100 py-3 text-center border-bottom border-4 border-success">
                    <h2 class="fw-bold text-success mb-0" id="kpiVivos">0</h2>
                    <small class="text-uppercase fw-bold text-muted">Nascidos Vivos</small>
                </div>
            </div>
            <div class="col-md-3 col-6 mb-2">
                <div class="card card-kpi bg-white h-100 py-3 text-center border-bottom border-4 border-primary">
                    <h2 class="fw-bold text-primary mb-0" id="kpiTotal">0</h2>
                    <small class="text-uppercase fw-bold text-muted">Total de Partos</small>
                </div>
            </div>
            <div class="col-md-3 col-6 mb-2">
                <div class="card card-kpi bg-white h-100 py-3 text-center border-bottom border-4 border-danger">
                    <h2 class="fw-bold text-danger mb-0" id="kpiObitos">0</h2>
                    <small class="text-uppercase fw-bold text-muted">Natimortos + Óbitos</small>
                </div>
            </div>
            <div class="col-md-3 col-6 mb-2">
                <div class="card card-kpi bg-primary text-white h-100 py-3 text-center">
                    <h2 class="fw-bold mb-0 text-white" id="kpiCesaria">0%</h2>
                    <small class="text-uppercase fw-bold opacity-75">Taxa Cesárea</small>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-4 mb-3">
                <div class="chart-box h-100">
                    <h6 class="text-center fw-bold text-secondary mb-3">Tipo de Parto</h6>
                    <div style="height: 200px;">
                        <canvas id="chartPizza"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-8 mb-3">
                <div class="chart-box h-100">
                    <h6 class="text-center fw-bold text-secondary mb-3">Top Procedimentos</h6>
                    <div style="height: 200px;">
                        <canvas id="chartBarras"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <div class="table-container">
            <h5 class="fw-bold text-secondary mb-3"><i class="fas fa-list"></i> Detalhamento</h5>
            <table id="tabelaDados" class="table table-hover align-middle w-100">
                <thead class="table-light">
                    <tr>
                        <th width="10%">Mês</th>
                        <th>Procedimento</th>
                        <th width="15%">Tipo</th>
                        <th class="text-center">Vivos</th>
                        <th class="text-center">Natimortos</th>
                        <th class="text-center">Óbitos</th>
                        <th class="text-center fw-bold">Total</th>
                    </tr>
                </thead>
                <tbody></tbody>
                <tfoot class="bg-light fw-bold">
                    <tr>
                        <td colspan="3" class="text-end">TOTAIS:</td>
                        <td class="text-center"></td>
                        <td class="text-center"></td>
                        <td class="text-center"></td>
                        <td class="text-center"></td>
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
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.53/pdfmake.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.53/vfs_fonts.js"></script>

    <script>
        const dadosRaw = {json_string};
        let table = null;
        let chartPizza = null;
        let chartBarras = null;

        function initTable(dados) {{
            if (table) {{ table.clear(); table.rows.add(dados); table.draw(); return; }}

            table = $('#tabelaDados').DataTable({{
                data: dados,
                columns: [
                    {{ data: 'mes' }},
                    {{ data: 'procedimento', className: 'fw-bold text-secondary' }},
                    {{ 
                        data: 'grupo',
                        render: function(data) {{
                            let cor = data === 'CESARIANA' ? 'badge-cesaria' : 'badge-normal';
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
                    {{ extend: 'excelHtml5', text: '<i class=\"fas fa-file-excel\"></i> Excel', className: 'btn-success btn-sm' }},
                    {{ extend: 'pdfHtml5', text: '<i class=\"fas fa-file-pdf\"></i> PDF', className: 'btn-danger btn-sm', orientation: 'landscape', pageSize: 'A4' }},
                    {{ extend: 'print', text: '<i class=\"fas fa-print\"></i> Imprimir', className: 'btn-dark btn-sm' }}
                ],
                paging: false,
                info: false,
                searching: true,
                language: {{ url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" }},
                footerCallback: function (row, data, start, end, display) {{
                    var api = this.api();
                    var intVal = function (i) {{ return typeof i === 'string' ? i.replace(/[\$,]/g, '')*1 : typeof i === 'number' ? i : 0; }};
                    
                    $(api.column(3).footer()).html(api.column(3).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                    $(api.column(4).footer()).html(api.column(4).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                    $(api.column(5).footer()).html(api.column(5).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                    $(api.column(6).footer()).html(api.column(6).data().reduce((a, b) => intVal(a) + intVal(b), 0));
                }}
            }});
        }}

        function atualizarDashboard() {{
            const mesSel = document.getElementById('filtroMes').value;
            let dados = dadosRaw;
            
            if (mesSel !== "TODOS") {{ dados = dadosRaw.filter(d => d.mes === mesSel); }}

            let tVivos = 0, tMortos = 0, tObitos = 0, tTotal = 0, tNormal = 0, tCesaria = 0;
            let procMap = {{}};

            dados.forEach(d => {{
                tVivos += d.vivos; tMortos += d.mortos; tObitos += d.obitos; tTotal += d.total;
                if(d.grupo === 'NORMAL') tNormal += d.total;
                if(d.grupo === 'CESARIANA') tCesaria += d.total;
                if(!procMap[d.procedimento]) procMap[d.procedimento] = 0;
                procMap[d.procedimento] += d.total;
            }});

            document.getElementById('kpiVivos').innerText = tVivos;
            document.getElementById('kpiTotal').innerText = tTotal;
            document.getElementById('kpiObitos').innerText = tMortos + tObitos;
            document.getElementById('kpiCesaria').innerText = tTotal > 0 ? ((tCesaria/tTotal)*100).toFixed(1) + '%' : '0%';

            initTable(dados);
            atualizarGraficos(tNormal, tCesaria, procMap);
        }}

        function atualizarGraficos(normal, cesaria, procMap) {{
            const ctx1 = document.getElementById('chartPizza').getContext('2d');
            if(chartPizza) chartPizza.destroy();
            chartPizza = new Chart(ctx1, {{
                type: 'doughnut',
                data: {{
                    labels: ['Normal', 'Cesariana'],
                    datasets: [{{ data: [normal, cesaria], backgroundColor: ['#20c997', '#fd7e14'], borderWidth: 0 }}]
                }},
                options: {{ 
                    responsive: true, 
                    maintainAspectRatio: false, 
                    plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }} }}
                }}
            }});

            const sortedProcs = Object.entries(procMap).sort((a,b) => b[1] - a[1]).slice(0, 5);
            const ctx2 = document.getElementById('chartBarras').getContext('2d');
            if(chartBarras) chartBarras.destroy();
            chartBarras = new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: sortedProcs.map(p => p[0]),
                    datasets: [{{
                        label: 'Qtd',
                        data: sortedProcs.map(p => p[1]),
                        backgroundColor: sortedProcs.map(p => p[0].includes('CESARIANA') ? '#fd7e14' : '#20c997')
                    }}]
                }},
                options: {{ 
                    indexAxis: 'y', 
                    responsive: true, 
                    maintainAspectRatio: false, 
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ x: {{ beginAtZero: true, ticks: {{ font: {{ size: 10 }} }} }}, y: {{ ticks: {{ font: {{ size: 10 }} }} }} }}
                }}
            }});
        }}

        document.addEventListener('DOMContentLoaded', () => {{ atualizarDashboard(); }});
    </script>
</body>
</html>
"""

try:
    with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("\n" + "="*50)
    print(f"✅ DASHBOARD VISUAL + DADOS LIMPOS!")
    print(f"📂 Arquivo: {ARQUIVO_HTML}")
    print("   Dica: Use a opção 'Paisagem' na hora de imprimir.")
    print("="*50)
except Exception as e:
    print(f"❌ Erro ao salvar HTML: {e}")