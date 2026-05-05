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

print(f"--- 2. AUTOMAÇÃO SISREG (V63 - PDF ISOLADO, LEVE E SELECIONÁVEL) ---")

# --- CONFIGURAÇÕES DE CONTROLE ---
FORCAR_RE_DOWNLOAD = True 

# --- DEFINIÇÃO DE DATAS (ALTERE AQUI) ---
DT_INICIO = "01/04/2026"
DT_FIM = "30/04/2026"

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

# --- FUNÇÕES DE NUVEM ---
def verificar_aih_na_nuvem(aih):
    try:
        response = supabase.table("regulacao").select("num_aih").eq("num_aih", aih).execute()
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as e:
        return False

def enviar_para_nuvem(caminho_local_pdf, nome_remoto_pdf, dados_paciente):
    print(f"☁️  Subindo PDF de {dados_paciente['nome_paciente'][:20]}...")
    link_publico_pdf = None
    try:
        res = supabase.storage.from_(NOME_BUCKET).upload(
            path=nome_remoto_pdf,
            file=caminho_local_pdf,
            file_options={"content-type": "application/pdf", "x-upsert": "true"}
        )
        
        link_publico_pdf = f"{SUPABASE_URL}/storage/v1/object/public/{NOME_BUCKET}/{nome_remoto_pdf}"
        
    except Exception as e:
        print(f"❌ Erro no upload do PDF: {e}")
        return False

    try:
        registro = {
            "num_aih": dados_paciente['aih'],
            "nome_paciente": dados_paciente['nome_paciente'],
            "status": dados_paciente['status'],
            "arquivo_pdf": link_publico_pdf,
            "data_atualizacao": datetime.now().isoformat()
        }
        supabase.table("regulacao").upsert(registro, on_conflict="num_aih").execute()
        print(f"✅ Sucesso! Ficha salva na nuvem e banco atualizado.")
        return True
    except Exception as e:
        print(f"❌ Erro ao gravar no banco de dados: {e}")
        return False

# --- FUNÇÕES AUXILIARES ---
def limpar_nome_arquivo(texto):
    texto = re.sub(r'[\\/*?:"<>|]', "", texto)
    texto = re.sub(r'[Ç]', "C", texto)
    texto = re.sub(r'[ÃÁÀÂ]', "A", texto)
    texto = re.sub(r'[ÉÊ]', "E", texto)
    texto = re.sub(r'[Í]', "I", texto)
    texto = re.sub(r'[ÓÔÕ]', "O", texto)
    texto = re.sub(r'[Ú]', "U", texto)
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

# --- SETUP ---
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
                    aih_encontrada = match_aih.group(0)
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
                        if "APROVAD" in txt_status or "AUTORIZAD" in txt_status: status_estimado = "Aprovado"
                        elif "NEGAD" in txt_status or "CANCELAD" in txt_status: status_estimado = "Negado"
                except Exception as e:
                    print(f"⚠️ Aviso: Não consegui achar o nome exato na ficha. ({e})")

                print(f"AIH {aih_encontrada} - {nome_paciente[:20]} [BAIXANDO NATIVO]...", end=" ")

                nome_arquivo_pdf = f"AIH_{aih_encontrada}_{nome_paciente.replace(' ', '_')}.pdf"
                caminho_completo_pdf = os.path.join(PASTA_TEMP_PDF, nome_arquivo_pdf)

                # ==============================================================
                # NOVA LÓGICA DE EXTRAÇÃO DE PDF (SEM IFRAME, SEM PYAUTOGUI)
                # ==============================================================
                try:
                    # 1. Pega o HTML exato apenas do quadro da Ficha
                    try:
                        ficha_html = driver.find_element(By.ID, "fichaInternacao").get_attribute("outerHTML")
                    except:
                        ficha_html = driver.find_element(By.XPATH, "/html/body/center/div[2]/form/div/table").get_attribute("outerHTML")

                    # 2. Abre uma aba nova e limpa
                    driver.execute_script("window.open('about:blank', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])

                    # 3. Injeta a ficha com CSS formatado
                    script_injecao = """
                    document.write('<html><head><style>body { font-family: Arial, sans-serif; font-size: 11px; color: #000; padding: 15px; } table { width: 100%; border-collapse: collapse; margin-bottom: 15px; } td, th { padding: 6px; border: 1px solid #ccc; text-align: left; } b { color: #111; }</style></head><body>' + arguments[0] + '</body></html>');
                    document.close();
                    """
                    driver.execute_script(script_injecao, ficha_html)
                    time.sleep(1) # Aguarda o DOM renderizar

                    # 4. Gera o PDF puramente digital
                    print_options = {
                        "landscape": False,
                        "displayHeaderFooter": False,
                        "printBackground": True,
                        "preferCSSPageSize": False,
                        "paperWidth": 8.27,
                        "paperHeight": 11.69,
                        "marginTop": 0.5,
                        "marginBottom": 0.5,
                        "marginLeft": 0.5,
                        "marginRight": 0.5
                    }
                    result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                    
                    with open(caminho_completo_pdf, "wb") as f:
                        f.write(base64.b64decode(result['data']))
                    
                    # 5. Fecha a aba extra e foca no iframe novamente
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    focar_na_tabela_dados(driver)

                    # Subir para a nuvem
                    dados_pct = { "aih": aih_encontrada, "nome_paciente": nome_paciente, "status": status_estimado }
                    caminho_remoto = f"Fichas_Internacao/{nome_arquivo_pdf}"
                    
                    enviar_para_nuvem(caminho_completo_pdf, caminho_remoto, dados_pct)
                    
                    try: os.remove(caminho_completo_pdf)
                    except: pass

                except Exception as e:
                    print(f"❌ Erro ao gerar PDF isolado: {e}")

                # Clicar no botão voltar do próprio site é mais seguro do que driver.back() no Iframe
                try:
                    btn_voltar = driver.find_element(By.XPATH, "//input[@value='VOLTAR']")
                    driver.execute_script("arguments[0].click();", btn_voltar)
                except:
                    driver.back()
                    
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro na linha: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0: break

        print(f">> Buscando página {pagina_atual + 1}...")
        paginou = False
        focar_na_tabela_dados(driver)
        
        try:
            candidatos = driver.find_elements(By.XPATH, "//a/img[contains(@src, 'avanca') or contains(@src, 'prox')]/..") + driver.find_elements(By.XPATH, "//input[@type='image' and (contains(@src, 'avanca') or contains(@src, 'prox'))]")
            if candidatos:
                driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", candidatos[-1])
                paginou = True
            elif not paginou:
                links_texto = driver.find_elements(By.XPATH, "//a[contains(text(), '>>')] | //a[text()='>']")
                if links_texto:
                    driver.execute_script("arguments[0].click();", links_texto[0])
                    paginou = True
        except: pass

        if not paginou: break
        time.sleep(8)
        pagina_atual += 1

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")