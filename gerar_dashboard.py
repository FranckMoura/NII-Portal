import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
import webbrowser

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
BANCO_DADOS = os.path.join(PASTA_PROJETO, "dados_sisreg.db")
NOME_ARQUIVO_HTML = "painel_regulacao.html"
CAMINHO_FINAL_HTML = os.path.join(PASTA_PROJETO, NOME_ARQUIVO_HTML)

# Define quantos dias para trás você quer ver (Ex: 90 dias pega Out, Nov e Dez)
DIAS_RETROATIVOS = 90 

def formatar_numero(valor):
    if valor is None or valor == "": return "-"
    valor_str = str(valor)
    if valor_str.endswith('.0'): return valor_str[:-2]
    return valor_str

def gerar_html():
    print("--- GERANDO DASHBOARD (JANELA DE TEMPO) ---")
    
    conn = sqlite3.connect(BANCO_DADOS)
    
    try:
        # Carrega TUDO
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
        df_full = pd.read_sql_query(query, conn)
        df_full['data_dt'] = pd.to_datetime(df_full['data_da_solicitacao'], dayfirst=True, errors='coerce')
        
        # --- FILTRO INTELIGENTE (ÚLTIMOS X DIAS) ---
        data_corte = datetime.now() - timedelta(days=DIAS_RETROATIVOS)
        
        # Filtra tudo que for MAIOR (mais recente) que a data de corte
        df_mes = df_full[df_full['data_dt'] >= data_corte].copy()
        
        # Formata a data de corte para mostrar no título
        texto_periodo = f"Últimos {DIAS_RETROATIVOS} dias (Desde {data_corte.strftime('%d/%m/%Y')})"
        
        print(f"Registros encontrados ({texto_periodo}): {len(df_mes)}")

    except Exception as e:
        print(f"Erro: {e}")
        conn.close()
        return

    conn.close()

    # INDICADORES
    total_solicitacoes = len(df_mes)
    status_series = df_mes['status_da_solicitacao_de_internacao'].fillna('Indefinido')
    aprovados = status_series[status_series.str.contains('Aprovado', case=False)].count()
    pendentes = status_series[status_series.str.contains('Pendente', case=False)].count()
    negados = status_series[status_series.str.contains('Negado|Cancelado', case=False)].count()

    # Top 5
    top_procs = df_mes['nome_do_procedimento_solicitado'].value_counts().head(5)
    labels_top = top_procs.index.tolist()
    data_top = top_procs.values.tolist()

    # Ordenação (Pendentes primeiro, depois data mais recente)
    df_mes['prioridade'] = df_mes['status_da_solicitacao_de_internacao'].apply(lambda x: 1 if x and 'Pendente' in x else 2)
    df_mes = df_mes.sort_values(by=['prioridade', 'data_dt'], ascending=[True, False])

    # HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel NII - Regulação HBSH</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <style>
            :root {{ --primary: #0056b3; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --light: #f8f9fa; --dark: #343a40; }}
            body {{ font-family: 'Roboto', sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            
            .header {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ margin: 0; color: var(--primary); font-size: 24px; }}
            .periodo-badge {{ background: #e9ecef; padding: 5px 15px; border-radius: 20px; color: #555; font-size: 14px; font-weight: bold; border: 1px solid #ced4da; }}

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
            
            .table-container {{ background: white; padding: 0; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); max-height: 600px; overflow-y: auto; position: relative; }}
            .table-header-title {{ padding: 20px; position: sticky; top: 0; background: white; z-index: 5; border-bottom: 2px solid #dee2e6; margin: 0; display: flex; justify-content: space-between; align-items: center; }}
            
            table {{ width: 100%; border-collapse: collapse; min-width: 1000px; }}
            
            /* ESTILO DOS CABEÇALHOS CLICÁVEIS */
            thead th {{ 
                position: sticky; top: 0; background-color: #f8f9fa; color: var(--dark); z-index: 2; 
                box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.1); 
                font-size: 13px; text-transform: uppercase; padding: 12px 15px; text-align: left; 
                cursor: pointer; /* Mãozinha */
                user-select: none; /* Não seleciona texto ao clicar rápido */
            }}
            thead th:hover {{ background-color: #e2e6ea; }}
            thead th i {{ margin-left: 5px; color: #ccc; font-size: 10px; }}
            
            td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #dee2e6; font-size: 13px; }}
            tr:hover {{ background-color: #f1f1f1; }}
            
            .status-badge {{ padding: 5px 10px; border-radius: 15px; font-size: 11px; color: white; font-weight: bold; display: inline-block; min-width: 80px; text-align: center; }}
            .bg-aprovado {{ background-color: var(--success); }}
            .bg-pendente {{ background-color: var(--warning); color: #333; }}
            .bg-negado {{ background-color: var(--danger); }}
            .bg-outro {{ background-color: var(--primary); }}
            .bg-neutro {{ background-color: #6c757d; }}
            
            .col-paciente {{ min-width: 200px; font-weight: 500; }}
            .col-proc {{ min-width: 200px; color: #555; }}

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
                <span class="periodo-badge">📅 {texto_periodo}</span>
                <p style="font-size: 12px; color: #999; margin-top: 5px;">Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
        </div>

        <div class="cards-container">
            <div class="card blue"><h3>Total (Período)</h3><div class="value">{total_solicitacoes}</div></div>
            <div class="card green"><h3>Aprovados</h3><div class="value">{aprovados}</div></div>
            <div class="card yellow"><h3>Pendentes</h3><div class="value">{pendentes}</div></div>
            <div class="card red"><h3>Negados/Cancel</h3><div class="value">{negados}</div></div>
        </div>

        <div class="charts-row">
            <div class="chart-container"><h3>Top 5 Procedimentos</h3><canvas id="chartProcedimentos"></canvas></div>
            <div class="chart-container"><h3>Status da Regulação</h3><canvas id="chartStatus"></canvas></div>
        </div>

        <div class="table-container">
            <div class="table-header-title">
                <span>Solicitações Recentes</span>
                <span style="font-size: 12px; color: #666;">{len(df_mes)} registros</span>
            </div>
            <table id="tabelaRegulacao">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)" style="min-width:90px">Data <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(1)" class="col-paciente">Paciente <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(2)">CNS <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(3)">Nº Solicit. <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(4)">Nº AIH <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(5)" class="col-proc">Procedimento <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(6)">Caráter <i class="fas fa-sort"></i></th>
                        <th onclick="sortTable(7)">Status <i class="fas fa-sort"></i></th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for index, row in df_mes.iterrows():
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
            // GRÁFICOS
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

            // FUNÇÃO DE ORDENAÇÃO
            function sortTable(n) {{
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("tabelaRegulacao");
                switching = true;
                dir = "asc"; 

                while (switching) {{
                    switching = false;
                    rows = table.rows;
                    for (i = 1; i < (rows.length - 1); i++) {{
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        
                        var xContent = x.innerText.toLowerCase();
                        var yContent = y.innerText.toLowerCase();

                        if (n === 0) {{ // Data
                            xContent = xContent.split('/').reverse().join(''); 
                            yContent = yContent.split('/').reverse().join('');
                        }}
                        else if (!isNaN(parseFloat(xContent)) && isFinite(xContent)) {{ // Número
                            xContent = parseFloat(xContent);
                            yContent = parseFloat(yContent);
                        }}

                        if (dir == "asc") {{
                            if (xContent > yContent) {{ shouldSwitch = true; break; }}
                        }} else if (dir == "desc") {{
                            if (xContent < yContent) {{ shouldSwitch = true; break; }}
                        }}
                    }}
                    if (shouldSwitch) {{
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                        switchcount ++;
                    }} else {{
                        if (switchcount == 0 && dir == "asc") {{
                            dir = "desc";
                            switching = true;
                        }}
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """

    with open(CAMINHO_FINAL_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Relatório gerado com sucesso! (Período: Últimos {DIAS_RETROATIVOS} dias)")

if __name__ == "__main__":
    gerar_html()