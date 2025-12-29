# ==============================================================================
# GERADOR DE CAPA DE RELATÓRIO (V2.3 - INTEGRADO AO PORTAL)
# Autor: Franck Moura (Via NII Automation)
# Data: 29/12/2025
# Descrição: Gera capa HTML e REGISTRA no painel web (JSON).
# ==============================================================================

import os
import glob
import re
import json
from datetime import datetime

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURAÇÕES ---
URL_LOGO = "https://franckmoura.github.io/NII-Portal/img/logo.png"
# FORCAR_COMPETENCIA = ("NOVEMBRO/2025", "112025") # Descomente se precisar forçar
FORCAR_COMPETENCIA = None

# ==============================================================================
# 1. DESCOBRIR COMPETÊNCIA
# ==============================================================================
def descobrir_competencia():
    if FORCAR_COMPETENCIA: return FORCAR_COMPETENCIA
    
    pdfs = glob.glob(os.path.join(PASTA_SCRIPT, '*.pdf'))
    for pdf in pdfs:
        match = re.search(r'_(\d{2})(\d{2})\.pdf', pdf)
        if match:
            mes, ano = match.groups()
            meses = {'01': 'JANEIRO', '02': 'FEVEREIRO', '03': 'MARÇO', '04': 'ABRIL', '05': 'MAIO', '06': 'JUNHO', '07': 'JULHO', '08': 'AGOSTO', '09': 'SETEMBRO', '10': 'OUTUBRO', '11': 'NOVEMBRO', '12': 'DEZEMBRO'}
            return f"{meses.get(mes, 'MÊS')}/{2000 + int(ano)}", f"{mes}{2000 + int(ano)}"
    
    agora = datetime.now()
    meses_pt = ['', 'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
    return f"{meses_pt[agora.month]}/{agora.year}", f"{agora.month:02d}{agora.year}"

nome_mes_ano, sufixo_arquivo = descobrir_competencia()

# ==============================================================================
# 2. GERAÇÃO HTML (CAPA)
# ==============================================================================
html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Capa - {nome_mes_ano}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap');
        body {{ margin: 0; padding: 0; font-family: 'Roboto', sans-serif; background-color: white; height: 100vh; display: flex; flex-direction: column; justify-content: space-between; align-items: center; text-align: center; }}
        .top-bar {{ width: 100%; height: 15px; background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); }}
        .content {{ flex-grow: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; width: 85%; }}
        .logo-container {{ margin-bottom: 50px; height: 120px; display: flex; align-items: center; justify-content: center; }}
        .logo-img {{ max-height: 100%; max-width: 450px; object-fit: contain; }}
        h2 {{ font-size: 22px; font-weight: 400; letter-spacing: 3px; color: #555; margin: 0; text-transform: uppercase; }}
        h1 {{ font-size: 42px; font-weight: 900; color: #1e3a8a; margin: 30px 0; line-height: 1.2; text-transform: uppercase; }}
        .divider {{ width: 120px; height: 5px; background: #3b82f6; margin: 20px auto; border-radius: 3px; }}
        .subtitle {{ font-size: 24px; color: #3b82f6; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; }}
        .competencia-box {{ margin-top: 50px; border: 2px solid #e5e7eb; padding: 25px 80px; border-radius: 8px; background-color: #f8fafc; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .competencia-label {{ font-size: 14px; color: #64748b; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px; font-weight: bold; }}
        .competencia-value {{ font-size: 42px; font-weight: 900; color: #1e293b; }}
        .footer {{ width: 100%; background-color: #f1f5f9; padding: 40px 0; border-top: 4px solid #1e3a8a; }}
        .dept-title {{ font-weight: 900; color: #1e3a8a; font-size: 16px; margin-bottom: 15px; letter-spacing: 1px; }}
        .name {{ font-size: 18px; font-weight: 700; color: #0f172a; margin: 0; }}
        .role {{ font-size: 14px; color: #64748b; margin: 2px 0 0 0; text-transform: uppercase; }}
        .location {{ margin-top: 30px; font-size: 12px; color: #94a3b8; }}
        @media print {{ @page {{ size: A4 portrait; margin: 0; }} body {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }} .no-print {{ display: none; }} }}
    </style>
</head>
<body>
    <div class="top-bar"></div>
    <div class="content">
        <div class="logo-container"><img src="{URL_LOGO}" alt="Logo" class="logo-img"></div>
        <h2>Hospital Beneficente Santa Helena</h2>
        <h1>Relatório Gerencial<br>de Faturamento e Produção Hospitalar</h1>
        <div class="divider"></div>
        <div class="subtitle">Convênio SUS</div>
        <div class="competencia-box">
            <div class="competencia-label">Competência</div>
            <div class="competencia-value">{nome_mes_ano}</div>
        </div>
    </div>
    <div class="footer">
        <div class="footer-content">
            <div class="dept-title">DEPARTAMENTO DE FATURAMENTO</div>
            <div class="signature-block">
                <p class="name">Franck Moura</p>
                <p class="role">Coordenador de Faturamento - SUS</p>
            </div>
            <div class="location">Cuiabá - Mato Grosso | Gerado em: {datetime.now().strftime("%d/%m/%Y")}</div>
        </div>
    </div>
    <div class="no-print" style="position: fixed; bottom: 30px; right: 30px;">
        <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 15px 25px; border-radius: 50px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 10px rgba(37,99,235,0.3); display: flex; align-items: center; gap: 10px;">
            <i class="fa-solid fa-print"></i> IMPRIMIR CAPA
        </button>
    </div>
</body>
</html>
"""

nome_arquivo = os.path.join(PASTA_SCRIPT, f"capa_relatorio_{sufixo_arquivo}.html")
with open(nome_arquivo, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ Capa HTML gerada: {os.path.basename(nome_arquivo)}")

# ==============================================================================
# 3. ATUALIZAÇÃO DO PORTAL (JSON)
# ==============================================================================
def atualizar_portal(novo_registro):
    caminho_atual = PASTA_SCRIPT
    caminho_json = None
    # Procura o JSON subindo pastas
    for _ in range(4):
        teste = os.path.join(caminho_atual, 'arquivos', 'dados_financeiro.json')
        if os.path.exists(teste): caminho_json = teste; break
        caminho_atual = os.path.dirname(caminho_atual)
    
    if not caminho_json: 
        # Fallback fixo se não achar
        caminho_json = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos\dados_financeiro.json"
    
    try:
        if os.path.exists(caminho_json):
            with open(caminho_json, 'r', encoding='utf-8') as f: dados = json.load(f)
        else: dados = []

        # Remove se já existir a capa deste mês
        dados = [d for d in dados if d['titulo'] != novo_registro['titulo']]
        
        # Insere no início
        dados.insert(0, novo_registro)

        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print("   -> Capa registrada no Portal com sucesso!")
    except Exception as e: print(f"❌ Erro ao atualizar JSON: {e}")

# Executa o registro
caminho_web = os.path.relpath(nome_arquivo, r"C:\Users\DELL\OneDrive\NII-Portal-1").replace("\\", "/")
reg = {
    "titulo": f"00. CAPA DO RELATÓRIO - {nome_mes_ano}", # "00" para forçar o topo da lista
    "competencia": nome_mes_ano,
    "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
    "valor_total": "---", # Capa não tem valor monetário
    "arquivo": caminho_web 
}
atualizar_portal(reg)