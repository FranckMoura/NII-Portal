# ==============================================================================
# SISTEMA INTEGRADO DE REPASSES MÉDICOS - NII PORTAL
# Autor: Franck Moura (Via NII Automation)
# Data: 2025-04-10
# Descrição: Processa Rateio + Individual e atualiza o Portal automaticamente.
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÕES AUTOMÁTICAS
# ==============================================================================
# Pasta onde este script está salvo (ex: .../10_outubro)
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Arquivos de Entrada (Devem estar na mesma pasta do script)
ARQUIVO_PDF_RATEIO_RECEITA = os.path.join(PASTA_SCRIPT, 'R_RECEITA_PROCEDIMENTO_RATEIO_1025.pdf')
ARQUIVO_PDF_PRODUCAO_CONTA = os.path.join(PASTA_SCRIPT, 'R_PRODUCAO_MEDICA_CONTA_1025.pdf')
ARQUIVO_CSV_VINCULOS = os.path.join(PASTA_SCRIPT, 'vinculos.csv')

print(f"--- Iniciando Processamento na pasta: {os.path.basename(PASTA_SCRIPT)} ---")

# ==============================================================================
# 2. FUNÇÕES DE BUSCA E UTILITÁRIOS
# ==============================================================================

def encontrar_arquivo_json_portal():
    """
    Procura o arquivo 'dados_financeiro.json' subindo os diretórios.
    Retorna o caminho absoluto do JSON e o caminho relativo da pasta atual até ele.
    """
    nome_json = 'dados_financeiro.json'
    diretorio_atual = PASTA_SCRIPT
    
    # Sobe até 5 níveis de pasta procurando o arquivo
    for _ in range(5):
        caminho_teste = os.path.join(diretorio_atual, nome_json)
        if os.path.exists(caminho_teste):
            return caminho_teste, diretorio_atual
        
        pai = os.path.dirname(diretorio_atual)
        if pai == diretorio_atual: # Chegou na raiz do disco
            break
        diretorio_atual = pai
            
    return None, None

def limpar_valor_monetario(valor_str):
    if not valor_str: return 0.0
    v = valor_str.replace('"', '').replace("'", "").strip()
    try:
        if ',' in v:
            v = v.replace('.', '').replace(',', '.')
        elif v.count('.') == 1:
            pass
        return float(v)
    except:
        return 0.0

def extrair_competencia_do_nome(nome_arquivo):
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo, re.IGNORECASE)
    if match:
        mes, ano_curto = match.groups()
        return f"{mes}/20{ano_curto}", f"{mes}20{ano_curto}"
    agora = datetime.now()
    return agora.strftime("%m/%Y"), agora.strftime("%m%Y")

# ==============================================================================
# 3. PROCESSAMENTO (MOTOR DE CÁLCULO)
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
                    # Extrai código e valor
                    cod = re.match(r'^"?(\d{8,10})"?', line.strip()).group(1)
                    codigos_rateio.add(cod)
                    valores = re.findall(r'"?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"?', line)
                    if len(valores) >= 2:
                        total_bolo_sp += limpar_valor_monetario(valores[-2])

    print(f"   -> Receita Total: R$ {total_bolo_sp:,.2f}")

    df_vinculos = pd.DataFrame()
    if os.path.exists(ARQUIVO_CSV_VINCULOS):
        try:
            df_vinculos = pd.read_csv(ARQUIVO_CSV_VINCULOS, sep=';', encoding='latin1')
            df_vinculos.columns = [c.lower().strip() for c in df_vinculos.columns]
            # Limpeza de formato numérico brasileiro (vírgula)
            if df_vinculos['vinculo'].dtype == object:
                 df_vinculos['vinculo'] = df_vinculos['vinculo'].astype(str).str.replace(',', '.').astype(float)
            
            total_pesos = df_vinculos['vinculo'].sum()
            if total_pesos > 0:
                valor_ponto = total_bolo_sp / total_pesos
                df_vinculos['valor_rateio'] = df_vinculos['vinculo'] * valor_ponto
            else:
                df_vinculos['valor_rateio'] = 0.0
        except Exception as e:
            print(f"[ERRO] CSV Vínculos: {e}")
    
    return total_bolo_sp, codigos_rateio, df_vinculos

