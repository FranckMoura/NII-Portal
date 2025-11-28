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
    """Remove o .0 de números que viraram texto (ex: 123.0 -> 123)"""
    if valor is None or valor == "":
        return "-"
    valor_str = str(valor)
    if valor_str.endswith('.0'):
        return valor_str[:-2]
    return valor_str

def gerar_html():
    print("--- GERANDO DASHBOARD COMPLETO (NII) - COLUNAS EXTRAS ---")
    
    # 1. Conectar ao Banco e Pegar Dados
    conn = sqlite3.connect(BANCO_DADOS)
    
    # A) Indicadores de Topo (KPIs)
    try:
        df_status = pd.read_sql_query("SELECT status_da_solicitacao_de_internacao, COUNT(*) as qtd FROM solicitacoes GROUP BY status_da_solicitacao_de_internacao", conn)
        total_solicitacoes = df_status['qtd'].sum()
        
        try: pendentes = df_status[df_status['status_da_solicitacao_de_internacao'].str.contains('Pendente', case=False, na=False)]['qtd'].sum()
        except: pendentes = 0
        
        try: aprovados = df_status[df_status['status_da_solicitacao_de_internacao'].str.contains('Aprovado', case=False, na=False)]['qtd'].sum()
        except: aprovados = 0
        
        try: negados = df_status[df_status['status_da_solicitacao_de_internacao'].str.contains('Negado|Cancelado', case=False, na=False)]['qtd'].sum()
        except: negados = 0

    except Exception as e:
        print(f"Erro ao ler KPIs: {e}")
        conn.close()
        return

    # B) Top 5 Procedimentos
    try:
        query_top = """
        SELECT nome_do_procedimento_solicitado, COUNT(*) as qtd 
        FROM solicitacoes 
        GROUP BY nome_do_procedimento_solicitado 
        ORDER BY qtd DESC LIMIT 5
        """
        df_top = pd.read_sql_query(query_top, conn)
        labels_top = df_top['nome_do_procedimento_solicitado'].tolist()
        data_top = df_top['qtd'].tolist()
    except:
        labels_top = []
        data_top = []

    # C) TODAS as Solicitações (Com Novas Colunas)
    try:
        # Aqui adicionamos as colunas que você pediu
        query_tabela = """
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
        ORDER BY 
            CASE WHEN status_da_solicitacao_de_internacao LIKE '%Pendente%' THEN 1 ELSE 2 END,
            data_da_solicitacao DESC
        """
        df_tabela = pd.read_sql_query(query_tabela, conn)
    except Exception as e:
        print(f"Erro ao buscar tabela: {e}")
        df_tabela = pd.DataFrame()

    conn.close()

    # 2. CONSTRUÇÃO DO HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel NII - Regulação HBSH</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
            :root {{ --primary: #0056b3; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --light: #f8f9fa; --dark: #343a40; }}
            body {{ font-family: 'Roboto', sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            
            .header {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ margin: 0; color: var(--primary); font-size: 24px; }}
            
            /* CARDS */
            .cards-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }}
            .card h3 {{ margin: 0 0 10px 0; color: #6c757d; font-size: 14px; text-transform: uppercase; }}
            .card .value {{ font-size: 36px; font-weight: bold; color: var(--dark); }}
            .card.blue .value {{ color: var(--primary); }}
            .card.green .value {{ color: var(--success); }}
            .card.yellow .value {{ color: var(--warning); }}
            .card.red .value {{ color: var(--danger); }}

            /* GRÁFICOS */
            .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
            .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            
            /* TABELA COM ROLAGEM */
            .table-container {{ 
                background: white; 
                padding: 0; 
                border-radius: 10px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
                max-height: 600px; 
                overflow-y: auto; 
                position: relative;
            }}
            
            .table-header-title {{
                padding: 20px;
                position: sticky;
                top: 0;
                background: white;
                z-index: 5;
                border-bottom: 2px solid #dee2e6;
                margin: 0;
            }}

            table {{ width: 100%; border-collapse: collapse; min-width: 1000px; }} /* min-width garante que a tabela não esmague em telas pequenas */
            
            thead th {{ 
                position: sticky; 
                top: 0; 
                background-color: #f8f9fa; 
                color: var(--dark);
                z-index: 2; 
                box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.1);
                font-size: 13px;
                text-transform: uppercase;
            }}
            
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #dee2e6; font-size: 13px; }}
            tr:hover {{ background-color: #f1f1f1; }}
            
            .status-badge {{ padding: 5px 10px; border-radius: 15px; font-size: 11px; color: white; font-weight: bold; display: inline-block; min-width: 80px; text-align: center; }}
            .bg-aprovado {{ background-color: var(--success); }}
            .bg-pendente {{ background-color: var(--warning); color: #333; }}
            .bg-negado {{ background-color: var(--danger); }}
            .bg-outro {{ background-color: var(--primary); }}
            .bg-neutro {{ background-color: #6c757d; }}

            .col-data {{ min-width: 90px; }}
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
                <p>Atualizado em:</p>
                <strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong>
            </div>
        </div>

        <div class="cards-container">
            <div class="card blue">
                <h3>Total Solicitações</h3>
                <div class="value">{total_solicitacoes}</div>
            </div>
            <div class="card green">
                <h3>Aprovados</h3>
                <div class="value">{aprovados}</div>
            </div>
            <div class="card yellow">
                <h3>Pendentes</h3>
                <div class="value">{pendentes}</div>
            </div>
            <div class="card red">
                <h3>Negados/Cancel</h3>
                <div class="value">{negados}</div>
            </div>
        </div>

        <div class="charts-row">
            <div class="chart-container">
                <h3>Top 5 Procedimentos</h3>
                <canvas id="chartProcedimentos"></canvas>
            </div>
            <div class="chart-container">
                <h3>Status da Regulação</h3>
                <canvas id="chartStatus"></canvas>
            </div>
        </div>

        <div class="table-container">
            <h3 class="table-header-title">
                Lista Completa de Solicitações
                <span style="font-size: 12px; color: #666; margin-left: 10px; font-weight: normal;">Exibindo {len(df_tabela)} registros</span>
            </h3>
            <table>
                <thead>
                    <tr>
                        <th class="col-data">Data</th>
                        <th class="col-paciente">Paciente</th>
                        <th>CNS</th>
                        <th>Nº Solicit.</th>
                        <th>Nº AIH</th>
                        <th class="col-proc">Procedimento</th>
                        <th>Caráter</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for index, row in df_tabela.iterrows():
        status = row['status_da_solicitacao_de_internacao']
        if status is None: status = "Indefinido"
        
        # Cores das badges
        css_class = "bg-outro"
        if "Aprovado" in status: css_class = "bg-aprovado"
        elif "Pendente" in status: css_class = "bg-pendente"
        elif "Negado" in status or "Cancelado" in status: css_class = "bg-negado"
        elif "Indefinido" in status: css_class = "bg-neutro"
        
        # Formatação
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
            // Gráfico de Barras
            new Chart(document.getElementById('chartProcedimentos'), {{
                type: 'bar',
                data: {{
                    labels: {labels_top},
                    datasets: [{{
                        label: 'Qtd',
                        data: {data_top},
                        backgroundColor: '#0056b3',
                        borderRadius: 5
                    }}]
                }},
                options: {{ indexAxis: 'y', responsive: true, plugins: {{ legend: {{ display: false }} }} }}
            }});

            // Gráfico de Rosca
            new Chart(document.getElementById('chartStatus'), {{
                type: 'doughnut',
                data: {{
                    labels: ['Aprovados', 'Pendentes', 'Negados/Outros'],
                    datasets: [{{
                        data: [{aprovados}, {pendentes}, {negados}],
                        backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                    }}]
                }},
                options: {{ responsive: true, cutout: '70%' }}
            }});
        </script>
    </body>
    </html>
    """

    with open(CAMINHO_FINAL_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Relatório gerado com sucesso! {len(df_tabela)} registros processados.")
    # Comente a linha abaixo se não quiser que abra o navegador toda vez
    # webbrowser.open('file://' + os.path.realpath(CAMINHO_FINAL_HTML))

if __name__ == "__main__":
    gerar_html()