import pandas as pd
import glob
import os
import math
from supabase import create_client, Client

print("==========================================================")
print(" 🏥 PROCESSADOR E UPLOAD CNES (ST e PF - BLINDADO) ")
print("==========================================================")

# Pasta onde você colocou os arquivos .csv convertidos no TabWin
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\bases_cnes_csv"

# SUAS CREDENCIAIS DO SUPABASE (Aviso: Use a SERVICE ROLE KEY para ter permissão de gravação)
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "SUA_CHAVE_SERVICE_ROLE_AQUI" 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}"); exit()

def upload_em_lotes(df, nome_tabela, tamanho_lote=1000):
    total_linhas = len(df)
    lotes = math.ceil(total_linhas / tamanho_lote)
    print(f"🚀 Iniciando injeção em '{nome_tabela}': {total_linhas} registros em {lotes} lotes.")
    
    for i in range(lotes):
        inicio = i * tamanho_lote
        fim = inicio + tamanho_lote
        lote_df = df.iloc[inicio:fim]
        
        dados_json = lote_df.to_dict(orient='records')
        try:
            # Usamos UPSERT para atualizar se já existir, ou inserir se for novo
            supabase.table(nome_tabela).upsert(dados_json).execute()
            print(f"   ✅ Lote {i+1}/{lotes} enviado com sucesso!")
        except Exception as e:
            print(f"   ❌ Erro no lote {i+1}: {e}")

# Busca todos os arquivos CSV na pasta
arquivos = glob.glob(os.path.join(PASTA_CSV, "*.csv"))
print(f">> Encontrados {len(arquivos)} arquivos CSV na pasta para processar...\n")

for arq in arquivos:
    nome_arquivo = os.path.basename(arq).upper()
    print(f"--- Processando arquivo: {nome_arquivo} ---")
    
    try:
        # Lê o CSV gerado pelo TabWin (Geralmente separado por ; e encoding latin1)
        df = pd.read_csv(arq, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        df = df.fillna('') # Troca nulos por vazio
        
        # Padroniza as colunas lidas do arquivo
        colunas_originais = [c.upper() for c in df.columns]
        df.columns = colunas_originais
        
        # ========================================================
        # LÓGICA PARA ARQUIVO ST (ESTABELECIMENTOS)
        # ========================================================
        if nome_arquivo.startswith("ST"):
            df_st = pd.DataFrame()
            
            col_cnes = next((c for c in colunas_originais if 'CNES' in c), None)
            col_fantasia = next((c for c in colunas_originais if 'FANTASIA' in c), None)
            col_razao = next((c for c in colunas_originais if 'NOME' in c or 'RAZAO' in c), None)
            
            if not col_cnes or not col_razao:
                print(f"⚠️ Colunas vitais (CNES/NOME) ausentes no arquivo {nome_arquivo}. Pulando.")
                continue
                
            df_st['cnes'] = df[col_cnes].str.strip()
            df_st['nome_fantasia'] = df[col_fantasia].str.strip().str.upper() if col_fantasia else ''
            df_st['razao_social'] = df[col_razao].str.strip().str.upper()
            
            # Remove linhas sem CNES e remove duplicações
            df_st = df_st[df_st['cnes'] != '']
            df_st = df_st.drop_duplicates(subset=['cnes'], keep='first')
            
            upload_em_lotes(df_st, 'cnes_estabelecimentos')

        # ========================================================
        # LÓGICA PARA ARQUIVO PF (PROFISSIONAIS)
        # ========================================================
        elif nome_arquivo.startswith("PF"):
            df_pf = pd.DataFrame()
            
            col_cnes = next((c for c in colunas_originais if 'CNES' in c), None)
            col_cns = next((c for c in colunas_originais if 'PROF_SUS' in c or 'CNS' in c), None)
            col_nome = next((c for c in colunas_originais if 'NOME_PROF' in c or 'NOME' in c), None)
            col_cbo = next((c for c in colunas_originais if 'CBO' in c), None)
            
            if not col_cns or not col_nome:
                print(f"⚠️ Colunas vitais (CNS/NOME) ausentes no arquivo {nome_arquivo}. Pulando.")
                continue
                
            df_pf['cnes'] = df[col_cnes].str.strip() if col_cnes else ''
            df_pf['cns_prof'] = df[col_cns].str.strip()
            df_pf['nome_prof'] = df[col_nome].str.strip().str.upper()
            df_pf['cbo'] = df[col_cbo].str.strip() if col_cbo else ''
            
            # Pega o ano e mês a partir do nome do arquivo (ex: PFMT2602 -> 2026/02)
            ano_abrev = nome_arquivo[4:6] # "26"
            mes_abrev = nome_arquivo[6:8] # "02"
            df_pf['comp_ano'] = f"20{ano_abrev}"
            df_pf['comp_mes'] = mes_abrev
            
            # Remove profissionais sem CNS e previne duplicações exatas no mesmo CNES/CBO
            df_pf = df_pf[df_pf['cns_prof'] != '']
            df_pf = df_pf.drop_duplicates(subset=['cns_prof', 'cnes', 'cbo'], keep='first')
            
            upload_em_lotes(df_pf, 'cnes_profissionais')
            
        else:
            print(f"⚠️ Arquivo ignorado (Não começa com ST nem PF): {nome_arquivo}")

    except Exception as e:
        print(f"❌ Erro grave ao processar {nome_arquivo}: {e}")

print("\n🎉 SINCRONIZAÇÃO DO CNES CONCLUÍDA COM SUCESSO!")