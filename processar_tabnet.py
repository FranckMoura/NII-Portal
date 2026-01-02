import pandas as pd
import glob
import os
import json
import re
import numpy as np
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V13 (FILTRO ESTRITO POR CÓDIGO) ---")

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
                linha = f.readline()
                match = re.search(r'Período:?\s*([A-Z][a-z]{2})/(\d{4})', linha, re.IGNORECASE)
                if match:
                    mes, ano = match.groups()
                    mes = mes.capitalize()
                    if mes in MESES_PT:
                        return f"{ano}-{MESES_PT[mes]}"
    except: pass
    return None

arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Processando {len(arquivos)} arquivos com filtro de código...")

buffer_meses = {}

for arq in arquivos:
    try:
        nome_arq = os.path.basename(arq)
        df = pd.DataFrame()
        origem = ""

        # 1. TENTA LER (HÍBRIDO)
        try:
            # Tenta CSV com ;
            with open(arq, 'r', encoding='latin-1') as f:
                head = [next(f) for _ in range(10)]
            
            header_row = -1
            for i, l in enumerate(head):
                if "Procedimento" in l and ";" in l: header_row = i; break
            
            if header_row != -1:
                df = pd.read_csv(arq, sep=';', encoding='latin-1', header=header_row, on_bad_lines='skip', engine='python')
                origem = "CSV"
            else:
                # Tenta TEXTO
                dados_txt = []
                with open(arq, 'r', encoding='latin-1') as f: lines = f.readlines()
                for l in lines:
                    parts = l.strip().split()
                    if len(parts) >= 7 and parts[0].isdigit(): # Pega só se começar com numero
                        dados_txt.append({
                            'procedimento': parts[0] + " " + " ".join(parts[1:-5]),
                            'qtd_aih': parts[-5], 'valor': parts[-4], 'dias': parts[-3], 'obitos': parts[-2]
                        })
                if dados_txt:
                    df = pd.DataFrame(dados_txt)
                    origem = "TXT"
        except: pass

        if df.empty: continue

        # 2. NORMALIZAÇÃO DE COLUNAS
        df.columns = [unidecode(c.strip().lower()).replace(" ", "_").replace(".", "").replace("-", "") for c in df.columns]
        
        mapa = {
            'procedimento': 'procedimento',
            'aih_aprovadas': 'qtd_aih', 'internacoes': 'qtd_aih',
            'valor_total': 'valor', 'dias_permanencia': 'dias', 'obitos': 'obitos',
            'valor_servicos_hospitalares': 'val_hosp', 'valor_servicos_profissionais': 'val_prof'
        }
        df.rename(columns=mapa, inplace=True)

        # 3. FILTRO "RAIO-X" (O SEGREDO) 💎
        # Mantém APENAS linhas onde 'procedimento' começa com digito (0-9)
        # Isso remove automaticamente: Total, Legendas, Cabeçalhos repetidos, Lixo.
        if 'procedimento' in df.columns:
            df = df[df['procedimento'].astype(str).str.match(r'^\d')]
        
        # Se sobrou nada, pula
        if df.empty: continue

        # 4. LIMPA NÚMEROS
        for c in ['qtd_aih', 'valor', 'dias', 'obitos', 'val_hosp', 'val_prof']:
            if c not in df.columns: df[c] = 0.0
            else: df[c] = df[c].apply(limpar_num)

        # 5. DATA
        periodo = encontrar_data_no_arquivo(arq)
        if not periodo:
            partes = nome_arq.replace(".csv", "").split("_")
            for p in partes:
                if "-" in p and len(p)>=7 and p[:3] in MESES_PT:
                    m, a = p.split("-")
                    periodo = f"{a}-{MESES_PT[m]}"
                    break
        
        if periodo:
            # Score: Arquivo com 'val_hosp' ganha prioridade
            score = len(df) + (1000 if df['val_hosp'].sum() > 0 else 0)
            
            # Deduplicação
            if periodo not in buffer_meses or score > buffer_meses[periodo]['score']:
                # Adiciona metadados
                df['data'] = f"{periodo}-01"
                mes_txt = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
                df['periodo'] = f"{mes_txt}-{periodo.split('-')[0]}"
                
                buffer_meses[periodo] = {'df': df, 'score': score, 'arq': nome_arq}

    except Exception as e: print(f"Erro em {arq}: {e}")

# CONSOLIDA
lista_final = [v['df'] for v in buffer_meses.values()]

if lista_final:
    df_final = pd.concat(lista_final, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Cálculos Finais
    df_final['media_perm'] = np.where(df_final['qtd_aih'] > 0, df_final['dias'] / df_final['qtd_aih'], 0.0).round(1)
    df_final['ticket_medio'] = np.where(df_final['qtd_aih'] > 0, df_final['valor'] / df_final['qtd_aih'], 0.0).round(2)

    cols = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'dias', 'obitos', 'media_perm', 'ticket_medio', 'val_hosp', 'val_prof']
    cols_ok = [c for c in cols if c in df_final.columns]
    
    df_final[cols_ok].to_json(CAMINHO_JSON, orient='records', indent=4)
    
    print(f"\n✅ SUCESSO! Base limpa e gerada.")
    print(f"   Meses: {len(buffer_meses)}")
    print(f"   Registros: {len(df_final)}")
    print(f"   Valor Total (18 Anos): R$ {df_final['valor'].sum():,.2f}")
    
    # Check Agosto 2025
    if '2025-08' in buffer_meses:
        d8 = buffer_meses['2025-08']['df']
        print(f"\n🔎 Check Agosto 2025 ({buffer_meses['2025-08']['arq']}):")
        print(f"   AIH: {int(d8['qtd_aih'].sum())} | Valor: R$ {d8['valor'].sum():,.2f}")
else:
    print("❌ Erro.")