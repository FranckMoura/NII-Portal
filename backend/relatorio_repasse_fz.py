import warnings
import pdfplumber
import pandas as pd
import os
import glob
import re
import unicodedata
import difflib
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

warnings.simplefilter(action='ignore', category=FutureWarning)
pd.set_option('future.no_silent_downcasting', True)

print("--- ROBÔ DE REPASSES MÉDICOS V18 (LEITURA DINÂMICA DA TABELA FILA ZERO) ---")

load_dotenv()
SB_URL = os.getenv("SB_URL")
SB_KEY = os.getenv("SB_KEY")
PASTA_REPASSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repasse")

if not SB_URL or not SB_KEY: exit("❌ Configure o .env")
supabase: Client = create_client(SB_URL, SB_KEY)

MAPA_MESES = {'01':'JANEIRO','02':'FEVEREIRO','03':'MARCO','04':'ABRIL','05':'MAIO','06':'JUNHO','07':'JULHO','08':'AGOSTO','09':'SETEMBRO','10':'OUTUBRO','11':'NOVEMBRO','12':'DEZEMBRO'}

CORRECAO_NOMES = {
    "ANGELICA": "ANGELICA RODRIGUEZ TORRES DE LUCENA",
    "FERNANDO": "FERNANDO CESAR PEREIRA CRUZ",
    "RENAN SOUZA MANCIO": "RENAN SOUZA MANCIO"
}

def ler_valor(texto):
    try: return float(texto.replace('.', '').replace(',', '.'))
    except: return 0.0

def normalizar(texto):
    if not texto: return ""
    return unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('ASCII').strip().upper()

def encontrar_nome_oficial(nome_sujo, lista_oficial):
    nome_sujo = normalizar(nome_sujo)
    if nome_sujo in CORRECAO_NOMES: return CORRECAO_NOMES[nome_sujo]
    termos_proibidos = ['HOSPITAL', 'SANTA HELENA', 'BENEFICENTE', 'TOTAL']
    if any(t in nome_sujo for t in termos_proibidos): return None
    if nome_sujo in lista_oficial: return nome_sujo
    matches = difflib.get_close_matches(nome_sujo, lista_oficial, n=1, cutoff=0.7)
    if matches: return matches[0]
    for oficial in lista_oficial:
        if nome_sujo in oficial or oficial in nome_sujo:
            if len(nome_sujo) > 4: return oficial
    return nome_sujo

def encontrar_arquivos(mes, ano, is_fila_zero=False):
    nome_mes = MAPA_MESES.get(mes)
    padrao_ano = ano[2:]
    
    todas_prods = glob.glob(os.path.join(PASTA_REPASSE, f"*PRODUCAO*{mes}{padrao_ano}*.pdf"))
    if is_fila_zero:
        prods = [f for f in todas_prods if "FILAZERO" in f.upper()]
    else:
        prods = [f for f in todas_prods if "FILAZERO" not in f.upper()]

    todas_receitas = glob.glob(os.path.join(PASTA_REPASSE, f"*RECEITA*{mes}{padrao_ano}*.pdf"))
    if is_fila_zero:
        receitas = [f for f in todas_receitas if "FILAZERO" in f.upper()]
    else:
        receitas = [f for f in todas_receitas if "FILAZERO" not in f.upper()]

    arq_receita = None
    for r in receitas:
        if "PROCEDIMENTO" in r.upper() or "RATEIO" in r.upper(): 
            arq_receita = r; break
    if not arq_receita and receitas: arq_receita = receitas[0] if receitas else None

    vinculos = glob.glob(os.path.join(PASTA_REPASSE, "*.csv"))
    arq_vinculo = None
    for v in vinculos:
        if nome_mes in normalizar(v) and ano in v: arq_vinculo = v; break
    
    return (prods[0] if prods else None), arq_receita, arq_vinculo

