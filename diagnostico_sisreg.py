import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" 

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    print("--- INICIANDO DIAGNÓSTICO ---")
    # 1. Login
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    time.sleep(2)
    driver.find_element(By.ID, "usuario").send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    time.sleep(3)

    # 2. Navegar
    driver.find_element(By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a").click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a").click()
    print("Chegamos na tela do Exportador.")
    time.sleep(5) # Espera bem longa para garantir que carregou tudo

    # 3. Investigação
    print("\n--- PROCURANDO FRAMES ---")
    frames = driver.find_elements(By.TAG_NAME, "frame")
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    
    print(f"Total de tags <frame> encontradas: {len(frames)}")
    for i, frame in enumerate(frames):
        nome = frame.get_attribute("name")
        id_frame = frame.get_attribute("id")
        src = frame.get_attribute("src")
        print(f"  Frame {i}: Name='{nome}', ID='{id_frame}', Src='{src}'")

    print(f"\nTotal de tags <iframe> encontradas: {len(iframes)}")
    for i, iframe in enumerate(iframes):
        nome = iframe.get_attribute("name")
        id_iframe = iframe.get_attribute("id")
        src = iframe.get_attribute("src")
        print(f"  iFrame {i}: Name='{nome}', ID='{id_iframe}', Src='{src}'")

    print("\n--- PROCURANDO O CAMPO DE DATA DIRETAMENTE ---")
    try:
        driver.find_element(By.ID, "dtaIniSolic")
        print("ACHEI! O campo está na página principal (não está dentro de frame nenhum).")
    except:
        print("NÃO ACHEI na página principal. Ele está definitivamente escondido dentro de um frame.")

except Exception as e:
    print(f"Erro: {e}")

finally:
    input("\nPressione ENTER para fechar...")
    driver.quit()