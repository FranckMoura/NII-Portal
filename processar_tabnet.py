import pandas as pd
import glob
import os
import json
import re
import numpy as np
from sqlalchemy import create_engine
from unidecode import unidecode

print("--- ⚙️ PROCESSAMENTO V11 (UNIVERSAL: TEXTO + CSV + DATA INTERNA) ---")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_tabnet.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)
engine = create_engine(f"sqlite:///{CAMINHO_DB}")

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try: return float(str(v).replace('.','').replace(',','.'))
    except: return 0.0

def extrair_data_conteudo(caminho):
    """Tenta achar 'Período: Mes/Ano' dentro do arquivo."""
    try:
        with open(caminho, 'r', encoding='latin-1') as f:
            for _ in range(15): # Lê as primeiras 15 linhas
                linha = f.readline()
                match = re.search(r'Período:\s*([A-Z][a-z]{2})/(\d{4})', linha, re.IGNORECASE)
                if match:
                    mes, ano = match.groups()
                    mes = mes.capitalize()
                    if mes in MESES_PT:
                        return f"{ano}-{MESES_PT[mes]}"
    except: pass
    return None

def ler_arquivo_texto(caminho):
    """Lê formato visual do TabNet (espaços)."""
    dados = []
    with open(caminho, 'r', encoding='latin-1') as f:
        linhas = f.readlines()
    iniciou = False
    for linha in linhas:
        l = linha.strip()
        if "Procedimento" in l: iniciou = True; continue
        if not iniciou or l.startswith("TOTAL") or l.startswith("Fonte") or l == "": continue
        
        partes = l.split()
        if len(partes) < 7: continue
        
        # Padrão visual TabNet: Código + Nome + 5 números
        taxa = partes[-1]; obitos = partes[-2]; dias = partes[-3]; valor = partes[-4]; aih = partes[-5]
        codigo = partes[0]
        nome = " ".join(partes[1:-5])
        
        dados.append({
            'procedimento': f"{codigo} {nome}",
            'qtd_aih': limpar_num(aih),
            'valor': limpar_num(valor),
            'dias': limpar_num(dias),
            'obitos': limpar_num(obitos),
            'val_hosp': 0.0, 'val_prof': 0.0 # Texto não tem esses dados
        })
    return pd.DataFrame(dados)

# Buffer para deduplicação: Chave '2025-09' -> DataFrame
buffer_meses = {}

arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Processando {len(arquivos)} arquivos mistos...")

for arq in arquivos:
    try:
        nome_arq = os.path.basename(arq)
        df = pd.DataFrame()
        tipo_leitura = ""

        # 1. TENTA CSV RICO (;)
        try:
            df_temp = pd.read_csv(arq, sep=';', encoding='latin-1', engine='python', on_bad_lines='skip')
            # Se a primeira célula não for Procedimento, tenta pular linhas
            if df_temp.shape[1] > 2:
                if "Procedimento" not in str(df_temp.columns[0]):
                     df_temp = pd.read_csv(arq, sep=';', encoding='latin-1', skiprows=3, on_bad_lines='skip')
                
                # Limpa rodapé/total
                df_temp = df_temp[~df_temp.iloc[:,0].astype(str).str.contains(r"^(Total|Fonte|Notas)", case=False, na=False)]
                
                # Normaliza colunas
                df_temp.columns = [unidecode(c.strip().lower()).replace(" ", "_").replace('"', '') for c in df_temp.columns]
                
                # Mapeia
                de_para = {
                    'aih_aprovadas':'qtd_aih', 'valor_total':'valor', 'dias_permanencia':'dias', 
                    'obitos':'obitos', 'valor_servicos_hospitalares':'val_hosp', 'valor_servicos_profissionais':'val_prof'
                }
                df_temp.rename(columns=de_para, inplace=True)
                
                if 'qtd_aih' in df_temp.columns:
                    df = df_temp
                    tipo_leitura = "CSV"
        except: pass

        # 2. TENTA TEXTO (Fallback)
        if df.empty:
            df = ler_arquivo_texto(arq)
            if not df.empty: tipo_leitura = "TXT"

        if df.empty: continue

        # 3. IDENTIFICA DATA
        periodo_chave = None
        
        # Tenta pelo nome do arquivo (Prioridade 1)
        partes_nome = nome_arq.replace(".csv", "").split("_")
        for p in partes_nome:
            if "-" in p and len(p) >= 7 and p[:3] in MESES_PT:
                mes, ano = p.split("-")
                periodo_chave = f"{ano}-{MESES_PT[mes]}"
                break
        
        # Tenta pelo conteúdo (Prioridade 2 - Para os arquivos sih_cnv...)
        if not periodo_chave:
            periodo_chave = extrair_data_conteudo(arq)

        if not periodo_chave:
            # print(f"⚠️ Pulo: Sem data identificável em {nome_arq}")
            continue

        # 4. LIMPEZA E PADRONIZAÇÃO FINAL
        for c in ['qtd_aih', 'valor', 'dias', 'obitos', 'val_hosp', 'val_prof']:
            if c not in df.columns: df[c] = 0.0
            else: df[c] = df[c].apply(limpar_num)

        # Adiciona metadados
        df['data'] = f"{periodo_chave}-01"
        mes_num = periodo_chave.split('-')[1]
        mes_nome = [k for k, v in MESES_PT.items() if v == mes_num][0]
        df['periodo'] = f"{mes_nome}-{periodo_chave.split('-')[0]}"

        # 5. DEDUPLICAÇÃO (Guarda o melhor)
        # Critério: Quem tem mais colunas preenchidas > Quem tem mais linhas
        score_atual = len(df.columns) + (100 if 'val_hosp' in df.columns and df['val_hosp'].sum() > 0 else 0)
        
        if periodo_chave in buffer_meses:
            df_old = buffer_meses[periodo_chave]
            score_old = len(df_old.columns) + (100 if 'val_hosp' in df_old.columns and df_old['val_hosp'].sum() > 0 else 0)
            
            if score_atual > score_old:
                buffer_meses[periodo_chave] = df
        else:
            buffer_meses[periodo_chave] = df

    except Exception as e:
        print(f"Erro em {arq}: {e}")

# Consolida
dfs_finais = list(buffer_meses.values())

if dfs_finais:
    df_final = pd.concat(dfs_finais, ignore_index=True)
    df_final.sort_values('data', inplace=True)
    
    # Cálculos Extras
    df_final['media_perm'] = np.where(df_final['qtd_aih'] > 0, df_final['dias'] / df_final['qtd_aih'], 0.0).round(1)
    df_final['ticket_medio'] = np.where(df_final['qtd_aih'] > 0, df_final['valor'] / df_final['qtd_aih'], 0.0).round(2)

    # Salva
    cols = ['periodo', 'data', 'procedimento', 'qtd_aih', 'valor', 'dias', 'obitos', 'media_perm', 'ticket_medio', 'val_hosp', 'val_prof']
    cols_ok = [c for c in cols if c in df_final.columns]
    
    df_final[cols_ok].to_json(CAMINHO_JSON, orient='records', indent=4)
    
    print(f"\n✅ SUCESSO ABSOLUTO!")
    print(f"   Meses processados: {len(buffer_meses)}")
    print(f"   Valor Total Acumulado: R$ {df_final['valor'].sum():,.2f}")
    print(f"   Registros: {len(df_final)}")
else:
    print("❌ Erro: Nenhum dado processado.")