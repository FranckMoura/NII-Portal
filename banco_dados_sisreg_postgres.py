import pandas as pd
import glob
import os
import json
import time
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- 2. PROCESSAMENTO: CSV -> BANCO LOCAL -> JSON (V51 - MAPA DE COLUNAS CORRIGIDO) ---")

# --- CONFIGURAÇÕES ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# --- CONEXÃO SQLITE ---
try:
    engine = create_engine(f"sqlite:///{CAMINHO_DB}")
    print("   -> Conexão SQLite OK.")
except Exception as e:
    print(f"❌ Erro ao criar banco: {e}")
    exit()

# --- LEITURA DOS ARQUIVOS ---
print("   -> Lendo arquivos CSV exportados...")
arquivos_csv = glob.glob(os.path.join(PASTA_CSV, "*.csv"))

if not arquivos_csv:
    print("      ⚠️ Nenhum arquivo CSV encontrado! Rode a extração primeiro.")
    exit()

dfs = []
for arq in arquivos_csv:
    try:
        # Tenta ler com ; (padrão SISREG)
        temp = pd.read_csv(arq, sep=';', encoding='latin-1', on_bad_lines='skip', low_memory=False)
        dfs.append(temp)
    except:
        pass

if dfs:
    df = pd.concat(dfs, ignore_index=True)
    print(f"   -> Total bruto de linhas lidas: {len(df)}")
    
    # --- 1. NORMALIZAÇÃO DOS NOMES DAS COLUNAS ---
    # Remove acentos, espaços e deixa minusculo. Ex: "N. da solicitação" vira "n._da_solicitacao"
    df.columns = [unidecode(c.strip().lower().replace(" ", "_").replace(".", "")) for c in df.columns]
    
    # --- 2. MAPEAMENTO CORRETO (AQUI ESTAVA O ERRO) ---
    # Mapeia o nome "feio" do CSV para o nome "bonito" do sistema
    mapa_colunas = {
        'n_da_solicitacao': 'cod_solicitacao',
        'nome_do_paciente': 'nome_paciente',
        'nome_do_procedimento_solicitado': 'procedimento',
        'data_da_solicitacao': 'data_solicitacao',
        'status_da_solicitacao_de_internacao': 'situacao',
        'classificacao_de_risco': 'carater',
        'cns_do_paciente': 'cns_paciente',
        'n_aih': 'aih'
    }
    
    df.rename(columns=mapa_colunas, inplace=True)
    
    # Fallback para "Procedimento" se não achar o nome completo
    if 'nome_do_procedimento' in df.columns and 'procedimento' not in df.columns:
        df.rename(columns={'nome_do_procedimento': 'procedimento'}, inplace=True)

    # Garante que colunas essenciais existam
    for col in ['cod_solicitacao', 'nome_paciente', 'situacao', 'data_solicitacao']:
        if col not in df.columns:
            df[col] = "N/A"

    # --- 3. LIMPEZA E DEDUPLICAÇÃO ---
    # Converte data
    df['data_iso'] = pd.to_datetime(df['data_solicitacao'], dayfirst=True, errors='coerce')
    
    # Remove linhas onde o código é nulo ou N/A
    df = df[df['cod_solicitacao'] != "N/A"]
    df = df[df['cod_solicitacao'].notna()]

    # DEDUPLICAÇÃO REAL
    # Ordena por data (mais recente primeiro) e mantem o primeiro
    # Isso garante que se houver o mesmo código em arquivos diferentes, pega o mais novo
    if 'data_iso' in df.columns:
        df.sort_values(by='data_iso', ascending=False, inplace=True)
    
    total_antes = len(df)
    df.drop_duplicates(subset=['cod_solicitacao'], keep='first', inplace=True)
    print(f"   -> Deduplicação: {total_antes} linhas -> {len(df)} linhas únicas.")

    # --- 4. SALVAR NO BANCO ---
    # Converte datas para string para o SQLite aceitar
    df_save = df.copy()
    if 'data_iso' in df_save.columns:
        df_save['data_iso'] = df_save['data_iso'].astype(str)
        
    df_save.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)
    print("      Banco atualizado com sucesso.")

    # --- 5. GERAR JSON PARA O PORTAL ---
    # Lógica de PDF mantida
    links_map = {}
    if os.path.exists(CAMINHO_JSON):
        try:
            with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
                dados_antigos = json.load(f)
            for row in dados_antigos:
                if 'aih' in row and row['aih'] and 'arquivo_pdf' in row:
                    aih_limpa = str(row['aih']).replace(".", "").replace("-", "").strip()
                    if aih_limpa: links_map[aih_limpa] = row['arquivo_pdf']
        except: pass

    def normalizar_aih(valor):
        if not valor: return ""
        return str(valor).replace(".", "").replace("-", "").strip()

    def aplicar_link(row):
        aih_banco = normalizar_aih(row.get('aih'))
        if aih_banco in links_map: return links_map[aih_banco]
        return None

    df_save['arquivo_pdf'] = df_save.apply(aplicar_link, axis=1)
    
    # Preparar JSON final (Renomeia para as chaves que o HTML espera)
    # HTML espera: data_visual, paciente, cns, num_sol, aih, proc, status, carater
    df_json = df_save.rename(columns={
        'data_solicitacao': 'data_visual',
        'nome_paciente': 'paciente',
        'cns_paciente': 'cns',
        'cod_solicitacao': 'num_sol',
        'procedimento': 'proc',
        'situacao': 'status'
    })
    
    # Seleciona apenas colunas necessárias para o JSON ficar leve
    cols_json = ['data_visual', 'paciente', 'cns', 'num_sol', 'aih', 'proc', 'status', 'carater', 'data_iso', 'arquivo_pdf']
    cols_existentes = [c for c in cols_json if c in df_json.columns]
    
    df_json[cols_existentes].to_json(CAMINHO_JSON, orient='records', force_ascii=False, indent=4)
    print("✅ JSON do Portal gerado corretamente.")

else:
    print("❌ Nenhum dado processado.")