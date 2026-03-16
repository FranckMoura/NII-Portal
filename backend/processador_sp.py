import pandas as pd
import glob
import os
import re
import io
from supabase import create_client, Client

print("==========================================================")
print(" ⚙️ PROCESSADOR TABNET SP (ITENS SECUNDÁRIOS) ")
print("==========================================================")

PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\tabnet_sp"
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}"); exit()

MESES_PT = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
            'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}

def limpar_num(v):
    if pd.isna(v) or str(v).strip() in ['-', '', '...']: return 0.0
    try: return float(str(v).replace('.', '').replace(',', '.'))
    except: return 0.0

arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Processando {len(arquivos)} arquivos de Itens Secundários...")

buffer_meses = {}

for arq in arquivos:
    try:
        with open(arq, 'r', encoding='latin-1', errors='ignore') as f:
            linhas = f.readlines()

        # Encontrar o Mês e Ano
        periodo = None
        for line in linhas[:20]:
            match = re.search(r'Per.odo:?\s*([A-Z][a-z]{2})/(\d{4})', line, re.IGNORECASE)
            if match:
                m, a = match.groups()
                periodo = f"{a}-{MESES_PT.get(m.capitalize(), '01')}"
                break
        
        if not periodo:
            print(f"⚠️ Atenção: Período não encontrado em {os.path.basename(arq)}")
            continue

        # Encontrar o cabeçalho real (A linha que começa com "Procedimento")
        header_idx = -1
        for i, line in enumerate(linhas):
            if "Procedimento" in line or "PROCEDIMENTO" in line.upper():
                header_idx = i
                break

        if header_idx == -1: continue

        # Transforma o texto num CSV real para o Pandas ler as colunas perfeitamente
        csv_texto = "".join(linhas[header_idx:])
        df = pd.read_csv(io.StringIO(csv_texto), sep=';', on_bad_lines='skip', engine='python')
        
        # Filtra apenas as linhas onde a primeira coluna começa com número (Código do procedimento)
        col_procedimento = df.columns[0]
        df = df[df[col_procedimento].astype(str).str.match(r'^\d')]
        
        # Encontra as colunas dinamicamente (pois o usuário pode ter baixado muitas)
        col_qtd = next((c for c in df.columns if 'Qtd' in c or 'Quantidade' in c), None)
        col_valor = next((c for c in df.columns if 'Valor aprovado' in c or 'Valor total' in c or 'Valor' == c.strip()), None)
        col_hosp = next((c for c in df.columns if 'hospit' in c.lower() or 'hosp' in c.lower()), None)
        col_prof = next((c for c in df.columns if 'profis' in c.lower() or 'prof' in c.lower()), None)

        if not col_qtd or not col_valor: continue

        registos = []
        for _, row in df.iterrows():
            registos.append({
                "procedimento": str(row[col_procedimento]).strip(),
                "qtd_aprovada": int(limpar_num(row[col_qtd])),
                "valor_total": limpar_num(row[col_valor]),
                "valor_serv_hosp": limpar_num(row[col_hosp]) if col_hosp else 0.0,
                "valor_serv_prof": limpar_num(row[col_prof]) if col_prof else 0.0
            })
            
        buffer_meses[periodo] = pd.DataFrame(registos)

    except Exception as e: 
        print(f"❌ Erro ao ler {os.path.basename(arq)}: {e}")

if buffer_meses:
    for periodo, df_mes in sorted(buffer_meses.items()):
        competencia_iso = f"{periodo}-01"
        mes_str = list(MESES_PT.keys())[list(MESES_PT.values()).index(periodo.split('-')[1])]
        competencia_fmt = f"{mes_str}/{periodo.split('-')[0]}"
        
        print(f"\n🚀 Sincronizando Itens SP: {competencia_fmt} ({len(df_mes)} itens)")
        
        supabase.table('faturamento_sp').delete().eq('competencia_iso', competencia_iso).execute()
        
        lote = []
        for _, row in df_mes.iterrows():
            lote.append({
                "competencia_iso": competencia_iso,
                "competencia_fmt": competencia_fmt,
                "procedimento": row['procedimento'],
                "qtd_aprovada": int(row['qtd_aprovada']),
                "valor_total": float(row['valor_total']),
                "valor_serv_hosp": float(row['valor_serv_hosp']),
                "valor_serv_prof": float(row['valor_serv_prof'])
            })
            
        for i in range(0, len(lote), 500):
            supabase.table('faturamento_sp').insert(lote[i:i+500]).execute()
            print(f"   ✅ Enviado {min(i + 500, len(lote))}/{len(lote)} registros.")

    print("\n🎉 BANCO DE ITENS SECUNDÁRIOS ATUALIZADO COM SUCESSO!")
else:
    print("❌ Erro: Nenhum dado válido.")