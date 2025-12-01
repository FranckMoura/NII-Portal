import sqlite3
import pandas as pd
import os
from datetime import datetime
import json

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
BANCO_DADOS = os.path.join(PASTA_PROJETO, "dados_sisreg.db")
NOME_ARQUIVO_HTML = "painel_regulacao.html"
CAMINHO_FINAL_HTML = os.path.join(PASTA_PROJETO, NOME_ARQUIVO_HTML)

def gerar_html():
    print("--- GERANDO DASHBOARD (PAINEL VIVO 100% DINÂMICO) ---")
    
    conn = sqlite3.connect(BANCO_DADOS)
    
    # Datas padrão (Mês atual)
    hoje = datetime.now()
    data_inicio_padrao = hoje.replace(day=1).strftime('%Y-%m-%d')
    data_fim_padrao = hoje.strftime('%Y-%m-%d')
    
    try:
        # Carrega TUDO do ano atual
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
        
        # Filtra apenas o ano atual para não pesar o navegador
        df = df[df['data_dt'].dt.year == hoje.year].copy()
        
        # Converte datas para string ISO (yyyy-mm-dd) para facilitar o JS
        df['data_iso'] = df['data_dt'].dt.strftime('%Y-%m-%d')
        
        # Prepara os dados para o JavaScript (JSON)
        # Vamos passar a lista de dicionários para o front-end
        dados_json = df.to_json(orient='records')
        
        print(f"Registros processados: {len(df)}")

    except Exception as e:
        print(f"Erro: {e}")
        conn.close()
        return

    conn.close()

    # HTML
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
            :root {{ --primary: #0056b3; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --dark: #343a40; }}
            body {{ font-family: 'Roboto', sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            
            .header {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ margin: 0; color: var(--primary); font-size: 24px; }}
            
            .filter-box {{ display: flex; gap: 15px; margin-bottom: 20px; align-items: center; background: #e3f2fd; padding: 15px; border-radius: 8px; border: 1px solid #90caf9; }}
            .filter-box label {{ font-weight: bold; color: #0056b3; }}
            .filter-box input {{ padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-weight: bold; }}
            
            .cards-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }}
            .card h3 {{ margin: 0 0 10px 0; color: #6c757d; font-size: 14px; text-transform: uppercase; }}
            .card .value {{ font-size: 36px; font-weight: bold; color: var(--dark); }}
            .card.blue .value {{ color: var(--primary); }}
            .card.green .value {{ color: var(--success); }}
            .card.yellow .value {{ color: var(--warning); }}
            .card.red .value {{ color: var(--danger); }}

            .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
            .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); position: relative; height: 350px; }}
            
            .table-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            
            .status-badge {{ padding: 5px 10px; border-radius: 15px; font-size: 11px; color: white; font-weight: bold; display: inline-block; min-width: 80px; text-align: center; }}
            .bg-aprovado {{ background-color: var(--success); }}
            .bg-pendente {{ background-color: var(--warning); color: #333; }}
            .bg-negado {{ background-color: var(--danger); }}
            .bg-outro {{ background-color: var(--primary); }}
            
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

        <div class="filter-box">
            <i class="fas fa-calendar-alt" style="font-size:20px; color:#0056b3;"></i>
            <div>
                <label>Início:</label>
                <input type="date" id="minDate" value="{data_inicio_padrao}">
            </div>
            <div>
                <label>Fim:</label>
                <input type="date" id="maxDate" value="{data_fim_padrao}">
            </div>
            <button onclick="atualizarDashboard()" style="background:#0056b3; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Filtrar</button>
        </div>

        <div class="cards-container">
            <div class="card blue"><h3>Total (Período)</h3><div class="value" id="valTotal">-</div></div>
            <div class="card green"><h3>Aprovados</h3><div class="value" id="valAprovados">-</div></div>
            <div class="card yellow"><h3>Pendentes</h3><div class="value" id="valPendentes">-</div></div>
            <div class="card red"><h3>Negados/Cancel</h3><div class="value" id="valNegados">-</div></div>
        </div>

        <div class="charts-row">
            <div class="chart-container"><h3>Top 5 Procedimentos</h3><canvas id="chartProcedimentos"></canvas></div>
            <div class="chart-container"><h3>Status da Regulação</h3><canvas id="chartStatus"></canvas></div>
        </div>

        <div class="table-container">
            <h3 style="margin-top:0;">Pesquisa Detalhada</h3>
            <table id="tabelaRegulacao" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Paciente</th>
                        <th>CNS</th>
                        <th>Nº Solicit.</th>
                        <th>Nº AIH</th>
                        <th>Procedimento</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <script>
            // --- DADOS DO PYTHON PARA O JS ---
            const todosDados = {dados_json}; // Lista completa de objetos
            
            let chartStatus = null;
            let chartProc = null;
            let table = null;

            // Inicializa a tabela vazia (mas configurada)
            $(document).ready(function() {{
                table = $('#tabelaRegulacao').DataTable({{
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" }},
                    "pageLength": 10,
                    "columns": [
                        {{ "data": "data_da_solicitacao" }},
                        {{ "data": "nome_do_paciente" }},
                        {{ "data": "cns_do_paciente" }},
                        {{ "data": "n_da_solicitacao" }},
                        {{ "data": "n_aih" }},
                        {{ "data": "nome_do_procedimento_solicitado" }},
                        {{ 
                            "data": "status_da_solicitacao_de_internacao",
                            "render": function(data, type, row) {{
                                let css = "bg-outro";
                                if(data && data.includes("Aprovado")) css = "bg-aprovado";
                                else if(data && data.includes("Pendente")) css = "bg-pendente";
                                else if(data && (data.includes("Negado") || data.includes("Cancelado"))) css = "bg-negado";
                                return `<span class="status-badge ${{css}}">${{data || '-'}}</span>`;
                            }}
                        }}
                    ]
                }});

                // Carrega primeira vez
                atualizarDashboard();
            }});

            function atualizarDashboard() {{
                const dInicio = document.getElementById('minDate').value;
                const dFim = document.getElementById('maxDate').value;

                // 1. FILTRAR DADOS
                const dadosFiltrados = todosDados.filter(item => {{
                    if (!item.data_iso) return false;
                    return item.data_iso >= dInicio && item.data_iso <= dFim;
                }});

                // 2. CALCULAR TOTAIS
                let total = dadosFiltrados.length;
                let aprovados = 0, pendentes = 0, negados = 0;
                let contagemProc = {{}};

                dadosFiltrados.forEach(item => {{
                    const st = item.status_da_solicitacao_de_internacao || "";
                    if(st.includes("Aprovado")) aprovados++;
                    else if(st.includes("Pendente")) pendentes++;
                    else if(st.includes("Negado") || st.includes("Cancelado")) negados++;

                    // Contagem Top 5
                    const proc = item.nome_do_procedimento_solicitado || "Indefinido";
                    contagemProc[proc] = (contagemProc[proc] || 0) + 1;
                }});

                // 3. ATUALIZAR CARDS
                document.getElementById('valTotal').innerText = total;
                document.getElementById('valAprovados').innerText = aprovados;
                document.getElementById('valPendentes').innerText = pendentes;
                document.getElementById('valNegados').innerText = negados;

                // 4. ATUALIZAR GRÁFICOS
                atualizarGraficos(aprovados, pendentes, negados, contagemProc);

                // 5. ATUALIZAR TABELA
                table.clear().rows.add(dadosFiltrados).draw();
            }}

            function atualizarGraficos(aprovados, pendentes, negados, contagemProc) {{
                // Gráfico Pizza
                const ctxStatus = document.getElementById('chartStatus');
                if (chartStatus) chartStatus.destroy();
                
                chartStatus = new Chart(ctxStatus, {{
                    type: 'doughnut',
                    data: {{
                        labels: ['Aprovados', 'Pendentes', 'Negados/Outros'],
                        datasets: [{{ data: [aprovados, pendentes, negados], backgroundColor: ['#28a745', '#ffc107', '#dc3545'] }}]
                    }},
                    options: {{ responsive: true, maintainAspectRatio: false, cutout: '65%' }}
                }});

                // Gráfico Barras (Top 5)
                // Ordena o objeto de contagem e pega os 5 primeiros
                const top5 = Object.entries(contagemProc).sort((a, b) => b[1] - a[1]).slice(0, 5);
                const labelsTop = top5.map(x => x[0].substring(0, 25) + '...');
                const dataTop = top5.map(x => x[1]);

                const ctxProc = document.getElementById('chartProcedimentos');
                if (chartProc) chartProc.destroy();

                chartProc = new Chart(ctxProc, {{
                    type: 'bar',
                    data: {{
                        labels: labelsTop,
                        datasets: [{{ label: 'Qtd', data: dataTop, backgroundColor: '#0056b3', borderRadius: 5 }}]
                    }},
                    options: {{ 
                        indexAxis: 'y', 
                        responsive: true, 
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }} }}
                    }}
                }});
            }}
        </script>
    </body>
    </html>
    """

    with open(CAMINHO_FINAL_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Painel Dinâmico gerado! Registros inclusos: {len(df)}")

if __name__ == "__main__":
    gerar_html()