import pandas as pd
import glob
import os
import json
import re
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V7 (HÍBRIDO: CSV + TEXTO) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)
engine = create_engine(f"sqlite:///{CAMINHO_DB}")

MESES = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
         'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    """Converte '1.234,56' ou '-' para float."""
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try: return float(str(v).replace('.','').replace(',','.'))
    except: return 0.0

def processar_arquivo_texto(caminho):
    """Lê arquivos que vieram sem separador (formato visual do TabNet)."""
    dados = []
    with open(caminho, 'r', encoding='latin-1') as f:
        linhas = f.readlines()
    
    iniciou = False
    for linha in linhas:
        l = linha.strip()
        # Pula cabeçalho e rodapé
        if "Procedimento" in l: 
            iniciou = True
            continue
        if not iniciou or "Total" in l or "Fonte" in l or l == "": continue
        
        # Lógica: O texto tem CODE NOME...NOME NUM NUM NUM NUM NUM
        # Quebramos por espaço
        partes = l.split()
        
        # Precisamos de pelo menos Código + 1 palavra + 5 números = 7 partes
        if len(partes) < 7: continue
        
        # Os últimos 5 são sempre: AIH, Valor, Dias, Óbitos, Taxa
        # Cuidado: às vezes Taxa é "..." ou "-", então pegamos os 5 últimos
        taxa = partes[-1]
        obitos = partes[-2]
        dias = partes[-3]
        valor = partes[-4]
        aih = partes[-5]
        
        # O código é o primeiro
        codigo = partes[0]
        
        # O nome é tudo que sobrou no meio
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

print(f">> Processando {len(arquivos)} arquivos...")

for arq in arquivos:
    try:
        nome_arq = os.path.basename(arq)
        
        # 1. TENTA FORMATO CSV (;)
        try:
            df = pd.read_csv(arq, sep=';', encoding='latin-1', engine='python', on_bad_lines='skip')
            # Verifica se funcionou (tem que ter mais de 1 coluna)
            if df.shape[1] > 2:
                # Limpeza padrão CSV
                if "Procedimento" not in str(df.columns[0]):
                     df = pd.read_csv(arq, sep=';', encoding='latin-1', skiprows=3, on_bad_lines='skip')
                
                df = df[~df.iloc[:,0].astype(str).str.contains(r"^(Total|Fonte|Notas)", case=False, na=False)]
                df.columns = [unidecode(c.strip().lower()).replace(" ", "_").replace('"', '') for c in df.columns]
                
                # Renomeia CSV
                de_para = {'aih_aprovadas':'qtd_aih', 'valor_total':'valor', 'dias_permanencia':'dias', 'obitos':'obitos', 'taxa_mortalidade':'taxa_mortalidade'}
                df.rename(columns=de_para, inplace=True)
            else:
                raise Exception("Não é CSV separado por ponto e vírgula")
                
        except:
            # 2. TENTA FORMATO TEXTO (Fallback)
            df = processar_arquivo_texto(arq)
        
        # Se o DF estiver vazio, pula
        if df.empty: continue

        # Extrai Data do Nome do Arquivo
        mes_txt = nome_arq.replace(".csv", "").split("_")[-1] # Ex: Set-2025
        if "-" in mes_txt:
            mes, ano = mes_txt.replace("/", "-").split("-")
            df['periodo'] = mes_txt
            df['data'] = f"{ano}-{MESES.get(mes, '01')}-01"
            
            # Garante numéricos
            for c in ['qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade']:
                if c in df.columns:
                    df[c] = df[c].apply(limpar_num)
            
            dfs.append(df)
            
    except Exception as e:
        print(f"⚠️ Erro em {nome_arq}: {e}")

if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    total = df_final['valor'].sum()
    print(f"\n💰 VALOR TOTAL RECUPERADO: R$ {total:,.2f}")
    
    cols = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'dias', 'obitos', 'taxa_mortalidade']
    cols_ok = [c for c in cols if c in df_final.columns]
    
    df_final[cols_ok].to_json(CAMINHO_JSON, orient='records', indent=4)
    print(f"✅ SUCESSO! JSON gerado com {len(df_final)} registros.")
    print(">> Rode o upload_manager.py agora!")
else:
    print("❌ Falha total: Nenhum dado recuperado.")