import pdfplumber
import glob
import os
import re
import calendar

print("--- 📉 CÁLCULO FINAL: TAXA DE OCUPAÇÃO ---")

# Garante que roda na pasta do script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# LEITOS CONFIRMADOS (Conforme sua tabela)
LEITOS_FIXOS = {
    "01/2025": 328,
    "02/2025": 326,
    "03/2025": 326,
    "04/2025": 326,
    "05/2025": 326,
    "06/2025": 326,
    "07/2025": 326,
    "08/2025": 326,
    "09/2025": 326,
    "10/2025": 326,
    "11/2025": 326,
    "12/2025": 326
}

arquivos = glob.glob("R_EST_HOSPITALAR*.pdf")
tabela_final = []

def ler_numero(txt):
    if not txt: return 0.0
    try: return float(txt.replace('.', '').replace(',', '.'))
    except: return 0.0

for arquivo in arquivos:
    with pdfplumber.open(arquivo) as pdf:
        # 1. Identificar Data
        texto_pag1 = pdf.pages[0].extract_text()
        match_data = re.search(r'Período de \d{2}/(\d{2})/(\d{4})', texto_pag1)
        
        if match_data:
            mes_num = int(match_data.group(1))
            ano_num = int(match_data.group(2))
        else:
            # Fallback se não achar data
            try:
                nums = re.findall(r'\d+', arquivo)[0]
                mes_num = int(nums[:2])
                ano_num = 2000 + int(nums[2:])
            except: continue

        chave_mes = f"{mes_num:02d}/{ano_num}"
        
        # 2. Somar Pacientes-Dia (O Numerador da fórmula)
        total_pac_dia = 0
        
        for page in pdf.pages:
            linhas = page.extract_text().split('\n')
            for linha in linhas:
                if "Unidade" in linha or "Entradas" in linha: continue
                
                # Ignora Leito Extra no numerador também, para ser justo com os leitos fixos
                if "LEITO EXTRA" in linha: continue 

                partes = linha.split()
                if len(partes) > 5 and partes[-1].replace(',','').replace('.','').isdigit():
                    try:
                        # O último número da linha geralmente é o Pac/Dia
                        # Ou usamos a lógica de procurar números na linha
                        numeros = [ler_numero(p) for p in partes if re.match(r'^\d+([.,]\d+)?$', p)]
                        
                        if len(numeros) >= 5:
                            # Assumindo que o Pac/Dia é o último valor numérico da estatística
                            pac_dia = numeros[-1]
                            total_pac_dia += pac_dia
                    except: pass
        
        # 3. Aplicar a Fórmula
        if chave_mes in LEITOS_FIXOS:
            leitos_ativos = LEITOS_FIXOS[chave_mes]
            dias_no_mes = calendar.monthrange(ano_num, mes_num)[1]
            
            # Capacidade Máxima (Denominador)
            capacidade_maxima = leitos_ativos * dias_no_mes
            
            # Cálculo da Taxa
            if capacidade_maxima > 0:
                taxa_ocupacao = (total_pac_dia / capacidade_maxima) * 100
            else:
                taxa_ocupacao = 0.0
            
            tabela_final.append({
                "sort": f"{ano_num}-{mes_num:02d}",
                "mes": chave_mes,
                "dias": dias_no_mes,
                "leitos": leitos_ativos,
                "pac_dia": int(total_pac_dia),
                "capacidade": capacidade_maxima,
                "taxa": taxa_ocupacao
            })

# Ordenação e Exibição
tabela_final.sort(key=lambda x: x['sort'])

print("\n" + "="*85)
print(f"{'MÊS':<8} | {'DIAS':<4} | {'LEITOS':<6} | {'CAPACIDADE':<10} | {'PAC/DIA (Real)':<14} | {'% OCUPAÇÃO':<10}")
print("="*85)

for d in tabela_final:
    print(f"{d['mes']:<8} | {d['dias']:<4} | {d['leitos']:<6} | {d['capacidade']:<10} | {d['pac_dia']:<14} | {d['taxa']:>6.2f}%")

print("="*85)
print("Fórmula: (Pac_Dia / (Leitos * Dias)) * 100")