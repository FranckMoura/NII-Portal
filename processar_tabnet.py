import pandas as pd
import glob
import os
import json
import re
import numpy as np
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V14 (CORREÇÃO AGOSTO + COLUNAS RICAS) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try: return float(str(v).replace('.','').replace(',','.'))
    except: return 0.0

def encontrar_data_no_arquivo(caminho):
    try:
        with open(caminho, 'r', encoding='latin-1') as f:
            for _ in range(20):
                match = re.search(r'Período:?\s*([A-Z][a-z]{2})/(\d{4})', f.readline(), re.IGNORECASE)
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
            with open(arq, 'r', encoding='latin-1') as f: head = [next(f) for _ in range(10)]
            header_row = -1
            for i, l in enumerate(head):
                if "Procedimento" in l and ";" in l: header_row = i; break
            
            if header_row != -1:
                df = pd.read_csv(arq, sep=';', encoding='latin-1', header=header_row, on_bad_lines='skip', engine='python')
        except: pass

        # 2. TENTA TEXTO (Fallback)
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

        # --- LIMPEZA E PADRONIZAÇÃO ---
        
        # Remove totais e lixo
        if isinstance(df.iloc[0,0], str):
            df = df[~df.iloc[:,0].str.contains(r"^(Total|Fonte|Notas)", case=False, na=False)]
        
        # Normaliza nomes de colunas
        df.columns = [unidecode(c.strip().lower()).replace(" ", "_").replace(".", "").replace("-", "") for c in df.columns]

        # CORREÇÃO DO ERRO DE AGOSTO (DUPLICIDADE DE COLUNAS)
        # Se tiver 'internacoes', jogamos fora para ficar só com 'aih_aprovadas'
        if 'internacoes' in df.columns:
            df.drop(columns=['internacoes'], inplace=True)

        # Mapeamento
        mapa = {
            'procedimento': 'procedimento',
            'aih_aprovadas': 'qtd_aih', 
            'valor_total': 'valor', 
            'dias_permanencia': 'dias', 
            'obitos': 'obitos',
            'valor_servicos_hospitalares': 'val_hosp', 
            'valor_servicos_profissionais': 'val_prof'
        }
        df.rename(columns=mapa, inplace=True)

        # Filtro Raio-X (Só linhas que começam com código numérico)
        if 'procedimento' in df.columns:
            df = df[df['procedimento'].astype(str).str.match(r'^\d')]

        if df.empty: continue

        # Identifica Data
        periodo = encontrar_data_no_arquivo(arq)
        if not periodo:
            parts = os.path.basename(arq).replace(".csv", "").split("_")
            for p in parts:
                if "-" in p and len(p)>=7 and p[:3] in MESES_PT:
                    m, a = p.split("-")
                    periodo = f"{a}-{MESES_PT[m]}"
                    break
        
        if periodo:
            # Garante colunas
            for c in ['qtd_aih', 'valor', 'dias', 'obitos', 'val_hosp', 'val_prof']:
                if c not in df.columns: df[c] = 0.0
                else: df[c] = df[c].apply(limpar_num)

            # Score para deduplicação (Prefere quem tem val_hosp preenchido)
            score = len(df) + (5000 if df['val_hosp'].sum() > 0 else 0)
            
            if periodo not in buffer_meses or score > buffer_meses[periodo]['score']:
                # Salva metadados
                df['data'] = f"{periodo}-01"
                mes_str = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
                df['periodo'] = f"{mes_str}-{periodo.split('-')[0]}"
                buffer_meses[periodo] = {'df': df, 'score': score, 'arq': os.path.basename(arq)}

    except Exception as e: print(f"Erro {arq}: {e}")

# Consolidação
dfs = [v['df'] for v in buffer_meses.values()]
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Cálculos Finais
    df_final['media_perm'] = np.where(df_final['qtd_aih']>0, df_final['dias']/df_final['qtd_aih'], 0).round(1)
    df_final['ticket_medio'] = np.where(df_final['qtd_aih']>0, df_final['valor']/df_final['qtd_aih'], 0).round(2)

    # Salva JSON
    cols = ['periodo','data','procedimento','qtd_aih','valor','dias','obitos','media_perm','ticket_medio','val_hosp','val_prof']
    cols_final = [c for c in cols if c in df_final.columns]
    df_final[cols_final].to_json(CAMINHO_JSON, orient='records', indent=4)
    
    print(f"\n✅ SUCESSO! Base limpa.")
    
    # Check Agosto 2025
    if '2025-08' in buffer_meses:
        d8 = buffer_meses['2025-08']['df']
        print(f"🔎 Check Agosto 2025: AIH = {int(d8['qtd_aih'].sum())} (Deve ser ~906)")
        print(f"   Val Hosp: {d8['val_hosp'].sum():,.2f} | Val Prof: {d8['val_prof'].sum():,.2f}")
else:
    print("❌ Erro.")