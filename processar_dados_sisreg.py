import pandas as pd
import glob
import os
import json
import time
from unidecode import unidecode
from sqlalchemy import create_engine, text

print("--- 2. PROCESSAMENTO: CSV -> BANCO -> JSON (V54 - COM RELATÓRIOS AUTOMÁTICOS) ---")

# --- CONFIGURAÇÕES ---
PASTA_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_ARQUIVOS = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos"
CAMINHO_DB = os.path.join(PASTA_ARQUIVOS, "banco_interno_nii.db")
CAMINHO_JSON = os.path.join(PASTA_ARQUIVOS, "dados_sisreg.json")

if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

# --- CONEXÃO SQLITE ---
engine = create_engine(f"sqlite:///{CAMINHO_DB}")

# --- LEITURA ---
print("   -> Lendo arquivos CSV...")
arquivos_csv = glob.glob(os.path.join(PASTA_CSV, "*.csv"))

if not arquivos_csv:
    print("      ⚠️ ERRO: Nenhum CSV encontrado em SISREG_Export.")
    exit()

dfs = []
for arq in arquivos_csv:
    for encoding in ['latin-1', 'utf-8', 'cp1252']:
        try:
            temp = pd.read_csv(arq, sep=';', encoding=encoding, on_bad_lines='skip', low_memory=False)
            if len(temp.columns) > 1:
                # Normaliza para busca
                cols_norm = [unidecode(c.strip().lower()) for c in temp.columns]
                if any("solicitacao" in c for c in cols_norm):
                    print(f"      Lido com sucesso: {os.path.basename(arq)}")
                    dfs.append(temp)
                    break
        except: continue