def carregar_tabela_referencia(caminho_csv):
    tabela = {}
    if not caminho_csv or not os.path.exists(caminho_csv):
        print("⚠️ Tabela de referência Fila Zero não encontrada!")
        return tabela
        
    tentativas = [(';', 'utf-8-sig'), (';', 'latin-1'), (';', 'cp1252'), (',', 'utf-8-sig'), (',', 'latin-1'), (',', 'cp1252')]
    df = None
    for sep, enc in tentativas:
        try:
            temp_df = pd.read_csv(caminho_csv, skiprows=3, sep=sep, encoding=enc, on_bad_lines='skip')
            temp_df.columns = [str(c).strip() for c in temp_df.columns]
            
            # Verifica dinamicamente se encontrou a coluna de CÓDIGO (Sigtap)
            if any('SIGTAP' in str(c).upper() for c in temp_df.columns):
                df = temp_df; break
        except: continue
            
    if df is None or df.empty:
        print("❌ Não foi possível mapear as colunas da tabela de referência Fila Zero.")
        return tabela
        
    # Encontra os nomes reais das colunas dinamicamente buscando qualquer coisa com 'CIRURGI' ou 'ANESTES'
    col_cod = next((c for c in df.columns if 'SIGTAP' in str(c).upper()), None)
    col_cirurgiao = next((c for c in df.columns if 'CIRURGIAO' in normalizar(c) or 'CIRURGIÃO' in str(c).upper()), None)
    col_anestesista = next((c for c in df.columns if 'ANESTESISTA' in normalizar(c)), None)

    try:
        for _, row in df.iterrows():
            cod = str(row.get(col_cod, '')).strip().split('.')[0]
            if not cod or cod == 'nan': continue
            
            cod_limpo = ''.join(c for c in cod if c.isdigit()).zfill(10)
            if not cod_limpo.startswith('04'): continue
            
            def limpar_val(val):
                if pd.isna(val): return 0.0
                s = str(val).strip().replace('.', '').replace(',', '.')
                try: return float(s)
                except:
                    try: return float(str(val).strip())
                    except: return 0.0
            
            # Pega EXATAMENTE o valor que estiver na célula, sem qualquer cálculo
            val_cirurgiao = limpar_val(row.get(col_cirurgiao, 0.0)) if col_cirurgiao else 0.0
            val_anestesista = limpar_val(row.get(col_anestesista, 0.0)) if col_anestesista else 0.0
            
            tabela[cod_limpo] = {
                'CIRURGIAO': val_cirurgiao,
                'ANESTESISTA': val_anestesista
            }
    except Exception as e:
        print(f"❌ Erro ao processar dados da tabela de apoio: {e}")
    return tabela

def processar_receita_bolo_e_codigos(arquivo):
    if not arquivo: return 0.0, set()
    soma_sp = 0.0
    codigos_blacklist = set()
    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split('\n')
            for line in lines:
                line_upper = line.upper()
                if "TOTAL" in line_upper or "GRUPO" in line_upper or "PÁGINA" in line_upper: continue
                match_cod = re.match(r'^(\d{8,10})', line.strip())
                if match_cod:
                    codigo = match_cod.group(1)
                    valores = re.findall(r'[\d\.]+,\d{2}', line)
                    if len(valores) >= 2:
                        valor_lido = ler_valor(valores[-2])
                        if valor_lido > 0:
                            soma_sp += valor_lido
                            codigos_blacklist.add(codigo)
    return round(soma_sp, 2), codigos_blacklist

