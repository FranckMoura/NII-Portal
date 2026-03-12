import pandas as pd
import glob
import os
import re
from supabase import create_client, Client

print("==========================================================")
print(" ⚙️ PROCESSADOR TABNET V21 (Sensor Inteligente de Arquivo)")
print("==========================================================")

# --- CONFIGURAÇÕES DE PASTAS ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\tabnet"

# --- CREDENCIAIS SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try:
        return float(str(v).replace('.', '').replace(',', '.'))
    except: return 0.0

# 🌟 NOVIDADE: Lê o arquivo corretamente independente de ser velho (Latin-1) ou novo (UTF-8)
def ler_linhas_arquivo(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.readlines()
    except UnicodeDecodeError:
        with open(caminho, 'r', encoding='latin-1') as f:
            return f.readlines()

def encontrar_data(linhas):
    for line in linhas[:20]:
        # 🌟 NOVIDADE: Regex modificado para tolerar acentos corrompidos ("Per.odo")
        match = re.search(r'Per.odo:?\s*([A-Z][a-z]{2})/(\d{4})', line, re.IGNORECASE)
        if match:
            m, a = match.groups()
            return f"{a}-{MESES_PT.get(m.capitalize(), '01')}"
    return None

def processar_linha_texto(linha):
    partes = linha.strip().split()
    if len(partes) < 17: return None
    if not partes[0].isdigit(): return None

    dados = {
        'obitos': partes[-2],
        'media_perm': partes[-3],
        'dias': partes[-4],
        'val_prof': partes[-9],
        'val_hosp': partes[-12],
        'valor': partes[-13],
        'internacoes': partes[-14],
        'qtd_aih': partes[-15],
    }
    
    codigo = partes[0]
    nome = " ".join(partes[1:-15])
    dados['procedimento'] = f"{codigo} {nome}"
    
    return dados

buffer_meses = {}
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Processando {len(arquivos)} arquivos TABNET...")

for arq in arquivos:
    try:
        linhas = ler_linhas_arquivo(arq)
        registros = []
        
        for linha in linhas:
            dado = processar_linha_texto(linha)
            if dado: registros.append(dado)
        
        if not registros: 
            continue
        
        df = pd.DataFrame(registros)
        cols_num = ['qtd_aih', 'internacoes', 'valor', 'val_hosp', 'val_prof', 'dias', 'obitos', 'media_perm']
        for c in cols_num:
            df[c] = df[c].apply(limpar_num)

        periodo = encontrar_data(linhas)
        
        if periodo:
            score = len(df) + (5000 if df['val_hosp'].sum() > 0 else 0)
            if periodo not in buffer_meses or score > buffer_meses[periodo]['score']:
                buffer_meses[periodo] = {'df': df, 'score': score}
        else:
            print(f"⚠️ Atenção: Não foi possível identificar o mês no arquivo {os.path.basename(arq)}")

    except Exception as e: 
        print(f"❌ Erro ao ler {os.path.basename(arq)}: {e}")

# ==========================================================
# INJEÇÃO NO BANCO DE DADOS (SUPABASE)
# ==========================================================
if buffer_meses:
    # Ordenei para mostrar no terminal numa sequência cronológica e mais bonita
    for periodo, info in sorted(buffer_meses.items()):
        df_mes = info['df']
        competencia_iso = f"{periodo}-01"
        mes_str = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
        competencia_fmt = f"{mes_str}/{periodo.split('-')[0]}"
        
        print(f"\n🚀 Sincronizando: {competencia_fmt} ({len(df_mes)} procedimentos)")
        
        # FAXINA: Apaga os dados antigos desse mês para evitar duplicidade
        supabase.table('faturamento').delete().eq('competencia_iso', competencia_iso).execute()
        
        lote = []
        for _, row in df_mes.iterrows():
            lote.append({
                "competencia_iso": competencia_iso,
                "competencia_fmt": competencia_fmt,
                "procedimento": row['procedimento'],
                "aih_aprovadas": int(row['qtd_aih']),
                "internacoes": int(row['internacoes']),
                "valor_total": float(row['valor']),
                "valor_serv_hosp": float(row['val_hosp']),
                "valor_serv_prof": float(row['val_prof']),
                "dias_permanencia": int(row['dias']),
                "media_permanencia": float(row['media_perm']),
                "obitos": int(row['obitos'])
            })
            
        TAMANHO_LOTE = 500
        for i in range(0, len(lote), TAMANHO_LOTE):
            pedaco = lote[i:i+TAMANHO_LOTE]
            supabase.table('faturamento').insert(pedaco).execute()
            print(f"   ✅ Enviado {i + len(pedaco)}/{len(lote)} registros.")

    print("\n🎉 BANCO DE FATURAMENTO TOTALMENTE ATUALIZADO!")
else:
    print("❌ Erro: Nenhum dado válido encontrado nos arquivos.")