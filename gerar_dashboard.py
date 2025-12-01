import sqlite3
import pandas as pd
import os
from datetime import datetime
import webbrowser

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
BANCO_DADOS = os.path.join(PASTA_PROJETO, "dados_sisreg.db")
NOME_ARQUIVO_HTML = "painel_regulacao.html"
CAMINHO_FINAL_HTML = os.path.join(PASTA_PROJETO, NOME_ARQUIVO_HTML)

def formatar_numero(valor):
    if valor is None or valor == "": return "-"
    valor_str = str(valor)
    if valor_str.endswith('.0'): return valor_str[:-2]
    return valor_str

def gerar_html():
    print("--- GERANDO DASHBOARD (COM FILTRO DINÂMICO) ---")
    
    conn = sqlite3.connect(BANCO_DADOS)
    
    try:
        # Carrega TUDO do banco (sem filtro de data no SQL)
        query = """
        SELECT 
            data_da_solicitacao,
            nome_do_paciente,
            cns_do_paciente,
            n_da_solicitacao,
            n_aih,
            nome_do_procedimento_solicitado,
            status_da_solicitacao_de_internacao,
            carater_internacao
        FROM solicitacoes
        """
        df = pd.read_sql_query(query, conn)
        df['data_dt'] = pd.to_datetime(df['data_da_solicitacao'], dayfirst=True, errors='coerce')
        
        # Opcional: Se o banco for MUITO gigante (anos), limite aqui ao ano atual para não pesar o site
        # df = df[df['data_dt'].dt.year >= 2024] 
        
        print(f"Total de registros carregados para o painel: {len(df)}")

    except Exception as e:
        print(f"Erro ao ler banco: {e}")
        conn.close()
        return

    conn.close()

    # Cálculos Gerais (Baseados em TODO o histórico carregado)
    total_geral = len(df)
    status_series = df['status_da_solicitacao_de_internacao'].fillna('Indefinido')
    aprovados = status_series[status_series.str.contains('Aprovado', case=False)].count()
    pendentes = status_series[status_series.str.contains('Pendente', case=False)].count()
    negados = status_series[status_series.str.contains('Negado|Cancelado', case=False)].count()

    # Top 5 (Geral)
    top_procs = df['nome_do_procedimento_solicitado'].value_counts().head(5)
    labels_top = top_procs.index.tolist()
    data_top = top_procs.values.tolist()

    # Ordenação Inicial (Pendentes no topo, depois data mais recente)
    df['prioridade'] = df['status_da_solicitacao_de_internacao'].apply(lambda x: 1 if x and 'Pendente' in x else 2)
    df = df.sort_values(by=['prioridade', 'data_dt'], ascending=[True, False])

    # HTML START
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel NII - Regulação HBSH</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>

        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            :root {{ --primary: #0056b3; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --light: #f8f9fa; --dark: #343a40; }}
            body {{ font-family: 'Roboto', sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            
            .header {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ margin: 0; color: var(--primary); font-size: 24px; }}
            
            .cards-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }}
            .card h3 {{ margin: 0 0 10px 0; color: #6c757d; font-size: 14px; text-transform: uppercase; }}
            .card .value {{ font-size: 36px; font-weight: bold; color: var(--dark); }}
            .card.blue .value {{ color: var(--primary); }}
            .card.green .value {{ color: var(--success); }}
            .card.yellow .value {{ color: var(--warning); }}
            .card.red .value {{ color: var(--danger); }}

            .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
            .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            
            .table-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            
            /* ESTILO DOS FILTROS DE DATA */
            .filter-box {{ display: flex; gap: 15px; margin-bottom: 15px; align-items: center; background: #e9ecef; padding: 10px; border-radius: 8px; }}
            .filter-box label {{ font-weight: bold; color: #555; }}
            .filter-box input {{ padding: 5px; border: 1px solid #ccc; border-radius: 4px; }}
            
            table.dataTable thead th {{ background-color: #f8f9fa; color: var(--dark); }}
            
            .status-badge {{ padding: 5px 10px; border-radius: 15px; font-size: 11px; color: white; font-weight: bold; display: inline-block; min-width: 80px; text-align: center; }}
            .bg-aprovado {{ background-color: var(--success); }}
            .bg-pendente {{ background-color: var(--warning); color: #333; }}
            .bg-negado {{ background-color: var(--danger); }}
            .bg-outro {{ background-color: var(--primary); }}
            .bg-neutro {{ background-color: #6c757d; }}

            @media (max-width: 768px) {{ .charts-row {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>

        <div class="header">
            <div>
                <h1>Portal NII - Monitoramento de Regulação</h1>
                <p>Hospital Beneficente Santa Helena</p>
            </div>
            <div style="text-align: right;">
                <p style="font-size: 12px; color: #999;">Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <a href="index.html" style="text-decoration:none; background:#6c757d; color:white; padding:5px 10px; border-radius:5px; font-size:12px;">Voltar</a>
            </div>
        </div>

        <div class="cards-container">
            <div class="card blue"><h3>Total Histórico</h3><div class="value">{total_geral}</div></div>
            <div class="card green"><h3>Aprovados</h3><div class="value">{aprovados}</div></div>
            <div class="card yellow"><h3>Pendentes</h3><div class="value">{pendentes}</div></div>
            <div class="card red"><h3>Negados/Cancel</h3><div class="value">{negados}</div></div>
        </div>

        <div class="charts-row">
            <div class="chart-container"><h3>Top 5 Procedimentos (Geral)</h3><canvas id="chartProcedimentos"></canvas></div>
            <div class="chart-container"><h3>Status da Regulação</h3><canvas id="chartStatus"></canvas></div>
        </div>

        <div class="table-container">
            <h3 style="margin-top:0;">Pesquisa Detalhada</h3>
            
            <div class="filter-box">
                <i class="fas fa-filter" style="color:#0056b3"></i>
                <label>De:</label>
                <input type="date" id="minDate" name="minDate">
                <label>Até:</label>
                <input type="date" id="maxDate" name="maxDate">
                <span style="font-size:12px; color:#666; margin-left:10px;">(Selecione as datas para filtrar a tabela)</span>
            </div>

            <table id="tabelaRegulacao" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Paciente</th>
                        <th>CNS</th>
                        <th>Nº Solicit.</th>
                        <th>Nº AIH</th>
                        <th>Procedimento</th>
                        <th>Caráter</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for index, row in df.iterrows():
        status = row['status_da_solicitacao_de_internacao']
        if status is None: status = "Indefinido"
        
        css_class = "bg-outro"
        if "Aprovado" in status: css_class = "bg-aprovado"
        elif "Pendente" in status: css_class = "bg-pendente"
        elif "Negado" in status or "Cancelado" in status: css_class = "bg-negado"
        elif "Indefinido" in status: css_class = "bg-neutro"
        
        data_sol = row['data_da_solicitacao']
        paciente = row['nome_do_paciente']
        cns = formatar_numero(row['cns_do_paciente'])
        n_sol = formatar_numero(row['n_da_solicitacao'])
        n_aih = formatar_numero(row['n_aih'])
        proc = row['nome_do_procedimento_solicitado']
        carater = row['carater_internacao'] if row['carater_internacao'] else "-"

        html_content += f"""
                    <tr>
                        <td>{data_sol}</td>
                        <td>{paciente}</td>
                        <td>{cns}</td>
                        <td>{n_sol}</td>
                        <td>{n_aih}</td>
                        <td>{proc}</td>
                        <td>{carater}</td>
                        <td><span class="status-badge {css_class}">{status}</span></td>
                    </tr>
        """

    html_content += f"""
                </tbody>
            </table>
        </div>

        <script>
            // GRÁFICOS (Estaticos do histórico)
            new Chart(document.getElementById('chartProcedimentos'), {{
                type: 'bar',
                data: {{ labels: {labels_top}, datasets: [{{ label: 'Qtd', data: {data_top}, backgroundColor: '#0056b3', borderRadius: 5 }}] }},
                options: {{ indexAxis: 'y', responsive: true, plugins: {{ legend: {{ display: false }} }} }}
            }});

            new Chart(document.getElementById('chartStatus'), {{
                type: 'doughnut',
                data: {{ labels: ['Aprovados', 'Pendentes', 'Negados/Outros'], datasets: [{{ data: [{aprovados}, {pendentes}, {negados}], backgroundColor: ['#28a745', '#ffc107', '#dc3545'] }}] }},
                options: {{ responsive: true, cutout: '70%' }}
            }});

            // --- LÓGICA DE FILTRO DE DATA (DataTables) ---
            
            // Função personalizada de busca
            $.fn.dataTable.ext.search.push(
                function(settings, data, dataIndex) {{
                    var min = $('#minDate').val();
                    var max = $('#maxDate').val();
                    
                    // A data está na coluna 0 no formato dd/mm/aaaa
                    var dateParts = data[0].split("/");
                    // Cria objeto Data (Ano, Mês-1, Dia)
                    var date = new Date(dateParts[2], dateParts[1] - 1, dateParts[0]);

                    if (
                        (min === "" && max === "") ||
                        (min === "" && date <= new Date(max)) ||
                        (new Date(min) <= date && max === "") ||
                        (new Date(min) <= date && date <= new Date(max))
                    ) {{
                        return true;
                    }}
                    return false;
                }}
            );

            $(document).ready(function() {{
                var table = $('#tabelaRegulacao').DataTable({{
                    "order": [], // Mantém ordenação do Python
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" }},
                    "pageLength": 10
                }});

                // Event listener para refazer o filtro quando mudar a data
                $('#minDate, #maxDate').on('change', function() {{
                    table.draw();
                }});
            }});
        </script>
    </body>
    </html>
    """

    with open(CAMINHO_FINAL_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Relatório gerado! Filtro de data disponível na tela.")

if __name__ == "__main__":
    gerar_html()