import pandas as pd
import os
import subprocess
from datetime import datetime

# --- CONFIGURAÇÕES ---
ARQUIVO_EXCEL = 'custos_hospitalares.xlsx'
ARQUIVO_HTML_SAIDA = 'relatorio_financeiro.html'
NOME_DO_REPO_GIT = 'NII-Portal'  # Nome da pasta do seu projeto se necessário verificar

# --- 1. FUNÇÃO PARA GERAR DADOS DE EXEMPLO (Se a planilha não existir) ---
def criar_planilha_modelo():
    if not os.path.exists(ARQUIVO_EXCEL):
        print(f"⚠️ Arquivo '{ARQUIVO_EXCEL}' não encontrado. Criando modelo automático...")
        
        # Dados fictícios baseados no perfil do Santa Helena
        dados = {
            'Data': [datetime.now().strftime('%d/%m/%Y')],
            'Paciente_ID': ['12345-SUS'],
            'Procedimento_Item': ['AIH - TRATAMENTO DE PNEUMONIA'],
            'Qtd': [1],
            'Custo_Total_Hospital': [850.00], # O que o hospital gastou de fato
            'Valor_SIGTAP': [600.00],         # O que a tabela paga
            'Observacao': ['Glosa provável se não justificar']
        }
        df = pd.DataFrame(dados)
        df.to_excel(ARQUIVO_EXCEL, index=False)
        print(f"✅ Planilha modelo criada! Abra o arquivo '{ARQUIVO_EXCEL}' e insira os dados reais.")
        return False # Indica que acabamos de criar, então não há dados reais para processar ainda
    return True

# --- 2. FUNÇÃO DE PROCESSAMENTO E GERAÇÃO DE HTML ---
def processar_dados_gerar_html():
    print("🔄 Lendo planilha e calculando custos...")
    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
    except Exception as e:
        print(f"Erro ao ler Excel: {e}")
        return

    # Cálculos Automáticos
    df['Diferença'] = df['Valor_SIGTAP'] - df['Custo_Total_Hospital']
    df['Status'] = df['Diferença'].apply(lambda x: 'LUCRO' if x >= 0 else 'PREJUÍZO')

    # Formatação de Moeda
    def formatar(val):
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    colunas_valores = ['Custo_Total_Hospital', 'Valor_SIGTAP', 'Diferença']
    for col in colunas_valores:
        df[col] = df[col].apply(formatar)

    # Geração do HTML (Design Responsivo para o Portal)
    data_atualizacao = datetime.now().strftime('%d/%m/%Y às %H:%M')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel de Custos - HBSH</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f8f9fa; padding: 20px; }}
            .card {{ margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .status-lucro {{ color: green; font-weight: bold; }}
            .status-prejuizo {{ color: red; font-weight: bold; background-color: #ffe6e6; }}
            h1 {{ color: #0d6efd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="text-center mb-4">
                <h1>🏥 Monitoramento de Custos SUS</h1>
                <p class="text-muted">Hospital Beneficente Santa Helena | Atualizado em: {data_atualizacao}</p>
            </div>

            <div class="card p-3">
                <h5>Resumo Financeiro</h5>
                <div class="table-responsive">
                    {df.to_html(classes='table table-hover', index=False, escape=False)}
                </div>
            </div>
            
            <footer class="text-center mt-4">
                <small>Gerado automaticamente via Python - NII Portal</small>
            </footer>
        </div>
        
        <script>
            // Script simples para colorir as células via JS (caso o Python escape não pegue)
            document.querySelectorAll('td').forEach(td => {{
                if (td.innerText === 'PREJUÍZO') {{
                    td.classList.add('status-prejuizo');
                    td.parentElement.style.backgroundColor = '#fff0f0';
                }} else if (td.innerText === 'LUCRO') {{
                    td.classList.add('status-lucro');
                }}
            }});
        </script>
    </body>
    </html>
    """

    with open(ARQUIVO_HTML_SAIDA, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML '{ARQUIVO_HTML_SAIDA}' gerado com sucesso!")

# --- 3. FUNÇÃO DE UPLOAD AUTOMÁTICO (GIT PUSH) ---
def subir_para_portal():
    print("🚀 Iniciando upload para o Portal...")
    
    # Comandos do Git automatizados
    comandos = [
        ['git', 'add', ARQUIVO_HTML_SAIDA],
        ['git', 'commit', '-m', f"Atualização automática de custos: {datetime.now()}"],
        ['git', 'push']
    ]

    for cmd in comandos:
        try:
            resultado = subprocess.run(cmd, check=True, text=True, capture_output=True)
            print(f"✔ Comando executado: {' '.join(cmd)}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao executar GIT: {e.stderr}")
            print("DICA: Verifique se você está logado no Git e dentro da pasta do repositório.")
            return

    print("🌐 Sucesso! Seu portal deve ser atualizado em instantes.")
    print(f"Acesse: https://franckmoura.github.io/NII-Portal/{ARQUIVO_HTML_SAIDA}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    # Passo 1: Verifica se existe planilha. Se não, cria e para para o usuário preencher.
    existe_dados = criar_planilha_modelo()
    
    if existe_dados:
        # Passo 2: Processa
        processar_dados_gerar_html()
        
        # Passo 3: Pergunta se quer subir para o portal
        resposta = input("\nDeseja subir os dados para o portal agora? (S/N): ").strip().upper()
        if resposta == 'S':
            subir_para_portal()
        else:
            print("Operação finalizada localmente.")