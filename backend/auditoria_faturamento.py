import re
import glob
import os

print("--- 🕵️‍♂️ AUDITORIA DE LINHAS IGNORADAS ---")

os.chdir(os.path.dirname(os.path.abspath(__file__)))
# Tenta pegar o arquivo de Novembro/2025
arquivos = glob.glob("*Nov-2025.csv") + glob.glob("*Nov-2025.txt")

if not arquivos:
    print("❌ Arquivo de Novembro/2025 não encontrado.")
    exit()

arquivo = arquivos[0]
print(f"Analisando: {arquivo}\n")

with open(arquivo, 'r', encoding='latin-1') as f:
    linhas = f.readlines()

total_ignorado = 0.0

print(f"{'LINHA':<5} | {'MOTIVO':<25} | {'CONTEÚDO (Início)'}")
print("-" * 80)

for i, linha in enumerate(linhas):
    linha = linha.strip()
    if not linha: continue

    # Filtro 1: Código Numérico
    match_codigo = re.match(r'^(\d{7,})', linha)
    
    if not match_codigo:
        # Se não tem código, vamos ver se tem dinheiro escondido
        # Tenta achar um valor monetário grande (ex: 1.698,00)
        valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
        
        possivel_valor = 0.0
        if len(valores) > 0:
            # Pega o maior valor encontrado na linha (geralmente é o Total)
            # Mas cuidado para não pegar o Total Geral (1.395.204,89)
            try:
                vals_float = [float(v.replace('.', '').replace(',', '.')) for v in valores]
                # Ignora o total geralzão se for a linha de TOTAL
                if "TOTAL" in linha and vals_float[0] > 1000000:
                    possivel_valor = 0
                else:
                    possivel_valor = vals_float[0]
            except: pass

        if possivel_valor > 0:
            print(f"{i+1:<5} | ⚠️ IGNORADO (Tem Valor!)  | {linha[:50]}... -> R$ {possivel_valor:,.2f}")
            total_ignorado += possivel_valor
        else:
            # print(f"{i+1:<5} | Ignorado (Texto/Lixo)   | {linha[:50]}...")
            pass
    else:
        # Linha aceita (tem código)
        pass

print("-" * 80)
print(f"💰 TOTAL DE DINHEIRO IGNORADO: R$ {total_ignorado:,.2f}")
print(f"   (Diferença procurada: R$ 1.698,00)")