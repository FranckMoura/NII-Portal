import pdfplumber
import glob
import os
import re
import calendar
import json
import sys

print("--- 📊 GERADOR DE DADOS PARA O PORTAL (FINAL) ---")

# 1. Configura Navegação de Pastas
caminho_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(caminho_script)

# 2. Definição de Leitos Fixos (Sua validação)
LEITOS_FIXOS = {
    "01/2025": 328, "02/2025": 326, "03/2025": 326, "04/2025": 326,
    "05/2025": 326, "06/2025": 326, "07/2025": 326, "08/2025": 326,
    "09/2025": 326, "10/2025": 326, "11/2025": 326, "12/2025": 326
}

arquivos = glob.glob("R_EST_HOSPITALAR*.pdf")
dados_consolidados = []

if not arquivos:
    print("❌ Nenhum PDF encontrado na pasta indicadores.")
    sys.exit()

def ler_numero(txt):
    if not txt: return 0.0
    try: return float(txt.replace('.', '').replace(',', '.'))
    except: return 0.0

for arquivo in arquivos:
    print(f"Processando: {os.path.basename(arquivo)}...")
    
    # Variáveis Acumuladoras
    soma_intern = 0
    soma_altas = 0
    soma_obitos = 0
    soma_pac_dia = 0
    lista_media_perm = []
    
    periodo_txt = "Desconhecido"
    mes_num = 0
    ano_num = 0

    with pdfplumber.open(arquivo) as pdf:
        # Tenta pegar a data
        texto_pag1 = pdf.pages[0].extract_text()
        match_data = re.search(r'Período de \d{2}/(\d{2})/(\d{4})', texto_pag1)
        
        if match_data:
            mes_num = int(match_data.group(1))
            ano_num = int(match_data.group(2))
            periodo_txt = f"{mes_num:02d}/{ano_num}"
        else:
            # Fallback (pegar do nome do arquivo)
            try:
                nums = re.findall(r'\d+', arquivo)[0]
                mes_num = int(nums[:2])
                ano_num = 2000 + int(nums[2:])
                periodo_txt = f"{mes_num:02d}/{ano_num}"
            except: pass

        # Varre as páginas
        for page in pdf.pages:
            linhas = page.extract_text().split('\n')
            for linha in linhas:
                if "Unidade" in linha or "Entradas" in linha: continue
                if "LEITO EXTRA" in linha: continue # Ignora leito extra para manter a base fixa

                partes = linha.split()
                # Verifica se é linha de dados (termina com número)
                if len(partes) > 8 and partes[-1].replace(',','').replace('.','').isdigit():
                    try:
                        # Extrai todos os números da linha
                        numeros = [ler_numero(p) for p in partes if re.match(r'^\d+([.,]\d+)?$', p)]
                        
                        # Estrutura padrão do SoulMV (quando tem todas as colunas)
                        # [SaldoAnt, Intern(1), TransfDe, Altas(3), TransfPara, Obitos(5), ..., MediaPerm(-4), ..., PacDia(-1)]
                        if len(numeros) >= 8:
                            # Pega os dados básicos
                            soma_intern += numeros[1]
                            soma_altas += numeros[3]
                            soma_obitos += numeros[5]
                            
                            # Pega Pac/Dia (geralmente o último) e Media Perm (4º do fim)
                            pac_dia = numeros[-1]
                            media_perm = numeros[-4]
                            
                            soma_pac_dia += pac_dia
                            if media_perm > 0: lista_media_perm.append(media_perm)
                    except: pass

    # --- CÁLCULOS FINAIS DO MÊS ---
    
    # 1. Taxa de Ocupação (Fórmula Precisa)
    taxa_ocupacao = 0.0
    if periodo_txt in LEITOS_FIXOS:
        leitos = LEITOS_FIXOS[periodo_txt]
        dias_mes = calendar.monthrange(ano_num, mes_num)[1]
        capacidade = leitos * dias_mes
        if capacidade > 0:
            taxa_ocupacao = (soma_pac_dia / capacidade) * 100

    # 2. Média de Permanência Geral (Média Simples das Unidades)
    media_perm_geral = sum(lista_media_perm) / len(lista_media_perm) if lista_media_perm else 0

    dados_consolidados.append({
        "periodo": periodo_txt,
        "internacoes": int(soma_intern),
        "altas": int(soma_altas),
        "obitos": int(soma_obitos),
        "taxa_ocupacao": round(taxa_ocupacao, 2), # O valor exato que calculamos
        "media_permanencia": round(media_perm_geral, 2),
        "leitos_ativos": LEITOS_FIXOS.get(periodo_txt, 0) # Para referência futura
    })

# Ordenação Cronológica
dados_consolidados.sort(key=lambda x: x['periodo'].split('/')[1] + x['periodo'].split('/')[0])

# Salvar no local correto para o Portal
pasta_raiz = os.path.dirname(caminho_script)
pasta_destino = os.path.join(pasta_raiz, "arquivos")

if not os.path.exists(pasta_destino):
    os.makedirs(pasta_destino)

caminho_final = os.path.join(pasta_destino, "dados_estatistica.json")

with open(caminho_final, "w", encoding="utf-8") as f:
    json.dump(dados_consolidados, f, indent=4)

print("\n" + "="*50)
print("✅ DADOS GERADOS COM SUCESSO!")
print(f"📂 Arquivo salvo em: {caminho_final}")
print("="*50)
print("👉 Agora abra o 'indicadores.html' no navegador.")