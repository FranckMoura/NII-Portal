import sqlite3
import pandas as pd
from supabase import create_client, Client
import sys
import os

print("--- ⏳ MIGRAÇÃO DE HISTÓRICO V2 (CORREÇÃO DE DATAS) ---")

# --- 1. CREDENCIAIS ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

# Caminho do banco SQLite
ARQUIVO_DB = os.path.join(os.path.dirname(__file__), "banco_interno_nii.db")

if not os.path.exists(ARQUIVO_DB):
    print(f"❌ Erro: O arquivo '{ARQUIVO_DB}' não foi encontrado.")
    sys.exit()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    sys.exit()

# --- 2. LER DADOS (USANDO DATA_ISO) ---
print(f"📂 Lendo banco antigo...")
conn = sqlite3.connect(ARQUIVO_DB)

# AQUI ESTÁ A CORREÇÃO: Pegamos 'data_iso' em vez de 'data_solicitacao'
query = """
SELECT 
    cod_solicitacao,
    aih,
    nome_paciente,
    cns_paciente,
    data_iso as data_solicitacao_real, -- Usa a coluna ISO (YYYY-MM-DD)
    data_da_autorizacao,
    data_da_alta,
    data_da_internacao,
    situacao,
    procedimento,
    procedimento_trocado,
    medico_solicitante,
    cpf_medico_executante,
    classificacao_de_risco,
    carater,
    nome_da_clinica
FROM sisreg_solicitacoes
"""
df = pd.read_sql_query(query, conn)
conn.close()

print(f"   ✅ {len(df)} registros carregados para correção.")

# --- 3. FUNÇÕES DE LIMPEZA ---
def limpar(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan': return None
    return str(val).strip().upper()

def garantir_formato_iso(val):
    # Garante que a data esteja em YYYY-MM-DD
    if pd.isna(val) or str(val).strip() == '': return None
    s = str(val).strip().split()[0] # Tira a hora se tiver
    
    # Se ainda estiver em DD/MM/YYYY, inverte
    if '/' in s:
        try:
            partes = s.split('/')
            # Verifica se é D/M/Y ou Y/M/D (embora ISO deva ser Y-M-D)
            if len(partes[2]) == 4: # DD/MM/YYYY
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
        except: return None
    
    # Se já estiver YYYY-MM-DD, retorna (verificação simples)
    if '-' in s and len(s.split('-')[0]) == 4:
        return s
        
    return None

def traduzir_carater(val):
    s = str(val).strip()
    if '10' in s: return 'ELETIVA'
    if '11' in s: return 'URGÊNCIA'
    return s.upper()

registros = []
print("⚙️  Processando datas...")

for _, row in df.iterrows():
    # DATA SOLICITACAO: Usa a coluna data_iso (já deve estar YYYY-MM-DD)
    dt_sol = garantir_formato_iso(row['data_solicitacao_real'])
    
    # DATA AUTORIZACAO: Tenta converter se estiver DD/MM/YYYY
    dt_aut = garantir_formato_iso(row['data_da_autorizacao'])

    item = {
        "num_solicitacao": str(row['cod_solicitacao']).strip(),
        "num_aih": limpar(row['aih']),
        "nome_paciente": limpar(row['nome_paciente']),
        "cns_paciente": limpar(row['cns_paciente']),
        
        "data_solicitacao": dt_sol, # Agora vai correto!
        "data_autorizacao": dt_aut,
        "data_alta": garantir_formato_iso(row['data_da_alta']),
        "data_internacao": garantir_formato_iso(row['data_da_internacao']),
        
        "status": limpar(row['situacao']),
        "procedimento_solicitado": limpar(row['procedimento']),
        "procedimento_autorizado": limpar(row['procedimento_trocado']) if pd.notna(row['procedimento_trocado']) else limpar(row['procedimento']),
        "medico_solicitante": limpar(row['medico_solicitante']),
        "medico_executante": limpar(row['cpf_medico_executante']),
        "classificacao_risco": limpar(row['classificacao_de_risco']),
        "carater_internacao": traduzir_carater(row['carater']),
        "nome_clinica": limpar(row['nome_da_clinica'])
    }
    registros.append(item)

# --- 4. ENVIAR ---
if registros:
    print(f"☁️  Atualizando datas de {len(registros)} registros...")
    batch_size = 500
    for i in range(0, len(registros), batch_size):
        batch = registros[i:i + batch_size]
        try:
            supabase.table('regulacao').upsert(batch).execute()
            sys.stdout.write(f"\r   Progresso: {int(((i+len(batch))/len(registros))*100)}%")
            sys.stdout.flush()
        except Exception as e:
            print(f"\n   Erro no lote {i}: {e}")
            
    print("\n\n✅ FEITO! Agora o filtro de 2024 deve funcionar.")
else:
    print("Nenhum dado para processar.")