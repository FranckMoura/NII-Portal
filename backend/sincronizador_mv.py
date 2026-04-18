import os
import csv
import pandas as pd
from supabase import create_client, Client
import math

print("--- 🔄 NII DATA SYNC: SOULMV -> SUPABASE (V2 - PARSER INTELIGENTE) ---")

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

PASTA_MV = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\bd_soulmv"
ARQ_PACIENTE = os.path.join(PASTA_MV, "PACIENTE.CSV")
ARQ_ATENDIMENTO = os.path.join(PASTA_MV, "ATENDIMENDO.CSV")

# Conectando no banco de dados da nuvem
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

# Função que entende a "sujeira" do exportador do SOULMV e limpa os dados
def ler_csv_mv(caminho):
    # Usamos latin1 porque bancos Oracle antigos geram arquivos com essa codificação
    with open(caminho, 'r', encoding='latin1', errors='replace') as f:
        reader = csv.reader(f)
        dados_limpos = []
        
        for row in reader:
            if not row: continue
            
            # Se o MV escondeu a linha toda dentro de uma aspa dupla, nós quebramos ela!
            if len(row) == 1:
                linha_real = row[0]
                sub_reader = csv.reader([linha_real])
                try: campos = next(sub_reader)
                except StopIteration: continue
            else:
                campos = row
            
            campos_limpos = []
            for c in campos:
                c = c.strip()
                # Remove a formatação de texto forçada do Excel/MV: ="TEXTO"
                if c.startswith('="') and c.endswith('"'): c = c[2:-1]
                elif c.startswith('="'): c = c[2:]
                
                # Remove aspas perdidas
                if c.startswith('"') and c.endswith('"'): c = c[1:-1]
                
                # Padroniza vazio para Null (None) do banco
                if c == "": c = None
                campos_limpos.append(c)
            
            dados_limpos.append(campos_limpos)
            
    if not dados_limpos: 
        return pd.DataFrame()
    
    # Converte os dados limpos para a estrutura do Pandas
    colunas = [str(c).lower().strip() for c in dados_limpos[0]]
    df = pd.DataFrame(dados_limpos[1:], columns=colunas)
    return df

def enviar_em_lotes(tabela_nome, lista_dicionarios, tamanho_lote=500):
    total = len(lista_dicionarios)
    if total == 0:
        print(f"⚠️ Nenhum registro válido encontrado para '{tabela_nome}'.")
        return

    lotes = math.ceil(total / tamanho_lote)
    print(f"🚀 Iniciando envio para '{tabela_nome}' ({total} registros em {lotes} lotes)...")
    
    for i in range(lotes):
        inicio = i * tamanho_lote
        fim = inicio + tamanho_lote
        lote_atual = lista_dicionarios[inicio:fim]
        
        try:
            # Upsert = Insere pacientes novos e atualiza dados dos que já existem
            supabase.table(tabela_nome).upsert(lote_atual).execute()
            print(f"   ✅ Lote {i+1}/{lotes} enviado com sucesso!")
        except Exception as e:
            print(f"   ❌ Erro no lote {i+1}: {e}")

# ==========================================
# 1. PROCESSAR PACIENTES
# ==========================================
if os.path.exists(ARQ_PACIENTE):
    print("\n📂 Lendo PACIENTE.CSV...")
    try:
        df_pac = ler_csv_mv(ARQ_PACIENTE)
        
        pacientes_prontos = []
        for _, row in df_pac.iterrows():
            if not row.get('codigo_mv'): continue
            
            try: cod = int(row['codigo_mv'])
            except: continue
                
            pacientes_prontos.append({
                "codigo_mv": cod,
                "nome_paciente": row.get('nome_paciente'),
                "nome_social": row.get('nome_social'),
                "cpf": row.get('cpf'),
                "cns": row.get('cns'),
                "data_nascimento": row.get('data_nascimento'),
                "sexo": row.get('sexo'),
                "nome_mae": row.get('nome_mae'),
                "celular": row.get('celular'),
                "email": row.get('email'),
                "endereco_completo": row.get('endereco_completo'),
                "bairro": row.get('bairro'),
                "cep": row.get('cep'),
                "codigo_ibge_cidade": row.get('codigo_ibge_cidade')
            })
            
        enviar_em_lotes("pacientes_mv", pacientes_prontos)

    except Exception as e:
        print(f"❌ Erro ao processar PACIENTES: {e}")
else:
    print(f"⚠️ Arquivo {ARQ_PACIENTE} não encontrado.")

# ==========================================
# 2. PROCESSAR ATENDIMENTOS
# ==========================================
if os.path.exists(ARQ_ATENDIMENTO):
    print("\n📂 Lendo ATENDIMENDO.CSV...")
    try:
        df_atd = ler_csv_mv(ARQ_ATENDIMENTO)
        
        atendimentos_prontos = []
        for _, row in df_atd.iterrows():
            if not row.get('atendimento_mv'): continue
            
            try:
                atd_mv = int(row['atendimento_mv'])
                # Tenta puxar o código do paciente se existir para fazer o vínculo
                cod_pac = int(row['codigo_mv_paciente']) if row.get('codigo_mv_paciente') else None
            except: continue
                
            atendimentos_prontos.append({
                "atendimento_mv": atd_mv,
                "codigo_mv_paciente": cod_pac,
                "nome_paciente": row.get('nome_paciente'),
                "data_internacao": row.get('data_internacao'),
                "hora_internacao": row.get('hora_internacao'),
                "data_alta": row.get('data_alta'),
                "leito_atual": row.get('leito_atual'),
                "numero_aih": row.get('numero_aih'),
                "cid_principal": row.get('cid_principal'),
                "medico_responsavel": row.get('medico_responsavel'),
                "status_internado": row.get('status_internado'),
                "indicativo_obito": row.get('indicativo_obito')
            })
            
        enviar_em_lotes("atendimentos_mv", atendimentos_prontos)

    except Exception as e:
        print(f"❌ Erro ao processar ATENDIMENTOS: {e}")
else:
    print(f"⚠️ Arquivo {ARQ_ATENDIMENTO} não encontrado.")

print("\n🎉 SINCRONIZAÇÃO CONCLUÍDA! O Supabase agora possui a base espelho do SOULMV.")