def processar_vinculos(arquivo):
    if not arquivo: return pd.DataFrame(columns=['medico', 'peso'])
    tentativas = [(';', 'utf-8-sig'), (';', 'latin-1'), (';', 'cp1252'), (',', 'utf-8-sig'), (',', 'latin-1'), (',', 'cp1252')]
    df = None
    for sep, enc in tentativas:
        try:
            temp_df = pd.read_csv(arquivo, sep=sep, encoding=enc, on_bad_lines='skip')
            if temp_df.shape[1] >= 2: df = temp_df; break  
        except: continue  

    if df is None or df.empty or df.shape[1] < 2: return pd.DataFrame(columns=['medico', 'peso'])

    try:
        df = df.iloc[:, [0, 1]].copy()
        df.columns = ['medico', 'peso']
        pattern = '|'.join(['TOTAL', 'HOSPITAL', 'SANTA HELENA', 'BENEFICENTE'])
        df = df[~df['medico'].astype(str).str.upper().str.contains(pattern, na=False)]
        df['medico'] = df['medico'].apply(normalizar).replace(CORRECAO_NOMES)
        df['peso'] = df['peso'].astype(str).str.strip().str.replace(',', '.')
        df['peso'] = df['peso'].apply(lambda x: float(x) if x != '' and str(x).lower() != 'nan' else 0.0)
        return df
    except: return pd.DataFrame(columns=['medico', 'peso'])

def processar_producao_individual(arquivo, codigos_blacklist, lista_nomes_oficiais):
    if not arquivo: return pd.DataFrame(columns=['medico', 'prod_extra'])
    dados = {}
    medico_atual = None
    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            lines = (page.extract_text() or "").split('\n')
            for line in lines:
                line = line.strip()
                match_med = re.search(r'^([A-Za-zÀ-ÿ\s\.\-\']+?)\s*\(\d+\)$', line)
                if match_med:
                    nome_cru = match_med.group(1).strip()
                    medico_atual = encontrar_nome_oficial(nome_cru, lista_nomes_oficiais)
                    if medico_atual and medico_atual not in dados: dados[medico_atual] = 0.0
                    continue
                
                match_cod_linha = re.search(r'(?:^|\s)(\d{8,10})\s', line)
                valores_moeda = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', line)
                
                if 'medico_atual' in locals() and medico_atual and valores_moeda:
                    line_upper = line.upper()
                    if any(t in line_upper for t in ["TOTAL", "GERAL", "GRUPO", "PÁGINA", "PAGINA", "DIRETO:", "RATEIO:"]): continue
                    if match_cod_linha and match_cod_linha.group(1) in codigos_blacklist: continue 
                    
                    val = ler_valor(valores_moeda[-1])
                    if val > 50000: continue
                    if val > 0: dados[medico_atual] += val
                        
    return pd.DataFrame(list(dados.items()), columns=['medico', 'prod_extra'])

def processar_producao_fila_zero(arquivo, tabela_valores, lista_nomes_oficiais):
    if not arquivo: return pd.DataFrame(columns=['medico', 'prod_extra'])
    dados = {}
    medico_atual = None
    
    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Identifica prestador no formato do SoulMV por página
                match_med = re.search(r'^([A-Za-zÀ-ÿ\s\.\-\']+?)\s*\(\d+\)$', line)
                if match_med:
                    nome_cru = match_med.group(1).strip()
                    medico_atual = encontrar_nome_oficial(nome_cru, lista_nomes_oficiais)
                    if medico_atual and medico_atual not in dados: 
                        dados[medico_atual] = 0.0
                    continue
                
                if medico_atual:
                    line_upper = normalizar(line)
                    if any(t in line_upper for t in ["TOTAL", "GERAL", "GRUPO", "PAGINA"]): continue
                    
                    # Busca código de procedimento
                    match_cod = re.search(r'(04\d{8})', line_upper)
                    if match_cod:
                        codigo_sigtap = match_cod.group(1)
                        
                        # Mapeamento estrito da atividade
                        atividade = None
                        if "ANESTESISTA" in line_upper:
                            atividade = "ANESTESISTA"
                        elif "CIRURGIAO" in line_upper:
                            atividade = "CIRURGIAO"
                        elif "AUXILIAR" in line_upper:
                            continue  # Regra de negócio: Auxiliar desconsiderado
                        
                        if atividade and codigo_sigtap in tabela_valores:
                            # Pega o valor lido DIRETAMENTE da tabela
                            valor_calculado = tabela_valores[codigo_sigtap][atividade]
                            dados[medico_atual] += valor_calculado
                            
    return pd.DataFrame(list(dados.items()), columns=['medico', 'prod_extra'])

