import time
import os
import re
import json
import pyautogui
import calendar
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 2. AUTOMAÇÃO SISREG (V57 - FORÇAR DOWNLOAD) ---")

# --- CONFIGURAÇÕES DE CONTROLE ---
# Mude para True se quiser baixar tudo de novo, mesmo o que já existe
FORCAR_RE_DOWNLOAD = True 

# --- DEFINIÇÃO DE DATAS (ALTERE AQUI) ---
DT_INICIO = "28/03/2026"
DT_FIM = "31/03/2026"

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

# Conexão Supabase
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
    print(f"☁️  Subindo dados de {dados_paciente['nome_paciente']}...")
    link_publico_pdf = None
    try:
        with open(caminho_local_pdf, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto_pdf,
                file=f,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
        link_publico_pdf = supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto_pdf)
    except Exception as e:
        print(f"❌ Erro no upload do PDF: {e}")

    try:
        registro = {
            "num_aih": dados_paciente['aih'],
            "nome_paciente": dados_paciente['nome_paciente'],
            "status": dados_paciente['status'],
            "arquivo_pdf": link_publico_pdf,
            "data_atualizacao": datetime.now().isoformat()
        }
        # Upsert atualiza se já existir
        supabase.table("regulacao").upsert(registro, on_conflict="num_aih").execute()
        print(f"✅ Sucesso! AIH {dados_paciente['aih']} atualizada.")
        return True
    except Exception as e:
        print(f"❌ Erro ao gravar no banco: {e}")
        return False

# --- FUNÇÕES AUXILIARES ---
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
        texto = alerta.text
        if "bloqueado" in texto.lower() and "horas" in texto.lower():
            print(f"⛔ BLOQUEIO DETECTADO: {texto}")
            alerta.accept()
            return True
        alerta.accept() 
    except NoAlertPresentException:
        pass
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

    print(">> Navegando para menu...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_na_tabela_dados(driver)
    
    if preencher_datas_robustamente(driver, DT_INICIO, DT_FIM):
        print(f">> Datas preenchidas: {DT_INICIO} até {DT_FIM}")
    else:
        print("⚠️ ALERTA: Não consegui preencher as datas visualmente.")

    try: driver.find_element(By.NAME, "enviar").click()
    except: 
        try: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
        except: pass
    
    print(">> Pesquisando...")
    time.sleep(8)

    pagina_atual = 1
    
    while True:
        if verificar_bloqueio_horario(driver): break
        print(f"\n>>> PROCESSANDO PÁGINA {pagina_atual} <<<")
        
        focar_na_tabela_dados(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        if not tabelas:
            print(">> Tabela não encontrada.")
            break
        
        tabela_dados = tabelas[-1]
        linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0

        print(f">> Linhas nesta página: {qtd_total}")

        # Se houver poucas linhas na pag 1, tenta recarregar filtro
        if pagina_atual == 1 and qtd_total < 3:
            print("⚠️ Poucos dados... Tentando reaplicar filtro...")
            preencher_datas_robustamente(driver, DT_INICIO, DT_FIM)
            try: driver.find_element(By.NAME, "enviar").click()
            except: pass
            time.sleep(5)
            focar_na_tabela_dados(driver)
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            if tabelas: 
                linhas = tabelas[-1].find_elements(By.TAG_NAME, "tr")
                qtd_total = len(linhas)

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

                nome_paciente = "PACIENTE"
                status_estimado = "Pendente"
                for col in colunas:
                    txt = col.text.strip()
                    if len(txt) > 5 and not txt[0].isdigit() and not "/" in txt:
                        nome_paciente = limpar_nome_arquivo(txt)
                    if "AUTORIZADO" in txt.upper() or "APROVADO" in txt.upper(): status_estimado = "Aprovado"
                    elif "NEGADO" in txt.upper() or "CANCELADO" in txt.upper(): status_estimado = "Negado"

                print(f"AIH {aih_encontrada}...", end=" ")
                
                # --- LÓGICA DE FORÇAR DOWNLOAD ---
                if not FORCAR_RE_DOWNLOAD:
                    if verificar_aih_na_nuvem(aih_encontrada):
                        print("[JÁ NA NUVEM] - Pulando.")
                        continue
                
                print("[BAIXANDO] - Processando...")
                
                for col in colunas:
                    if aih_encontrada in col.text:
                        driver.execute_script("arguments[0].style.backgroundColor = 'yellow';", col)

                coluna_clique = colunas[1] 
                for col in colunas:
                    if len(col.text) > 4: coluna_clique = col; break
                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                time.sleep(1)
                coluna_clique.click()
                time.sleep(5)

                nome_arquivo_pdf = f"AIH_{aih_encontrada}_{nome_paciente}.pdf"
                caminho_completo_pdf = os.path.join(PASTA_TEMP_PDF, nome_arquivo_pdf)

                if os.path.exists(caminho_completo_pdf): os.remove(caminho_completo_pdf)

                width, height = pyautogui.size()
                pyautogui.click(width/2, height/2)
                pyautogui.hotkey('ctrl', 'a'); time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'p'); time.sleep(4)
                pyautogui.press('enter'); time.sleep(3)
                
                pyautogui.write(caminho_completo_pdf); time.sleep(2)
                pyautogui.press('enter'); time.sleep(5)

                if os.path.exists(caminho_completo_pdf):
                    dados_pct = {
                        "aih": aih_encontrada,
                        "nome_paciente": nome_paciente,
                        "status": status_estimado
                    }
                    caminho_remoto = f"Fichas_Internacao/{nome_arquivo_pdf}"
                    enviar_para_nuvem(caminho_completo_pdf, caminho_remoto, dados_pct)
                    try: os.remove(caminho_completo_pdf)
                    except: pass
                else:
                    print("❌ Erro: PDF não foi salvo.")

                driver.back()
                try: WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro na linha: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0:
            print(">> Página vazia.")
            break

        # --- PAGINAÇÃO (LÓGICA V46 RESTAURADA) ---
        print(f">> Buscando página {pagina_atual + 1}...")
        paginou = False
        focar_na_tabela_dados(driver)
        
        try:
            # 1. Busca por Imagem (Estratégia V46 - Principal)
            links_imagem = driver.find_elements(By.XPATH, "//a/img[contains(@src, 'avanca') or contains(@src, 'prox') or contains(@src, 'seta') or contains(@src, 'next')]/..")
            inputs_imagem = driver.find_elements(By.XPATH, "//input[@type='image' and (contains(@src, 'avanca') or contains(@src, 'prox'))]")
            
            candidatos = links_imagem + inputs_imagem
            
            if candidatos:
                btn = candidatos[-1] # O último da lista costuma ser o 'próximo'
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn)
                paginou = True
            
            # 2. Busca por Texto (Plano B)
            if not paginou:
                links_texto = driver.find_elements(By.XPATH, "//a[contains(text(), '>>')] | //a[text()='>']")
                if links_texto:
                    btn = links_texto[0]
                    driver.execute_script("arguments[0].click();", btn)
                    paginou = True

        except Exception as e:
            print(f"⚠️ Erro paginação: {e}")

        if not paginou:
            print("⚠️ Fim da paginação (Nenhum botão encontrado).")
            break
            
        time.sleep(8)
        pagina_atual += 1

    driver.quit()

except KeyboardInterrupt:
    print("\n🛑 Interrompido.")
except Exception as e:
    print(f"❌ ERRO GERAL: {e}")