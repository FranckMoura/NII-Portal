# ==============================================================================
# SISTEMA INTEGRADO DE REPASSES MÉDICOS - NII PORTAL
# Autor: Franck Moura (Via NII Automation)
# Data: 2025-04-10
# Versão: 3.1 (Correção de KeyError e Robustez)
# Descrição: Processa Rateio + Individual.
#            Gera relatórios com cabeçalhos formais e força a impressão dos TOTAIS.
#            Correção de erro 'KeyError: Prestador' ao gerar HTML.
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
import glob
import difflib  # Biblioteca para comparação de textos similares
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÕES AUTOMÁTICAS
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

ARQUIVO_PDF_RATEIO_RECEITA = os.path.join(PASTA_SCRIPT, 'R_RECEITA_PROCEDIMENTO_RATEIO_1125.pdf')
ARQUIVO_PDF_PRODUCAO_CONTA = os.path.join(PASTA_SCRIPT, 'R_PRODUCAO_MEDICA_CONTA_1125.pdf')

print(f"--- Iniciando Processamento na pasta: {os.path.basename(PASTA_SCRIPT)} ---")

# ==============================================================================
# 2. FUNÇÕES UTILITÁRIAS E CORREÇÃO DE NOMES
# ==============================================================================

def encontrar_arquivo_json_portal():
    nome_json = 'dados_financeiro.json'
    diretorio_atual = PASTA_SCRIPT
    for _ in range(5):
        caminho_teste = os.path.join(diretorio_atual, nome_json)
        if os.path.exists(caminho_teste):
            return caminho_teste, diretorio_atual
        pai = os.path.dirname(diretorio_atual)
        if pai == diretorio_atual: break
        diretorio_atual = pai
    return None, None

def limpar_valor_monetario(valor_str):
    if not valor_str: return 0.0
    v = valor_str.replace('"', '').replace("'", "").strip()
    try:
        if ',' in v: v = v.replace('.', '').replace(',', '.')
        elif v.count('.') == 1: pass
        return float(v)
    except: return 0.0

def extrair_competencia_do_nome(nome_arquivo):
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo, re.IGNORECASE)
    if match:
        mes, ano_curto = match.groups()
        return f"{mes}/20{ano_curto}", f"{mes}20{ano_curto}"
    agora = datetime.now()
    return agora.strftime("%m/%Y"), agora.strftime("%m%Y")

def corrigir_nome_similar(nome_pdf, lista_nomes_oficiais, corte=0.80):
    """
    Compara o nome vindo do PDF com a lista oficial (CSV).
    Tenta match exato, match parcial (inicio da string) e fuzzy match.
    """
    if not nome_pdf or not lista_nomes_oficiais:
        return nome_pdf
    
    nome_upper = nome_pdf.upper().strip()
    
    # 1. Busca exata (rápida)
    if nome_upper in lista_nomes_oficiais:
        return nome_upper
        
    # 2. Busca por Contenção/Início (NOVO - Resolve caso Cristiane)
    # Verifica se o nome oficial é o começo do nome do PDF (ou vice-versa)
    for oficial in lista_nomes_oficiais:
        # Ex: "CRISTIANE CAROLINE PEREIRA..." (PDF) começa com "CRISTIANE CAROLINE" (CSV)
        if nome_upper.startswith(oficial) or oficial.startswith(nome_upper):
             # Validação extra de tamanho para evitar falsos positivos muito curtos (ex: "ANA")
             if len(oficial) > 4 and len(nome_upper) > 4:
                 return oficial

    # 3. Busca aproximada (Fuzzy) - Resolve erros de digitação (Allan vs Alan)
    matches = difflib.get_close_matches(nome_upper, lista_nomes_oficiais, n=1, cutoff=corte)
    
    if matches:
        return matches[0]
    
    return nome_upper

# ==============================================================================
# 3. LEITURA INTELIGENTE DE VÍNCULOS
# ==============================================================================

