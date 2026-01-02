import pandas as pd
import glob
import os
import json
import re
import numpy as np
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V19 (CIRURGIÃO DE TEXTO - BASE RICA) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    """Converte '1.234,56' ou '-' para float."""
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try:
        return float(str(v).replace('.', '').replace(',', '.'))
    except: return 0.0

def encontrar_data(caminho):
    try:
        with open(caminho, 'r', encoding='latin-1') as f:
            for _ in range(20):
                line = f.readline()
                match = re.search(r'Período:?\s*([A-Z][a-z]{2})/(\d{4})', line, re.IGNORECASE)
                if match:
                    m, a = match.groups()
                    return f"{a}-{MESES_PT.get(m.capitalize(), '01')}"
    except: pass
    return None

def processar_linha_texto(linha):
    """Quebra a linha de texto baseada na lógica: 1 Código + Nome + 15 Valores"""
    partes = linha.strip().split()
    
    # Precisamos de: 1 Código + Pelo menos 1 palavra de nome + 15 Colunas de dados = 17 itens mín.
    if len(partes) < 17: return None
    
    # Validação: O primeiro deve ser código numérico
    if not partes[0].isdigit(): return None

    # Extração de trás para frente (garante as colunas numéricas)
    dados = {
        'taxa_mort': partes[-1],
        'obitos': partes[-2],
        'media_perm': partes[-3],
        'dias': partes[-4],
        'val_medio_intern': partes[-5],
        'val_medio_aih': partes[-6],
        'val_prof_gest': partes[-7],
        'val_prof_fed': partes[-8],
        'val_prof': partes[-9],       # Valor Serv. Profissionais
        'val_hosp_gest': partes[-10],
        'val_hosp_fed': partes[-11],
        'val_hosp': partes[-12],      # Valor Serv. Hospitalares
        'valor': partes[-13],         # Valor Total
        'internacoes': partes[-14],   # Ignorar depois
        'qtd_aih': partes[-15],       # AIH Aprovadas
    }
    
    # O que sobrou é o nome + código
    codigo = partes[0]
    nome = " ".join(partes[1:-15])
    dados['procedimento'] = f"{codigo} {nome}"
    
    return dados

buffer_meses = {}
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Processando {len(arquivos)} arquivos formato TEXTO...")

for arq in arquivos:
    try:
        registros = []
        with open(arq, 'r', encoding='latin-1') as f:
            for linha in f:
                dado = processar_linha_texto(linha)
                if dado:
                    registros.append(dado)
        
        if not registros: continue
        
        df = pd.DataFrame(registros)
        
        # Limpeza Numérica
        cols_num = ['qtd_aih', 'valor', 'val_hosp', 'val_prof', 'dias', 'obitos', 'media_perm', 'val_medio_aih']
        for c in cols_num:
            df[c] = df[c].apply(limpar_num)

        # Identifica Data
        periodo = encontrar_data(arq)
        if not periodo:
            parts = os.path.basename(arq).replace(".csv", "").split("_")
            for p in parts:
                if "-" in p and len(p)>=7 and p[:3] in MESES_PT:
                    m, a = p.split("-")
                    periodo = f"{a}-{MESES_PT[m]}"
                    break
        
        if periodo:
            # Score: Prefere arquivos com dados > 0
            score = len(df) + (5000 if df['val_hosp'].sum() > 0 else 0)
            
            if periodo not in buffer_meses or score > buffer_meses[periodo]['score']:
                df['data'] = f"{periodo}-01"
                mes_str = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
                df['periodo'] = f"{mes_str}-{periodo.split('-')[0]}"
                buffer_meses[periodo] = {'df': df, 'score': score, 'arq': os.path.basename(arq)}

    except Exception as e: print(f"Erro em {arq}: {e}")

# Consolidação
dfs = [v['df'] for v in buffer_meses.values()]
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Recalcula Ticket Médio para garantir
    df_final['ticket_medio'] = np.where(df_final['qtd_aih']>0, df_final['valor']/df_final['qtd_aih'], 0).round(2)

    # Seleciona colunas finais para o JSON
    cols_export = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'val_hosp', 'val_prof', 'dias', 'media_perm', 'ticket_medio', 'obitos']
    
    df_final[cols_export].to_json(CAMINHO_JSON, orient='records', indent=4)
    print(f"\n✅ SUCESSO! Base RICA e FORMATADA gerada.")
    print(f"   Total de Meses: {len(buffer_meses)}")
    
    # Validação Setembro 2024 (Seu exemplo)
    if '2024-09' in buffer_meses:
        d = buffer_meses['2024-09']['df']
        print(f"\n🔎 CHECK SETEMBRO/24 (Arquivo Texto):")
        print(f"   AIH: {int(d['qtd_aih'].sum())}")
        print(f"   V.Hosp: {d['val_hosp'].sum():,.2f}")
        print(f"   V.Prof: {d['val_prof'].sum():,.2f}")
else:
    print("❌ Erro: Nenhum dado processado.")