def processar_individual(codigos_blacklist):
    print(f"2. Processando Produção Individual...")
    if not os.path.exists(ARQUIVO_PDF_PRODUCAO_CONTA):
        print(f"[ERRO] Arquivo não encontrado: {os.path.basename(ARQUIVO_PDF_PRODUCAO_CONTA)}")
        return pd.DataFrame(), pd.DataFrame()

    dados = []
    prestador_atual = "DESCONHECIDO"
    regex_prestador = re.compile(r'^([A-Z\s\.]+)\s+\(\d+\)$')
    regex_cod = re.compile(r'\b(\d{10})\b')

    with pdfplumber.open(ARQUIVO_PDF_PRODUCAO_CONTA) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                line = line.strip()
                match_prest = regex_prestador.match(line)
                if match_prest and "HOSPITAL" not in line:
                    prestador_atual = match_prest.group(1).strip()
                    continue
                
                if re.search(r'\d+,\d{2}$', line):
                    match_c = regex_cod.search(line)
                    cod_enc = match_c.group(1) if match_c else None
                    
                    try:
                        val_str = line.split()[-1]
                        valor = limpar_valor_monetario(val_str)
                        if valor > 0 and prestador_atual != "DESCONHECIDO":
                            if not (cod_enc and cod_enc in codigos_blacklist):
                                dados.append({
                                    'Prestador': prestador_atual,
                                    'Procedimento': cod_enc or "N/D",
                                    'Valor_Individual': valor,
                                    'Detalhes': line[:60]
                                })
                    except: pass
    
    df = pd.DataFrame(dados)
    if not df.empty:
        df_agrup = df.groupby('Prestador')['Valor_Individual'].sum().reset_index()
        return df_agrup, df
    return pd.DataFrame(), pd.DataFrame()

# ==============================================================================
# 4. ATUALIZAÇÃO DO JSON DO PORTAL
# ==============================================================================

def atualizar_portal(novo_registro):
    caminho_json, pasta_raiz = encontrar_arquivo_json_portal()
    
    if not caminho_json:
        print("[AVISO] Arquivo 'dados_financeiro.json' não encontrado nas pastas acima.")
        print("Certifique-se de que ele existe na raiz do projeto NII-Portal.")
        return

    # Calcular o caminho relativo para o link funcionar no HTML
    # Ex: se o JSON está em /Portal e o HTML em /Portal/Fat/2025/10, o link é Fat/2025/10/relatorio.html
    rel_path = os.path.relpath(os.path.join(PASTA_SCRIPT, novo_registro['arquivo']), os.path.dirname(caminho_json))
    # Corrige barras para funcionar na web (sempre /)
    novo_registro['arquivo'] = rel_path.replace(os.sep, '/')
    
    print(f"   -> Atualizando base de dados em: {caminho_json}")
    
    dados = []
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except: pass # Se estiver vazio ou corrompido, começa do zero

    # Remove registro anterior desse mesmo arquivo para atualizar
    dados = [d for d in dados if d['arquivo'] != novo_registro['arquivo']]
    dados.append(novo_registro)
    
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    print("   -> Portal atualizado com sucesso!")

# ==============================================================================
# 5. GERAÇÃO HTML E MAIN
# ==============================================================================

