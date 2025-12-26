# ==============================================================================
# SISTEMA DE CONFERÊNCIA DE FATURAMENTO - NII PORTAL
# Versão: V26 (Correção Final: Scanner de Dinheiro "Força Bruta")
# ==============================================================================

import pandas as pd
import csv
import os
import json
import re
from datetime import datetime

# --- 1. CONFIGURAÇÕES ---
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ENTRADA = os.path.join(PASTA_ATUAL, 'R_CONF_PROCEDIMENTO_P321.csv')
ARQUIVO_HTML_SAIDA = os.path.join(PASTA_ATUAL, 'painel_conferencia_faturamento.html')
ARQUIVO_EXCEL_SAIDA = os.path.join(PASTA_ATUAL, 'Relatorio_Conferencia_Final_V26.xlsx')
ARQUIVO_JSON_PORTAL = os.path.join(PASTA_ATUAL, 'dados_portal.json')

COMPETENCIA_ATUAL = "11/2025"

# VALORES DO REPASSE SADT (UTI)
VALOR_SADT_ADULTO = 50.00
VALOR_SADT_NEO = 70.00

# --- 2. FUNÇÕES AUXILIARES ---
def formatar_codigo(valor):
    if pd.isna(valor) or valor == '': return ''
    return str(valor).replace('.', '').strip().zfill(10)

def limpar_valor(valor):
    if pd.isna(valor) or valor == '': return 0.0
    # Remove aspas extras que o CSV as vezes traz
    val_clean = str(valor).replace('"', '').strip()
    # Remove R$, pontos de milhar e troca virgula por ponto
    val_clean = val_clean.replace('R$', '').replace('.', '').replace(',', '.')
    try: return float(val_clean)
    except: return 0.0

def extrair_valores_da_linha(lista_cols):
    """
    Varre a lista de colunas procurando qualquer coisa que pareça dinheiro.
    Retorna uma lista de floats encontrados.
    """
    valores_encontrados = []
    for col in lista_cols:
        txt = str(col).strip()
        # Regex para identificar formato monetario brasileiro: 1.000,00 ou 100,00
        # Deve ter virgula e numeros depois
        if re.search(r'\d+,\d{2}', txt):
            val = limpar_valor(txt)
            if val > 0:
                valores_encontrados.append(val)
    return valores_encontrados

def parece_nome_pessoa(texto):
    texto = str(texto).strip()
    if len(texto) < 4: return False
    if any(char.isdigit() for char in texto): return False
    palavras_proibidas = ['DATA', 'ALTA', 'INTERNA', 'MOTIVO', 'QTDE', 'TOTAL', 'PROCEDIMENTO', 'PACIENTE', 'SH:', 'SP:', 'ATENDIM.', 'SUS', 'VALOR', 'PRESTADOR']
    if texto.upper() in palavras_proibidas: return False
    return True

