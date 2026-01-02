import pandas as pd
import glob
import os
import json
import re
import numpy as np
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V18 (MAPEAMENTO COMPLETO 15 COLUNAS) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try:
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
        
        # LÊ CSV RICO (;)
        try:
            with open(arq, 'r', encoding='latin-1') as f: lines = f.readlines()
            
            # Procura a linha que tem "Procedimento" e "Valor" (Cabeçalho Real)
            header_row = -1
            for i, l in enumerate(lines[:30]): # Olha até linha 30
                if "Procedimento" in l and "Valor" in l:
                    header_row = i
                    break
            
            if header_row != -1:
                df = pd.read_csv(arq, sep=';', encoding='latin-1', header=header_row, on_bad_lines='skip', engine='python')
        except: pass

        if df.empty: continue

        # --- PADRONIZAÇÃO DE NOMES ---
        df.columns = [unidecode(str(c).strip().lower()).replace('"', '').replace("'", "").replace("_", " ").replace(".", "").replace("-", "") for c in df.columns]

        # --- MAPEAMENTO DAS 15 COLUNAS ---
        # Baseado na sua lista exata
        mapa = {}
        for c in df.columns:
            if "procedimento" in c: mapa[c] = 'procedimento'
            
            # Quantidades
            elif "aprov" in c: mapa[c] = 'qtd_aih'
            # 'Internações' ignoramos para não duplicar (ou mapeamos para check)
            
            # Valores Totais
            elif "valor total" in c: mapa[c] = 'valor'
            
            # Serviços Hospitalares
            elif "hosp" in c and "compl" not in c: mapa[c] = 'val_hosp'
            elif "hosp" in c and "federal" in c: mapa[c] = 'val_hosp_fed'
            elif "hosp" in c and "gestor" in c: mapa[c] = 'val_hosp_gest'
            
            # Serviços Profissionais
            elif "prof" in c and "compl" not in c: mapa[c] = 'val_prof'
            elif "prof" in c and "federal" in c: mapa[c] = 'val_prof_fed'
            elif "prof" in c and "gestor" in c: mapa[c] = 'val_prof_gest'
            
            # Médios
            elif "medio aih" in c: mapa[c] = 'val_medio_aih'
            elif "medio intern" in c: mapa[c] = 'val_medio_intern'
            
            # Dias e Óbitos
            elif "dias permanencia" in c: mapa[c] = 'dias'
            elif "media permanencia" in c: mapa[c] = 'media_perm_orig'
            elif "obitos" in c: mapa[c] = 'obitos'
            elif "taxa" in c: mapa[c] = 'taxa_mort'

        df.rename(columns=mapa, inplace=True)

        # --- FILTRO RAIO-X (Limpeza) ---
        if 'procedimento' in df.columns:
            # Mantém só se começar com número (ex: 0303...)
            df = df[df['procedimento'].astype(str).str.match(r'^"?\d')]
            df.drop_duplicates(subset=['procedimento'], keep='first', inplace=True)

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
            # Garante colunas numéricas (Preenche com 0 se não existir)
            cols_desejadas = ['qtd_aih', 'valor', 'val_hosp', 'val_prof', 'val_hosp_fed', 'val_hosp_gest', 'val_prof_fed', 'val_prof_gest', 'dias', 'obitos', 'media_perm_orig', 'val_medio_aih', 'taxa_mort']
            
            for col in cols_desejadas:
                if col not in df.columns: df[col] = 0.0
                else: df[col] = df[col].apply(limpar_num)

            # Score: Prefere arquivos mais completos (com val_hosp)
            is_rich = df['val_hosp'].sum() > 0
            score = len(df) + (10000 if is_rich else 0)
            
            if periodo not in buffer_meses or score > buffer_meses[periodo]['score']:
                df['data'] = f"{periodo}-01"
                mes_str = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
                df['periodo'] = f"{mes_str}-{periodo.split('-')[0]}"
                buffer_meses[periodo] = {'df': df, 'score': score, 'arq': os.path.basename(arq)}

    except Exception as e: print(f"Erro {arq}: {e}")

# Consolida
dfs = [v['df'] for v in buffer_meses.values()]
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Salva JSON completo
    cols_export = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'val_hosp', 'val_prof', 'val_hosp_fed', 'val_hosp_gest', 'val_prof_fed', 'val_prof_gest', 'dias', 'obitos', 'media_perm_orig', 'val_medio_aih', 'taxa_mort']
    
    # Filtra colunas que realmente existem
    cols_final = [c for c in cols_export if c in df_final.columns]
    
    df_final[cols_final].to_json(CAMINHO_JSON, orient='records', indent=4)
    print(f"\n✅ SUCESSO! Base RICA gerada.")
    print(f"   Meses: {len(buffer_meses)}")
    
    # Check Agosto
    if '2025-08' in buffer_meses:
        d = buffer_meses['2025-08']['df']
        print(f"\n🔎 CHECK AGOSTO/25 ({buffer_meses['2025-08']['arq']}):")
        print(f"   AIH: {int(d['qtd_aih'].sum())}")
        print(f"   V.Hosp: {d['val_hosp'].sum():,.2f}")
        print(f"   V.Prof: {d['val_prof'].sum():,.2f}")
else:
    print("❌ Erro.")