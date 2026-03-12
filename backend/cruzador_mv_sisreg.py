import os
import pandas as pd
import glob
from supabase import create_client, Client
import unicodedata
from datetime import datetime
import subprocess # 💡 IMPORT NOVO PARA RODAR COMANDOS DE TERMINAL

print("--- 🚀 CRUZADOR DE DADOS: SOULMV vs SISREG (Gerador de Painel Web) ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_RAIZ = os.path.dirname(BASE_DIR) # Pasta principal do repositório

PASTA_FRONTEND = os.path.join(DIRETORIO_RAIZ, "frontend")
if not os.path.exists(PASTA_FRONTEND): os.makedirs(PASTA_FRONTEND)

ARQUIVO_EXCEL = os.path.join(BASE_DIR, "FICHAS_PARA_IMPRIMIR.xlsx")
ARQUIVO_HTML = os.path.join(PASTA_FRONTEND, "Painel_Fichas_Liberadas.html")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão com o banco: {e}")
    exit()

def padronizar_nome(nome):
    if not isinstance(nome, str):
        return ""
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8')
    nome = nome.upper().strip()
    return " ".join(nome.split())

def encontrar_arquivo_mv():
    padrao_busca = os.path.join(BASE_DIR, "*conferencia_autorizacao*.*")
    arquivos_encontrados = glob.glob(padrao_busca)
    arquivos_validos = [f for f in arquivos_encontrados if not os.path.basename(f).startswith("~$")]
    
    if arquivos_validos:
        return arquivos_validos[0] 
    return None

# 💡 FUNÇÃO NOVA: AUTOMAÇÃO DO GITHUB
def enviar_para_github():
    print("\n🌐 6. Iniciando sincronização automática com o GitHub...")
    try:
        # 1. Adiciona o arquivo HTML específico
        caminho_relativo_html = os.path.join("frontend", "Painel_Fichas_Liberadas.html")
        subprocess.run(["git", "add", caminho_relativo_html], cwd=DIRETORIO_RAIZ, check=True, capture_output=True)

        # 2. Faz o Commit com a data e hora
        mensagem_commit = f"Automação: Atualiza Painel de Fichas Cruzadas - {datetime.now().strftime('%d/%m %H:%M')}"
        commit_process = subprocess.run(["git", "commit", "-m", mensagem_commit], cwd=DIRETORIO_RAIZ, capture_output=True, text=True)

        # Verifica se havia algo novo para commitar
        if "nothing to commit" in commit_process.stdout or "nada a commitar" in commit_process.stdout.lower():
            print("   ⚠️ O painel não teve alterações novas em relação ao último envio.")
            return

        # 3. Faz o Push
        print("   ⏳ Enviando para a nuvem (Push)...")
        subprocess.run(["git", "push"], cwd=DIRETORIO_RAIZ, check=True, capture_output=True)
        
        print("   ✅ SUCESSO! O painel já está ao vivo no GitHub Pages!")

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro ao tentar enviar para o GitHub. Detalhes: {e.stderr.decode() if e.stderr else e}")
    except Exception as e:
        print(f"   ❌ Erro inesperado com o Git: {e}")

def processar_cruzamento():
    arquivo_mv = encontrar_arquivo_mv()
    
    if not arquivo_mv:
        print(f"❌ Nenhum arquivo chamado 'conferencia_autorizacao' foi encontrado na pasta: {BASE_DIR}")
        return

    nome_base = os.path.basename(arquivo_mv)
    print(f"📄 1. Lendo arquivo encontrado: {nome_base}...")
    
    try:
        if arquivo_mv.lower().endswith('.csv'):
            try:
                df_mv = pd.read_csv(arquivo_mv, sep=',', encoding='utf-8') 
            except UnicodeDecodeError:
                df_mv = pd.read_csv(arquivo_mv, sep=';', encoding='latin1')
        else:
            df_mv = pd.read_excel(arquivo_mv)
            
    except Exception as e:
        print(f"❌ Erro ao tentar abrir o arquivo: {e}")
        return

    if 'PACIENTE' not in df_mv.columns:
        print("❌ O arquivo não tem a coluna 'PACIENTE'. Verifique se o relatório do MV está correto.")
        return

    if 'NR.AIH' in df_mv.columns:
        df_mv_sem_aih = df_mv[df_mv['NR.AIH'].isna() | (df_mv['NR.AIH'].astype(str).str.strip() == '')].copy()
    else:
        df_mv_sem_aih = df_mv.copy()

    df_mv_sem_aih['NOME_BUSCA'] = df_mv_sem_aih['PACIENTE'].apply(padronizar_nome)
    print(f"🔍 Total de pacientes do MV sem AIH para pesquisar: {len(df_mv_sem_aih)}")

    print("☁️  2. Puxando dados do SISREG no banco...")
    try:
        response = supabase.table('regulacao').select('nome_paciente, num_aih, status, data_solicitacao, arquivo_pdf, num_solicitacao, cns_paciente').order('data_solicitacao', desc=True).execute()
        dados_sisreg = response.data
    except Exception as e:
        print(f"❌ Erro ao puxar dados do banco: {e}")
        return

    df_sisreg = pd.DataFrame(dados_sisreg)
    
    df_sisreg['num_aih_limpo'] = df_sisreg['num_aih'].astype(str).str.strip()
    df_sisreg['status_limpo'] = df_sisreg['status'].astype(str).str.upper()

    df_sisreg = df_sisreg[
        (df_sisreg['num_aih_limpo'].str.len() >= 12) & 
        (df_sisreg['status_limpo'].str.contains('APROVAD|AUTORIZAD', na=False))
    ].copy()

    df_sisreg['NOME_BUSCA'] = df_sisreg['nome_paciente'].apply(padronizar_nome)
    df_sisreg = df_sisreg.drop_duplicates(subset=['NOME_BUSCA'], keep='first')

    print("⚙️  3. Cruzando os dados (SoulMV x SISREG)...")
    df_resultado = pd.merge(df_mv_sem_aih, df_sisreg[['NOME_BUSCA', 'num_aih_limpo', 'status', 'arquivo_pdf', 'num_solicitacao', 'cns_paciente']], 
                            on='NOME_BUSCA', 
                            how='left')

    df_achados = df_resultado[df_resultado['num_aih_limpo'].notna()].copy()

    if len(df_achados) == 0:
        print("⚠️ Nenhum paciente da lista do MV foi encontrado com AIH válida/aprovada no SISREG.")
        return

    print(f"✅ SUCESSO! Encontramos {len(df_achados)} pacientes que já possuem AIH liberada.")

    df_final = pd.DataFrame({
        'CONTA MV': df_achados.get('NR.CONTA', '-'),
        'PACIENTE': df_achados['PACIENTE'],
        'CNS': df_achados['cns_paciente'], 
        'DATA INT.': df_achados.get('DT. INT.', '-'),
        'PROCEDIMENTO MV': df_achados.get('PROCED. SOLICITADO', '-'),
        'SOLICITAÇÃO': df_achados['num_solicitacao'], 
        'AIH SISREG': df_achados['num_aih_limpo'],
        'STATUS SISREG': df_achados['status'],
        'ARQUIVO PDF': df_achados['arquivo_pdf']
    })

    print("💾 4. Gerando planilha de backup Excel...")
    df_final.drop(columns=['ARQUIVO PDF']).to_excel(ARQUIVO_EXCEL, index=False)
    
    print(f"🎨 5. Construindo Painel HTML na pasta {PASTA_FRONTEND}...")
    
    html_top = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cruzamento MV x SISREG - NII</title>
    
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>

    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        body { font-family: 'Roboto', sans-serif; background: #f3f4f6; color: #1e293b; padding: 0; margin: 0; min-height: 100vh; padding-bottom: 50px; }
        .header-bg { background: linear-gradient(135deg, #000428 0%, #004e92 100%) !important; color: white !important; padding: 25px 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); margin-bottom: 25px; }
        .header-mini-logo { height: 40px; margin-right: 15px; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.3)); }
        .container { max-width: 1400px; margin: 0 auto; padding: 0 15px; }
        .btn-back { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; display: flex; align-items: center; gap: 8px; text-decoration: none; }
        .btn-back:hover { background: rgba(255,255,255,0.3); color: white; }
        .table-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; overflow-x: auto; }
        table.dataTable { width: 100% !important; border-collapse: collapse !important; }
        table.dataTable thead th { background-color: #004e92 !important; color: white !important; font-weight: 700 !important; text-transform: uppercase; padding: 10px 8px !important; font-size: 0.75rem; white-space: nowrap; border: none; }
        table.dataTable tbody td { padding: 8px 10px !important; border-bottom: 1px solid #f1f5f9; color: #334155; font-size: 0.8rem; vertical-align: middle; }
        .dt-button { background: #10b981 !important; color: white !important; border: none !important; border-radius: 6px !important; padding: 6px 12px !important; font-weight: 600 !important; font-size: 0.75rem !important; }
        .dt-button:hover { background: #059669 !important; }
        .badge-aih { background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.8rem; letter-spacing: 0.5px; }
        .btn-pdf { background-color: white; border: 1px solid #ef4444; color: #ef4444; padding: 5px 12px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; transition: 0.2s; }
        .btn-pdf:hover { background-color: #ef4444; color: white; }
    </style>
</head>
<body>

    <div class='header-bg'>
        <div class='max-w-7xl mx-auto flex justify-between items-center px-4'>
            <div class="flex items-center gap-4">
                <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-code-compare text-3xl"></i></div>
                <div>
                    <h1 class='text-3xl font-bold'>Auditoria de Faturamento</h1>
                    <p class='text-gray-300'>Cruzamento: Contas Pendentes (MV) vs Fichas Aprovadas (SISREG)</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <img src="logo.png" alt="Logo HSH" class="header-mini-logo" onerror="this.style.display='none'">
                <a href="modulo_operacional.html" class="btn-back"><i class="fas fa-arrow-left"></i> Voltar</a>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4 font-semibold flex justify-between items-center">
            <div><i class="fas fa-check-circle mr-2"></i> VAR_QTD pacientes encontrados com AIH liberada para faturamento!</div>
            <div class="text-sm font-normal text-green-600">Emissão: VAR_DATA_HOJE</div>
        </div>
        
        <div class="table-card">
            <table id="tabelaContas" class="display compact w-full">
                <thead>
                    <tr>
                        <th style="width: 80px;">Conta MV</th>
                        <th>Paciente</th>
                        <th style="width: 100px;">CNS</th>
                        <th style="width: 90px;">Data Int.</th>
                        <th>Procedimento (MV)</th>
                        <th style="width: 100px;">Solicitação</th>
                        <th style="width: 140px;">AIH Aprovada</th>
                        <th style="width: 100px; text-align:center;">Ficha SISREG</th>
                    </tr>
                </thead>
                <tbody>
"""
    html_rows = ""
    for _, row in df_final.iterrows():
        conta = row['CONTA MV'] if pd.notna(row['CONTA MV']) else "-"
        pac = row['PACIENTE']
        dt_int = row['DATA INT.'] if pd.notna(row['DATA INT.']) else "-"
        proc = str(row['PROCEDIMENTO MV'])[:45] + "..." if len(str(row['PROCEDIMENTO MV'])) > 45 else row['PROCEDIMENTO MV']
        aih = row['AIH SISREG']
        pdf_link = row['ARQUIVO PDF']
        
        cns = row['CNS'] if pd.notna(row['CNS']) else "-"
        solicitacao = row['SOLICITAÇÃO'] if pd.notna(row['SOLICITAÇÃO']) else "-"
        
        if pd.notna(pdf_link) and str(pdf_link).strip() != "":
            btn_pdf = f'<a href="{pdf_link}" target="_blank" class="btn-pdf"><i class="fas fa-file-pdf text-lg"></i> Imprimir Ficha</a>'
        else:
            btn_pdf = '<span class="text-gray-400 text-xs italic">Sem PDF</span>'

        html_rows += f"""
                    <tr>
                        <td class="font-bold text-gray-700">{conta}</td>
                        <td class="font-bold text-gray-900 uppercase">{pac}</td>
                        <td class="text-gray-600">{cns}</td>
                        <td class="text-gray-600">{dt_int}</td>
                        <td class="text-xs text-gray-500" title="{row['PROCEDIMENTO MV']}">{proc}</td>
                        <td class="font-bold text-gray-600">{solicitacao}</td>
                        <td><span class="badge-aih">{aih}</span></td>
                        <td class="text-center">{btn_pdf}</td>
                    </tr>
        """

    html_bottom = """
                </tbody>
            </table>
        </div>
    </div>

    <script>
        $(document).ready(function() {
            $('#tabelaContas').DataTable({
                language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" },
                dom: 'Bfrtip',
                pageLength: 50,
                order: [[1, 'asc']], // Ordena por nome do paciente
                buttons: [
                    { extend: 'excelHtml5', text: '<i class="fas fa-file-excel"></i> Exportar para Excel', className: 'dt-button' }
                ]
            });
        });
    </script>
</body>
</html>
"""
    
    data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
    html_final = html_top.replace("VAR_QTD", str(len(df_achados))).replace("VAR_DATA_HOJE", data_hoje) + html_rows + html_bottom

    with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html_final)
    
    print(f"🎉 Painel HTML atualizado localmente!")
    
    # CHAMA A FUNÇÃO DE AUTOMAÇÃO
    enviar_para_github()
    
    os.startfile(ARQUIVO_HTML)

if __name__ == "__main__":
    processar_cruzamento()