def definir_prestador_sigtap(cod_procedimento, nome_grupo_relatorio):
    codigo = formatar_codigo(cod_procedimento)
    grupo_nome = str(nome_grupo_relatorio).upper()
    
    if not codigo or len(codigo) < 4:
        if 'LABORAT' in grupo_nome: return 'LABORATORIO SANTA HELENA', 'Nome Grupo (Laborat)'
        return 'HOSPITAL BENEFICENTE SANTA HELENA', 'Sem Código (Padrao)'

    excecoes = {
        '0214010058': ('LABORATORIO SANTA HELENA', 'Excecao (Teste Rapido)'),
        '0214010279': ('LABORATORIO SANTA HELENA', 'Excecao (Teste Rapido)'),
        '0214010040': ('LABORATORIO SANTA HELENA', 'Excecao (Teste Rapido)'),
        '0301060061': ('HOSPITAL (TRIAGEM)', 'Excecao (Triagem)'),
        '0205010032': ('HOSPITAL BENEFICENTE SANTA HELENA', 'Excecao (Ecocardio)'),
        '0211020036': ('HOSPITAL BENEFICENTE SANTA HELENA', 'Excecao (ECG)'),
        '0702050059': ('HOSPITAL BENEFICENTE SANTA HELENA', 'Excecao OPME (Hosp)'),
        '0702040118': ('HOSPITAL BENEFICENTE SANTA HELENA', 'Excecao OPME (Hosp)'),
    }
    if codigo in excecoes: return excecoes[codigo]

    prefixo4 = codigo[:4]
    prefixo6 = codigo[:6]

    if prefixo4 == '0702':
        if prefixo6 == '070203': return 'ASTRAMED', 'Prefixo OPME 070203'
        elif prefixo6 == '070204': return 'HOSPITAL BENEFICENTE SANTA HELENA', 'Prefixo OPME 070204'
        elif prefixo6 == '070205': return 'QUALITY', 'Prefixo OPME 070205'
        return 'HOSPITAL BENEFICENTE SANTA HELENA', 'Prefixo OPME Padrao'

    if prefixo4 == '0202': return 'LABORATORIO SANTA HELENA', 'Prefixo 0202'
    elif prefixo4 == '0203': return 'LAPAT CUIABA', 'Prefixo 0203'
    elif prefixo4 == '0204': return 'SANTA HELENA IMAGEM', 'Prefixo 0204'
    elif prefixo4 == '0205': return 'SANTA HELENA IMAGEM', 'Prefixo 0205'
    elif prefixo4 == '0206': return 'DIAG X DIGITAL', 'Prefixo 0206'
    elif prefixo4 == '0209': return 'GASTROMAT', 'Prefixo 0209'
    elif prefixo4 == '0211': return 'CINECOR', 'Prefixo 0211'
    elif prefixo4 == '0212': return 'HEMOSAN', 'Prefixo 0212'
    elif prefixo4 == '0305': return 'CLINEMAT', 'Prefixo 0305'
    elif prefixo4 == '0306': return 'HEMOSAN', 'Prefixo 0306'
    
    return 'HOSPITAL BENEFICENTE SANTA HELENA', '!!! PADRAO (SEM REGRA) !!!'

# --- 3. INTEGRAÇÃO COM NII-PORTAL ---