def gerar_html(df_rateio, df_ind_res, df_ind_det, total_bolo):
    # Setup de Nomes
    comp_label, comp_sufixo = extrair_competencia_do_nome(os.path.basename(ARQUIVO_PDF_RATEIO_RECEITA))
    nome_html = f"relatorio_repasse_{comp_sufixo}.html"
    caminho_html = os.path.join(PASTA_SCRIPT, nome_html)
    
    # Merge de Dados
    df_rateio['chave'] = df_rateio['prestador'].str.upper().str.strip()
    df_geral = df_rateio.rename(columns={'valor_rateio': 'Vl_Rateio', 'prestador': 'Prestador'})
    
    if not df_ind_res.empty:
        df_ind_res['chave'] = df_ind_res['Prestador'].str.upper().str.strip()
        df_geral = pd.merge(df_geral, df_ind_res[['chave', 'Valor_Individual']], on='chave', how='outer')
    else: df_geral['Valor_Individual'] = 0.0
    
    df_geral['Vl_Rateio'] = df_geral['Vl_Rateio'].fillna(0)
    df_geral['Valor_Individual'] = df_geral['Valor_Individual'].fillna(0)
    df_geral['Total_Final'] = df_geral['Vl_Rateio'] + df_geral['Valor_Individual']
    df_geral['Prestador'] = df_geral['Prestador'].fillna(df_geral['chave'])
    df_geral = df_geral.sort_values('Prestador')
    
    total_pagar = df_geral['Total_Final'].sum()
    
    # HTML Simplificado
    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <title>Repasse {comp_label}</title>
        <script src='https://cdn.tailwindcss.com'></script>
        <link href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css' rel='stylesheet'>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
        <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
        <style>body{{background-color:#f3f4f6;font-family:sans-serif}}.tab-btn{{padding:10px 20px;cursor:pointer;border-bottom:2px solid transparent}}.tab-btn.active{{border-color:#2563eb;color:#2563eb;font-weight:bold}}</style>
    </head>
    <body>
        <div class='bg-white shadow sticky top-0 z-50'>
            <div class='max-w-7xl mx-auto px-4 py-4 flex justify-between items-center'>
                <div><h1 class='text-xl font-bold text-gray-800'>Repasse {comp_label}</h1><p class='text-sm text-gray-500'>HBSH - Faturamento</p></div>
                <div class='text-right'><div class='text-2xl font-bold text-green-600'>R$ {total_pagar:,.2f}</div><div class='text-xs text-gray-500'>Total Geral</div></div>
            </div>
            <div class='max-w-7xl mx-auto px-4 flex gap-4'>
                <div onclick="verTab('geral')" id='btn-geral' class='tab-btn active'>Resumo Geral</div>
                <div onclick="verTab('rateio')" id='btn-rateio' class='tab-btn'>Rateio</div>
                <div onclick="verTab('indiv')" id='btn-indiv' class='tab-btn'>Individual</div>
            </div>
        </div>
        <main class='max-w-7xl mx-auto px-4 py-8'>
            <div id='tab-geral' class='view-tab'>
                <div class='bg-white rounded shadow p-4'>
                    <table id='tbl-geral' class='w-full text-sm text-left'>
                        <thead class='bg-gray-100 uppercase text-xs font-bold'><tr><th>Prestador</th><th class='text-right'>Vl. Rateio</th><th class='text-right'>Vl. Individual</th><th class='text-right'>Total Final</th></tr></thead>
                        <tbody>
    """
    for _, r in df_geral.iterrows():
        html += f"<tr class='border-b hover:bg-gray-50'><td class='py-3 font-medium'>{r['Prestador']}</td><td class='text-right'>R$ {r['Vl_Rateio']:,.2f}</td><td class='text-right'>R$ {r['Valor_Individual']:,.2f}</td><td class='text-right font-bold text-green-700'>R$ {r['Total_Final']:,.2f}</td></tr>"
    
    html += """</tbody></table></div></div>
            <div id='tab-rateio' class='view-tab hidden'><div class='bg-white rounded shadow p-4'><table id='tbl-rateio' class='w-full text-sm'><thead><tr><th>Prestador</th><th>Peso</th><th class='text-right'>Valor</th></tr></thead><tbody>"""
    for _, r in df_rateio.iterrows():
        html += f"<tr><td>{r['prestador']}</td><td>{r['vinculo']}</td><td class='text-right'>R$ {r['valor_rateio']:,.2f}</td></tr>"
    
    html += """</tbody></table></div></div>
            <div id='tab-indiv' class='view-tab hidden'><div class='bg-white rounded shadow p-4'><table id='tbl-indiv' class='w-full text-sm'><thead><tr><th>Prestador</th><th>Procedimento</th><th class='text-right'>Valor</th></tr></thead><tbody>"""
    for _, r in df_ind_det.iterrows():
        html += f"<tr><td>{r['Prestador']}</td><td>{r['Procedimento']}</td><td class='text-right'>R$ {r['Valor_Individual']:,.2f}</td></tr>"

    html += """</tbody></table></div></div>
        </main>
        <script>
            $(document).ready(function() { 
                var conf = { language: {url:'//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json'}, dom: 'Bfrtip', buttons: ['excel', 'print'] };
                $('#tbl-geral, #tbl-rateio, #tbl-indiv').DataTable(conf); 
            });
            function verTab(id){ $('.view-tab').addClass('hidden'); $('#tab-'+id).removeClass('hidden'); $('.tab-btn').removeClass('active'); $('#btn-'+id).addClass('active'); }
        </script>
    </body></html>
    """
    
    with open(caminho_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Sucesso! Relatório gerado: {nome_html}")
    
    # Atualiza Portal
    reg = {
        "titulo": f"Repasse {comp_label}",
        "competencia": comp_label,
        "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "valor_total": f"R$ {total_pagar:,.2f}",
        "arquivo": nome_html # O script já ajusta o caminho relativo
    }
    atualizar_portal(reg)

if __name__ == "__main__":
    bolo, bl, df_r = processar_rateio()
    if not df_r.empty:
        df_ind_res, df_ind_det = processar_individual(bl)
        gerar_html(df_r, df_ind_res, df_ind_det, bolo)
    else: print("Erro: Não foi possível processar o rateio.")