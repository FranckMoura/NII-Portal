import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("--- 📸 ROBÔ DUMPER (CÓPIA TOTAL) ---")

# 1. Config
try:
    if getattr(sys, 'frozen', False): app_path = os.path.dirname(sys.executable)
    else: app_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(app_path, "config.json"), 'r') as f: config = json.load(f)
    URL, USER, PASS = config['url'], config['usuario'], config['senha']
except: sys.exit()

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors=yes")
options.add_argument("--log-level=3")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 30)

try:
    print(">> Acessando e Logando...")
    driver.get(URL)
    
    # Pula SSL
    try:
        if "Privacy" in driver.title:
            driver.execute_script("document.getElementById('details-button').click();")
            driver.execute_script("document.getElementById('proceed-link').click();")
    except: pass

    # Login
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for i in inputs:
        if i.get_attribute("type") == "text": i.send_keys(USER)
        if i.get_attribute("type") == "password": i.send_keys(PASS + "\n")
    
    print("\n⏳ AGUARDANDO 20 SEGUNDOS NA TELA DE INSTITUIÇÃO...")
    print("   (Por favor, não feche o navegador)")
    time.sleep(20) # Tempo exagerado para garantir

    # SALVA O HTML COMPLETO
    html_content = driver.page_source
    
    arquivo_saida = os.path.join(app_path, "CODIGO_FONTE_TELA.html")
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("\n✅ CÓPIA CONCLUÍDA!")
    print(f"📄 Arquivo gerado: {arquivo_saida}")
    print("👉 ME MANDE ESSE ARQUIVO 'CODIGO_FONTE_TELA.html' (ou copie o conteúdo dele se for pequeno).")
    input("Enter para fechar...")

except Exception as e:
    print(e)
    input()
finally:
    driver.quit()