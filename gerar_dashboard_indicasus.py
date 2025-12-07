import sqlite3
import pandas as pd
import os
from datetime import datetime
import json

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
PASTA_ARQUIVOS = os.path.join(PASTA_PROJETO, "arquivos")
BANCO_DADOS = os.path.join(PASTA_PROJETO, "dados_sisreg.db")

NOME_HTML = "indicasus.html" 
NOME_JSON = "dados_indicasus.json"

CAMINHO_HTML = os.path.join(PASTA_PROJETO, NOME_HTML)
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, NOME_JSON)

def gerar_painel():
    print("--- GERANDO DASHBOARD INDICASUS (V3 - CARGA TOTAL) ---")
    
    if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

    conn = sqlite3.connect(BANCO_DADOS)
    
    try:
        # Carrega dados
        df = pd.read_sql_query("SELECT * FROM indicasus", conn)
        
        if df.empty:
            print("❌ Tabela Indicasus vazia no banco.")
            return

        # Diagnóstico de Data
        print(f"   Exemplo de data no banco: {df['data_internacao'].iloc[0]}")

        # Tenta converter Data para ordenação (sem filtrar/cortar nada)
        df['data_obj'] = pd.to_datetime(df['data_internacao'], dayfirst=True, errors='coerce')
        
        # Ordena (Mais recente primeiro) e cria string ISO
        df = df.sort_values(by='data_obj', ascending=False)
        df['data_internacao'] = df['data_obj'].dt.strftime('%d/%m/%Y').fillna("-") # Garante formato BR visual
        
        # Remove a coluna temporária de objeto para não bugar o JSON
        df = df.drop(columns=['data_obj'])
        
        # Preenche vazios
        df = df.fillna("-")
        
        # Salva JSON COMPLETO (Sem cortes de data)
        df.to_json(CAMINHO_JSON, orient='records', force_ascii=False)
        
        print(f"   💾 JSON gerado com SUCESSO: {len(df)} registros.")

        # HTML (Visual)
        html_template = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NII - IndicaSUS</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        :root {{ --primary: #6f42c1; --success: #28a745; --warning: #ffc107; --danger: #dc3545; }}
        body {{ font-family: 'Roboto', sans-serif; background: #f4f6f9; padding: 20px; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .cards-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #ccc; }}
        .card .value {{ font-size: 32px; font-weight: bold; margin-top: 10px; color: #333; }}
        .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .chart-box {{ background: white; padding: 20px; border-radius: 8px; height: 350px; }}
        .table-box {{ background: white; padding: 20px; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1 style="color:var(--primary)">Monitoramento IndicaSUS</h1>
            <p>Histórico Completo ({len(df)} registros)</p>
        </div>
        <a href="index.html" style="text-decoration:none; background:#666; color:white; padding:8px 15px; border-radius:4px;">Voltar</a>
    </div>

    <div class="cards-container">
        <div class="card" style="border-color: var(--primary)"><h3>Total</h3><div class="value" id="vTotal">-</div></div>
        <div class="card" style="border-color: #28a745"><h3>Altas</h3><div class="value" id="vAlta">-</div></div>
        <div class="card" style="border-color: #dc3545"><h3>Óbitos</h3><div class="value" id="vObito">-</div></div>
        <div class="card" style="border-color: #ffc107"><h3>Internados</h3><div class="value" id="vInternado">-</div></div>
    </div>

    <div class="charts-row">
        <div class="chart-box"><h3>Tipo de Leito</h3><canvas id="cLeito"></canvas></div>
        <div class="chart-box"><h3>Desfecho Clínico</h3><canvas id="cEvolucao"></canvas></div>
    </div>

    <div class="table-box">
        <table id="tabelaIndica" class="display" style="width:100%">
            <thead>
                <tr><th>Data</th><th>Paciente</th><th>CNS</th><th>Município</th><th>Leito</th><th>Evolução</th><th>AIH</th></tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>

    <script>
        // Cache Buster para garantir dados novos
        fetch('arquivos/{NOME_JSON}?v=' + new Date().getTime())
            .then(res => res.json())
            .then(dados => {{
                processar(dados);
            }})
            .catch(err => console.error("Erro ao carregar JSON:", err));

        function processar(dados) {{
            let total = dados.length;
            let alta = 0, obito = 0, internado = 0;
            let tiposLeito = {{}};
            let evolucoes = {{}};

            dados.forEach(d => {{
                let ev = (d.evolucao || "").toLowerCase();
                let leito = d.tipo_leito || "Não Informado";

                if(ev.includes("alta") || ev.includes("cura")) alta++;
                else if(ev.includes("obito") || ev.includes("óbito") || ev.includes("falecimento")) obito++;
                else internado++;

                // Contagens
                tiposLeito[leito] = (tiposLeito[leito] || 0) + 1;
                
                let evSimples = "Internado/Outros";
                if(ev.includes("alta")) evSimples = "Alta";
                if(ev.includes("obito")) evSimples = "Óbito";
                evolucoes[evSimples] = (evolucoes[evSimples] || 0) + 1;
            }});

            document.getElementById('vTotal').innerText = total;
            document.getElementById('vAlta').innerText = alta;
            document.getElementById('vObito').innerText = obito;
            document.getElementById('vInternado').innerText = internado;

            $('#tabelaIndica').DataTable({{
                data: dados,
                language: {{ url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" }},
                order: [], // Mantem ordem do Python
                pageLength: 10,
                columns: [
                    {{ data: "data_internacao" }},
                    {{ data: "paciente" }},
                    {{ data: "cns" }},
                    {{ data: "municipio" }},
                    {{ data: "nome_leito" }},
                    {{ data: "evolucao" }},
                    {{ data: "aih" }}
                ]
            }});

            gerarGraficos(tiposLeito, evolucoes);
        }}

        function gerarGraficos(leitos, evolucoes) {{
            const ctxL = document.getElementById('cLeito');
            new Chart(ctxL, {{
                type: 'doughnut',
                data: {{
                    labels: Object.keys(leitos),
                    datasets: [{{ data: Object.values(leitos), backgroundColor: ['#6f42c1', '#20c997', '#fd7e14', '#0d6efd', '#6610f2'] }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});

            const ctxE = document.getElementById('cEvolucao');
            new Chart(ctxE, {{
                type: 'bar',
                data: {{
                    labels: Object.keys(evolucoes),
                    datasets: [{{ label:'Qtd', data: Object.values(evolucoes), backgroundColor: ['#28a745', '#dc3545', '#ffc107'] }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});
        }}
    </script>
</body>
</html>
"""
        with open(CAMINHO_HTML, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print("✅ Dashboard IndicaSUS gerado com SUCESSO!")

    except Exception as e:
        print(f"❌ Erro: {e}")
        conn.close()

if __name__ == "__main__":
    gerar_painel()