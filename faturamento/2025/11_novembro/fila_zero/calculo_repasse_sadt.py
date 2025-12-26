# ==============================================================================
# SISTEMA DE REPASSES SADT / TERCEIROS - NII PORTAL
# Autor: Franck Moura (Via NII Automation)
# Data: 2025-04-10
# Descrição: Processa o relatório de lançamentos (SADT), gera dashboard HTML
#            e atualiza o Portal automaticamente.
# ==============================================================================

import pdfplumber
import pandas as pd
import os
import re
import json
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Tenta encontrar o arquivo PDF de lançamentos automaticamente
arquivos_pdf = [f for f in os.listdir(PASTA_SCRIPT) if f.startswith('R_PROC_LANCAMENTOS') and f.endswith('.pdf')]
if arquivos_pdf:
    ARQUIVO_PDF_ENTRADA = os.path.join(PASTA_SCRIPT, arquivos_pdf[0])
else:
    # Fallback para o nome padrão se não achar automático
    ARQUIVO_PDF_ENTRADA = os.path.join(PASTA_SCRIPT, 'R_PROC_LANCAMENTOS_102025.pdf')

print(f"--- Processando SADT na pasta: {os.path.basename(PASTA_SCRIPT)} ---")
print(f"Arquivo alvo: {os.path.basename(ARQUIVO_PDF_ENTRADA)}")

# ==============================================================================
# 2. FUNÇÕES UTILITÁRIAS
# ==============================================================================

def encontrar_arquivo_json_portal():
    nome_json = 'dados_financeiro.json'
    diretorio_atual = PASTA_SCRIPT
    for _ in range(5):
        caminho_teste = os.path.join(diretorio_atual, nome_json)
        if os.path.exists(caminho_teste):
            return caminho_teste
        pai = os.path.dirname(diretorio_atual)
        if pai == diretorio_atual: break
        diretorio_atual = pai
    return None

def limpar_valor_monetario(valor_str):
    if not valor_str: return 0.0
    v = valor_str.replace('"', '').replace("'", "").strip()
    try:
        if ',' in v: v = v.replace('.', '').replace(',', '.')
        elif v.count('.') == 1: pass
        return float(v)
    except: return 0.0

def extrair_competencia(nome_arquivo):
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo, re.IGNORECASE)
    if match:
        mes, ano_curto = match.groups()
        return f"{mes}/20{ano_curto}", f"{mes}20{ano_curto}"
    return datetime.now().strftime("%m/%Y"), datetime.now().strftime("%m%Y")

# ==============================================================================
# 3. PROCESSAMENTO DO PDF
# ==============================================================================

