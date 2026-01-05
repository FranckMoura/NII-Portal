import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

print("--- 🤖 ROBÔ SOULMV (V1.7 - REACT ANT-DESIGN) ---")

# 1. Configurações
try:
    if getattr(sys, 'frozen', False): app_path = os.path.dirname(sys.executable)
    else: app_path = os.path.dirname(os.path.abspath(__file__))
    
    config_path = os.path.join(app_path, "config.json")
    if not os.path.exists(config_path):
        print("Erro: config.json não achado."); sys.exit()
        
    with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
    URL, USER, PASS = config['url'], config['usuario'], config['senha']
    CODIGO_TELA = config.get('codigo_tela', 'M_LACTO_AIH_P321')
except: sys.exit()

# 2. Navegador
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors=yes")
options.add_argument("--log-level=3")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 30) # Seu pedido: 30 segundos de tolerância
action = ActionChains(driver)

try:
    print(f">> Acessando: {URL}")
    driver.get(URL)

    # Pula SSL
    try:
        if "Privacy" in driver.title:
            driver.execute_script("document.getElementById('details-button').click();document.getElementById('proceed-link').click();")
    except: pass

    # --- LOGIN ---
    print(">> Login...")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
    inputs = driver.find_elements(By.TAG_NAME, "input")
    user_f = next((i for i in inputs if i.get_attribute("type") == "text"), None)
    pass_f = next((i for i in inputs if i.get_attribute("type") == "password"), None)
    
    if user_f and pass_f:
        user_f.send_keys(USER)
        pass_f.send_keys(PASS)
        time.sleep(0.5)
        # Tenta clicar no botão de login explicitamente
        try: driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        except: pass_f.send_keys(Keys.ENTER)
        print("✅ Login enviado!")

    # --- ETAPA NOVA: SELEÇÃO DE INSTITUIÇÃO (REACT) ---
    print("\n🏢 Aguardando carregamento do REACT (Até 30s)...")
    
    # 1. Espera a caixa de seleção (Classe do Ant Design) aparecer
    # O seletor .ant-select-selector é padrão dessa biblioteca
    seletor_caixa = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "ant-select-selector")))
    
    print("   -> Caixa de seleção encontrada! Aguardando estabilização (2s)...")
    time.sleep(2) # Espera o React terminar de "hidratar" a página

    try:
        print("   -> Clicando na caixa...")
        seletor_caixa.click()
        time.sleep(1) # Espera o menu abrir
        
        print("   -> Selecionando item...")
        action.send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(0.5)
        action.send_keys(Keys.ENTER).perform()
        time.sleep(1)
        
        # 2. Clicar no botão ACESSAR
        print("   -> Procurando botão 'Acessar'...")
        # Procura o botão que contém o texto 'Acessar'
        xpath_botao = "//button[contains(., 'Acessar')]"
        botao_acessar = driver.find_element(By.XPATH, xpath_botao)
        
        # Verifica se o botão ainda está desabilitado (disabled)
        if botao_acessar.get_attribute("disabled"):
            print("   ⚠️ Botão ainda desabilitado. Tentando Enter forçado...")
            action.send_keys(Keys.ENTER).perform()
        else:
            print("   -> Clicando em Acessar...")
            botao_acessar.click()
            
        print("✅ Instituição definida!")

    except Exception as e:
        print(f"⚠️ Erro na seleção visual: {e}")
        print("   -> Tentando Plano B (Enter x3)...")
        action.send_keys(Keys.ENTER).pause(1).send_keys(Keys.ENTER).pause(1).send_keys(Keys.ENTER).perform()

    # --- NAVEGAÇÃO FINAL ---
    print(f"\n>> Aguardando Menu Principal...")
    time.sleep(10) # Tempo para o carregamento pós-seleção

    sucesso = False
    
    # Tentativa Busca Genérica (Funciona melhor agora)
    try:
        print("🔎 Buscando...")
        campos = driver.find_elements(By.CSS_SELECTOR, "input.search-input, input[placeholder*='Pesquisar']")
        for c in campos:
            if c.is_displayed():
                c.clear()
                c.send_keys(CODIGO_TELA)
                c.send_keys(Keys.ENTER)
                sucesso = True
                print("✅ SUCESSO! Tela acessada.")
                break
    except: pass

    if not sucesso:
        print("\n⚠️ ALERTA: Menu não acessado automaticamente.")
        print(f"👉 Digite '{CODIGO_TELA}' manualmente.")

    print("\n🏁 FINALIZADO.")
    input("🔴 Pressione ENTER para fechar...")

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    input()
finally:
    try: driver.quit()
    except: pass