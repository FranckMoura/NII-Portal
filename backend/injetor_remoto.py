import time
import json
import os
import sys
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

import warnings
warnings.filterwarnings("ignore")

print("--- 🤖 ROBÔ DE INJEÇÃO SOUL MV (VERSÃO REMOTA JSON CLONE V3) ---")

# --- 1. CONFIGURAÇÕES E LEITURA DE ARQUIVOS ---
try:
    if getattr(sys, 'frozen', False): app_path = os.path.dirname(sys.executable)
    else: app_path = os.path.dirname(os.path.abspath(__file__))
    
    config_path = os.path.join(app_path, "config.json")
    arquivo_excel = os.path.join(app_path, "FICHAS_PARA_IMPRIMIR.xlsx")
    
    if not os.path.exists(config_path):
        print("❌ Erro: config.json não encontrado."); sys.exit()
    if not os.path.exists(arquivo_excel):
        print("❌ Erro: FICHAS_PARA_IMPRIMIR.xlsx não encontrado."); sys.exit()
        
    with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
    URL, USER, PASS = config['url'], config['usuario'], config['senha']
except Exception as e: 
    print(f"Erro ao ler arquivos: {e}")
    sys.exit()

print("📄 Lendo planilha de faturamento...")
df = pd.read_excel(arquivo_excel)
df_validos = df[(df['CONTA MV'].astype(str) != '-') & 
                (df['AIH SISREG'].notna()) & 
                (df['AIH SISREG'].astype(str) != '-')]

if len(df_validos) == 0:
    print("⚠️ Nenhum paciente com Conta MV e AIH prontos para injeção na planilha.")
    sys.exit()

print(f"✅ {len(df_validos)} pacientes na fila de injeção!\n")

# --- 2. CONFIGURAÇÃO DO NAVEGADOR E DAS FLAGS DO CHROME ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors=yes")
options.add_argument("--log-level=3")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

# 🚩 FLAGS DO CHROME PARA O SOUL MV
options.add_argument("--disable-web-security")
options.add_argument("--disable-site-isolation-trials")
options.add_argument("--disable-features=IsolateOrigins,site-per-process")
options.add_argument("--allow-running-insecure-content")

print("🌐 Abrindo navegador remoto com Flags desativadas...")
os.environ['WDM_SSL_VERIFY'] = '0'
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 25)
wait_rapido = WebDriverWait(driver, 5)
action = ActionChains(driver)