def rodar_extracao(mes, ano, is_fila_zero=False):
    competencia_base = f"{mes}/{ano}"
    tag_banco = "FILA ZERO" if is_fila_zero else "PLANO UNICO"
    competencia_db = f"{competencia_base} - {tag_banco}"

    print(f"\n🚀 PROCESSANDO: {competencia_db}")
    arq_prod, arq_rec, arq_vinc = encontrar_arquivos(mes, ano, is_fila_zero)
    
    if not arq_prod and not arq_rec:
        print(f"    ⚠️ Sem arquivos de produção para {tag_banco}.")
        return

    df_pesos = processar_vinculos(arq_vinc)
    lista_nomes_oficiais = df_pesos['medico'].unique().tolist() if not df_pesos.empty else []

    if is_fila_zero:
        valor_bolo_vl_sp = 0.0
        codigos_blacklist = set()
        
        # Localiza a tabela externa com os tetos financeiros
        tabelas_ref = glob.glob(os.path.join(PASTA_REPASSE, "*TABELA_REPASSE_FILAZERO*.csv"))
        arq_tabela_ref = tabelas_ref[0] if tabelas_ref else None
        
        if arq_tabela_ref:
            print(f"    📊 Cruzando dados com a tabela de apoio: {os.path.basename(arq_tabela_ref)}")
            tabela_valores = carregar_tabela_referencia(arq_tabela_ref)
            df_prod = processar_producao_fila_zero(arq_prod, tabela_valores, lista_nomes_oficiais)
        else:
            print("    ❌ ERRO CRÍTICO: O arquivo CSV da TABELA_REPASSE_FILAZERO não foi encontrado em /repasse.")
            df_prod = pd.DataFrame(columns=['medico', 'prod_extra'])
    else:
        valor_bolo_vl_sp, codigos_blacklist = processar_receita_bolo_e_codigos(arq_rec)
        df_prod = processar_producao_individual(arq_prod, codigos_blacklist, lista_nomes_oficiais)

    COTAS_TOTAIS_FIXAS = 21.0
    valor_por_cota = valor_bolo_vl_sp / COTAS_TOTAIS_FIXAS if valor_bolo_vl_sp > 0 else 0
    
    df_pesos['valor_rateio'] = df_pesos['peso'] * valor_por_cota
    df_final = pd.merge(df_pesos, df_prod, on='medico', how='outer').fillna(0)
    df_final['total_liquido'] = df_final['valor_rateio'] + df_final['prod_extra']
    
    registros = []
    for _, row in df_final.iterrows():
        nome_med = str(row['medico']).upper()
        if any(t in nome_med for t in ["TOTAL", "HOSPITAL", "SANTA HELENA"]): continue
        if row['total_liquido'] <= 0.01: continue
        
        registros.append({
            "competencia": competencia_base,
            "convenio": tag_banco, 
            "medico": row['medico'],
            "producao_individual": 0,
            "fator_vinculo": round(float(row['peso']), 4),
            "valor_rateio": round(float(row['valor_rateio']), 2),
            "valor_prod_extra": round(float(row['prod_extra']), 2),
            "valor_liquido": round(float(row['total_liquido']), 2)
        })

    if registros:
        supabase.table("financeiro_repasses").delete().eq("competencia", competencia_base).eq("convenio", tag_banco).execute()
        supabase.table("financeiro_repasses").insert(registros).execute()
        print(f"    ✅ {len(registros)} registros calculados e salvos com sucesso em {tag_banco}!")

def executar():
    arquivos_base = glob.glob(os.path.join(PASTA_REPASSE, "R_PRODUCAO*.pdf"))
    meses_processar = set()
    for arq in arquivos_base:
        match = re.search(r'_(\d{2})(\d{2})\.pdf', arq.lower())
        if match: meses_processar.add((match.group(1), "20" + match.group(2)))

    for mes, ano in sorted(meses_processar):
        rodar_extracao(mes, ano, is_fila_zero=False)
        rodar_extracao(mes, ano, is_fila_zero=True)

if __name__ == "__main__":
    executar()