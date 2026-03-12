import time
import os
import shutil
import pandas as pd
import numpy as np
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print("--- 🚀 ROBÔ INDICASUS V20 (CENSO FOTOGRÁFICO) ---")

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
USUARIO_INDICASUS = "046.941.841-99"
SENHA_INDICASUS = "@ntoniO22"

PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\downloads"

try: 
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar Supabase: {e}"); exit()

if os.path.exists(PASTA_DOWNLOAD):
    try: shutil.rmtree(PASTA_DOWNLOAD)
    except: pass
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

options = webdriver.ChromeOptions()
prefs = { "download.default_directory": PASTA_DOWNLOAD, "download.prompt_for_download": False, "directory_upgrade": True }
options.add_experimental_option("prefs", prefs)

def formatar_data(valor):
    if pd.isna(valor) or str(valor).lower() in ['nan', 'nat', 'none', '']: return None
    if isinstance(valor, (pd.Timestamp, datetime)): return valor.strftime('%Y-%m-%d')
    valor_str = str(valor).strip().split(' ')[0]
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
        try: return datetime.strptime(valor_str, fmt).strftime('%Y-%m-%d')
        except: continue
    return None

def limpar_e_separar(valor):
    if pd.isna(valor) or str(valor).strip() == '': return []
    texto = str(valor).replace('\n', ',').replace('/', ',').replace(';', ',')
    return [x.strip() for x in texto.split(',') if x.strip()]