def atualizar_portal(novo_registro):
    dados = []
    if os.path.exists(ARQUIVO_JSON_PORTAL):
        try:
            with open(ARQUIVO_JSON_PORTAL, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except: pass
    
    dados = [d for d in dados if d['arquivo'] != novo_registro['arquivo']]
    dados.append(novo_registro)
    
    try:
        with open(ARQUIVO_JSON_PORTAL, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print("✅ Portal atualizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao atualizar JSON do portal: {e}")

def gerar_html_portal(df_analitico, df_sintetico, total_geral, dados_sadt):
    linhas_sintetico = ""
    for _, row in df_sintetico.iterrows():
        classe_tr = "hover:bg-gray-50"
        pres = str(row['Prestador'])
        qtd_val = row['Qtd']
        qtd_fmt = f"{int(qtd_val)}"
        
        if "TOTAL GERAL" in pres:
            classe_tr = "bg-gray-100 font-bold text-gray-800"
        elif "CÁLCULO DE REPASSE" in pres:
            classe_tr = "bg-blue-50 font-bold text-blue-800 mt-4"
            qtd_fmt = ""
        elif "SADT" in pres:
            classe_tr = "bg-yellow-50 text-yellow-800"
            
        vl_fmt = f"R$ {row['Vl_Total_Geral']:,.2f}"
        
        linhas_sintetico += f"""
        <tr class="{classe_tr}">
            <td class="p-3 border-b">{row['Prestador']}</td>
            <td class="p-3 border-b text-center">{qtd_fmt}</td>
            <td class="p-3 border-b text-right text-gray-600">R$ {row['Vl_Total_SH']:,.2f}</td>
            <td class="p-3 border-b text-right text-gray-600">R$ {row['Vl_Total_SP']:,.2f}</td>
            <td class="p-3 border-b text-right font-semibold">{vl_fmt}</td>
        </tr>
        """

    linhas_analitico = ""
    for _, row in df_analitico.head(5000).iterrows():
        qtd_fmt = f"{int(row['Qtd'])}"
        linhas_analitico += f"""
        <tr class="hover:bg-gray-50 text-sm">
            <td class="p-2 border-b">{row['AIH']}</td>
            <td class="p-2 border-b">{row['Paciente_Nome']}</td>
            <td class="p-2 border-b">{row['Procedimento']}</td>
            <td class="p-2 border-b">{row['Prestador']}</td>
            <td class="p-2 border-b text-center">{qtd_fmt}</td>
            <td class="p-2 border-b text-right">R$ {row['Vl_Total_Geral']:,.2f}</td>
        </tr>
        """

    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Conferência de Faturamento - {COMPETENCIA_ATUAL}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
        
        <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
        
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
            body {{ font-family: 'Roboto', sans-serif; background-color: #f3f4f6; }}
            .tab-btn.active {{ color: #15803d; border-color: #15803d; }}
        </style>
    </head>
    <body>
        <header class="bg-white shadow-sm border-b border-gray-200">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="bg-green-100 p-2 rounded-lg text-green-700">
                        <i class="fa-solid fa-file-invoice-dollar text-xl"></i>
                    </div>
                    <div>
                        <h1 class="text-xl font-bold text-gray-800">Conferência de Faturamento</h1>
                        <p class="text-sm text-gray-500">Competência: {COMPETENCIA_ATUAL}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-xs text-gray-400">Total Geral</p>
                    <p class="text-2xl font-bold text-green-700">R$ {total_geral:,.2f}</p>
                </div>
            </div>
        </header>
        <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-sm font-medium text-gray-500">Faturamento Bruto</p>
                            <h3 class="text-2xl font-bold text-gray-800 mt-2">R$ {total_geral:,.2f}</h3>
                        </div>
                        <div class="p-2 bg-blue-50 rounded-lg text-blue-600"><i class="fa-solid fa-chart-line"></i></div>
                    </div>
                </div>
                <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-sm font-medium text-gray-500">SADT UTI (Extra)</p>
                            <h3 class="text-2xl font-bold text-gray-800 mt-2">R$ {dados_sadt['total_sadt']:,.2f}</h3>
                        </div>
                        <div class="p-2 bg-yellow-50 rounded-lg text-yellow-600"><i class="fa-solid fa-bed-pulse"></i></div>
                    </div>
                    <p class="text-xs text-gray-400 mt-2">Adulto: {int(dados_sadt['adulto_qtd'])} | Neo: {int(dados_sadt['neo_qtd'])} diárias</p>
                </div>
                 <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-sm font-medium text-gray-500">Registros Processados</p>
                            <h3 class="text-2xl font-bold text-gray-800 mt-2">{len(df_analitico)}</h3>
                        </div>
                        <div class="p-2 bg-purple-50 rounded-lg text-purple-600"><i class="fa-solid fa-list-check"></i></div>
                    </div>
                </div>
            </div>
            <div class="bg-white rounded-t-xl border-b border-gray-200 px-6 flex gap-8">
                <button onclick="verTab('sintetico')" id="btn-sintetico" class="tab-btn active py-4 font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors">
                    Relatório Sintético
                </button>
                <button onclick="verTab('analitico')" id="btn-analitico" class="tab-btn py-4 font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors">
                    Relatório Analítico
                </button>
            </div>
            <div class="bg-white rounded-b-xl shadow-sm border border-gray-200 p-6 min-h-[500px]">
                <div id="tab-sintetico" class="view-tab">
                    <table id="tbl-sintetico" class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-gray-50 text-gray-600 text-sm uppercase tracking-wider">
                                <th class="p-3 font-semibold border-b">Prestador</th>
                                <th class="p-3 font-semibold border-b text-center">Qtd</th>
                                <th class="p-3 font-semibold border-b text-right">Vl. SH</th>
                                <th class="p-3 font-semibold border-b text-right">Vl. SP</th>
                                <th class="p-3 font-semibold border-b text-right">Total</th>
                            </tr>
                        </thead>
                        <tbody class="text-gray-700">
                            {linhas_sintetico}
                        </tbody>
                    </table>
                </div>
                <div id="tab-analitico" class="view-tab hidden">
                    <table id="tbl-analitico" class="w-full text-left border-collapse display" style="width:100%">
                        <thead>
                            <tr class="bg-gray-50 text-gray-600 text-sm uppercase tracking-wider">
                                <th class="p-2 font-semibold border-b">AIH</th>
                                <th class="p-2 font-semibold border-b">Paciente</th>
                                <th class="p-2 font-semibold border-b">Procedimento</th>
                                <th class="p-2 font-semibold border-b">Prestador</th>
                                <th class="p-2 font-semibold border-b text-center">Qtd</th>
                                <th class="p-2 font-semibold border-b text-right">Valor</th>
                            </tr>
                        </thead>
                        <tbody class="text-gray-700">
                            {linhas_analitico}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="mt-8 text-center">
                 <a href="https://franckmoura.github.io/NII-Portal/" class="inline-flex items-center gap-2 px-6 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors">
                    <i class="fa-solid fa-arrow-left"></i> Voltar ao NII Portal
                </a>
            </div>
        </main>
        <script>
            function verTab(id){{
                $('.view-tab').addClass('hidden');
                $('#tab-'+id).removeClass('hidden');
                $('.tab-btn').removeClass('active');
                $('#btn-'+id).addClass('active');
            }}
            $(document).ready(function() {{
                $('#tbl-sintetico').DataTable({{dom: 'Brt', buttons: ['excel', 'pdf', 'print'], paging: false, ordering: false}});
                $('#tbl-analitico').DataTable({{language: {{url:'//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json'}}, dom: 'Bfrtip', buttons: ['excel', 'pdf', 'print'], pageLength: 25}});
            }});
        </script>
    </body>
    </html>
    """
    
    with open(ARQUIVO_HTML_SAIDA, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"✨ HTML gerado com sucesso: {ARQUIVO_HTML_SAIDA}")

# --- 4. EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print(f"Iniciando processamento V26 (Força Bruta)...")

    try:
        try:
            f = open(ARQUIVO_ENTRADA, 'r', encoding='latin1')
            linhas = f.readlines()
        except:
            f = open(ARQUIVO_ENTRADA, 'r', encoding='utf-8')
            linhas = f.readlines()
        f.close()

        # --- PASSO 1: MAPA DE VALORES REAIS (MEMÓRIA BLINDADA) ---
        mapa_valores_reais = {} 
        cod_proc_temp = ""
        
        # Mapa auxiliar para saber quantos pacientes existem por código (para divisão correta)
        contador_qtd_por_codigo = {} 

        # Primeira varredura APENAS para contar qtd total por código
        # Isso é necessário porque o "QTD" do rodapé as vezes não bate com a soma das linhas individuais
        # Vamos confiar na SOMA DAS LINHAS para o divisor.
        
        # ... Na verdade, o mais seguro é pegar o VALOR TOTAL do rodapé e dividir pela QTD TOTAL do rodapé
        # E se a qtd do rodapé estiver errada? 
        # Vamos confiar nos valores MONETÁRIOS do rodapé.
        
        for i, linha in enumerate(linhas):
            # Detecta início de código (Atualiza memória)
            if 'Procedimento:' in linha:
                cols = list(csv.reader([linha], delimiter=','))[0]
                for p in cols:
                    clean = p.strip().replace('.0','')
                    if clean.isdigit() and len(clean) >= 8:
                        cod_proc_temp = formatar_codigo(clean)
                        break
            
            # Detecta total e associa ao ultimo codigo visto
            if 'Total Procedimento' in linha and cod_proc_temp:
                if i + 1 < len(linhas):
                    val_line = linhas[i+1]
                    cols = list(csv.reader([val_line], delimiter=','))[0]
                    
                    # SCANNER DE DINHEIRO
                    valores_monetarios = extrair_valores_da_linha(cols)
                    
                    # Se achou pelo menos 1 valor, é o total. Se achou 2, é SH e SP.
                    if valores_monetarios:
                        if len(valores_monetarios) == 1:
                            # Só tem um valor, assume que é SP se for médico, ou SH se for hospital.
                            # Na dúvida, guarda como 'total' e divide depois
                            mapa_valores_reais[cod_proc_temp] = {'sh': 0.0, 'sp': 0.0, 'total_bruto': valores_monetarios[0]}
                        else:
                            # Tem dois valores, o padrão visual é SH primeiro, SP depois (ou vice-versa dependendo da coluna)
                            # Mas a soma deles é o que importa para o 'total'
                            # Vamos guardar a SOMA deles como 'total_bruto' do bloco
                            soma_bloco = sum(valores_monetarios)
                            
                            # Tenta separar SH e SP baseado na ordem (SH geralmente vem antes do SP nas colunas)
                            # Mas para evitar erro, vamos focar no TOTAL do paciente.
                            mapa_valores_reais[cod_proc_temp] = {'sh': valores_monetarios[0], 'sp': valores_monetarios[1], 'total_bruto': soma_bloco}
                        
                        # Tenta achar a QTD nesse bolo
                        # A qtd é um numero, mas não tem virgula de centavos geralmente.
                        # Vamos varrer a linha de novo procurando inteiros ou floats simples
                        qtd_bloco = 0
                        for c in cols:
                            c_clean = c.strip()
                            if c_clean.isdigit():
                                qtd_bloco = float(c_clean)
                                break
                        
                        if qtd_bloco > 0:
                            mapa_valores_reais[cod_proc_temp]['qtd_bloco'] = qtd_bloco

        # --- PASSO 2: PROCESSAMENTO ANALÍTICO ---
        dados_brutos = []
        memoria_aih_nomes = {} 
        grupo_atual = "INDEFINIDO"
        cod_proc_atual = ""
        desc_proc_atual = ""
        sh_unit_atual = 0.0
        sp_unit_atual = 0.0
        qtd_uti_adulto = 0
        qtd_uti_neo = 0
        
        for linha in linhas:
            reader = csv.reader([linha], delimiter=',')
            cols = list(reader)[0]
            if not cols: continue
            
            texto_col0 = str(cols[0]).strip()
            texto_col1 = str(cols[1]).strip() if len(cols) > 1 else ""
            
            if 'Grupo:' in texto_col1:
                grupo_atual = " ".join([c for c in cols[2:] if c.strip()])
            elif 'Procedimento:' in texto_col1 or 'Procedimento:' in texto_col0:
                partes = [c for c in cols if c.strip()]
                if len(partes) >= 2:
                    for parte in partes:
                        clean = parte.replace('.0','')
                        if clean.isdigit() and len(clean) >= 8:
                            cod_proc_atual = formatar_codigo(clean)
                            idx = partes.index(parte)
                            if idx + 1 < len(partes):
                                desc_proc_atual = " ".join(partes[idx+1:])
                            sh_unit_atual = 0.0
                            sp_unit_atual = 0.0
                            break
            
            if 'SH:' in linha or 'SP:' in linha:
                for i, col in enumerate(cols):
                    txt = str(col).strip().upper()
                    if 'SH:' in txt and i + 1 < len(cols):
                        sh_unit_atual = limpar_valor(cols[i+1])
                    if 'SP:' in txt and i + 1 < len(cols):
                        sp_unit_atual = limpar_valor(cols[i+1])

            # Identificação de Paciente
            idx_aih = -1
            idx_nome = -1
            for i, val in enumerate(cols):
                v = str(val).strip()
                if (v.startswith('512') or v.startswith('42')) and len(v) >= 12:
                    idx_aih = i
                    break
            if len(cols) > 4 and parece_nome_pessoa(cols[4]): idx_nome = 4
            
            if (idx_aih != -1) or (idx_nome != -1):
                aih = cols[idx_aih] if idx_aih != -1 else "N/D"
                nome_encontrado = cols[idx_nome].strip() if idx_nome != -1 else ""
                
                if not nome_encontrado and idx_aih != -1:
                    inicio = max(0, idx_aih - 10)
                    fim = idx_aih
                    for k in range(inicio, fim):
                        if parece_nome_pessoa(cols[k]):
                            nome_encontrado = cols[k].strip()
                            break
                if idx_aih != -1 and len(nome_encontrado) > 3:
                    nome_anterior = memoria_aih_nomes.get(aih, "")
                    if len(nome_encontrado) > len(nome_anterior):
                        memoria_aih_nomes[aih] = nome_encontrado
                
                # Scanner Qtd
                candidatos_qtd = []
                ponto_partida = idx_aih if idx_aih != -1 else 10
                inicio_scan = ponto_partida + 6
                fim_scan = ponto_partida + 25
                limite_loop = min(len(cols), fim_scan)
                for k in range(inicio_scan, limite_loop):
                    val_str = cols[k].strip().replace(',', '.')
                    if val_str.replace('.', '').isdigit() and len(val_str) < 5:
                        try: candidatos_qtd.append(float(val_str))
                        except: pass
                qtd = candidatos_qtd[-1] if candidatos_qtd else 1.0
                if len(cols) > ponto_partida + 14 and not candidatos_qtd:
                    try: qtd = float(cols[ponto_partida + 14].replace(',', '.'))
                    except: qtd = 1.0

                if cod_proc_atual == '0802010083': qtd_uti_adulto += qtd
                elif cod_proc_atual == '0802010121': qtd_uti_neo += qtd

                # --- LÓGICA DE VALOR HÍBRIDA ---
                # 1. Tenta valor do cabeçalho
                val_total_item = (sh_unit_atual + sp_unit_atual) * qtd
                val_sh_final = sh_unit_atual
                val_sp_final = sp_unit_atual

                # 2. Se cabeçalho for zero, usa o MAPA DE TOTAIS (MÉDIA)
                if val_total_item == 0 and cod_proc_atual in mapa_valores_reais:
                    info_real = mapa_valores_reais[cod_proc_atual]
                    total_bloco = info_real.get('total_bruto', 0)
                    qtd_bloco = info_real.get('qtd_bloco', 1)
                    
                    if qtd_bloco > 0:
                        preco_medio = total_bloco / qtd_bloco
                        val_total_item = preco_medio * qtd
                        # Tenta ratear SH/SP proporcionalmente se disponivel
                        if info_real['sh'] + info_real['sp'] > 0:
                            ratio_sh = info_real['sh'] / (info_real['sh'] + info_real['sp'])
                            val_sh_final = (preco_medio * ratio_sh)
                            val_sp_final = (preco_medio * (1-ratio_sh))
                        else:
                            val_sh_final = preco_medio # Joga tudo no SH se nao souber
                            val_sp_final = 0

                prestador, regra = definir_prestador_sigtap(cod_proc_atual, grupo_atual)

                item = {
                    'Competencia': COMPETENCIA_ATUAL,
                    'Familia_Sigtap': cod_proc_atual[:4] if cod_proc_atual else '',
                    'Prestador': prestador,
                    'Codigo': cod_proc_atual,
                    'Procedimento': desc_proc_atual,
                    'AIH': aih,
                    'Paciente_Nome': nome_encontrado, 
                    'Qtd': qtd,
                    'Vl_Unit_SH': val_sh_final,
                    'Vl_Total_SH': val_sh_final * qtd,
                    'Vl_Unit_SP': val_sp_final,
                    'Vl_Total_SP': val_sp_final * qtd,
                    'Vl_Total_Geral': val_total_item
                }
                dados_brutos.append(item)

        dados_analiticos = []
        for item in dados_brutos:
            aih = item['AIH']
            if len(item['Paciente_Nome']) < 3:
                item['Paciente_Nome'] = memoria_aih_nomes.get(aih, "--- NOME NAO ENCONTRADO ---")
            dados_analiticos.append(item)

        if dados_analiticos:
            df_analitico = pd.DataFrame(dados_analiticos)
            df_sintetico = df_analitico.groupby('Prestador')[['Qtd', 'Vl_Total_SH', 'Vl_Total_SP', 'Vl_Total_Geral']].sum().reset_index()
            
            total_geral = df_sintetico['Vl_Total_Geral'].sum()
            linha_total = {
                'Prestador': '=== TOTAL GERAL (FATURAMENTO) ===',
                'Qtd': df_sintetico['Qtd'].sum(),
                'Vl_Total_SH': df_sintetico['Vl_Total_SH'].sum(),
                'Vl_Total_SP': df_sintetico['Vl_Total_SP'].sum(),
                'Vl_Total_Geral': total_geral
            }
            df_sintetico = pd.concat([df_sintetico, pd.DataFrame([linha_total])], ignore_index=True)

            total_sadt_adulto = qtd_uti_adulto * VALOR_SADT_ADULTO
            total_sadt_neo = qtd_uti_neo * VALOR_SADT_NEO
            total_sadt_geral = total_sadt_adulto + total_sadt_neo

            linhas_sadt = [
                {'Prestador': '*** CÁLCULO DE REPASSE (EXTRA) ***', 'Qtd': 0, 'Vl_Total_SH': 0, 'Vl_Total_SP': 0, 'Vl_Total_Geral': 0},
                {'Prestador': f'SADT UTI-ADULTO ({int(qtd_uti_adulto)} x {VALOR_SADT_ADULTO})', 'Qtd': qtd_uti_adulto, 'Vl_Total_SH':0, 'Vl_Total_SP':0, 'Vl_Total_Geral': total_sadt_adulto},
                {'Prestador': f'SADT UTI-NEONATAL ({int(qtd_uti_neo)} x {VALOR_SADT_NEO})', 'Qtd': qtd_uti_neo, 'Vl_Total_SH':0, 'Vl_Total_SP':0, 'Vl_Total_Geral': total_sadt_neo}
            ]
            df_sintetico = pd.concat([df_sintetico, pd.DataFrame(linhas_sadt)], ignore_index=True)

            with pd.ExcelWriter(ARQUIVO_EXCEL_SAIDA, engine='openpyxl') as writer:
                df_analitico.to_excel(writer, sheet_name='Analitico', index=False)
                df_sintetico.to_excel(writer, sheet_name='Sintetico', index=False)
            print(f"📁 Excel de backup gerado: {ARQUIVO_EXCEL_SAIDA}")

            dados_sadt = {
                'total_sadt': total_sadt_geral,
                'adulto_qtd': qtd_uti_adulto,
                'neo_qtd': qtd_uti_neo
            }
            gerar_html_portal(df_analitico, df_sintetico, total_geral, dados_sadt)

            registro = {
                "titulo": f"Conferência Faturamento {COMPETENCIA_ATUAL}",
                "competencia": COMPETENCIA_ATUAL,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "valor_total": f"R$ {total_geral:,.2f}",
                "arquivo": os.path.basename(ARQUIVO_HTML_SAIDA),
                "tipo": "Faturamento"
            }
            atualizar_portal(registro)
        else:
            print("❌ Nenhum dado encontrado.")

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")