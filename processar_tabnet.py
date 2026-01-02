import pandas as pd
import glob
import os
import json
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V8 (CORREÇÃO DE FILTROS E TOTAL) ---")

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
    dados = []
    with open(caminho, 'r', encoding='latin-1') as f:
        linhas = f.readlines()
    
    iniciou = False
    for linha in linhas:
        l = linha.strip()
        if "Procedimento" in l: 
            iniciou = True
            continue
        
        # CORREÇÃO: Só ignora se COMEÇAR com Total (evita apagar Histerectomia Total)
        if not iniciou or l.startswith("TOTAL") or l.startswith("Fonte") or l == "": continue
        
        partes = l.split()
        if len(partes) < 7: continue
        
        taxa = partes[-1]
        obitos = partes[-2]
        dias = partes[-3]
        valor = partes[-4]
        aih = partes[-5]
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

print(f">> Refinando {len(arquivos)} arquivos...")

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
                
                # CORREÇÃO: Regex mais estrito para não apagar procedimentos com 'Total' no nome
                # Procura por "Total" no INÍCIO da célula, aceitando aspas opcionais
                df_temp = df_temp[~df_temp.iloc[:,0].astype(str).str.contains(r"^\"?Total", case=False, regex=True, na=False)]
                df_temp = df_temp[~df_temp.iloc[:,0].astype(str).str.contains(r"^Fonte", case=False, regex=True, na=False)]
                
                df_temp.columns = [unidecode(c.strip().lower()).replace(" ", "_").replace('"', '') for c in df_temp.columns]
                de_para = {'aih_aprovadas':'qtd_aih', 'valor_total':'valor', 'dias_permanencia':'dias', 'obitos':'obitos', 'taxa_mortalidade':'taxa_mortalidade'}
                df_temp.rename(columns=de_para, inplace=True)
                df = df_temp
        except: pass

        # TENTA TEXTO (Fallback)
        if df.empty:
            df = processar_arquivo_texto(arq)
        
        if df.empty: continue

        # Extrai Data
        mes_txt = nome_arq.replace(".csv", "").split("_")[-1]
        if "-" in mes_txt:
            mes, ano = mes_txt.replace("/", "-").split("-")
            df['periodo'] = mes_txt
            df['data'] = f"{ano}-{MESES.get(mes, '01')}-01"
            
            for c in ['qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade']:
                if c in df.columns:
                    df[c] = df[c].apply(limpar_num)
            
            dfs.append(df)
            
    except Exception as e:
        print(f"⚠️ Erro em {nome_arq}: {e}")

if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Salva
    cols = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade']
    cols_ok = [c for c in cols if c in df_final.columns]
    
    df_final[cols_ok].to_json(CAMINHO_JSON, orient='records', indent=4)
    print(f"✅ SUCESSO! Valor Total Acumulado (18 anos): R$ {df_final['valor'].sum():,.2f}")
else:
    print("❌ Falha crítica.")