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

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

print("--- 🤖 ROBÔ SOULMV (V1.6 - ESTRATÉGIA TECLADO) ---")

# ==============================================================================
# 1. CARREGAMENTO DAS CONFIGURAÇÕES
# ==============================================================================
try:
    if getattr(sys, 'frozen', False): application_path = os.path.dirname(sys.executable)
    else: application_path = os.path.dirname(os.path.abspath(__file__))

    config_path = os.path.join(application_path, "config.json")
    if not os.path.exists(config_path):
        print(f"⚠️ ERRO: 'config.json' não encontrado."); input("Enter para sair..."); sys.exit()

    with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
    URL_SOULMV, USUARIO, SENHA = config['url'], config['usuario'], config['senha']
    CODIGO_TELA = config.get('codigo_tela', 'M_LACTO_AIH_P321')
except Exception as e:
    print(f"❌ Erro Config: {e}"); sys.exit()

# ==============================================================================
# 2. CONFIGURAÇÃO DO NAVEGADOR
# ==============================================================================
print("🚀 Configurando navegador...")
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-running-insecure-content")
options.add_argument("--ignore-ssl-errors=yes")
options.add_argument("--accept-insecure-certs")
options.add_argument("--disable-extensions")
options.add_argument("--log-level=3")

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)
    action = ActionChains(driver)

    print(f">> Acessando: {URL_SOULMV}")
    driver.get(URL_SOULMV)

    # Pula aviso de segurança
    try:
        if "Privacy" in driver.title or "conexão" in driver.title:
            driver.execute_script("document.getElementById('details-button').click();")
            driver.execute_script("document.getElementById('proceed-link').click();")
    except: pass

    # --- LOGIN (A PARTE QUE FUNCIONA) ---
    print(">> Aguardando tela de login...")
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        inputs = driver.find_elements(By.TAG_NAME, "input")
        user_f, pass_f = None, None
        for i in inputs:
            if i.get_attribute("type") == "text" and not user_f: user_f = i
            if i.get_attribute("type") == "password" and not pass_f: pass_f = i
        
        if user_f and pass_f:
            user_f.clear(); user_f.send_keys(USUARIO)
            pass_f.clear(); pass_f.send_keys(SENHA)
            time.sleep(0.5)
            pass_f.send_keys(Keys.ENTER)
            print("✅ Login enviado!")
        else: print("⚠️ Login manual necessário.")
    except: pass

    # --- NOVA ESTRATÉGIA: INSTITUIÇÃO ---
    print("\n🏢 Aguardando Janela de Instituição (10s)...")
    time.sleep(8) # Tempo fixo para garantir que a janela apareceu

    # Verifica se existe IFRAME (Janela dentro da Janela)
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(iframes) > 0:
        print(f"   ℹ️ Detectei {len(iframes)} janelas internas (Iframes).")
        try:
            driver.switch_to.frame(0) # Tenta focar na primeira janela interna
            print("   -> Foco alterado para a janela interna.")
        except: pass

    print("   -> Tentando navegar via TECLADO (TAB + SETAS)...")
    
    # Tenta focar no campo clicando "no nada" primeiro para garantir o foco na janela
    try:
        driver.find_element(By.TAG_NAME, "body").click()
    except: pass

    # Sequência de teclas: TAB algumas vezes para achar o campo, depois Baixo, depois Enter
    # Vamos tentar TAB 1 vez, depois Seta Baixo
    try:
        print("   -> Enviando: TAB...")
        action.send_keys(Keys.TAB).perform()
        time.sleep(0.5)
        
        print("   -> Enviando: SETA BAIXO (Para abrir a lista)...")
        action.send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(1)
        
        print("   -> Enviando: ENTER (Para selecionar)...")
        action.send_keys(Keys.ENTER).perform()
        time.sleep(1)
        
        print("   -> Enviando: ENTER (Para confirmar)...")
        action.send_keys(Keys.ENTER).perform()
    except Exception as e:
        print(f"   ⚠️ Erro no envio de teclas: {e}")

    # Volta para o contexto principal (caso tenha entrado em iframe)
    driver.switch_to.default_content()

    # --- NAVEGAÇÃO TELA (MENU) ---
    print(f"\n>> Aguardando Menu Principal...")
    time.sleep(5)

    sucesso = False
    
    # TENTATIVA 1: Busca Genérica (Mais confiável que XPath neste ponto)
    if not sucesso:
        try:
            print("🔎 Procurando barra de pesquisa...")
            # Procura qualquer input visível que pareça de busca
            inputs_busca = driver.find_elements(By.CSS_SELECTOR, "input.search-input, input[placeholder*='Pesquisar'], input[type='text']")
            
            for input_b in inputs_busca:
                if input_b.is_displayed():
                    try:
                        input_b.clear()
                        input_b.send_keys(CODIGO_TELA)
                        input_b.send_keys(Keys.ENTER)
                        print("✅ SUCESSO! Comando enviado.")
                        sucesso = True
                        break
                    except: continue
        except: pass

    # TENTATIVA 2: XPath Antigo da Lupa (Backup)
    if not sucesso:
        try:
            xpath_lupa = "/html/body/div/div/section/ul/li[1]/input"
            busca = driver.find_element(By.XPATH, xpath_lupa)
            busca.click()
            busca.send_keys(CODIGO_TELA)
            busca.send_keys(Keys.ENTER)
            sucesso = True
        except: pass

    if not sucesso:
        print("\n⚠️ ALERTA: Não consegui acessar a tela automaticamente.")
        print(f"👉 AÇÃO: Digite '{CODIGO_TELA}' manualmente.")

    print("\n" + "="*40)
    print("🏁 PROCESSO FINALIZADO")
    print("="*40)
    input("🔴 Pressione ENTER para fechar...")

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    input("Enter para sair...")
finally:
    try: driver.quit()
    except: pass