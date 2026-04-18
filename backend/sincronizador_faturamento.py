import os
import csv
import pandas as pd
from supabase import create_client, Client
import math

print("--- 💰 NII DATA SYNC: FATURAMENTO SOULMV -> SUPABASE ---")

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

PASTA_MV = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\bd_soulmv"
ARQ_FATURAMENTO = os.path.join(PASTA_MV, "tabelas_faturamento_analitica.CSV")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def limpar_texto_mv(valor):
    if pd.isna(valor) or valor == "": return None
    texto = str(valor).strip()
    if texto.startswith('="') and texto.endswith('"'): texto = texto[2:-1]
    elif texto.startswith('="'): texto = texto[2:]
    if texto.startswith('"') and texto.endswith('"'): texto = texto[1:-1]
    if texto == "": return None
    return texto

def converter_numero(valor):
    texto = limpar_texto_mv(valor)
    if not texto: return 0
    try:
        # Se vier com vírgula (padrão Brasil), converte para ponto (padrão Banco de Dados)
        texto = texto.replace(',', '.')
        return float(texto)
    except:
        return 0

def ler_csv_faturamento(caminho):
    with open(caminho, 'r', encoding='latin1', errors='replace') as f:
        reader = csv.reader(f)
        dados_limpos = []
        for row in reader:
            if not row: continue
            if len(row) == 1:
                sub_reader = csv.reader([row[0]])
                try: campos = next(sub_reader)
                except: continue
            else:
                campos = row
            dados_limpos.append([limpar_texto_mv(c) for c in campos])
            
    if not dados_limpos: return pd.DataFrame()
    colunas = [str(c).lower().strip() for c in dados_limpos[0]]
    return pd.DataFrame(dados_limpos[1:], columns=colunas)

if os.path.exists(ARQ_FATURAMENTO):
    print("\n📂 Lendo tabelas_faturamento_analitica.CSV...")
    try:
        df_fat = ler_csv_faturamento(ARQ_FATURAMENTO)
        registros_prontos = []
        
        for _, row in df_fat.iterrows():
            try:
                # Ajuste o nome das chaves abaixo de acordo com a primeira linha do seu CSV
                atd = int(row.get('atendimento', 0))
                if atd == 0: continue
                
                registros_prontos.append({
                    "mes_competencia": row.get('mes_competencia'),
                    "atendimento_mv": atd,
                    "numero_aih": row.get('numero_aih'),
                    "nome_paciente": row.get('paciente'),
                    "data_internacao": row.get('data_internacao'),
                    "data_alta": row.get('data_alta'),
                    "cod_prestador": row.get('cod_prestador_executante'),
                    "codigo_sus": row.get('codigo_sus'),
                    "descricao_procedimento": row.get('descricao_procedimento'),
                    "qtd": converter_numero(row.get('qtd') or row.get('quantidade')),
                    "valor_hospitalar": converter_numero(row.get('valor_hospitalar')),
                    "valor_profissional": converter_numero(row.get('valor_profissional')),
                    "valor_total_item": converter_numero(row.get('valor_total_item'))
                })
            except Exception as e:
                continue

        total = len(registros_prontos)
        tamanho_lote = 1000 # Lotes maiores pois são muitos itens
        lotes = math.ceil(total / tamanho_lote)
        
        print(f"🚀 Iniciando envio de {total} itens de faturamento em {lotes} lotes...")
        for i in range(lotes):
            inicio = i * tamanho_lote
            fim = inicio + tamanho_lote
            lote_atual = registros_prontos[inicio:fim]
            try:
                supabase.table("faturamento_analitico_mv").insert(lote_atual).execute()
                print(f"   ✅ Lote {i+1}/{lotes} enviado!")
            except Exception as e:
                print(f"   ❌ Erro no lote {i+1}: {e}")

    except Exception as e:
        print(f"❌ Erro ao processar Faturamento: {e}")
else:
    print(f"⚠️ Arquivo {ARQ_FATURAMENTO} não encontrado.")

print("\n🎉 CONCLUÍDO! O Supabase agora possui o espelho financeiro completo.")