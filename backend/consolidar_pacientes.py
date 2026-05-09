import os
import re
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

print("--- 🔄 CONSOLIDADOR DE PACIENTES (MPI) V2 - FILTRO DE CPF ---")

SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro Supabase: {e}")
    exit()

def limpar_cpf(valor):
    if pd.isna(valor):
        return None
    # Remove tudo que não for número (tira letras, pontos, traços e palavras como 'Responsável')
    numeros = re.sub(r'[^0-9]', '', str(valor))
    # Se sobrar um número válido (11 dígitos para CPF), ele mantém. Se não, vira nulo.
    if len(numeros) == 11:
        return numeros
    return None

def consolidar_pacientes():
    print(">> Baixando base histórica da Regulação...")
    res_reg = supabase.table("regulacao").select("nome_paciente, cns_paciente, cns, cpf_medico_solicitante, data_nascimento, nome_mae, municipio, telefone").execute()
    df_reg = pd.DataFrame(res_reg.data)
    
    print(">> Baixando base do IndicaSUS...")
    res_ind = supabase.table("indicasus_leitos").select("nome_paciente, cns, cpf, data_nascimento, nome_mae, municipio_residencia").execute()
    df_ind = pd.DataFrame(res_ind.data)

    if not df_reg.empty:
        df_reg['cns_final'] = df_reg['cns_paciente'].fillna(df_reg['cns'])
        df_reg = df_reg[['nome_paciente', 'cns_final', 'data_nascimento', 'nome_mae', 'municipio', 'telefone']].rename(
            columns={'cns_final': 'cns', 'municipio': 'municipio_residencia'}
        )
        
    if not df_ind.empty:
        df_ind = df_ind[['nome_paciente', 'cns', 'cpf', 'data_nascimento', 'nome_mae', 'municipio_residencia']]

    print(">> Mesclando e removendo duplicidades...")
    df_full = pd.concat([df_reg, df_ind], ignore_index=True)
    
    df_full['nome_paciente'] = df_full['nome_paciente'].str.strip().str.upper()
    df_full['cns'] = df_full['cns'].str.replace(r'[^0-9]', '', regex=True)
    
    # Aplica o novo filtro de CPF
    if 'cpf' in df_full.columns:
        df_full['cpf'] = df_full['cpf'].apply(limpar_cpf)
    
    df_full = df_full.dropna(subset=['nome_paciente'])
    df_full = df_full[~df_full['nome_paciente'].isin(['APROVADA', 'PENDENTE', 'PACIENTE DESCONHECIDO'])]

    df_full['qtd_nulos'] = df_full.isnull().sum(axis=1)
    df_full = df_full.sort_values('qtd_nulos')

    df_unicos = df_full.drop_duplicates(subset=['cns'], keep='first').copy()
    
    mask_sem_cns = df_unicos['cns'].isna() | (df_unicos['cns'] == '')
    df_sem_cns = df_unicos[mask_sem_cns].drop_duplicates(subset=['nome_paciente', 'data_nascimento'], keep='first')
    df_com_cns = df_unicos[~mask_sem_cns]
    
    df_final = pd.concat([df_com_cns, df_sem_cns]).reset_index(drop=True)
    
    print(f">> Identificados {len(df_final)} pacientes únicos. Iniciando carga...")
    
    sucessos = 0
    lote = []
    
    for _, row in df_final.iterrows():
        nasc = row.get('data_nascimento')
        if pd.notna(nasc) and len(str(nasc)) > 5:
            try:
                if '/' in str(nasc):
                    nasc = datetime.strptime(str(nasc).split(' ')[0], "%d/%m/%Y").strftime("%Y-%m-%d")
                else:
                    nasc = str(nasc).split('T')[0]
            except:
                nasc = None
        else:
            nasc = None

        registro = {
            "nome_completo": row['nome_paciente'],
            "cns": row['cns'] if pd.notna(row['cns']) and row['cns'] else None,
            "cpf": row.get('cpf') if pd.notna(row.get('cpf')) and row.get('cpf') else None,
            "data_nascimento": nasc,
            "nome_mae": row.get('nome_mae') if pd.notna(row.get('nome_mae')) else None,
            "municipio_residencia": row.get('municipio_residencia') if pd.notna(row.get('municipio_residencia')) else None,
            "telefone": row.get('telefone') if pd.notna(row.get('telefone')) else None,
            "ultima_atualizacao": datetime.now().isoformat()
        }
        lote.append(registro)

        if len(lote) >= 100:
            try:
                supabase.table("pacientes").upsert(lote, on_conflict="cns").execute()
                sucessos += len(lote)
                print(f"   Enviados {sucessos} pacientes...", end="\r")
            except Exception as e:
                # Se falhar o lote, insere um por um para não perder 99 pacientes por causa de 1
                for item in lote:
                    try:
                        supabase.table("pacientes").upsert(item, on_conflict="cns").execute()
                        sucessos += 1
                    except:
                        pass
                print(f"\n   ⚠️ Lote com conflito tratado individualmente. Sucessos até agora: {sucessos}")
            lote = []

    if lote:
        try:
            supabase.table("pacientes").upsert(lote, on_conflict="cns").execute()
            sucessos += len(lote)
        except:
            for item in lote:
                try:
                    supabase.table("pacientes").upsert(item, on_conflict="cns").execute()
                    sucessos += 1
                except:
                    pass

    print(f"\n✅ Migração concluída! {sucessos} pacientes totais processados na tabela Mestre.")

if __name__ == "__main__":
    consolidar_pacientes()