def tratar_e_enviar_dados(caminho_arquivo):
    print("\n>> Tratando dados e gerando Censo Diário...")
    df = None
    try:
        dfs = pd.read_html(caminho_arquivo, encoding='latin1', header=None)
        if dfs: df = dfs[0]
    except:
        try: df = pd.read_excel(caminho_arquivo, header=None)
        except Exception as e: print(f"❌ Erro leitura: {e}"); return

    if df is not None:
        header_index = -1
        for i, row in df.head(20).iterrows():
            linha = row.astype(str).str.upper().str.strip().tolist()
            if "NOME DO PACIENTE" in linha or "PACIENTE" in linha:
                header_index = i; df.columns = linha; df = df.iloc[i+1:].reset_index(drop=True); break
        
        if header_index == -1: print("❌ Cabeçalho não encontrado."); return

        df.columns = df.columns.astype(str).str.strip().str.upper()
        df = df.loc[:, ~df.columns.str.contains('^UNNAMED')]
        df = df.replace({np.nan: None})
        df = df.where(pd.notnull(df), None)

        mapa = {
            'NOME DO PACIENTE': 'nome_paciente', 'CARTÃO NACIONAL DO SUS': 'cns',
            'CÓDIGO DA SOLICITAÇÃO DO SISREG': 'sisreg', 'NÚMERO AIH': 'aih',
            'INTERNAÇÃO SUS': 'internacao_sus', 'CPF': 'cpf', 'NOME DA MÃE': 'nome_mae',
            'DATA DE NASCIMENTO': 'data_nascimento', 'MUNICÍPIO DE RESIDÊNCIA': 'municipio_residencia',
            'DATA DA INTERNAÇÃO': 'data_internacao', 'DATA DA EVOLUÇÃO': 'data_evolucao',
            'TIPO DE LEITO': 'tipo_leito'
        }

        df_final = pd.DataFrame()
        cols_orig = list(df.columns)
        
        def get_col(alvo):
            for col in cols_orig:
                for k, v in mapa.items():
                    if v == alvo and k in col: 
                        if alvo == 'internacao_sus' and 'CART' in col: continue 
                        return col
            return None

        campos = ['nome_paciente','cns','sisreg','aih','internacao_sus','cpf','nome_mae','data_nascimento',
                  'municipio_residencia','data_internacao','data_evolucao','tipo_leito']
        
        for c in campos:
            orig = get_col(c)
            df_final[c] = df[orig] if orig else None

        # Formata datas para o Filtro
        df_final['data_internacao_fmt'] = df_final['data_internacao'].apply(formatar_data)
        df_final['data_evolucao_fmt'] = df_final['data_evolucao'].apply(formatar_data)
        hoje_str = datetime.now().strftime('%Y-%m-%d')
        
        # 🧠 A MÁGICA DO CENSO: Só mantém quem está internado hoje (Alta vazia) 
        # OU quem teve "Bate e Volta" exato no dia de hoje (Internou e teve alta no mesmo dia).
        filtro_censo = df_final['data_evolucao_fmt'].isna() | ((df_final['data_internacao_fmt'] == df_final['data_evolucao_fmt']) & (df_final['data_internacao_fmt'] == hoje_str))
        df_censo = df_final[filtro_censo].copy()

        df_censo['data_extracao'] = hoje_str
        df_censo['sisreg'] = df_censo['sisreg'].astype(str)
        df_censo['sisreg_lista'] = df_censo['sisreg'].apply(limpar_e_separar)
        df_exploded = df_censo.explode('sisreg_lista')
        df_exploded['cod_solicitacao_sisreg'] = df_exploded['sisreg_lista']
        df_exploded = df_exploded.replace({np.nan: None})

        registros = []
        for _, row in df_exploded.iterrows():
            nome = str(row['nome_paciente'])
            if len(nome) < 4 or "TOTAL" in nome.upper(): continue

            reg = {
                "nome_paciente": nome.strip(),
                "cns": ''.join(filter(str.isdigit, str(row['cns']))) if row['cns'] else None,
                "cod_solicitacao_sisreg": str(row['cod_solicitacao_sisreg']).strip() if row['cod_solicitacao_sisreg'] else None,
                "aih": ''.join(filter(str.isdigit, str(row['aih']))) if row['aih'] else None,
                "internacao_sus": str(row['internacao_sus']).strip().upper() if row['internacao_sus'] else None,
                "cpf": ''.join(filter(str.isdigit, str(row['cpf']))) if row['cpf'] else None,
                "nome_mae": str(row['nome_mae']).strip() if row['nome_mae'] else None,
                "data_nascimento": formatar_data(row['data_nascimento']),
                "municipio_residencia": str(row['municipio_residencia']).strip() if row['municipio_residencia'] else None,
                "data_internacao": row['data_internacao_fmt'],
                "data_evolucao": row['data_evolucao_fmt'],
                "tipo_leito": str(row['tipo_leito']).strip() if row['tipo_leito'] else None,
                "data_extracao": row['data_extracao']
            }
            registros.append(reg)

        if registros:
            print(f">> Enviando Censo Diário: {len(registros)} pacientes ocupando leitos.")
            # Apaga a foto de hoje se já existir, para não duplicar, e salva a nova
            try: supabase.table("indicasus_leitos").delete().eq("data_extracao", hoje_str).execute()
            except: pass
            
            tamanho_lote = 100
            for i in range(0, len(registros), tamanho_lote):
                lote = registros[i:i + tamanho_lote]
                try: supabase.table("indicasus_leitos").insert(lote).execute()
                except Exception as e: print(f"❌ Erro lote {i}: {e}")
            
            print("✅ SUCESSO! Foto do dia salva.")
        else:
            print("⚠️ Nenhum paciente internado hoje.")

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 40)
    print(">> Acessando IndicaSUS...")
    driver.get("https://sistemas.saude.mt.gov.br/")
    driver.maximize_window()
    
    try: wait.until(EC.invisibility_of_element_located((By.ID, "btnFecharLoading")))
    except: pass
    try: driver.find_element(By.XPATH, "//button[contains(text(), '×')]").click()
    except: pass

    wait.until(EC.presence_of_element_located((By.ID, "CPF"))).send_keys(USUARIO_INDICASUS)
    driver.find_element(By.ID, "Senha").send_keys(SENHA_INDICASUS + Keys.RETURN)
    time.sleep(8)

    driver.get("https://sistemas.saude.mt.gov.br/Administracao/InternacaoGeral?limpar=1")
    print(">> Baixando relatório...")
    
    try: wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading"))) 
    except: pass
    
    try: wait.until(EC.element_to_be_clickable((By.ID, "exportFormInternacaoGeral"))).click()
    except: driver.execute_script("document.getElementById('exportFormInternacaoGeral').click();")
        
    time.sleep(2)
    try: driver.find_element(By.XPATH, "//*[@id='exportFormInternacaoGeral']//span").click()
    except: pass

    tempo, max_t, path = 0, 60, None
    while tempo < max_t:
        arqs = [f for f in os.listdir(PASTA_DOWNLOAD) if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if arqs: path = os.path.join(PASTA_DOWNLOAD, arqs[0]); break
        time.sleep(2); tempo += 2

    if path: tratar_e_enviar_dados(path)
    else: print("❌ Timeout download.")

except Exception as e: print(f"❌ Erro Geral: {e}")
finally: 
    try: driver.quit()
    except: pass