import json
import os
from datetime import datetime
from collections import defaultdict

print("--- GERADOR DE INDICADORES (HTML INTERATIVO) ---")

# --- CONFIGURAÇÕES ---
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
ARQUIVO_DADOS = os.path.join(PASTA_PROJETO, "arquivos", "dados_sisreg.json")
ARQUIVO_SAIDA = os.path.join(PASTA_PROJETO, "dashboard_faturamento.html")

# --- CARREGAR DADOS ---
try:
    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
        dados_brutos = json.load(f)
    print(f">> Dados carregados: {len(dados_brutos)} registros.")
except Exception as e:
    print(f"❌ Erro ao ler JSON: {e}")
    exit()

# --- PROCESSAMENTO DOS DADOS ---
# Estrutura: dados_processados[MES_ANO][SETOR] = { totais... }
dados_agrupados = defaultdict(lambda: defaultdict(lambda: {"total": 0, "aprovados": 0, "negados": 0, "pendentes": 0, "lista": []}))
setores_existentes = set()
meses_existentes = set()

for item in dados_brutos:
    # 1. Tratamento de Data
    try:
        data_obj = datetime.strptime(item.get("data_visual", ""), "%d/%m/%Y")
        chave_mes = data_obj.strftime("%Y-%m") # Ex: 2025-12
        label_mes = data_obj.strftime("%m/%Y")
    except:
        continue # Pula datas inválidas

    # 2. Tratamento de Setor (Como o Sisreg não dá o setor direto na listagem simples,
    # vamos usar o 'proc' ou definir 'Geral' se não houver distinção ainda)
    setor = item.get("proc", "Internação").strip()
    if not setor: setor = "Geral"
    
    # 3. Contagem
    status = item.get("status", "").lower()
    
    stats = dados_agrupados[label_mes][setor]
    stats["total"] += 1
    stats["lista"].append(item)
    
    if "aprovado" in status or "autorizado" in status:
        stats["aprovados"] += 1
    elif "negado" in status or "cancelado" in status:
        stats["negados"] += 1
    else:
        stats["pendentes"] += 1
        
    setores_existentes.add(setor)
    meses_existentes.add(label_mes)

# Ordenar meses cronologicamente
meses_ordenados = sorted(list(meses_existentes), key=lambda x: datetime.strptime(x, "%m/%Y"), reverse=True)
setores_ordenados = sorted(list(setores_existentes))

# Adicionar opção "Todos"
setores_ordenados.insert(0, "Todos")

# Converter para JSON string para embutir no HTML
dados_json_js = json.dumps(dados_agrupados, ensure_ascii=False)

