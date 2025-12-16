import pandas as pd
from sqlalchemy import create_engine, text
import os
import re

print("--- RELATÓRIO DE AUDITORIA FINANCEIRA V2 (COM LIMPEZA DE CHAVE) ---")

# --- CONFIGURAÇÕES ---
USUARIO_DB = "postgres"
SENHA_DB = "admin123" 
HOST_DB = "localhost"
NOME_DB = "nii_portal"

# --- CONEXÃO ---
url_db = f"postgresql://{USUARIO_DB}:{SENHA_DB}@{HOST_DB}/{NOME_DB}"
engine = create_engine(url_db)

print(">> Carregando tabelas do Banco de Dados...")

try:
    # 1. Carrega SISREG
    df_sisreg = pd.read_sql("SELECT * FROM sisreg_solicitacoes", engine)
    print(f"   [SISREG] {len(df_sisreg)} registros.")

    # 2. Carrega FATURAMENTO
    df_fat = pd.read_sql("SELECT * FROM faturamento_producao", engine)
    print(f"   [FATURAMENTO] {len(df_fat)} registros.")

except Exception as e:
    print(f"❌ Erro ao ler banco: {e}")
    exit()

# --- HIGIENIZAÇÃO DAS CHAVES ---
print("\n>> Higienizando colunas AIH...")

def limpar_apenas_numeros(serie):
    return serie.astype(str).str.replace(r'[^0-9]', '', regex=True)

df_sisreg['aih_limpa'] = limpar_apenas_numeros(df_sisreg['aih'])
df_fat['aih_limpa'] = limpar_apenas_numeros(df_fat['aih'])

# --- CRUZAMENTO ---
print(">> Cruzando dados...")

# Filtra SISREG (Apenas Aprovados e com AIH válida)
df_sisreg_validas = df_sisreg[
    (df_sisreg['status'].str.contains('Aprovado', case=False, na=False)) & 
    (df_sisreg['aih_limpa'].str.len() > 5)
].copy()

df_merge = pd.merge(
    df_sisreg_validas, 
    df_fat, 
    on='aih_limpa', 
    how='left', 
    suffixes=('_sisreg', '_fat'),
    indicator=True
)

df_encontrados = df_merge[df_merge['_merge'] == 'both']
df_nao_faturado = df_merge[df_merge['_merge'] == 'left_only'].copy()

print(f"\n📊 RESUMO DA AUDITORIA:")
print(f"   Total Aprovado Sisreg: {len(df_sisreg_validas)}")
print(f"   ✅ FATURADO: {len(df_encontrados)}")
print(f"   ⚠️ PERDA POTENCIAL: {len(df_nao_faturado)}")

# --- EXPORTAR RELATÓRIO ---
arquivo_saida = r"C:\Users\DELL\OneDrive\NII-Portal-1\RELATORIO_NAO_FATURADOS.xlsx"
print(f"\n>> Gerando Excel: {arquivo_saida} ...")

coluna_data = next((c for c in df_sisreg.columns if 'data' in c and 'iso' not in c), 'data_solicitacao')
cols_export = ['aih_limpa', 'paciente', coluna_data, 'proc', 'status']
cols_finais = [c for c in cols_export if c in df_nao_faturado.columns]

df_export = df_nao_faturado[cols_finais].sort_values(by=coluna_data, ascending=False)
df_export.rename(columns={'aih_limpa': 'AIH'}, inplace=True)

try:
    df_export.to_excel(arquivo_saida, index=False)
    print("✅ Relatório Excel gerado com sucesso!")
except Exception as e:
    print(f"⚠️ Erro ao salvar Excel: {e}")