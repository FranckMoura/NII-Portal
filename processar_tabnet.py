import pandas as pd
import glob
import os
import json
from sqlalchemy import create_engine
from unidecode import unidecode
import numpy as np

print("--- ⚙️ PROCESSAMENTO V9 (CÁLCULO DE INDICADORES + ENRIQUECIMENTO) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)
engine = create_engine(f"sqlite:///{CAMINHO_DB}")

MESES = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
         'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try: return float(str(v).replace('.','').replace(',','.'))
    except: return 0.0

def processar_arquivo_texto(caminho):
    # Lógica de fallback para arquivos de texto sem separador
    dados = []
    with open(caminho, 'r', encoding='latin-1') as f:
        linhas = f.readlines()
    iniciou = False
    for linha in linhas:
        l = linha.strip()
        if "Procedimento" in l: 
            iniciou = True; continue
        if not iniciou or l.startswith("TOTAL") or l.startswith("Fonte") or l == "": continue
        
        partes = l.split()
        if len(partes) < 7: continue
        
        # Pega os 5 últimos campos padrão
        taxa = partes[-1]; obitos = partes[-2]; dias = partes[-3]; valor = partes[-4]; aih = partes[-5]
        codigo = partes[0]
        nome = " ".join(partes[1:-5])
        
        dados.append({
            'procedimento': f"{codigo} {nome}",
            'qtd_aih': limpar_num(aih),
            'valor': limpar_num(valor),
            'dias': limpar_num(dias),
            'obitos': limpar_num(obitos),
            'taxa_mortalidade': limpar_num(taxa)
        })
    return pd.DataFrame(dados)

arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
dfs = []

print(f">> Enriquecendo {len(arquivos)} arquivos...")

for arq in arquivos:
    try:
        nome_arq = os.path.basename(arq)
        df = pd.DataFrame()

        # TENTA CSV (;)
        try:
            df_temp = pd.read_csv(arq, sep=';', encoding='latin-1', engine='python', on_bad_lines='skip')
            if df_temp.shape[1] > 2:
                if "Procedimento" not in str(df_temp.columns[0]):
                     df_temp = pd.read_csv(arq, sep=';', encoding='latin-1', skiprows=3, on_bad_lines='skip')
                
                # Limpa Rodapé
                df_temp = df_temp[~df_temp.iloc[:,0].astype(str).str.contains(r"^\"?Total", case=False, regex=True, na=False)]
                df_temp = df_temp[~df_temp.iloc[:,0].astype(str).str.contains(r"^Fonte", case=False, regex=True, na=False)]
                
                # Normaliza colunas
                df_temp.columns = [unidecode(c.strip().lower()).replace(" ", "_").replace('"', '').replace("-", "").replace("__", "_") for c in df_temp.columns]
                
                # Mapeamento Estendido (Pega o que tiver)
                de_para = {
                    'aih_aprovadas': 'qtd_aih',
                    'valor_total': 'valor',
                    'dias_permanencia': 'dias',
                    'obitos': 'obitos',
                    'taxa_mortalidade': 'taxa_mortalidade',
                    'valor_servicos_hospitalares': 'val_hosp',
                    'valor_servicos_profissionais': 'val_prof',
                    'media_permanencia': 'media_perm_orig', # Se tiver original, guarda
                    'valor_medio_aih': 'val_medio_orig'
                }
                df_temp.rename(columns=de_para, inplace=True)
                df = df_temp
        except: pass

        # TENTA TEXTO
        if df.empty:
            df = processar_arquivo_texto(arq)
        
        if df.empty: continue

        # Extrai Data
        mes_txt = nome_arq.replace(".csv", "").split("_")[-1]
        if "-" in mes_txt:
            mes, ano = mes_txt.replace("/", "-").split("-")
            df['periodo'] = mes_txt
            df['data'] = f"{ano}-{MESES.get(mes, '01')}-01"
            
            # Limpa números básicos
            for c in ['qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade']:
                if c in df.columns: df[c] = df[c].apply(limpar_num)
                else: df[c] = 0.0
            
            # Limpa colunas extras se existirem
            for c in ['val_hosp', 'val_prof']:
                if c in df.columns: df[c] = df[c].apply(limpar_num)
                else: df[c] = 0.0

            dfs.append(df)
            
    except Exception as e:
        print(f"⚠️ Erro em {nome_arq}: {e}")

if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # --- CÁLCULOS MATEMÁTICOS DE ENRIQUECIMENTO ---
    # Aqui criamos as colunas que faltam usando matemática pura
    
    # 1. Média de Permanência (Dias / AIH)
    # np.where evita divisão por zero
    df_final['media_perm'] = np.where(df_final['qtd_aih'] > 0, df_final['dias'] / df_final['qtd_aih'], 0.0)
    
    # 2. Ticket Médio (Valor / AIH)
    df_final['ticket_medio'] = np.where(df_final['qtd_aih'] > 0, df_final['valor'] / df_final['qtd_aih'], 0.0)

    # Arredondamento para JSON ficar limpo
    df_final['media_perm'] = df_final['media_perm'].round(1)
    df_final['ticket_medio'] = df_final['ticket_medio'].round(2)

    # Seleção final de colunas
    cols = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade', 'media_perm', 'ticket_medio', 'val_hosp', 'val_prof']
    cols_ok = [c for c in cols if c in df_final.columns]
    
    df_final[cols_ok].to_json(CAMINHO_JSON, orient='records', indent=4)
    print(f"✅ SUCESSO! Dados calculados e salvos.")
    print(f"   Exemplo 1ª linha: Média Perm={df_final['media_perm'].iloc[0]} dias | Ticket={df_final['ticket_medio'].iloc[0]}")
else:
    print("❌ Falha crítica.")