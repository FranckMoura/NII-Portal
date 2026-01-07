import pdfplumber
import glob
import os
import re
import calendar
from datetime import datetime

print("--- 🏥 CÁLCULO DE LEITOS ATIVOS POR MÊS ---")

# Garante que roda na pasta do script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

arquivos = glob.glob("R_EST_HOSPITALAR*.pdf")
resultados = []

def ler_numero(txt):
    """Converte '92,58' para 92.58"""
    if not txt: return 0.0
    try:
        return float(txt.replace('.', '').replace(',', '.'))
    except:
        return 0.0

for arquivo in arquivos:
    with pdfplumber.open(arquivo) as pdf:
        # 1. Descobrir o Mês e Ano do arquivo
        texto_pag1 = pdf.pages[0].extract_text()
        
        # Procura "Período de 01/MM/AAAA"
        match_data = re.search(r'Período de \d{2}/(\d{2})/(\d{4})', texto_pag1)
        
        if match_data:
            mes = int(match_data.group(1))
            ano = int(match_data.group(2))
        else:
            # Tenta pegar do nome do arquivo (ex: 0125 -> 01/2025)
            try:
                nums = re.findall(r'\d+', arquivo)[0]
                mes = int(nums[:2])
                ano = 2000 + int(nums[2:])
            except:
                mes, ano = 1, 2025 # Fallback
        
        # 2. Calcular dias exatos do mês (28, 30 ou 31)
        dias_no_mes = calendar.monthrange(ano, mes)[1]
        
        total_leitos_mes = 0
        detalhes_unidades = []

        # 3. Ler todas as páginas
        for page in pdf.pages:
            linhas = page.extract_text().split('\n')
            for linha in linhas:
                # Filtra linhas de dados (ignora cabeçalhos)
                if "Unidade" in linha or "Entradas" in linha: continue
                
                partes = linha.split()
                # Verifica se tem números suficientes no final
                if len(partes) > 5 and partes[-1].replace(',','').replace('.','').isdigit():
                    try:
                        # Identifica colunas (geralmente fixas no fim)
                        # ... %Ocup(-5), MediaPerm(-4), TaxaMov(-3), TaxaMort(-2), PacDia(-1)
                        
                        pac_dia = ler_numero(partes[-1])
                        ocupacao = ler_numero(partes[-5])
                        
                        # Nome da unidade (tudo antes dos números)
                        # Ex: "UTI ADULTO" ou "2º ANDAR"
                        # Filtra "LEITO EXTRA" se não quiser contar (geralmente não conta como fixo)
                        if "LEITO EXTRA" in linha: continue 

                        if ocupacao > 0:
                            # FÓRMULA: Leitos = PacDia / (Dias * %Ocup)
                            leitos_calculados = pac_dia / (dias_no_mes * (ocupacao/100))
                            leitos_arredondados = int(round(leitos_calculados))
                            
                            total_leitos_mes += leitos_arredondados
                            
                    except: pass
        
        resultados.append({
            "data_sort": f"{ano}-{mes:02d}",
            "mes": f"{mes:02d}/{ano}",
            "dias": dias_no_mes,
            "leitos": total_leitos_mes
        })

# Ordena e Imprime
resultados.sort(key=lambda x: x['data_sort'])

print("\n" + "="*45)
print(f"{'MÊS/ANO':<10} | {'DIAS':<5} | {'TOTAL LEITOS (ATIVOS)':<20}")
print("="*45)

for r in resultados:
    print(f"{r['mes']:<10} | {r['dias']:<5} | {r['leitos']:<20}")

print("="*45)
print("Obs: Este cálculo exclui 'LEITO EXTRA'.")