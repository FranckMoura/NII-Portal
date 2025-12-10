# ==============================================================================
# SCRIPT DE PROCESSAMENTO DE FATURAMENTO SUS (VERSÃO CSV - ROBUST)
# Autor: Franck Moura (Via NII Portal)
# Data: 2025-04-10
# Descrição: Processa CSV do SOULMV, unifica nomes de pacientes por AIH e
#            gera HTML com layout integrado ao NII Portal.
# ==============================================================================

import pandas as pd
import csv
import os
import re

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ENTRADA = os.path.join(PASTA_SCRIPT, 'R_PROC_LANCAMENTOS.csv')
NOME_ARQUIVO_SAIDA = os.path.join(PASTA_SCRIPT, 'index.html')

print(f"--- Iniciando processamento NII Portal ---")
print(f"Buscando arquivo em: {ARQUIVO_ENTRADA}")

# ==============================================================================
# 2. FUNÇÕES AUXILIARES DE LIMPEZA E DETECÇÃO
# ==============================================================================

def is_aih(texto):
    """Verifica se o texto parece uma AIH (apenas números, ~13 dígitos)."""
    return texto.isdigit() and len(texto) >= 10

def is_codigo_proc(texto):
    """Verifica se o texto parece um código SUS (apenas números, ~8-10 dígitos)."""
    return texto.isdigit() and 8 <= len(texto) <= 10

def is_valor_monetario(texto):
    """Verifica se é um valor monetário válido (ex: '1.200,50')."""
    return re.match(r'^\d{1,3}(\.\d{3})*,\d{2}$', texto) is not None