def processar_pdf_sadt(caminho_pdf):
    if not os.path.exists(caminho_pdf):
        print("[ERRO] Arquivo PDF não encontrado.")
        return pd.DataFrame()

    dados = []
    
    # Variáveis de Estado
    grupo_atual = "GERAL"
    prestador_atual = "DESCONHECIDO"
    
    # Regex Patterns
    # Captura "123 NOME DO PRESTADOR"
    regex_prestador = re.compile(r'^"?\d+\s+([A-Z\s\.\-]+)"?') 
    # Captura código SUS (0202...)
    regex_cod = re.compile(r'\b(\d{8,10})\b')
    # Captura Grupo
    regex_grupo = re.compile(r'Grupo Procedimento:\s*(.*)', re.IGNORECASE)

    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                line = line.strip()
                if not line: continue
                
                # 1. Identifica Grupo
                match_grupo = regex_grupo.search(line)
                if match_grupo:
                    raw_grupo = match_grupo.group(1).replace('"','').replace(',','').strip()
                    if raw_grupo: grupo_atual = raw_grupo
                    continue

                # 2. Identifica Prestador (Geralmente começa com um código numérico curto)
                # Ex: "677 LABORATORIO SANTA HELENA"
                # Cuidado: Às vezes o procedimento também começa com número, mas é longo (8-10 digitos)
                # O código do prestador costuma ser pequeno (1-4 digitos)
                parts = line.split()
                if parts and parts[0].isdigit() and len(parts[0]) < 6:
                    # É provável que seja um prestador
                    # Mas verifique se não é um falso positivo (ex: dia do mês)
                    match_p = regex_prestador.match(line)
                    if match_p:
                        potencial_prestador = match_p.group(1).strip()
                        # Filtra palavras que não são prestadores
                        if "TOTAL" not in potencial_prestador and "PÁGINA" not in potencial_prestador:
                            prestador_atual = potencial_prestador
                
                # 3. Identifica Procedimento e Valor
                # Procura por linhas que tenham valor monetário no final
                if re.search(r'\d+,\d{2}$', line):
                    # Filtros de exclusão (Diárias, Totais)
                    linha_upper = line.upper()
                    if "TOTAL" in linha_upper or "DIARIA" in linha_upper or "DIÁRIA" in linha_upper:
                        continue
                    
                    # Tenta achar código do procedimento
                    match_c = regex_cod.search(line)
                    cod_proc = match_c.group(1) if match_c else "N/D"
                    
                    # Extrai Valor (último token)
                    try:
                        partes = line.split()
                        valor_str = partes[-1]
                        valor = limpar_valor_monetario(valor_str)
                        
                        # Extrai Qtd (penúltimo token, geralmente)
                        qtd = 1
                        if len(partes) >= 2 and partes[-2].isdigit():
                            qtd = int(partes[-2])
                        
                        if valor > 0:
                            # Limpeza do nome do procedimento (remove o código e o valor)
                            desc = line
                            if cod_proc != "N/D": desc = desc.replace(cod_proc, "")
                            desc = desc.replace(valor_str, "")
                            desc = re.sub(r'\d+$', '', desc.strip()) # Remove qtd do final se sobrou
                            
                            dados.append({
                                'Grupo': grupo_atual,
                                'Prestador': prestador_atual,
                                'Codigo': cod_proc,
                                'Procedimento': desc.strip()[:50],
                                'Qtd': qtd,
                                'Valor': valor
                            })
                    except: pass

    return pd.DataFrame(dados)

# ==============================================================================
# 4. ATUALIZAÇÃO DO JSON
# ==============================================================================

def atualizar_portal(novo_registro):
    caminho_json = encontrar_arquivo_json_portal()
    if not caminho_json:
        print("[AVISO] JSON do portal não encontrado. Verifique a estrutura de pastas.")
        return

    # Caminho relativo para web
    rel_path = os.path.relpath(os.path.join(PASTA_SCRIPT, novo_registro['arquivo']), os.path.dirname(caminho_json))
    novo_registro['arquivo'] = rel_path.replace(os.sep, '/')
    
    dados = []
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except: pass

    # Remove duplicados e adiciona novo
    dados = [d for d in dados if d['arquivo'] != novo_registro['arquivo']]
    dados.append(novo_registro)
    
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    print("   -> Portal atualizado!")

# ==============================================================================
# 5. GERAÇÃO HTML
# ==============================================================================

