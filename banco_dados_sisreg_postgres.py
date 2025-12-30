import pandas as pd
import glob
import os
import json
import time
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- 2. PROCESSAMENTO: CSV -> BANCO LOCAL -> JSON (V52 - SUPER ROBUSTO) ---")

# --- CONFIGURAÇÕES ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# --- CONEXÃO SQLITE ---
engine = create_engine(f"sqlite:///{CAMINHO_DB}")

# --- LEITURA DOS ARQUIVOS ---
print("   -> Lendo arquivos CSV...")
arquivos_csv = glob.glob(os.path.join(PASTA_CSV, "*.csv"))

if not arquivos_csv:
    print("      ⚠️ ERRO: Nenhum arquivo CSV encontrado em SISREG_Export.")
    exit()

dfs = []
for arq in arquivos_csv:
    # Tenta várias codificações até conseguir ler corretamente
    for encoding in ['latin-1', 'utf-8', 'cp1252']:
        try:
            temp = pd.read_csv(arq, sep=';', encoding=encoding, on_bad_lines='skip', low_memory=False)
            # Verifica se leu direito (se tem mais de 1 coluna)
            if len(temp.columns) > 1:
                # Normaliza colunas para verificar se achamos a chave
                cols_norm = [unidecode(c.strip().lower()) for c in temp.columns]
                # Verifica se tem alguma coluna de solicitação
                if any("solicitacao" in c for c in cols_norm):
                    print(f"      Lido com sucesso ({encoding}): {os.path.basename(arq)}")
                    dfs.append(temp)
                    break
        except:
            continue

if dfs:
    df = pd.concat(dfs, ignore_index=True)
    print(f"   -> Total bruto: {len(df)} linhas.")
    
    # --- 1. NORMALIZAÇÃO INTELIGENTE ---
    # Limpa nomes das colunas
    df.columns = [unidecode(c.strip().lower().replace(" ", "_").replace(".", "")) for c in df.columns]
    
    # Debug: Mostra colunas encontradas para saber se deu certo
    # print(f"      Colunas encontradas: {list(df.columns)}")

    # --- 2. LOCALIZADOR DE COLUNAS ---
    # Em vez de um mapa fixo, procuramos a coluna correta dinamicamente
    def achar_coluna(termos, obrigatorio=False):
        for col in df.columns:
            # Verifica se todos os termos estão no nome da coluna
            if all(t in col for t in termos):
                return col
        return None

    # Mapeia colunas críticas
    col_id = achar_coluna(["n", "solicitacao"]) or achar_coluna(["cod", "solicitacao"])
    col_paciente = achar_coluna(["nome", "paciente"])
    col_data = achar_coluna(["data", "solicitacao"])
    col_status = achar_coluna(["status"]) or achar_coluna(["situacao"])
    col_procedimento = achar_coluna(["procedimento", "solicitado"]) or achar_coluna(["procedimento"])
    col_aih = achar_coluna(["n", "aih"]) or "aih"
    col_cns = achar_coluna(["cns", "paciente"]) or "cns"
    col_carater = achar_coluna(["classificacao"]) or achar_coluna(["carater"])

    # Se não achou o ID, não tem como continuar
    if not col_id:
        print("      ❌ ERRO: Não foi possível identificar a coluna 'N. da Solicitação'.")
        print(f"      Colunas disponíveis: {list(df.columns)}")
        exit()

    # Renomeia para o padrão do sistema
    df.rename(columns={
        col_id: 'cod_solicitacao',
        col_paciente: 'nome_paciente',
        col_data: 'data_solicitacao',
        col_status: 'situacao',
        col_procedimento: 'procedimento',
        col_aih: 'aih',
        col_cns: 'cns_paciente',
        col_carater: 'carater'
    }, inplace=True)

    # --- 3. LIMPEZA ---
    # Preenche colunas faltantes não críticas
    for col in ['aih', 'cns_paciente', 'carater']:
        if col not in df.columns: df[col] = "---"

    # Converte Data
    df['data_iso'] = pd.to_datetime(df['data_solicitacao'], dayfirst=True, errors='coerce')
    
    # Filtro de Duplicatas (Mantém o status mais recente)
    if 'data_iso' in df.columns:
        df.sort_values(by='data_iso', ascending=False, inplace=True)
    
    # Remove linhas inválidas (sem código)
    df = df[df['cod_solicitacao'].notna()]
    # Remove se for só "N/A" string
    df = df[df['cod_solicitacao'].astype(str).str.contains(r'\d')] # Tem que ter número

    total_antes = len(df)
    df.drop_duplicates(subset=['cod_solicitacao'], keep='first', inplace=True)
    print(f"   -> Deduplicação: {len(df)} registros válidos.")

    # --- 4. SALVAR ---
    # Banco
    df_save = df.copy()
    if 'data_iso' in df_save.columns:
        df_save['data_iso'] = df_save['data_iso'].astype(str)
    df_save.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)

    # JSON
    # Recupera Links de PDF antigos se existirem
    links_map = {}
    if os.path.exists(CAMINHO_JSON):
        try:
            with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
                dados_antigos = json.load(f)
            for row in dados_antigos:
                if row.get('aih') and row.get('arquivo_pdf'):
                    k = str(row['aih']).replace(".", "").replace("-", "").strip()
                    links_map[k] = row['arquivo_pdf']
        except: pass

    def get_pdf(row):
        k = str(row.get('aih', '')).replace(".", "").replace("-", "").strip()
        return links_map.get(k, None)

    df_save['arquivo_pdf'] = df_save.apply(get_pdf, axis=1)

    # Renomeia para o HTML
    df_json = df_save.rename(columns={
        'data_solicitacao': 'data_visual',
        'nome_paciente': 'paciente',
        'cns_paciente': 'cns',
        'cod_solicitacao': 'num_sol',
        'procedimento': 'proc',
        'situacao': 'status'
    })

    cols_export = ['data_visual', 'paciente', 'cns', 'num_sol', 'aih', 'proc', 'status', 'carater', 'data_iso', 'arquivo_pdf']
    cols_finais = [c for c in cols_export if c in df_json.columns]
    
    df_json[cols_finais].to_json(CAMINHO_JSON, orient='records', force_ascii=False, indent=4)
    print("✅ JSON gerado com sucesso!")

else:
    print("❌ Nenhum dado válido encontrado nos CSVs.")