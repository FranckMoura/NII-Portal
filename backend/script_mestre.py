import time
import os
import re
import json
import pyautogui
import calendar
import pdfplumber
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 2. AUTOMAÇÃO SISREG (V69 - UNIFICAÇÃO DE CHAVES) ---")

# --- CONFIGURAÇÕES DE CONTROLE ---
FORCAR_RE_DOWNLOAD = True 

# --- DEFINIÇÃO DE DATAS ---
DT_INICIO = "01/01/2026"
DT_FIM = "15/01/2026"

# --- SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

# --- SISREG ---
USUARIO = "046FRANCK"
SENHA = "515462"
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend"
PASTA_TEMP_PDF = os.path.join(PASTA_PROJETO, "temp_fichas")

if not os.path.exists(PASTA_TEMP_PDF): os.makedirs(PASTA_TEMP_PDF)

# Conexão Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

# --- FUNÇÃO DE EXTRAÇÃO ---
def extrair_dados_pdf(caminho_arquivo):
    """Lê o PDF e extrai dados usando Regex"""
    dados = {
        "cns": None, "data_nascimento": None, "nome_mae": None,
        "municipio": None, "telefone": None, "procedimento": None,
        "cod_solicitacao": None, "data_solicitacao": None
    }
    
    time.sleep(2) # Espera arquivo
    
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            texto_completo = ""
            for page in pdf.pages: texto_completo += page.extract_text() or ""
            
            # Regex Patterns
            m_cns = re.search(r'(?:Nacional de Saúde|CNS)[:\s\.]*(\d{15})', texto_completo, re.IGNORECASE)
            if m_cns: dados['cns'] = m_cns.group(1)

            m_nasc = re.search(r'(?:Nascimento)[:\s\.]*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m_nasc: dados['data_nascimento'] = m_nasc.group(1)

            m_mae = re.search(r'(?:Mãe)[:\s\.]*(.+?)(?:\n|Município)', texto_completo, re.IGNORECASE)
            if m_mae: dados['nome_mae'] = m_mae.group(1).strip()

            m_mun = re.search(r'(?:Residência)[:\s\.]*(.+?)(?:\n|\s{2,})', texto_completo, re.IGNORECASE)
            if m_mun: dados['municipio'] = m_mun.group(1).strip()

            m_tel = re.search(r'(?:Telefones)[:\s\.]*([\d\s\(\)-]+)', texto_completo, re.IGNORECASE)
            if m_tel: dados['telefone'] = m_tel.group(1).strip()

            # AQUI ESTÁ O SEGREDO: Capturar a solicitação do PDF também
            m_cod = re.search(r'(?:Solicitação)[:\s\.]*(\d{9,})', texto_completo, re.IGNORECASE)
            if m_cod: dados['cod_solicitacao'] = m_cod.group(1)

            m_dt = re.search(r'(?:Solicitação)[:\s\.]*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m_dt: dados['data_solicitacao'] = m_dt.group(1)

            m_proc = re.search(r'(?:Procedimento)[:\s\.]*(\d{2}\.\d{2}\.\d{2}\.\d{3}-\d\s+-.+)', texto_completo, re.IGNORECASE)
            if not m_proc: m_proc = re.search(r'(?:Procedimento)[:\s\.]*(.+?)(?:\n|Qtde)', texto_completo, re.IGNORECASE)
            if m_proc: dados['procedimento'] = m_proc.group(1).strip()

    except Exception as e:
        print(f"⚠️ Erro OCR: {e}")
    return dados

# --- FUNÇÕES DE NUVEM ---
def verificar_aih_na_nuvem(aih):
    try:
        response = supabase.table("regulacao").select("num_aih").eq("num_aih", aih).execute()
        return bool(response.data)
    except: return False

def enviar_para_nuvem(caminho_local_pdf, nome_remoto_pdf, dados_basicos, dados_extraidos_pdf):
    print(f"☁️  Enviando {dados_basicos['nome_paciente']}...")
    link_publico_pdf = None
    
    # 1. Upload
    try:
        with open(caminho_local_pdf, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto_pdf, file=f, file_options={"content-type": "application/pdf", "upsert": "true"}
            )
        link_publico_pdf = supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto_pdf)
    except Exception as e:
        print(f"❌ Erro Upload: {e}")

    # 2. Banco de Dados (CORREÇÃO DE CHAVE)
    try:
        # Tenta pegar a solicitação extraída do PDF ou usa uma alternativa se falhar
        solicitacao_final = dados_extraidos_pdf.get('cod_solicitacao') 
        
        # Se não achou no PDF (raro), precisamos de um plano B, mas por enquanto vamos confiar no OCR
        if not solicitacao_final:
            print("⚠️ AVISO: Número da solicitação não encontrado no PDF. Tentando salvar por AIH...")
            chave_conflito = "num_aih"
        else:
            chave_conflito = "num_solicitacao"

        registro = {
            "num_aih": dados_basicos['aih'],
            "nome_paciente": dados_basicos['nome_paciente'],
            "status": dados_basicos['status'],
            "arquivo_pdf": link_publico_pdf,
            "data_atualizacao": datetime.now().isoformat(),
            # CAMPOS DO PDF
            "num_solicitacao": solicitacao_final, # ATUALIZA O CAMPO CHAVE
            "cns": dados_extraidos_pdf.get('cns'),
            "data_nascimento": dados_extraidos_pdf.get('data_nascimento'),
            "nome_mae": dados_extraidos_pdf.get('nome_mae'),
            "municipio": dados_extraidos_pdf.get('municipio'),
            "telefone": dados_extraidos_pdf.get('telefone'),
            "procedimento": dados_extraidos_pdf.get('procedimento'),
            "cod_solicitacao": solicitacao_final,
            "data_solicitacao": dados_extraidos_pdf.get('data_solicitacao')
        }
        
        # O SEGREDO: upsert usando a chave certa
        supabase.table("regulacao").upsert(registro, on_conflict=chave_conflito).execute()
        print(f"✅ Salvo/Atualizado! (Chave: {chave_conflito})")
        return True
    except Exception as e:
        print(f"❌ Erro Banco: {e}")
        return False

# --- AUXILIARES ---
def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def focar_na_tabela_dados(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            if driver.find_elements(By.CLASS_NAME, "table_listagem") or driver.find_elements(By.NAME, "data_inicio"):
                return True
        except: pass
    driver.switch_to.default_content()
    return False

def verificar_bloqueio_horario(driver):
    try:
        alerta = driver.switch_to.alert
        if "bloqueado" in alerta.text.lower():
            alerta.accept(); return True
        alerta.accept() 
    except: pass
    return False

def preencher_datas_robustamente(driver, dt_ini, dt_fim):
    print(f">> Preenchendo datas: {dt_ini} a {dt_fim}...")
    sucesso = False
    try:
        driver.find_element(By.NAME, "data_inicio").clear()
        driver.find_element(By.NAME, "data_inicio").send_keys(dt_ini)
        driver.find_element(By.NAME, "data_fim").clear()
        driver.find_element(By.NAME, "data_fim").send_keys(dt_fim)
        sucesso = True
    except: pass
    if not sucesso:
        try:
            driver.execute_script(f"document.getElementsByName('data_inicio')[0].value = '{dt_ini}'")
            driver.execute_script(f"document.getElementsByName('data_fim')[0].value = '{dt_fim}'")
            sucesso = True
        except: pass
    return sucesso

# --- SETUP ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 1.0
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
prefs = { "download.default_directory": PASTA_TEMP_PDF, "download.prompt_for_download": False, "plugins.always_open_pdf_externally": True }
options.add_experimental_option("prefs", prefs)

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    if verificar_bloqueio_horario(driver): driver.quit(); exit()

    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    if verificar_bloqueio_horario(driver): driver.quit(); exit()

    print(">> Navegando...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_na_tabela_dados(driver)
    if preencher_datas_robustamente(driver, DT_INICIO, DT_FIM):
        try: driver.find_element(By.NAME, "enviar").click()
        except: 
            try: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
            except: pass
    
    print(">> Pesquisando...")
    time.sleep(8)

    pagina_atual = 1
    while True:
        if verificar_bloqueio_horario(driver): break
        print(f"\n>>> PÁGINA {pagina_atual} <<<")
        focar_na_tabela_dados(driver)
        
        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        if not tabelas:
            print(">> Tabela não encontrada.")
            break
        
        linhas = tabelas[-1].find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0

        if pagina_atual == 1 and qtd_total < 3:
            print("⚠️ Reaplicando filtro...")
            preencher_datas_robustamente(driver, DT_INICIO, DT_FIM)
            try: driver.find_element(By.NAME, "enviar").click()
            except: pass
            time.sleep(5)
            focar_na_tabela_dados(driver)
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            if tabelas: linhas = tabelas[-1].find_elements(By.TAG_NAME, "tr"); qtd_total = len(linhas)

        for i in range(qtd_total):
            try:
                focar_na_tabela_dados(driver)
                tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
                if not tabelas: break
                linha = tabelas[-1].find_elements(By.TAG_NAME, "tr")[i]

                if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 6: continue 
                
                match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', linha.text)
                if not match_aih: continue
                aih_encontrada = match_aih.group(0)
                registros_pagina += 1

                # Filtro de Nome
                nome_paciente = "PACIENTE"
                status_estimado = "Pendente"
                proibidos = ["APROVADO", "APROVADA", "AUTORIZADO", "NEGADO", "PENDENTE", "URGENCIA", "ELETIVA"]
                
                for col in colunas:
                    txt = col.text.strip().upper()
                    if len(txt) > 5 and not txt[0].isdigit() and "/" not in txt:
                        if not any(p in txt for p in proibidos):
                            nome_paciente = limpar_nome_arquivo(txt)
                    if "AUTORIZADO" in txt or "APROVADO" in txt: status_estimado = "Aprovado"
                    elif "NEGADO" in txt or "CANCELADO" in txt: status_estimado = "Negado"

                print(f"AIH {aih_encontrada}...", end=" ")
                
                # --- FORCAR DOWNLOAD: Sempre baixa para atualizar os dados ---
                # if not FORCAR_RE_DOWNLOAD and verificar_aih_na_nuvem(aih_encontrada): ... (Removido para garantir update)
                
                print("[BAIXANDO]...", end=" ")
                
                coluna_clique = colunas[1] 
                for col in colunas: 
                    if len(col.text) > 4: coluna_clique = col; break
                
                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                coluna_clique.click()
                time.sleep(5)

                nome_arquivo_pdf = f"AIH_{aih_encontrada}_{nome_paciente}.pdf"
                caminho_completo_pdf = os.path.join(PASTA_TEMP_PDF, nome_arquivo_pdf)
                if os.path.exists(caminho_completo_pdf): os.remove(caminho_completo_pdf)

                width, height = pyautogui.size()
                pyautogui.click(width/2, height/2) # Foco
                pyautogui.hotkey('ctrl', 'a'); time.sleep(0.5) # Selecionar tudo
                pyautogui.hotkey('ctrl', 'p'); time.sleep(4) # Imprimir
                pyautogui.press('enter'); time.sleep(3)
                pyautogui.write(caminho_completo_pdf); time.sleep(2)
                pyautogui.press('enter'); time.sleep(5)

                if os.path.exists(caminho_completo_pdf):
                    dados_extraidos = extrair_dados_pdf(caminho_completo_pdf)
                    dados_basicos = { "aih": aih_encontrada, "nome_paciente": nome_paciente, "status": status_estimado }
                    caminho_remoto = f"Fichas_Internacao/{nome_arquivo_pdf}"
                    
                    enviar_para_nuvem(caminho_completo_pdf, caminho_remoto, dados_basicos, dados_extraidos)
                    try: os.remove(caminho_completo_pdf)
                    except: pass
                else:
                    print("❌ Erro: PDF não foi salvo.")

                driver.back()
                try: WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(2)

            except Exception as e:
                print(f"❌ Erro linha: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0: break

        print(f">> Próxima página...")
        paginou = False
        focar_na_tabela_dados(driver)
        try:
            btns = driver.find_elements(By.XPATH, "//input[@type='image' and contains(@src, 'prox')]")
            if btns:
                driver.execute_script("arguments[0].click();", btns[-1])
                paginou = True
            elif driver.find_elements(By.XPATH, "//a[contains(text(), '>>')]"):
                driver.execute_script("arguments[0].click();", driver.find_elements(By.XPATH, "//a[contains(text(), '>>')]")[0])
                paginou = True
        except: pass

        if not paginou: break
        time.sleep(5)
        pagina_atual += 1

    driver.quit()
except Exception as e:
    print(f"❌ ERRO GERAL: {e}")