if dfs:
    df = pd.concat(dfs, ignore_index=True)
    
    # --- 1. LOCALIZADOR DE COLUNAS PRECISO ---
    # Normaliza nomes das colunas originais para facilitar a busca
    df.columns = [unidecode(c.strip().lower().replace(" ", "_").replace(".", "")) for c in df.columns]
    
    def achar(termos_obrigatorios, termos_excluir=[]):
        # Procura coluna que tenha TODOS os termos obrigatórios e NENHUM dos termos excluir
        for col in df.columns:
            if all(t in col for t in termos_obrigatorios):
                if not any(e in col for e in termos_excluir):
                    return col
        return None

    # Mapeamento Inteligente
    col_id = achar(["n", "solicitacao"]) or achar(["cod", "solicitacao"])
    col_paciente = achar(["nome", "paciente"])
    col_cns = achar(["cns", "paciente"])
    col_data = achar(["data", "solicitacao"])
    col_proc = achar(["procedimento", "solicitado"]) or achar(["procedimento"])
    
    # CORREÇÃO CRÍTICA: Procura status ESPECÍFICO de internação
    col_status = achar(["status", "internacao"]) or achar(["situacao", "internacao"]) or achar(["status", "solicitacao"])
    
    # CORREÇÃO CRÍTICA: AIH
    col_aih = achar(["n", "aih"]) or achar(["aih"])
    
    # CORREÇÃO CRÍTICA: Caráter
    col_carater = achar(["carater", "internacao"]) or achar(["classificacao", "risco"])

    # Renomear
    mapa = {
        col_id: 'cod_solicitacao',
        col_paciente: 'nome_paciente',
        col_cns: 'cns_paciente',
        col_data: 'data_solicitacao',
        col_proc: 'procedimento',
        col_status: 'situacao',
        col_aih: 'aih',
        col_carater: 'carater'
    }
    # Remove chaves None (caso não ache alguma coluna)
    mapa = {k: v for k, v in mapa.items() if k}
    
    df.rename(columns=mapa, inplace=True)
    
    print(f"      Colunas Mapeadas: Status='{col_status}' | AIH='{col_aih}' | Caráter='{col_carater}'")

    # --- 2. TRADUÇÃO E LIMPEZA ---
    
    # TRADUÇÃO DO CARÁTER (11 -> Urgência, 10 -> Eletiva)
    if 'carater' in df.columns:
        # Converte para string primeiro para garantir
        df['carater'] = df['carater'].astype(str).str.replace(r'\.0$', '', regex=True) # Remove .0 se tiver
        mapeamento_carater = {
            '11': 'Urgência',
            '10': 'Eletiva',
            'nan': '---',
            'None': '---'
        }
        df['carater'] = df['carater'].map(mapeamento_carater).fillna(df['carater']) # Se não for 10 ou 11, mantém o original

    # GARANTIA DE STATUS
    if 'situacao' not in df.columns:
        df['situacao'] = "Pendente" # Se não achou a coluna, assume pendente
    else:
        # Preenche vazios com Pendente
        df['situacao'] = df['situacao'].fillna("Pendente")
        # Se estiver vazio string "", põe Pendente
        df.loc[df['situacao'] == "", 'situacao'] = "Pendente"

    # GARANTIA DE AIH
    if 'aih' not in df.columns: df['aih'] = "---"
    df['aih'] = df['aih'].fillna("---")

    # --- 3. DEDUPLICAÇÃO E DATAS ---
    df['data_iso'] = pd.to_datetime(df['data_solicitacao'], dayfirst=True, errors='coerce')
    
    # Remove linhas inválidas (sem código de solicitação)
    df = df[df['cod_solicitacao'].notna()]
    df = df[df['cod_solicitacao'].astype(str).str.contains(r'\d')] # Tem que ter número

    # Ordena para manter o mais recente
    if 'data_iso' in df.columns:
        df.sort_values(by='data_iso', ascending=False, inplace=True)
    
    df.drop_duplicates(subset=['cod_solicitacao'], keep='first', inplace=True)
    print(f"   -> Deduplicação final: {len(df)} registros.")

    # --- 4. SALVAR ---
    # SQLite
    df_save = df.copy()
    if 'data_iso' in df_save.columns:
        df_save['data_iso'] = df_save['data_iso'].astype(str)
    df_save.to_sql('sisreg_solicitacoes', engine, if_exists='replace', index=False)

    # --- 5. CRIAR RELATÓRIOS SALVOS (VIEWS) NO BANCO ---
    print("   -> Criando atalhos de relatórios (Views)...")
    try:
        with engine.connect() as conn:
            # View 1: Status
            conn.execute(text("DROP VIEW IF EXISTS relatorio_status"))
            conn.execute(text("""
                CREATE VIEW relatorio_status AS
                SELECT situacao, COUNT(*) as quantidade
                FROM sisreg_solicitacoes
                GROUP BY situacao
                ORDER BY quantidade DESC
            """))

            # View 2: Urgência vs Eletiva
            conn.execute(text("DROP VIEW IF EXISTS relatorio_urgencia"))
            conn.execute(text("""
                CREATE VIEW relatorio_urgencia AS
                SELECT carater, COUNT(*) as quantidade
                FROM sisreg_solicitacoes
                GROUP BY carater
                ORDER BY quantidade DESC
            """))

            # View 3: Top Procedimentos
            conn.execute(text("DROP VIEW IF EXISTS relatorio_top_procedimentos"))
            conn.execute(text("""
                CREATE VIEW relatorio_top_procedimentos AS
                SELECT procedimento, COUNT(*) as qtd
                FROM sisreg_solicitacoes
                GROUP BY procedimento
                ORDER BY qtd DESC
                LIMIT 10
            """))
            # Em versões novas do SQLAlchemy, precisa do commit para DDL
            try: conn.commit() 
            except: pass
            
    except Exception as e:
        print(f"      ⚠️ Aviso: Não foi possível criar as Views: {e}")

    # JSON (Lógica de PDF mantida)
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
    print("✅ JSON atualizado com traduções e Relatórios SQL Criados!")

else:
    print("❌ Nenhum dado válido encontrado.")