def gerar_html(df, nome_arquivo_saida, competencia_label):
    if df.empty:
        print("[AVISO] DataFrame vazio. Nada para gerar.")
        return

    # Agrupamentos
    total_geral = df['Valor'].sum()
    
    # Resumo por Prestador
    df_prestador = df.groupby('Prestador').agg(
        Qtd=('Qtd', 'sum'),
        Valor=('Valor', 'sum')
    ).reset_index().sort_values('Valor', ascending=False)
    
    # HTML
    html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head>
        <meta charset='UTF-8'>
        <title>SADT {competencia_label}</title>
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
            body{{background-color:#f3f4f6;font-family:'Segoe UI', sans-serif;}}
            .tab-btn{{padding:10px 20px;cursor:pointer;border-bottom:3px solid transparent;font-weight:600;color:#6b7280;}}
            .tab-btn.active{{border-color:#2563eb;color:#2563eb;background:white;border-radius:8px 8px 0 0;}}
            .dataTables_wrapper .dataTables_filter input {{border: 1px solid #d1d5db; border-radius: 4px; padding: 4px;}}
        </style>
    </head>
    <body>
        <div class='bg-white shadow sticky top-0 z-50'>
            <div class='max-w-7xl mx-auto px-4 py-4 flex justify-between items-center'>
                <div class="flex items-center gap-3">
                    <div class="bg-indigo-600 text-white p-2 rounded"><i class="fa-solid fa-flask"></i></div>
                    <div><h1 class='text-xl font-bold text-gray-800'>Repasse SADT / Terceiros</h1><p class='text-sm text-gray-500'>Competência: {competencia_label}</p></div>
                </div>
                <div class='text-right'>
                    <div class='text-2xl font-bold text-indigo-700'>R$ {total_geral:,.2f}</div>
                    <div class='text-xs text-gray-500'>Total Produção</div>
                </div>
            </div>
            <div class='max-w-7xl mx-auto px-4 flex gap-2 mt-2'>
                <div onclick="verTab('resumo')" id='btn-resumo' class='tab-btn active'>Resumo por Prestador</div>
                <div onclick="verTab('detalhe')" id='btn-detalhe' class='tab-btn'>Detalhamento Completo</div>
            </div>
        </div>

        <main class='max-w-7xl mx-auto px-4 py-6'>
            <!-- ABA RESUMO -->
            <div id='tab-resumo' class='view-tab bg-white rounded shadow p-6'>
                <table id='tbl-resumo' class='w-full text-sm text-left display' style="width:100%">
                    <thead class='bg-gray-50 uppercase text-xs font-bold text-gray-600'>
                        <tr><th>Prestador</th><th class='text-right'>Qtd Itens</th><th class='text-right'>Valor Total</th></tr>
                    </thead>
                    <tbody>
    """
    for _, r in df_prestador.iterrows():
        html += f"<tr class='border-b hover:bg-gray-50'><td class='py-3 font-medium'>{r['Prestador']}</td><td class='text-right'>{r['Qtd']}</td><td class='text-right font-bold text-indigo-700'>R$ {r['Valor']:,.2f}</td></tr>"
    
    html += f"""
                    </tbody>
                    <tfoot>
                        <tr class="font-bold bg-gray-100"><td class="py-3">TOTAL GERAL</td><td class="text-right">{df_prestador['Qtd'].sum()}</td><td class="text-right text-indigo-800">R$ {total_geral:,.2f}</td></tr>
                    </tfoot>
                </table>
            </div>

            <!-- ABA DETALHE -->
            <div id='tab-detalhe' class='view-tab hidden bg-white rounded shadow p-6'>
                <table id='tbl-detalhe' class='w-full text-sm text-left display' style="width:100%">
                    <thead class='bg-gray-50 uppercase text-xs font-bold text-gray-600'>
                        <tr><th>Grupo</th><th>Prestador</th><th>Procedimento</th><th class='text-right'>Valor</th></tr>
                    </thead>
                    <tbody>
    """
    for _, r in df.iterrows():
        html += f"<tr class='border-b hover:bg-gray-50'><td class='text-xs text-gray-500'>{r['Grupo']}</td><td class='font-medium'>{r['Prestador']}</td><td>{r['Procedimento']}</td><td class='text-right'>R$ {r['Valor']:,.2f}</td></tr>"

    html += """
                    </tbody>
                </table>
            </div>
        </main>

        <script>
            $(document).ready(function() { 
                var conf = { 
                    language: {url:'//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json'}, 
                    dom: 'Bfrtip', buttons: ['excel', 'print'], pageLength: 25 
                };
                $('#tbl-resumo').DataTable(conf); 
                $('#tbl-detalhe').DataTable(conf); 
            });
            function verTab(id){ 
                $('.view-tab').addClass('hidden'); 
                $('#tab-'+id).removeClass('hidden'); 
                $('.tab-btn').removeClass('active'); 
                $('#btn-'+id).addClass('active'); 
            }
        </script>
    </body></html>
    """
    
    with open(nome_arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Sucesso! Relatório gerado: {os.path.basename(nome_arquivo_saida)}")

# ==============================================================================
# 6. EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    df_sadt = processar_pdf_sadt(ARQUIVO_PDF_ENTRADA)
    
    if not df_sadt.empty:
        comp_label, comp_sufixo = extrair_competencia(os.path.basename(ARQUIVO_PDF_ENTRADA))
        nome_html = os.path.join(PASTA_SCRIPT, f"relatorio_sadt_{comp_sufixo}.html")
        
        gerar_html(df_sadt, nome_html, comp_label)
        
        # Atualiza Portal
        reg = {
            "titulo": f"Repasse SADT - {comp_label}",
            "competencia": comp_label,
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "valor_total": f"R$ {df_sadt['Valor'].sum():,.2f}",
            "arquivo": nome_html
        }
        atualizar_portal(reg)
    else:
        print("Não foram encontrados dados no arquivo PDF.")