def encontrar_e_ler_vinculos_flexivel():
    padrao_busca = os.path.join(PASTA_SCRIPT, "*vinculo*.csv")
    arquivos_encontrados = glob.glob(padrao_busca) + glob.glob(os.path.join(PASTA_SCRIPT, "*VINCULO*.csv"))
    
    if not arquivos_encontrados:
        print("[ERRO] Nenhum arquivo de vínculo encontrado.")
        return pd.DataFrame()
    
    arquivo_alvo = arquivos_encontrados[0]
    print(f"   -> Arquivo de Vínculos detectado: {os.path.basename(arquivo_alvo)}")
    
    try:
        with open(arquivo_alvo, 'r', encoding='latin1') as f:
            linhas = f.readlines()
        
        linha_cabecalho = 0
        sep_detectado = ',' 
        for i, linha in enumerate(linhas):
            if 'MEDICO' in linha.upper() or 'PRESTADOR' in linha.upper():
                linha_cabecalho = i
                if ';' in linha: sep_detectado = ';'
                break
        
        df = pd.read_csv(arquivo_alvo, sep=sep_detectado, skiprows=linha_cabecalho, encoding='latin1')
        
        colunas_normalizadas = {}
        for col in df.columns:
            c = col.upper().strip()
            if c in ['MEDICO', 'MÉDICO', 'PRESTADOR', 'NOME', 'PROFISSIONAL']:
                colunas_normalizadas[col] = 'prestador'
            elif c in ['QTDE', 'QTD', 'VINCULO', 'VÍNCULO', 'PESO', 'VALOR']:
                colunas_normalizadas[col] = 'vinculo'
        
        df = df.rename(columns=colunas_normalizadas)
        
        if 'prestador' not in df.columns or 'vinculo' not in df.columns:
            print("[ERRO] Colunas essenciais não encontradas no CSV.")
            return pd.DataFrame()

        df = df.dropna(subset=['prestador'])
        df['vinculo'] = df['vinculo'].astype(str).str.replace(',', '.').apply(pd.to_numeric, errors='coerce')
        df = df.fillna({'vinculo': 0})
        df = df[df['vinculo'] > 0]
        
        # Padroniza nomes do CSV (sempre maiúsculos e sem espaços extras)
        df['prestador'] = df['prestador'].str.upper().str.strip()
        
        print(f"   -> Vínculos carregados: {len(df)}")
        return df[['prestador', 'vinculo']]

    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao ler CSV: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESSAMENTO (MOTOR DE CÁLCULO)
# ==============================================================================

def processar_rateio():
    print(f"1. Processando Rateio...")
    total_bolo_sp = 0.0
    codigos_rateio = set()
    
    if not os.path.exists(ARQUIVO_PDF_RATEIO_RECEITA):
        print(f"[ERRO] Arquivo não encontrado: {os.path.basename(ARQUIVO_PDF_RATEIO_RECEITA)}")
        return 0.0, set(), pd.DataFrame()

    with pdfplumber.open(ARQUIVO_PDF_RATEIO_RECEITA) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                if re.match(r'^"?(\d{8,10})"?', line.strip()):
                    cod = re.match(r'^"?(\d{8,10})"?', line.strip()).group(1)
                    codigos_rateio.add(cod)
                    valores = re.findall(r'"?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"?', line)
                    if len(valores) >= 2:
                        total_bolo_sp += limpar_valor_monetario(valores[-2])

    print(f"   -> Receita Total Rateio: R$ {total_bolo_sp:,.2f}")

    df_vinculos = encontrar_e_ler_vinculos_flexivel()
    if not df_vinculos.empty:
        total_pesos = df_vinculos['vinculo'].sum()
        if total_pesos > 0:
            valor_ponto = total_bolo_sp / total_pesos
            df_vinculos['valor_rateio'] = df_vinculos['vinculo'] * valor_ponto
        else: df_vinculos['valor_rateio'] = 0.0
    
    return total_bolo_sp, codigos_rateio, df_vinculos