try:
    # --- 3. AUTO-LOGIN ---
    print(">> Acessando MV e Logando...")
    driver.get(URL)
    
    try:
        if "Privacy" in driver.title or "erro de privacidade" in driver.page_source:
            driver.execute_script("document.getElementById('details-button').click();")
            driver.execute_script("document.getElementById('proceed-link').click();")
    except: pass

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for i in inputs:
        if i.get_attribute("type") == "text": i.send_keys(USER)
        if i.get_attribute("type") == "password": i.send_keys(PASS + "\n")
    
    print(">> Aguardando tela de Instituição...")
    time.sleep(5)
    
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.ant-table-row")
        alvo = None
        for linha in linhas:
            if "HOSPITAL BENEFICENTE SANTA HELENA" in linha.text.upper():
                alvo = linha
                break
                
        if alvo:
            alvo.click()
            time.sleep(1)
            botao_acessar = driver.find_element(By.XPATH, "//button[contains(., 'Acessar')]")
            if botao_acessar.get_attribute("disabled"):
                ActionChains(driver).send_keys(Keys.ENTER).perform()
            else:
                botao_acessar.click()
            print("✅ Instituição definida!")
    except:
        ActionChains(driver).send_keys(Keys.ENTER).pause(1).send_keys(Keys.ENTER).pause(1).send_keys(Keys.ENTER).perform()

    # --- 4. NAVEGAÇÃO PARA A TELA DE CONTA ---
    print(f"\n>> Aguardando Menu Principal carregar...")
    time.sleep(12) 
    
    print("🔎 Buscando a tela C_CONSULTA_CONTA_P321...")
    try:
        pesquisa_menu = wait.until(EC.element_to_be_clickable((By.ID, "menu-filter-1")))
        pesquisa_menu.clear()
        pesquisa_menu.send_keys("C_CONSULTA_CONTA_P321")
        time.sleep(2)
        
        # Clique forçado via JS para evitar falhas de renderização
        item_menu = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="workspace-menubar"]/ul/li[2]/a')))
        driver.execute_script("arguments[0].click();", item_menu)
        print("✅ Menu clicado! Aguardando o formulário interno abrir...")
        
        time.sleep(6) # Pausa dramática para o MV respirar antes de procurar a tela
        
        iframe_pronto = False
        for tentativa in range(45): # Aumentado para 45 segundos de tolerância
            driver.switch_to.default_content()
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            
            for frame in reversed(iframes):
                try:
                    driver.switch_to.frame(frame)
                    if driver.find_elements(By.XPATH, '//*[@id="tb-search"]/a/i'):
                        iframe_pronto = True
                        break
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
            if iframe_pronto: break
            time.sleep(1)
            
        if not iframe_pronto:
            print("❌ A tela de contas não carregou a tempo.")
            driver.quit()
            sys.exit()
            
    except Exception as e:
        print(f"❌ Falha ao tentar abrir a tela de contas: {e}")
        driver.quit()
        sys.exit()

    # --- 5. LOOP DE INJEÇÃO EM MASSA ---
    print("\n🚀 FORMULÁRIO PRONTO! INICIANDO INJEÇÃO DOS DADOS...")
    sucessos = 0
    erros = 0

    for index, row in df_validos.iterrows():
        conta_bruta = str(row['CONTA MV']).replace('.0', '')
        aih_bruta = str(row['AIH SISREG']).replace('.0', '')
        paciente = str(row['PACIENTE'])
        
        conta = re.sub(r'\D', '', conta_bruta)
        aih = re.sub(r'\D', '', aih_bruta)
        
        print(f"🔄 Injetando: Conta {conta} | AIH {aih} | {paciente[:20]}...", end=" ")
        
        try:
            # 🛡️ Foca no Iframe
            driver.switch_to.default_content()
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes: driver.switch_to.frame(iframes[-1])
            
            # 1. Clicar em Pesquisar (Lupa)
            icone_lupa = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tb-search"]/a/i')))
            action.move_to_element(icone_lupa).click().perform()
            time.sleep(1.5)
            
            # 2. Clicar na célula da Conta
            celula_conta = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="grdAtendConta"]/div[4]/div[3]/div/div/div[1]')))
            action.move_to_element(celula_conta).click().perform()
            time.sleep(0.5) 
            
            # Digitar a conta e apertar ENTER
            active = driver.switch_to.active_element
            active.send_keys(Keys.CONTROL + "a")
            active.send_keys(Keys.BACKSPACE)
            active.send_keys(conta)
            active.send_keys(Keys.ENTER) 
            time.sleep(0.5)
            
            # 3. Clicar em Executar Pesquisa (Check)
            icone_check = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tb-execute"]/a/i')))
            action.move_to_element(icone_check).click().perform()
            time.sleep(3) 
            
            try:
                # 4. Clicar na célula da AIH
                celula_aih = wait_rapido.until(EC.presence_of_element_located((By.XPATH, '//*[@id="grdAtendConta"]/div[4]/div[3]/div/div/div[2]')))
                action.move_to_element(celula_aih).click().perform()
                time.sleep(0.5)
                
                # Digitar AIH e apertar ENTER
                active = driver.switch_to.active_element
                active.send_keys(Keys.CONTROL + "a")
                active.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                active.send_keys(aih)
                active.send_keys(Keys.ENTER)
                time.sleep(0.5)
                
                # 5. Clicar em Salvar (Disquete)
                icone_salvar = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tb-record-save"]/a/i')))
                action.move_to_element(icone_salvar).click().perform()
                time.sleep(2) 
                
                print("✅ OK")
                sucessos += 1
                
            except Exception as e_inner:
                print(f"❌ Erro na AIH (Duplicada ou Não Encontrada).")
                erros += 1
                
                # --- DESTRUIDOR DE POPUPS ---
                try: driver.switch_to.alert.accept() # Fecha alertas nativos
                except: pass
                
                ActionChains(driver).send_keys(Keys.ESCAPE).perform() # Aperta ESC para fechar janelas do MV
                time.sleep(1)
                
                try: 
                    icone_cancelar = driver.find_element(By.XPATH, '//*[@id="tb-cancel"]/a/i')
                    action.move_to_element(icone_cancelar).click().perform()
                except: pass
                time.sleep(1.5)
                continue
                
        except Exception as e:
            print(f"❌ Erro de navegação na tela principal.")
            erros += 1
            
            # --- DESTRUIDOR DE POPUPS (Segurança) ---
            try: driver.switch_to.alert.accept()
            except: pass
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
            continue

    print("-" * 50)
    print(f"🎉 INJEÇÃO FINALIZADA! | Sucessos: {sucessos} | Erros: {erros}")
    print("-" * 50)

except Exception as e:
    print(f"\n❌ Erro Fatal no Robô: {e}")

input("\n✅ Processo concluído! Aperte ENTER para fechar o robô e o navegador...")
try: driver.quit()
except: pass