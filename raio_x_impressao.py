import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V10 - DIAGNÓSTICO DE LINHA) ---")
# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"

options = webdriver.ChromeOptions()
options.add_argument("--disable-print-preview")

def get_datas_mes_atual():
    hoje = datetime.now()
    return hoje.replace(day=1).strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def focar_frame_principal(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            if "Período" in driver.page_source or "Solicitacao" in driver.page_source: return True
        except: pass
    driver.switch_to.default_content()
    try: driver.switch_to.frame(1); return True
    except: return False

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    # LOGIN
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    # NAVEGAÇÃO
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)
    focar_frame_principal(driver)

    # PESQUISA
    dt_ini, dt_fim = get_datas_mes_atual()
    try:
        inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
        if len(inputs) >= 2: inputs[0].clear(); inputs[0].send_keys(dt_ini); inputs[1].clear(); inputs[1].send_keys(dt_fim)
    except: pass
    
    try: driver.find_element(By.NAME, "enviar").click()
    except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
    time.sleep(5)
    
    # --- DIAGNÓSTICO ---
    print("\n\n--- INÍCIO DO RAIO-X DA TABELA ---")
    tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
    tabela = tabelas[-1]
    linhas = tabela.find_elements(By.TAG_NAME, "tr")
    
    if len(linhas) > 1:
        primeira_linha_dados = linhas[1] # Pula header
        html_linha = primeira_linha_dados.get_attribute('innerHTML')
        
        print(">> HTML ENCONTRADO NA LINHA DO PACIENTE:")
        print("--------------------------------------------------")
        print(html_linha)
        print("--------------------------------------------------")
        print(">> Copie o código acima e mande no chat!")
    else:
        print("❌ Nenhuma linha de dados encontrada para diagnosticar.")

    driver.quit()

except Exception as e:
    print(f"❌ ERRO: {e}")