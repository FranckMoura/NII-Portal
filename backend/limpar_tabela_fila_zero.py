import pandas as pd
import re
import os
import csv

print("--- 🧹 FAXINA DE DADOS V3: PREPARANDO PARA SUPABASE ---")

ARQUIVO_ENTRADA = "tabela_sus_mt_2026.csv"
ARQUIVO_SAIDA = "fila_zero_pronto_supabase.csv"

if not os.path.exists(ARQUIVO_ENTRADA):
    print(f"❌ Arquivo '{ARQUIVO_ENTRADA}' não encontrado.")
    exit()

print(">> Lendo e decodificando a estrutura do arquivo...")
linhas_validas = []

# O CSV que você enviou está encapsulando a linha inteira dentro de uma única coluna.
# Então nós lemos a linha e aplicamos um SEGUNDO leitor de CSV nela para extrair as colunas corretas.
with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8', errors='ignore') as arquivo:
    leitor_externo = csv.reader(arquivo)
    
    for linha in leitor_externo:
        if not linha: 
            continue
            
        # Pega a "linha crua" (que na verdade é uma string contendo todas as colunas separadas por vírgula)
        texto_cru = linha[0]
        
        # Pede para o Python interpretar essa string como uma nova linha de CSV para separar os campos
        colunas = list(csv.reader([texto_cru]))[0]
        
        if len(colunas) < 2:
            continue
            
        codigo = str(colunas[0]).strip()
        
        # 1. VALIDAÇÃO DE CÓDIGO (Só aceita se for 10 dígitos cravados)
        if not re.match(r'^\d{10}$', codigo):
            continue
            
        # O valor sempre estará na última coluna
        valor_bruto = str(colunas[-1]).strip()
        if not valor_bruto:
            continue

        # 2. LIMPEZA DE VALOR (Remove R$, pontos de milhar e acerta a vírgula)
        valor_limpo = valor_bruto.upper().replace("R$", "").replace('"', '').replace(" ", "")
        
        if ',' in valor_limpo:
            valor_limpo = valor_limpo.replace(".", "").replace(",", ".")
            
        try:
            valor_float = float(valor_limpo)
        except:
            continue # Se a conversão falhar, pula a linha
        
        linhas_validas.append({
            "codigo_sigtap": codigo,
            "valor_unitario": valor_float
        })

if not linhas_validas:
    print("❌ Nenhum procedimento foi extraído. Verifique a formatação do arquivo de origem.")
    exit()

# Transforma a lista em um DataFrame
df_limpo = pd.DataFrame(linhas_validas)

# Remove duplicatas mantendo a última
df_limpo = df_limpo.drop_duplicates(subset=['codigo_sigtap'], keep='last')

print(f">> Sucesso! {len(df_limpo)} procedimentos foram limpos e validados.")
print(">> Salvando arquivo final para o Supabase...")

# Exporta em UTF-8 sem os números de linha à esquerda
df_limpo.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')

print(f"✅ O arquivo '{ARQUIVO_SAIDA}' está pronto!")
print("👉 Vá no Supabase > Table Editor > fila_zero_procedimentos > Insert > Import data from CSV.")