import pandas as pd
import glob
import os
import json
import re
import numpy as np
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V17 (FAXINA DE DUPLICATAS + DIAGNÓSTICO) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try:
        # Remove R$, aspas e espaços
        v_str = str(v).replace('R$', '').replace('"', '').replace("'", "").strip()
        v_str = v_str.replace('.', '').replace(',', '.')
        return float(v_str)
    except: return 0.0

def encontrar_data_no_arquivo(caminho):
    try:
        with open(caminho, 'r', encoding='latin-1') as f:
            for _ in range(30):
                line = f.readline()
                match = re.search(r'Período:?\s*([A-Z][a-z]{2})/(\d{4})', line, re.IGNORECASE)
                if match:
                    m, a = match.groups()
                    return f"{a}-{MESES_PT.get(m.capitalize(), '01')}"
    except: pass
    return None

buffer_meses = {}
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Processando {len(arquivos)} arquivos...")

for arq in arquivos:
    try:
        df = pd.DataFrame()
        
        # 1. TENTA CSV RICO (;)
        try:
            with open(arq, 'r', encoding='latin-1') as f: head = [next(f) for _ in range(15)]
            header_row = -1
            for i, l in enumerate(head):
                if "Procedimento" in l and ";" in l: header_row = i; break
            
            if header_row != -1:
                df = pd.read_csv(arq, sep=';', encoding='latin-1', header=header_row, on_bad_lines='skip', engine='python')
                
                # REMOVE COLUNA DE INTERNAÇÕES
                cols_dup = [c for c in df.columns if "nterna" in c and "edio" not in c]
                if cols_dup: df.drop(columns=cols_dup, inplace=True)

        except: pass

        # 2. TENTA TEXTO
        if df.empty:
            try:
                dados_txt = []
                with open(arq, 'r', encoding='latin-1') as f:
                    for l in f:
                        p = l.strip().split()
                        if len(p) >= 7 and p[0].isdigit(): 
                            dados_txt.append({
                                'procedimento': p[0]+" "+" ".join(p[1:-5]),
                                'aih_aprovadas': p[-5], 'valor_total': p[-4], 
                                'dias_permanencia': p[-3], 'obitos': p[-2]
                            })
                if dados_txt: df = pd.DataFrame(dados_txt)
            except: pass

        if df.empty: continue

        # --- PADRONIZAÇÃO DE COLUNAS ---
        # Remove aspas e normaliza
        df.columns = [unidecode(str(c).strip().lower()).replace('"', '').replace("'", "").replace("_", " ").replace(".", "") for c in df.columns]

        # Mapeamento Flexível (Caça palavras-chave)
        mapa = {}
        for c in df.columns:
            if "procedimento" in c: mapa[c] = 'procedimento'
            elif "aih" in c and "aprov" in c: mapa[c] = 'qtd_aih'
            elif "valor" in c and "total" in c: mapa[c] = 'valor'
            elif "dias" in c: mapa[c] = 'dias'
            elif "obito" in c: mapa[c] = 'obitos'
            # Caça ao tesouro dos valores extras
            elif "valor" in c and "hosp" in c and "fed" not in c and "gest" not in c: mapa[c] = 'val_hosp'
            elif "valor" in c and "prof" in c and "fed" not in c and "gest" not in c: mapa[c] = 'val_prof'
        
        df.rename(columns=mapa, inplace=True)

        # --- FILTRO "RAIO-X" + REMOÇÃO DE DUPLICATAS ---
        if 'procedimento' in df.columns:
            # 1. Mantém só linhas que começam com número (ignora Total)
            df = df[df['procedimento'].astype(str).str.match(r'^"?\d')]
            
            # 2. *** NOVO: REMOVE LINHAS DUPLICADAS EXATAS ***
            # Se a linha "0409... PARTO" aparecer 2x com os mesmos valores, apaga a segunda.
            df.drop_duplicates(subset=['procedimento'], keep='first', inplace=True)

        if df.empty: continue

        # Identifica Data
        periodo = encontrar_data_no_arquivo(arq)
        if not periodo:
            # Fallback para nome do arquivo
            parts = os.path.basename(arq).replace(".csv", "").split("_")
            for p in parts:
                if "-" in p and len(p)>=7 and p[:3] in MESES_PT:
                    m, a = p.split("-")
                    periodo = f"{a}-{MESES_PT[m]}"
                    break
        
        if periodo:
            # Garante colunas numéricas
            cols_num = ['qtd_aih', 'valor', 'dias', 'obitos', 'val_hosp', 'val_prof']
            for col in cols_num:
                if col not in df.columns: df[col] = 0.0
                else: df[col] = df[col].apply(limpar_num)

            # Score: Prefere arquivos com val_hosp > 0 (Ricos)
            is_rich = df['val_hosp'].sum() > 0
            score = len(df) + (5000 if is_rich else 0)
            
            if periodo not in buffer_meses or score > buffer_meses[periodo]['score']:
                # Metadados
                df['data'] = f"{periodo}-01"
                mes_str = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
                df['periodo'] = f"{mes_str}-{periodo.split('-')[0]}"
                buffer_meses[periodo] = {'df': df, 'score': score, 'arq': os.path.basename(arq), 'is_rich': is_rich}

    except Exception as e: print(f"Erro {arq}: {e}")

# Consolidação
dfs = [v['df'] for v in buffer_meses.values()]
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Cálculos
    df_final['media_perm'] = np.where(df_final['qtd_aih']>0, df_final['dias']/df_final['qtd_aih'], 0).round(1)
    df_final['ticket_medio'] = np.where(df_final['qtd_aih']>0, df_final['valor']/df_final['qtd_aih'], 0).round(2)

    # Salva
    cols = ['periodo','data','procedimento','qtd_aih','valor','dias','obitos','media_perm','ticket_medio','val_hosp','val_prof']
    cols_final = [c for c in cols if c in df_final.columns]
    df_final[cols_final].to_json(CAMINHO_JSON, orient='records', indent=4)
    
    print(f"\n✅ SUCESSO! Base limpa.")
    print(f"   Meses únicos: {len(buffer_meses)}")
    
    # RELATÓRIO DE AGOSTO
    if '2025-08' in buffer_meses:
        info = buffer_meses['2025-08']
        d8 = info['df']
        print(f"\n🔎 RELATÓRIO AGOSTO/2025:")
        print(f"   Arquivo usado: {info['arq']}")
        print(f"   Tipo: {'RICO (Detalhado)' if info['is_rich'] else 'POBRE (Básico)'}")
        print(f"   Qtd AIH:   {int(d8['qtd_aih'].sum())} (Esperado ~900)")
        print(f"   Val Hosp:  R$ {d8['val_hosp'].sum():,.2f}")
        
        if not info['is_rich']:
            print("   ⚠️ AVISO: O arquivo de Agosto não tem colunas detalhadas (Hosp/Prof).")
            print("      Isso acontece porque o script escolheu o arquivo 'tabnet_...csv' (básico)")
            print("      em vez do manual, ou o manual está ilegível/sem data.")
    
else:
    print("❌ Erro.")