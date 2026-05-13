import time
import os
import re
import json
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 2. AUTOMAÇÃO SISREG (V66 - CORREÇÃO DA PAGINAÇÃO 'SETA DIREITA') ---")

# --- CONFIGURAÇÕES DE CONTROLE ---
FORCAR_RE_DOWNLOAD = True 

# --- DEFINIÇÃO DE DATAS (ALTERE AQUI) ---
DT_INICIO = "01/05/2026"
DT_FIM = "13/05/2026"

# --- 1. CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

# --- CONFIGURAÇÕES DO SISREG ---
USUARIO = "046FRANCK"
SENHA = "212425"
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend"
PASTA_TEMP_PDF = os.path.join(PASTA_PROJETO, "temp_fichas")

if not os.path.exists(PASTA_TEMP_PDF): os.makedirs(PASTA_TEMP_PDF)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def verificar_aih_na_nuvem(aih):
    try:
        response = supabase.table("regulacao").select("num_aih").eq("num_aih", aih).execute()
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as e:
        return False

def enviar_para_nuvem(caminho_local_pdf, nome_remoto_pdf, dados_paciente):
    print(f"☁️  Subindo arquivo...", end=" ")
    link_publico_pdf = None
    sucesso_upload = False
    
    for tentativa in range(3):
        try:
            with open(caminho_local_pdf, 'rb') as f:
                file_data = f.read()
                supabase.storage.from_(NOME_BUCKET).upload(
                    path=nome_remoto_pdf,
                    file=file_data,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            sucesso_upload = True
            break
        except Exception as e:
            time.sleep(2)
            
    if not sucesso_upload:
        print(f"❌ Falha de rede no upload.")
        return False

    base_url = SUPABASE_URL.rstrip('/')
    link_publico_pdf = f"{base_url}/storage/v1/object/public/{NOME_BUCKET}/{nome_remoto_pdf}"

    try:
        registro = {
            "num_aih": dados_paciente['aih'],
            "nome_paciente": dados_paciente['nome_paciente'],
            "status": dados_paciente['status'],
            "arquivo_pdf": link_publico_pdf,
            "data_atualizacao": datetime.now().isoformat()
        }
        supabase.table("regulacao").upsert(registro, on_conflict="num_aih").execute()
        print(f"✅ OK!")
        return True
    except Exception as e:
        print(f"❌ Erro ao gravar no BD.")
        return False

def limpar_nome_arquivo(texto):
    texto = re.sub(r'[\\/*?:"<>|]', "", texto)
    return texto.strip()

def focar_na_tabela_dados(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            if driver.find_elements(By.CLASS_NAME, "table_listagem") or driver.find_elements(By.NAME, "data_inicio") or driver.find_elements(By.ID, "fichaInternacao"):
                return True
        except: pass
    driver.switch_to.default_content()
    return False

def preencher_datas_robustamente(driver, dt_ini, dt_fim):
    print(f">> Tentando preencher datas: {dt_ini} a {dt_fim}...")
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
            inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
            if len(inputs) >= 2:
                inputs[0].clear(); inputs[0].send_keys(dt_ini)
                inputs[1].clear(); inputs[1].send_keys(dt_fim)
                sucesso = True
        except: pass
    return sucesso

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument('--kiosk-printing') 

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    print(">> Navegando para menu...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_na_tabela_dados(driver)
    
    if preencher_datas_robustamente(driver, DT_INICIO, DT_FIM):
        print(f">> Datas preenchidas: {DT_INICIO} até {DT_FIM}")
        
    try: driver.find_element(By.NAME, "enviar").click()
    except: 
        try: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
        except: pass
    
    print(">> Pesquisando...")
    time.sleep(8)

    pagina_atual = 1
    
    while True:
        print(f"\n>>> PROCESSANDO PÁGINA {pagina_atual} <<<")
        focar_na_tabela_dados(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        if not tabelas: break
        
        tabela_dados = tabelas[-1]
        linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0

        for i in range(qtd_total):
            try:
                focar_na_tabela_dados(driver)
                tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
                if not tabelas: break
                linha = tabelas[-1].find_elements(By.TAG_NAME, "tr")[i]

                if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 6: continue 
                
                registros_pagina += 1
                match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', linha.text)
                
                if match_aih:
                    aih_encontrada = match_aih.group(0).replace('-', '')
                else: continue

                coluna_clique = colunas[1] 
                for col in colunas:
                    if len(col.text) > 4: coluna_clique = col; break
                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                time.sleep(0.5)
                
                if not FORCAR_RE_DOWNLOAD:
                    if verificar_aih_na_nuvem(aih_encontrada):
                        print(f"AIH {aih_encontrada} [JÁ NA NUVEM] - Pulando.")
                        continue

                coluna_clique.click()
                time.sleep(5) 

                focar_na_tabela_dados(driver)

                nome_paciente = "PACIENTE_DESCONHECIDO"
                status_estimado = "PENDENTE"
                
                try:
                    nome_el = driver.find_elements(By.XPATH, "//b[contains(text(), 'Nome do Paciente')]/ancestor::tr/following-sibling::tr[1]/td[1]")
                    if nome_el:
                        nome_paciente = limpar_nome_arquivo(nome_el[0].text)
                    
                    status_el = driver.find_elements(By.XPATH, "//b[contains(text(), 'Status da Solicitação')]/ancestor::tr/following-sibling::tr[1]/td[1]")
                    if status_el:
                        txt_status = status_el[0].text.strip().upper()
                        if "APROVAD" in txt_status or "AUTORIZAD" in txt_status: status_estimado = "APROVADA"
                        elif "NEGAD" in txt_status or "CANCELAD" in txt_status: status_estimado = "NEGADA"
                except: pass

                print(f"AIH {aih_encontrada} - {nome_paciente[:15]}...", end=" ")

                nome_arquivo_pdf = f"AIH_{aih_encontrada}_{status_estimado.upper()}.pdf"
                caminho_completo_pdf = os.path.join(PASTA_TEMP_PDF, nome_arquivo_pdf)

                try:
                    iframe_html = driver.execute_script("return document.documentElement.outerHTML;")
                    
                    driver.execute_script("window.open('about:blank', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    script_injecao = """
                    var html = arguments[0];
                    document.open();
                    document.write(html);
                    document.close();
                    
                    var base = document.createElement('base');
                    base.href = 'https://sisregiii.saude.gov.br/';
                    document.head.insertBefore(base, document.head.firstChild);
                    
                    var botoes = document.querySelectorAll('input[type="button"], input[type="submit"], button');
                    botoes.forEach(b => b.style.display = 'none');
                    """
                    driver.execute_script(script_injecao, iframe_html)
                    time.sleep(2) 
                    
                    print_options = {
                        "landscape": False,
                        "displayHeaderFooter": False,
                        "printBackground": True,
                        "preferCSSPageSize": True
                    }
                    result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                    
                    with open(caminho_completo_pdf, "wb") as f:
                        f.write(base64.b64decode(result['data']))
                    
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    focar_na_tabela_dados(driver)

                    dados_pct = { "aih": aih_encontrada, "nome_paciente": nome_paciente, "status": status_estimado }
                    caminho_remoto = f"Fichas_Internacao/{nome_arquivo_pdf}"
                    
                    enviar_para_nuvem(caminho_completo_pdf, caminho_remoto, dados_pct)
                    
                    try: os.remove(caminho_completo_pdf)
                    except: pass

                except Exception as e:
                    print(f"❌ Erro ao gerar PDF: {e}")
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        focar_na_tabela_dados(driver)

                try:
                    btn_voltar = driver.find_element(By.XPATH, "//input[@value='VOLTAR']")
                    driver.execute_script("arguments[0].click();", btn_voltar)
                except:
                    driver.back()
                    
                try: WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro na linha: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0: break

        print(f">> Buscando página {pagina_atual + 1}...")
        paginou = False
        focar_na_tabela_dados(driver)
        
        try:
            # V66 - Múltiplas estratégias para encontrar o botão de Próxima Página
            btn_next = driver.find_elements(By.XPATH, "//img[contains(@src, 'seta_direita') or contains(@alt, 'Proxima')]/parent::a")
            
            if not btn_next:
                btn_next = driver.find_elements(By.XPATH, "//a/img[contains(@src, 'avanca') or contains(@src, 'prox')]/..")
                
            if not btn_next:
                btn_next = driver.find_elements(By.XPATH, "//input[@type='image' and (contains(@src, 'avanca') or contains(@src, 'prox') or contains(@src, 'seta_direita'))]")

            if btn_next:
                alvo = btn_next[-1] 
                driver.execute_script("arguments[0].scrollIntoView(true);", alvo)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", alvo)
                paginou = True
            elif not paginou:
                links_texto = driver.find_elements(By.XPATH, "//a[contains(text(), '>>')] | //a[text()='>']")
                if links_texto:
                    driver.execute_script("arguments[0].click();", links_texto[0])
                    paginou = True
                    
        except Exception as e:
            print(f"⚠️ Erro paginação: {e}")

        if not paginou:
            print("⚠️ Fim da paginação (Nenhum botão encontrado).")
            break
            
        time.sleep(8)
        pagina_atual += 1

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")