def limpar_valor(texto):
    """Converte '1.000,00' para float 1000.00"""
    try:
        if not texto: return 0.0
        return float(texto.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def encontrar_prestador_na_linha(linha):
    """Tenta encontrar um nome de prestador na linha."""
    ignorar = ["TOTAL PRESTADOR", "GRUPO PROCEDIMENTO", "PRESTADOR", "ATENDIMENTO", "PACIENTE"]
    
    # Prioridade 1: Coluna 2 (Padrão Hospital/PJ)
    if len(linha) > 2 and linha[2].strip():
        cand = linha[2].strip().upper()
        if not any(x in cand for x in ignorar) and not cand.replace('/','').isdigit():
            return cand
            
    # Prioridade 2: Busca ampla
    for i in [7, 8, 3, 1]: 
        if len(linha) > i and linha[i].strip():
            cand = linha[i].strip().upper()
            if len(cand) > 5 and not any(x in cand for x in ignorar) and not is_aih(cand) and not is_codigo_proc(cand):
                return cand
    return None

def encontrar_paciente_inteligente(linha, idx_aih, prestador_atual):
    """
    Procura o nome do paciente próximo à coluna da AIH.
    Varre colunas vizinhas caso o CSV esteja deslocado.
    """
    if idx_aih == -1: return "N/D"
    
    # Define um intervalo de busca: da AIH até 6 colunas para frente
    inicio = idx_aih + 1
    fim = min(len(linha), idx_aih + 7)
    
    for i in range(inicio, fim):
        texto = linha[i].strip()
        # Critérios para ser um nome de paciente:
        # 1. Ter tamanho razoável (> 4)
        # 2. Não ser data (dd/mm)
        # 3. Não ser numérico (código)
        # 4. Não ser igual ao Prestador
        # 5. Não ser letra solta ('A')
        if (len(texto) > 4 and 
            not re.search(r'\d', texto) and # Geralmente nomes não tem números
            texto != prestador_atual and
            len(texto.split()) >= 1): # Pelo menos um nome
            return texto
            
    return "N/D"

# ==============================================================================
# 3. PROCESSAMENTO DO CSV
# ==============================================================================

def processar_csv_soulmv(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        print(f"[ERRO] Arquivo não encontrado: {caminho_arquivo}")
        return pd.DataFrame()

    dados_limpos = []
    
    # Variáveis de Estado (Memória)
    grupo_atual = "GERAL"
    prestador_atual = "DESCONHECIDO"

    try:
        with open(caminho_arquivo, 'r', encoding='latin-1', errors='replace') as f:
            leitor = csv.reader(f)
            
            for linha in leitor:
                if not linha: continue
                texto_linha_full = "".join(linha).upper()
                
                # --- DETECÇÃO DE CONTEXTO ---
                if "GRUPO PROCEDIMENTO:" in texto_linha_full:
                    for item in linha:
                        item = item.strip()
                        if item and "GRUPO PROCEDIMENTO" not in item.upper() and len(item) > 3:
                            grupo_atual = item
                            break
                    continue

                # Atualizar Prestador
                novo_prestador = encontrar_prestador_na_linha(linha)
                if novo_prestador:
                    prestador_atual = novo_prestador

                # --- EXTRAÇÃO DE DADOS ---
                idx_aih = -1
                idx_proc = -1
                idx_valor = -1
                
                for i, col in enumerate(linha):
                    col = col.strip()
                    if not col: continue
                    if is_aih(col): idx_aih = i
                    if is_codigo_proc(col): idx_proc = i
                    if is_valor_monetario(col): idx_valor = i
                
                if idx_proc != -1 or idx_aih != -1:
                    aih = linha[idx_aih].strip() if idx_aih != -1 else "N/D"
                    cod = linha[idx_proc].strip() if idx_proc != -1 else "N/D"
                    
                    proc_nome = "N/D"
                    if idx_proc != -1 and len(linha) > idx_proc + 1:
                        proc_nome = linha[idx_proc + 1].strip()
                        
                    valor = 0.0
                    if idx_valor != -1:
                        valor = limpar_valor(linha[idx_valor])
                    else:
                        try:
                            vals = [c for c in linha if c.strip()]
                            if vals and ',' in vals[-1]: valor = limpar_valor(vals[-1])
                        except: pass

                    # Data
                    data = ""
                    for col in linha:
                        if re.search(r'\d{2}/\d{2}', col):
                            data = col
                            break
                    
                    # Paciente (Tentativa Inicial)
                    paciente = encontrar_paciente_inteligente(linha, idx_aih, prestador_atual)
                    
                    if valor > 0 or (cod != "N/D" and cod != "0"):
                        dados_limpos.append({
                            'Grupo': grupo_atual,
                            'Prestador': prestador_atual,
                            'AIH': aih,
                            'Paciente': paciente,
                            'Data': data,
                            'Codigo': cod,
                            'Procedimento': proc_nome,
                            'Valor': valor
                        })

    except Exception as e:
        print(f"Erro ao processar: {e}")
        return pd.DataFrame()

    # --- PÓS-PROCESSAMENTO: CURA DE NOMES (Sincronização de AIH) ---
    # Estratégia: Varrer todos os dados. Se acharmos uma AIH com nome válido (ex: LINHA 1),
    # usamos esse nome para preencher as linhas que estão "N/D" (ex: LINHA 2, 3) mas tem a mesma AIH.
    
    print("Iniciando unificação de nomes de pacientes por AIH...")
    mapa_aih_nomes = {}
    
    # Pass 1: Catalogar todos os nomes válidos encontrados
    for registro in dados_limpos:
        aih = registro['AIH']
        paciente = registro['Paciente']
        
        # Se temos uma AIH válida e um nome válido (não N/D), guardamos no mapa
        if aih != "N/D" and paciente != "N/D":
            # Se já tem nome, ficamos com o mais longo (geralmente o mais completo)
            nome_existente = mapa_aih_nomes.get(aih, "")
            if len(paciente) > len(nome_existente):
                mapa_aih_nomes[aih] = paciente

    # Pass 2: Preencher as lacunas (N/D) consultando o mapa
    registros_corrigidos = 0
    for registro in dados_limpos:
        if registro['Paciente'] == "N/D":
            aih = registro['AIH']
            if aih in mapa_aih_nomes:
                registro['Paciente'] = mapa_aih_nomes[aih]
                registros_corrigidos += 1
            else:
                 # Se realmente não achou em lugar nenhum do arquivo
                 registro['Paciente'] = "PACIENTE NÃO IDENTIFICADO"
    
    print(f"Correção concluída: {registros_corrigidos} linhas 'N/D' foram preenchidas com nomes encontrados.")

    return pd.DataFrame(dados_limpos)

# ==============================================================================
# 3. GERAÇÃO DO DASHBOARD HTML (LAYOUT NII PORTAL)
# ==============================================================================

def gerar_dashboard(df, caminho_saida):
    if df.empty:
        print("Nenhum dado válido foi extraído.")
        return

    total_producao = df['Valor'].sum()
    total_procedimentos = len(df)
    total_prestadores = df['Prestador'].nunique()
    
    df_sintetico = df.groupby(['Prestador', 'Grupo']).agg(
        Qtd_Total=('Codigo', 'count'),
        Valor_Total=('Valor', 'sum')
    ).reset_index()
    
    html_parts = []
    html_parts.append(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NII - Relatório de Faturamento</title>
        
        <!-- Tailwind CSS (Estilização Moderna) -->
        <script src="https://cdn.tailwindcss.com"></script>
        
        <!-- FontAwesome -->
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        
        <!-- DataTables CSS -->
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
        
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            
            body {{
                font-family: 'Roboto', sans-serif;
                background-color: #f8f9fa; /* Cor de fundo do Portal */
                color: #333;
            }}
            
            /* Header estilo NII Portal */
            .nii-header {{
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                padding: 1rem 0;
                margin-bottom: 2rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            
            .nii-brand {{
                font-size: 1.5rem;
                font-weight: 700;
                color: #2c3e50;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            /* Cards de Métricas */
            .metric-card {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 1.5rem;
                transition: transform 0.2s;
            }}
            .metric-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            
            /* Botões de Aba (Estilo Clean) */
            .tab-btn {{
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 500;
                transition: all 0.3s;
            }}
            .tab-btn.active {{
                background-color: #3498db;
                color: white;
                box-shadow: 0 2px 4px rgba(52, 152, 219, 0.3);
            }}
            .tab-btn.inactive {{
                background-color: #e9ecef;
                color: #495057;
            }}
            .tab-btn.inactive:hover {{
                background-color: #dee2e6;
            }}
            
            /* Tabela e Filtros */
            .dataTables_wrapper .dataTables_length select {{ border: 1px solid #ddd; padding: 4px; border-radius: 4px; }}
            .dataTables_wrapper .dataTables_filter input {{ border: 1px solid #ddd; padding: 5px; border-radius: 4px; margin-left: 5px; }}
            tfoot input, tfoot select {{ width: 100%; padding: 4px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; }}
            tfoot {{ display: table-header-group; }}
        </style>
    </head>
    <body>
    
        <!-- HEADER NII PORTAL -->
        <header class="nii-header">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center">
                <div class="nii-brand">
                    <i class="fa-solid fa-folder-open text-blue-600"></i>
                    <span>NII - Núcleo Interno de Informação</span>
                </div>
                <div class="text-right">
                    <div class="text-sm font-bold text-gray-700">Hospital Beneficente Santa Helena</div>
                    <div class="text-xs text-gray-500">Relatório de Faturamento SUS</div>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
            
            <!-- Cards de Resumo -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="metric-card border-l-4 border-green-500">
                    <div class="text-sm text-gray-500 font-medium uppercase tracking-wide">Valor Total Produzido</div>
                    <div class="mt-2 flex items-baseline gap-2">
                        <span class="text-3xl font-bold text-gray-800">R$ {total_producao:,.2f}</span>
                    </div>
                </div>
                <div class="metric-card border-l-4 border-blue-500">
                    <div class="text-sm text-gray-500 font-medium uppercase tracking-wide">Qtd. Procedimentos</div>
                    <div class="mt-2">
                        <span class="text-3xl font-bold text-gray-800">{total_procedimentos}</span>
                    </div>
                </div>
                <div class="metric-card border-l-4 border-purple-500">
                    <div class="text-sm text-gray-500 font-medium uppercase tracking-wide">Prestadores Listados</div>
                    <div class="mt-2">
                        <span class="text-3xl font-bold text-gray-800">{total_prestadores}</span>
                    </div>
                </div>
            </div>

            <!-- Controles de Navegação -->
            <div class="flex items-center justify-between mb-4">
                <div class="space-x-2">
                    <button onclick="switchTab('sintetico')" id="btn-sintetico" class="tab-btn active">
                        <i class="fa-solid fa-chart-pie mr-2"></i>Visão Sintética
                    </button>
                    <button onclick="switchTab('analitico')" id="btn-analitico" class="tab-btn inactive">
                        <i class="fa-solid fa-table-list mr-2"></i>Visão Analítica
                    </button>
                </div>
                <div class="text-xs text-gray-400">
                    Gerado automaticamente via NII Automation
                </div>
            </div>

            <!-- TABELA SINTÉTICA -->
            <div id="view-sintetico" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden p-4">
                <table id="table-sintetico" class="w-full text-sm text-left text-gray-600 hover stripe">
                    <thead class="bg-gray-50 text-gray-700 uppercase font-bold">
                        <tr><th>Prestador</th><th>Grupo</th><th class="text-right">Qtd</th><th class="text-right">Valor (R$)</th></tr>
                    </thead>
                    <tfoot><tr><th>Prestador</th><th>Grupo</th><th></th><th></th></tr></tfoot>
                    <tbody>
    """)
    
    for _, row in df_sintetico.iterrows():
        html_parts.append(f"<tr><td class='font-medium'>{row['Prestador']}</td><td>{row['Grupo']}</td><td class='text-right'>{row['Qtd_Total']}</td><td class='text-right font-bold text-green-600'>{row['Valor_Total']:,.2f}</td></tr>")
        
    html_parts.append("""</tbody></table></div>

        <!-- TABELA ANALÍTICA -->
        <div id="view-analitico" class="hidden bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden p-4">
            <table id="table-analitico" class="w-full text-sm text-left text-gray-600 hover stripe">
                <thead class="bg-gray-50 text-gray-700 uppercase font-bold">
                    <tr><th>Data</th><th>AIH</th><th>Paciente</th><th>Prestador</th><th>Procedimento</th><th class="text-right">Valor (R$)</th></tr>
                </thead>
                <tfoot><tr><th>Data</th><th>AIH</th><th>Paciente</th><th>Prestador</th><th>Procedimento</th><th></th></tr></tfoot>
                <tbody>
    """)
    
    for _, row in df.iterrows():
        # Destaque visual se o paciente for "NÃO IDENTIFICADO"
        class_paciente = "text-red-500 font-bold" if "NÃO IDENTIFICADO" in str(row['Paciente']) else ""
        
        html_parts.append(f"""
        <tr>
            <td>{row['Data']}</td>
            <td class="font-mono text-xs">{row['AIH']}</td>
            <td class="{class_paciente}">{row['Paciente']}</td>
            <td>{row['Prestador']}</td>
            <td>{row['Procedimento']}</td>
            <td class='text-right font-medium'>{row['Valor']:,.2f}</td>
        </tr>""")

    html_parts.append("""
                </tbody>
            </table>
        </div>
        
        <footer class="mt-12 text-center text-gray-400 text-xs pb-4 border-t border-gray-200 pt-4">
            &copy; 2025 Hospital Beneficente Santa Helena - Núcleo Interno de Informação
        </footer>

    </main>
    
    <!-- Scripts -->
    <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
    
    <script>
        $(document).ready(function() {
            function initTable(id) {
                $(id).DataTable({
                    language: { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json' },
                    dom: 'Bfrtip',
                    buttons: [
                        { extend: 'excel', text: '<i class="fa-solid fa-file-excel mr-2"></i>Excel', className: 'bg-green-600 text-white rounded px-3 py-1 text-sm hover:bg-green-700 border-none' },
                        { extend: 'print', text: '<i class="fa-solid fa-print mr-2"></i>Imprimir', className: 'bg-gray-600 text-white rounded px-3 py-1 text-sm hover:bg-gray-700 border-none' }
                    ],
                    pageLength: 25,
                    initComplete: function () {
                        this.api().columns().every(function () {
                            var column = this;
                            if ($(column.footer()).text() !== "") {
                                var select = $('<select><option value=""></option></select>')
                                    .appendTo($(column.footer()).empty())
                                    .on('change', function () {
                                        var val = $.fn.dataTable.util.escapeRegex($(this).val());
                                        column.search(val ? '^' + val + '$' : '', true, false).draw();
                                    });
                                column.data().unique().sort().each(function (d, j) {
                                    select.append('<option value="' + d + '">' + d + '</option>');
                                });
                            }
                        });
                    }
                });
            }

            initTable('#table-sintetico');
            initTable('#table-analitico');
        });

        function switchTab(t) {
            $('#view-sintetico, #view-analitico').addClass('hidden');
            $('#view-'+t).removeClass('hidden');
            $('.tab-btn').removeClass('active').addClass('inactive');
            $('#btn-'+t).removeClass('inactive').addClass('active');
        }
    </script>
    </body></html>
    """)
    
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write("".join(html_parts))
    print(f"Sucesso! HTML gerado em: {caminho_saida}")

if __name__ == "__main__":
    df = processar_csv_soulmv(ARQUIVO_ENTRADA)
    gerar_dashboard(df, NOME_ARQUIVO_SAIDA)