def processar_individual(codigos_blacklist, lista_nomes_oficiais=None):
    """
    Processa o PDF individual.
    Recebe 'lista_nomes_oficiais' para corrigir grafias erradas.
    """
    print(f"2. Processando Produção Individual (com correção de nomes)...")
    if not os.path.exists(ARQUIVO_PDF_PRODUCAO_CONTA):
        print(f"[ERRO] Arquivo não encontrado: {os.path.basename(ARQUIVO_PDF_PRODUCAO_CONTA)}")
        return pd.DataFrame(), pd.DataFrame()

    dados = []
    prestador_atual = "DESCONHECIDO"
    codigo_em_espera = None 
    
    regex_prestador = re.compile(r'^([A-Z\s\.]+)\s+\(\d+\)$')
    regex_cod = re.compile(r'\b(\d{10})\b')
    regex_data = re.compile(r'\b\d{2}/\d{2}\b')

    with pdfplumber.open(ARQUIVO_PDF_PRODUCAO_CONTA) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                line = line.strip()
                linha_upper = line.upper()
                
                # --- FILTROS ---
                if "TOTAL" in linha_upper and ("PRESTADOR" in linha_upper or "GERAL" in linha_upper or "GRUPO" in linha_upper): continue
                if "DIARIA" in linha_upper or "DIÁRIA" in linha_upper: continue
                if "CONSULTA" in linha_upper or "VISITA" in linha_upper or "ATENDIMENTO" in linha_upper: continue
                
                # 1. Identifica Prestador e CORRIGE O NOME
                match_prest = regex_prestador.match(line)
                if match_prest and "HOSPITAL" not in line:
                    nome_extraido = match_prest.group(1).strip()
                    
                    # A MÁGICA ACONTECE AQUI: Normaliza o nome com base no CSV
                    if lista_nomes_oficiais:
                        prestador_atual = corrigir_nome_similar(nome_extraido, lista_nomes_oficiais)
                    else:
                        prestador_atual = nome_extraido
                        
                    codigo_em_espera = None 
                    continue
                
                # 2. Captura Código
                match_c = regex_cod.search(line)
                if match_c: codigo_em_espera = match_c.group(1)
                
                # 3. Verifica Data
                tem_data = regex_data.search(line)

                # 4. Captura Valor
                if re.search(r'\d+,\d{2}$', line):
                    try:
                        val_str = line.split()[-1]
                        valor = limpar_valor_monetario(val_str)
                        
                        if valor > 0 and prestador_atual != "DESCONHECIDO":
                            codigo_final = match_c.group(1) if match_c else codigo_em_espera
                            eh_valido = codigo_final is not None or tem_data is not None
                            
                            if eh_valido:
                                eh_rateio = codigo_final and codigo_final in codigos_blacklist
                                
                                if not eh_rateio:
                                    dados.append({
                                        'Prestador': prestador_atual,
                                        'Procedimento': codigo_final or "N/D",
                                        'Valor_Individual': valor,
                                        'Detalhes': line[:60]
                                    })
                            codigo_em_espera = None 
                    except: pass
    
    df = pd.DataFrame(dados)
    if not df.empty:
        # Agrupa pelo nome CORRIGIDO, somando as duplicidades
        df_agrup = df.groupby('Prestador')['Valor_Individual'].sum().reset_index()
        return df_agrup, df
    return pd.DataFrame(), pd.DataFrame()

# ==============================================================================
# 5. ATUALIZAÇÃO DO JSON DO PORTAL
# ==============================================================================

