import pandas as pd
import os
import subprocess
from datetime import datetime

# --- CONFIGURAÇÕES ---
ARQUIVO_EXCEL = 'custos_detalhados.xlsx'
ARQUIVO_HTML_SAIDA = 'relatorio_analitico_custos.html'

# --- 1. GERAR A PLANILHA DETALHADA (SE NÃO EXISTIR) ---
def criar_planilha_modelo():
    if not os.path.exists(ARQUIVO_EXCEL):
        print(f"⚠️ Criando planilha detalhada '{ARQUIVO_EXCEL}'...")
        
        # Estrutura exata para lançar item a item
        dados_exemplo = {
            'DATA': ['07/01/2026', '07/01/2026', '07/01/2026'],
            'PACIENTE': ['Fulano de Tal', 'Fulano de Tal', 'Fulano de Tal'],
            'TIPO': ['MAT', 'MED', 'EXA'], # Material, Medicamento, Exame
            'DESCRICAO_ITEM': ['Seringa 10ml', 'Ceftriaxona 1g', 'Hemograma Completo'],
            'QTD': [2, 1, 1],
            'CUSTO_UNIT_HOSPITAL': [0.45, 8.50, 12.00], # Quanto você paga na nota
            'VALOR_UNIT_SUS': [0.00, 5.00, 4.11]        # Quanto o SUS paga (ou 0 se for pacote)
        }
        
        df = pd.DataFrame(dados_exemplo)
        df.to_excel(ARQUIVO_EXCEL, index=False)
        print(f"✅ Planilha criada! Abra o arquivo '{ARQUIVO_EXCEL}' e preencha os itens.")
        return False
    return True

# --- 2. PROCESSAR DADOS E GERAR RELATÓRIO ---
def processar_e_gerar_html():
    print("🔄 Lendo os itens lançados...")
    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
    except Exception as e:
        print(f"Erro ao ler Excel: {e}")
        return

    # --- CÁLCULOS AUTOMÁTICOS ---
    # Calcula o total gasto e recebido por linha
    df['TOTAL_CUSTO_HOSP'] = df['QTD'] * df['CUSTO_UNIT_HOSPITAL']
    df['TOTAL_RECEITA_SUS'] = df['QTD'] * df['VALOR_UNIT_SUS']
    df['DIFERENCA'] = df['TOTAL_RECEITA_SUS'] - df['TOTAL_CUSTO_HOSP']
    
    # Define status
    df['STATUS'] = df['DIFERENCA'].apply(lambda x: 'LUCRO' if x >= 0 else 'PREJUÍZO')

    # Totais Gerais para o Cabeçalho do Relatório
    total_gasto = df['TOTAL_CUSTO_HOSP'].sum()
    total_recebido = df['TOTAL_RECEITA_SUS'].sum()
    balanco_geral = total_recebido - total_gasto
    cor_balanco = "green" if balanco_geral >= 0 else "red"

    # Formatação de Moeda Visual
    def formatar_br(val):
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Aplica formatação apenas para exibição (mantém números originais para cálculo se precisasse)
    cols_moeda = ['CUSTO_UNIT_HOSPITAL', 'VALOR_UNIT_SUS', 'TOTAL_CUSTO_HOSP', 'TOTAL_RECEITA_SUS', 'DIFERENCA']
    df_view = df.copy()
    for col in cols_moeda:
        df_view[col] = df_view[col].apply(formatar_br)

    # --- GERAÇÃO DO HTML COM DATATABLES (FILTROS E PESQUISA) ---
    data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Análise de Custos Detalhada</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/buttons/2.3.6/css/buttons.bootstrap5.min.css" rel="stylesheet">
        
        <style>
            body {{ background-color: #f4f6f9; padding: 20px; }}
            .card-summary {{ color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
            .bg-custo {{ background-color: #e74c3c; }}
            .bg-receita {{ background-color: #27ae60; }}
            .bg-balanco {{ background-color: #2c3e50; }}
            .status-PREJUÍZO {{ color: #e74c3c; font-weight: bold; background-color: #fadbd8; }}
            .status-LUCRO {{ color: #27ae60; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <h2 class="mb-4">📊 Detalhamento de Custos: Materiais, Medicamentos e Exames</h2>
            <p>Atualizado em: {data_hoje}</p>

            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card-summary bg-custo">
                        <h5>Custo Total Hospital</h5>
                        <h3>{formatar_br(total_gasto)}</h3>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card-summary bg-receita">
                        <h5>Receita Total SUS</h5>
                        <h3>{formatar_br(total_recebido)}</h3>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card-summary bg-balanco">
                        <h5>Balanço Final</h5>
                        <h3 style="color: {cor_balanco}">{formatar_br(balanco_geral)}</h3>
                    </div>
                </div>
            </div>

            <div class="card shadow">
                <div class="card-body">
                    <table id="tabelaCustos" class="table table-striped table-bordered" style="width:100%">
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Paciente</th>
                                <th>Tipo</th>
                                <th>Descrição Item</th>
                                <th>Qtd</th>
                                <th>Custo Unit. (Hosp)</th>
                                <th>Valor Unit. (SUS)</th>
                                <th>Total Custo</th>
                                <th>Total SUS</th>
                                <th>Diferença</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    # Preenchendo as linhas da tabela
    for _, row in df_view.iterrows():
        classe_status = f"status-{row['STATUS']}"
        html += f"""
            <tr>
                <td>{row['DATA']}</td>
                <td>{row['PACIENTE']}</td>
                <td>{row['TIPO']}</td>
                <td>{row['DESCRICAO_ITEM']}</td>
                <td>{row['QTD']}</td>
                <td>{row['CUSTO_UNIT_HOSPITAL']}</td>
                <td>{row['VALOR_UNIT_SUS']}</td>
                <td>{row['TOTAL_CUSTO_HOSP']}</td>
                <td>{row['TOTAL_RECEITA_SUS']}</td>
                <td>{row['DIFERENCA']}</td>
                <td class="{classe_status}">{row['STATUS']}</td>
            </tr>
        """

    html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.3.6/js/dataTables.buttons.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.3.6/js/buttons.html5.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.1.3/jszip.min.js"></script>
        
        <script>
            $(document).ready(function() {
                $('#tabelaCustos').DataTable({
                    dom: 'Bfrtip',
                    buttons: ['excelHtml5', 'csvHtml5', 'copyHtml5'],
                    language: {
                        url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                    },
                    pageLength: 25
                });
            });
        </script>
    </body>
    </html>
    """

    with open(ARQUIVO_HTML_SAIDA, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Relatório '{ARQUIVO_HTML_SAIDA}' gerado com sucesso!")

# --- 3. SUBIR PARA O PORTAL (GIT) ---
def subir_git():
    print("🚀 Subindo para o GitHub...")
    cmds = [
        ['git', 'add', ARQUIVO_HTML_SAIDA],
        ['git', 'commit', '-m', 'Atualização de custos analíticos'],
        ['git', 'push']
    ]
    for cmd in cmds:
        subprocess.run(cmd, shell=True) # shell=True para Windows as vezes é necessário no VS Code
    print("🌐 Upload concluído!")

# --- EXECUÇÃO ---
if __name__ == "__main__":
    if criar_planilha_modelo():
        processar_e_gerar_html()
        resp = input("Deseja subir para o portal agora? (S/N): ")
        if resp.upper() == 'S':
            subir_git()