# --- HTML TEMPLATE (COM JAVASCRIPT EMBUTIDO) ---
html_content = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Faturamento - HSH</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; font-family: 'Segoe UI', sans-serif; }}
        .header {{ background: linear-gradient(135deg, #0d6efd, #0a58ca); color: white; padding: 20px 0; margin-bottom: 30px; }}
        .card-indicador {{ border: none; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .card-indicador:hover {{ transform: translateY(-5px); }}
        .icon-box {{ font-size: 2rem; opacity: 0.8; }}
        .table-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .status-badge {{ padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }}
        .bg-aprovado {{ background-color: #d1e7dd; color: #0f5132; }}
        .bg-negado {{ background-color: #f8d7da; color: #842029; }}
        .bg-pendente {{ background-color: #fff3cd; color: #664d03; }}
        @media print {{
            .no-print {{ display: none !important; }}
            .header {{ background: white; color: black; border-bottom: 2px solid black; }}
        }}
    </style>
</head>
<body>

    <div class="header text-center">
        <div class="container">
            <h1><i class="fas fa-hospital-user"></i> Painel de Controle SISREG</h1>
            <p class="mb-0">Hospital Beneficente Santa Helena - Faturamento SUS</p>
            <small>Atualizado em: {datetime.now().strftime("%d/%m/%Y às %H:%M")}</small>
        </div>
    </div>

    <div class="container">
        
        <div class="row mb-4 no-print">
            <div class="col-md-3">
                <label class="form-label fw-bold">Período (Mês/Ano):</label>
                <select id="filtroMes" class="form-select shadow-sm" onchange="atualizarDashboard()">
                    {''.join([f'<option value="{m}">{m}</option>' for m in meses_ordenados])}
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label fw-bold">Setor / Procedimento:</label>
                <select id="filtroSetor" class="form-select shadow-sm" onchange="atualizarDashboard()">
                    {''.join([f'<option value="{s}">{s}</option>' for s in setores_ordenados])}
                </select>
            </div>
            <div class="col-md-6 text-end align-self-end">
                <button class="btn btn-outline-primary" onclick="window.print()"><i class="fas fa-print"></i> Imprimir Relatório</button>
            </div>
        </div>

        <h4 class="mb-3 text-secondary"><i class="fas fa-chart-pie"></i> Indicadores Institucionais</h4>
        <div class="row mb-4 text-center">
            <div class="col-md-3 mb-2">
                <div class="card card-indicador bg-white text-primary h-100 py-3">
                    <div class="card-body">
                        <div class="icon-box mb-2"><i class="fas fa-folder-open"></i></div>
                        <h2 class="fw-bold" id="txtTotal">0</h2>
                        <span class="text-muted">Total Solicitado</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-2">
                <div class="card card-indicador bg-success text-white h-100 py-3">
                    <div class="card-body">
                        <div class="icon-box mb-2"><i class="fas fa-check-circle"></i></div>
                        <h2 class="fw-bold" id="txtAprovados">0</h2>
                        <span>Aprovados</span>
                        <div id="pctAprovados" class="small mt-1 opacity-75">0%</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-2">
                <div class="card card-indicador bg-danger text-white h-100 py-3">
                    <div class="card-body">
                        <div class="icon-box mb-2"><i class="fas fa-times-circle"></i></div>
                        <h2 class="fw-bold" id="txtNegados">0</h2>
                        <span>Negados/Canc.</span>
                        <div id="pctNegados" class="small mt-1 opacity-75">0%</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-2">
                <div class="card card-indicador bg-warning text-dark h-100 py-3">
                    <div class="card-body">
                        <div class="icon-box mb-2"><i class="fas fa-hourglass-half"></i></div>
                        <h2 class="fw-bold" id="txtPendentes">0</h2>
                        <span>Pendentes</span>
                        <div id="pctPendentes" class="small mt-1 opacity-75">0%</div>
                    </div>
                </div>
            </div>
        </div>

        <h4 class="mb-3 text-secondary"><i class="fas fa-list"></i> Detalhamento das Solicitações</h4>
        <div class="table-container">
            <table class="table table-hover align-middle">
                <thead class="table-light">
                    <tr>
                        <th>Data</th>
                        <th>AIH / Solicitação</th>
                        <th>Paciente</th>
                        <th>Setor</th>
                        <th class="text-center">Status</th>
                        <th class="text-center">Arquivo</th>
                    </tr>
                </thead>
                <tbody id="tabelaDados">
                    </tbody>
            </table>
        </div>
        
        <footer class="mt-5 text-center text-muted small">
            <p>Gerado automaticamente pelo NII-Portal • HSH Faturamento</p>
        </footer>

    </div>

    <script>
        // Dados vindos do Python
        const dadosAgrupados = {dados_json_js};

        function atualizarDashboard() {{
            const mesSelecionado = document.getElementById('filtroMes').value;
            const setorSelecionado = document.getElementById('filtroSetor').value;
            
            // Verifica se o mês existe
            if (!dadosAgrupados[mesSelecionado]) return;

            let total = 0, aprovados = 0, negados = 0, pendentes = 0;
            let listaFinal = [];

            // Lógica de Soma (Setor Específico ou Todos)
            const setoresDoMes = dadosAgrupados[mesSelecionado];
            
            if (setorSelecionado === "Todos") {{
                for (let setor in setoresDoMes) {{
                    total += setoresDoMes[setor].total;
                    aprovados += setoresDoMes[setor].aprovados;
                    negados += setoresDoMes[setor].negados;
                    pendentes += setoresDoMes[setor].pendentes;
                    listaFinal = listaFinal.concat(setoresDoMes[setor].lista);
                }}
            }} else if (setoresDoMes[setorSelecionado]) {{
                const dados = setoresDoMes[setorSelecionado];
                total = dados.total;
                aprovados = dados.aprovados;
                negados = dados.negados;
                pendentes = dados.pendentes;
                listaFinal = dados.lista;
            }}

            // Atualizar Cards
            animarNumero('txtTotal', total);
            animarNumero('txtAprovados', aprovados);
            animarNumero('txtNegados', negados);
            animarNumero('txtPendentes', pendentes);

            // Porcentagens
            document.getElementById('pctAprovados').innerText = total > 0 ? ((aprovados/total)*100).toFixed(1) + '%' : '0%';
            document.getElementById('pctNegados').innerText = total > 0 ? ((negados/total)*100).toFixed(1) + '%' : '0%';
            document.getElementById('pctPendentes').innerText = total > 0 ? ((pendentes/total)*100).toFixed(1) + '%' : '0%';

            // Atualizar Tabela
            const tbody = document.getElementById('tabelaDados');
            tbody.innerHTML = '';
            
            // Ordenar lista por dia
            listaFinal.sort((a, b) => {{
                // Converter DD/MM/YYYY para Date para ordenar
                const dataA = a.data_visual.split('/').reverse().join('-');
                const dataB = b.data_visual.split('/').reverse().join('-');
                return new Date(dataB) - new Date(dataA); // Decrescente
            }});

            listaFinal.forEach(item => {{
                let classeBadge = 'bg-pendente';
                let iconeStatus = '<i class="fas fa-clock"></i>';
                
                const st = item.status ? item.status.toLowerCase() : '';
                if(st.includes('aprov') || st.includes('auto')) {{ classeBadge = 'bg-aprovado'; iconeStatus = '<i class="fas fa-check"></i>'; }}
                if(st.includes('neg') || st.includes('canc')) {{ classeBadge = 'bg-negado'; iconeStatus = '<i class="fas fa-times"></i>'; }}

                // Link do PDF (Tenta ajustar caminho relativo se necessário)
                let linkPdf = item.arquivo_pdf ? `<a href="${{item.arquivo_pdf}}" target="_blank" class="btn btn-sm btn-outline-danger"><i class="fas fa-file-pdf"></i> PDF</a>` : '<span class="text-muted">-</span>';

                const tr = `
                    <tr>
                        <td>${{item.data_visual}}</td>
                        <td class="fw-bold">${{item.aih}}</td>
                        <td>${{item.paciente}}</td>
                        <td>${{item.proc || 'Internação'}}</td>
                        <td class="text-center"><span class="status-badge ${{classeBadge}}">${{iconeStatus}} ${{item.status}}</span></td>
                        <td class="text-center">${{linkPdf}}</td>
                    </tr>
                `;
                tbody.innerHTML += tr;
            }});
        }}

        function animarNumero(id, valorFinal) {{
            const obj = document.getElementById(id);
            obj.innerText = valorFinal;
            // (Poderia adicionar animação de contagem aqui se quisesse)
        }}

        // Inicializar
        document.addEventListener('DOMContentLoaded', () => {{
            atualizarDashboard();
        }});
    </script>
</body>
</html>
"""

# --- SALVAR ARQUIVO ---
try:
    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f">> Relatório gerado com sucesso em: {ARQUIVO_SAIDA}")
    print(">> Abra este arquivo no seu navegador (Chrome/Edge).")
except Exception as e:
    print(f"❌ Erro ao salvar HTML: {e}")