def atualizar_portal(novo_registro):
    caminho_json, pasta_raiz = encontrar_arquivo_json_portal()
    if not caminho_json: return

    rel_path = os.path.relpath(os.path.join(PASTA_SCRIPT, novo_registro['arquivo']), os.path.dirname(caminho_json))
    novo_registro['arquivo'] = rel_path.replace(os.sep, '/')
    
    dados = []
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except: pass

    dados = [d for d in dados if d['arquivo'] != novo_registro['arquivo']]
    dados.append(novo_registro)
    
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    print("   -> Portal atualizado!")

# ==============================================================================
# 6. GERAÇÃO HTML E MAIN
# ==============================================================================

def gerar_html(df_rateio, df_ind_res, df_ind_det, total_bolo):
    comp_label, comp_sufixo = extrair_competencia_do_nome(os.path.basename(ARQUIVO_PDF_RATEIO_RECEITA))
    nome_html = f"relatorio_repasse_{comp_sufixo}.html"
    caminho_html = os.path.join(PASTA_SCRIPT, nome_html)
    
    # --- PREPARAÇÃO DE DADOS RATEIO ---
    # Garante que df_rateio tem as colunas corretas antes do merge
    if df_rateio.empty:
        # Cria DataFrame vazio com colunas esperadas se estiver vazio
        df_rateio = pd.DataFrame(columns=['prestador', 'vinculo', 'valor_rateio'])
    
    # Padroniza nomes e cria chave
    if 'prestador' in df_rateio.columns:
        df_rateio['chave'] = df_rateio['prestador'].str.upper().str.strip()
        df_geral = df_rateio.rename(columns={'valor_rateio': 'Vl_Rateio', 'prestador': 'Prestador'})
    else:
        # Fallback se colunas não existirem
        print("[AVISO] Coluna 'prestador' não encontrada em df_rateio")
        df_geral = pd.DataFrame(columns=['Prestador', 'chave', 'Vl_Rateio'])

    # --- PREPARAÇÃO DE DADOS INDIVIDUAL ---
    if not df_ind_res.empty:
        if 'Prestador' in df_ind_res.columns:
            df_ind_res['chave'] = df_ind_res['Prestador'].str.upper().str.strip()
            # Full Outer Join garantido pela chave de nomes corrigidos
            df_geral = pd.merge(df_geral, df_ind_res[['chave', 'Valor_Individual']], on='chave', how='outer')
        else:
             print("[AVISO] Coluna 'Prestador' não encontrada em df_ind_res")
             df_geral['Valor_Individual'] = 0.0
    else: 
        df_geral['Valor_Individual'] = 0.0
    
    # Preenchimento de Nulos
    if 'Vl_Rateio' not in df_geral.columns: df_geral['Vl_Rateio'] = 0.0
    if 'Valor_Individual' not in df_geral.columns: df_geral['Valor_Individual'] = 0.0
    
    df_geral['Vl_Rateio'] = df_geral['Vl_Rateio'].fillna(0)
    df_geral['Valor_Individual'] = df_geral['Valor_Individual'].fillna(0)
    df_geral['Total_Final'] = df_geral['Vl_Rateio'] + df_geral['Valor_Individual']
    
    # Garante que a coluna Prestador exista e esteja preenchida
    if 'Prestador' not in df_geral.columns: df_geral['Prestador'] = None
    df_geral['Prestador'] = df_geral['Prestador'].fillna(df_geral['chave'])
    
    # Remove linhas inválidas
    df_geral = df_geral.dropna(subset=['Prestador']).sort_values('Prestador')
    
    # TOTAIS GERAIS
    total_geral_rateio = df_geral['Vl_Rateio'].sum()
    total_geral_indiv = df_geral['Valor_Individual'].sum()
    total_geral_final = df_geral['Total_Final'].sum()
    
    total_rateio_val = df_rateio['valor_rateio'].sum() if 'valor_rateio' in df_rateio.columns else 0.0
    total_indiv_val = df_ind_det['Valor_Individual'].sum() if not df_ind_det.empty else 0.0
    
    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <title>Relatório de Repasse Médico - {comp_label}</title>
        <script src='https://cdn.tailwindcss.com'></script>
        <link href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css' rel='stylesheet'>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
        <style>
            body{{background-color:#f8f9fa;font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}}
            .tab-btn{{padding:12px 24px;cursor:pointer;border-bottom:3px solid transparent;font-weight:600;color:#6c757d;transition:all 0.2s;}}
            .tab-btn.active{{border-color:#0d6efd;color:#0d6efd;background-color:#fff;border-radius:5px 5px 0 0;}}
            .tab-container{{background-color:#fff;border:1px solid #dee2e6;border-radius:0 0 5px 5px;padding:20px;box-shadow:0 2px 4px rgba(0,0,0,0.05);}}
            table.dataTable thead th {{background-color: #f1f3f5; color: #495057; border-bottom: 2px solid #dee2e6;}}
            table.dataTable tbody tr:nth-of-type(odd) {{background-color: #f8f9fa;}}
            table.dataTable tfoot th {{background-color: #e9ecef; color: #212529; font-weight: bold; border-top: 2px solid #dee2e6;}}
            .val-pos {{color: #198754; font-weight: 600;}}
        </style>
    </head>
    <body>
        <div class='bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm'>
            <div class='max-w-7xl mx-auto px-4 py-3 flex justify-between items-center'>
                <div>
                    <h1 class='text-2xl font-bold text-gray-800'><i class="fa-solid fa-file-invoice-dollar mr-2 text-blue-600"></i>Relatório de Repasse Médico</h1>
                    <p class='text-sm text-gray-500'>Competência {comp_label} - HBSH</p>
                </div>
                <div class='text-right bg-green-50 px-4 py-2 rounded border border-green-100'><div class='text-sm text-green-600 font-bold uppercase'>Total Geral</div><div class='text-2xl font-bold text-green-700'>R$ {total_geral_final:,.2f}</div></div>
            </div>
            <div class='max-w-7xl mx-auto px-4 flex gap-2 mt-2'>
                <div onclick="verTab('geral')" id='btn-geral' class='tab-btn active'><i class="fa-solid fa-list mr-2"></i>Resumo Geral</div>
                <div onclick="verTab('rateio')" id='btn-rateio' class='tab-btn'><i class="fa-solid fa-users mr-2"></i>Rateio (Pool)</div>
                <div onclick="verTab('indiv')" id='btn-indiv' class='tab-btn'><i class="fa-solid fa-user-doctor mr-2"></i>Produção Individual</div>
            </div>
        </div>
        <main class='max-w-7xl mx-auto px-4 py-6'>
            <div id='tab-geral' class='view-tab tab-container'>
                <table id='tbl-geral' class='display w-full text-sm' style="width:100%">
                    <thead><tr><th>Prestador / Médico</th><th class='text-right'>Vl. Rateio</th><th class='text-right'>Vl. Individual</th><th class='text-right'>Total Final</th></tr></thead>
                    <tbody>
    """
    for _, r in df_geral.iterrows():
        html += f"<tr><td class='font-medium text-gray-700'>{r['Prestador']}</td><td class='text-right'>R$ {r['Vl_Rateio']:,.2f}</td><td class='text-right'>R$ {r['Valor_Individual']:,.2f}</td><td class='text-right val-pos'>R$ {r['Total_Final']:,.2f}</td></tr>"
    
    html += f"""</tbody>
                    <tfoot>
                        <tr>
                            <th>TOTAL GERAL</th>
                            <th class="text-right">R$ {total_geral_rateio:,.2f}</th>
                            <th class="text-right">R$ {total_geral_indiv:,.2f}</th>
                            <th class="text-right text-green-800">R$ {total_geral_final:,.2f}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <div id='tab-rateio' class='view-tab hidden tab-container'>
                <div class="mb-4 p-3 bg-blue-50 text-blue-800 rounded border border-blue-100 flex justify-between items-center">
                    <span><i class="fa-solid fa-info-circle mr-2"></i>Receita Total do Grupo (PDF): <b>R$ {total_bolo:,.2f}</b></span>
                </div>
                <table id='tbl-rateio' class='display w-full text-sm' style="width:100%">
                    <thead><tr><th>Prestador</th><th class="text-center">Peso/Vínculo</th><th class='text-right'>Valor Rateio</th></tr></thead>
                    <tbody>"""
    if 'valor_rateio' in df_rateio.columns:
        for _, r in df_rateio.iterrows():
            html += f"<tr><td>{r['prestador']}</td><td class='text-center'>{r['vinculo']}</td><td class='text-right font-bold text-gray-700'>R$ {r['valor_rateio']:,.2f}</td></tr>"
    
    html += f"""</tbody>
                    <tfoot>
                        <tr>
                            <th>TOTAL RATEIO</th>
                            <th>-</th>
                            <th class="text-right text-blue-800">R$ {total_rateio_val:,.2f}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <div id='tab-indiv' class='view-tab hidden tab-container'>
                <div class="mb-4 p-3 bg-yellow-50 text-yellow-800 rounded border border-yellow-100">
                    <i class="fa-solid fa-filter mr-2"></i>Itens filtrados (Rateio, Diárias, Consultas).
                </div>
                <table id='tbl-indiv' class='display w-full text-sm' style="width:100%">
                    <thead><tr><th>Prestador</th><th>Procedimento / Cód.</th><th class='text-right'>Valor</th></tr></thead>
                    <tbody>"""
    if not df_ind_det.empty:
        for _, r in df_ind_det.iterrows():
            html += f"<tr><td>{r['Prestador']}</td><td>{r['Procedimento']}</td><td class='text-right'>R$ {r['Valor_Individual']:,.2f}</td></tr>"

    html += f"""</tbody>
                    <tfoot>
                        <tr>
                            <th>TOTAL INDIVIDUAL</th>
                            <th>-</th>
                            <th class="text-right text-yellow-800">R$ {total_indiv_val:,.2f}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </main>
        <script>
            $(document).ready(function() {{ 
                var conf = {{ 
                    language: {{url:'//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json'}}, 
                    dom: 'Bfrtip', 
                    buttons: [
                        'excel', 
                        {{
                            extend: 'print',
                            title: 'Relatório de Repasse Médico - Competência {comp_label}',
                            footer: true,
                            customize: function ( win ) {{
                                $(win.document.body).find('h1').css('text-align', 'center');
                            }}
                        }}
                    ],
                    pageLength: 50 
                }};
                $('#tbl-geral, #tbl-rateio, #tbl-indiv').DataTable(conf); 
            }});
            function verTab(id){{ $('.view-tab').addClass('hidden'); $('#tab-'+id).removeClass('hidden'); $('.tab-btn').removeClass('active'); $('#btn-'+id).addClass('active'); }}
        </script>
    </body></html>
    """
    
    with open(caminho_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Sucesso! Relatório gerado: {nome_html}")
    
    reg = {
        "titulo": f"Repasse {comp_label}",
        "competencia": comp_label,
        "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "valor_total": f"R$ {total_geral_final:,.2f}",
        "arquivo": nome_html 
    }
    atualizar_portal(reg)

if __name__ == "__main__":
    bolo, bl, df_r = processar_rateio()
    if not df_r.empty:
        # Extrai a lista oficial de nomes do CSV para usar na correção
        lista_oficial_nomes = df_r['prestador'].unique().tolist() if 'prestador' in df_r.columns else []
        df_ind_res, df_ind_det = processar_individual(bl, lista_oficial_nomes)
        
        gerar_html(df_r, df_ind_res, df_ind_det, bolo)
    else: print("Erro: Não foi possível processar o rateio.")