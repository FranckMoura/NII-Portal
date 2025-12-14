import time
import os
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V9 - COM SCROLL E CHECKBOX) ---")

# --- SUAS CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- SUA SENHA AQUI
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

# --- FUNÇÃO AUXILIAR: CLIQUE FORÇADO ---
def forcar_clique(driver, elemento):
    # Rola a tela até o elemento e clica via Javascript (ignora erros de visibilidade)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", elemento)

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    # LOGIN
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    wait.until(EC.presence_of_element_located((By.ID, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # NAVEGAÇÃO
    print(">> Acessando Exportador...")
    try:
        # Menu Relatórios -> Exportação
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()
    except:
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/rel_exportacao_solicitacoes_amb")

    # LOOP DE DATAS
    hoje = datetime.now()
    data_atual = hoje - timedelta(days=90)
    
    print(">> Iniciando ciclo de downloads...")

    while data_atual < hoje:
        fim = data_atual + timedelta(days=29)
        if fim > hoje: fim = hoje
        
        d1 = data_atual.strftime("%d/%m/%Y")
        d2 = fim.strftime("%d/%m/%Y")
        print(f">> Processando: {d1} a {d2}")

        # 1. Focar no Iframe (Obrigatório)
        driver.switch_to.default_content()
        try:
            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
        except: pass

        try:
            # 2. INJETAR DATAS (Resolve o problema de não conseguir clicar no campo)
            # Em vez de digitar, mandamos o valor direto pro HTML
            script_datas = f"""
                document.getElementsByName('data_inicio')[0].value = '{d1}';
                document.getElementsByName('data_fim')[0].value = '{d2}';
            """
            driver.execute_script(script_datas)
            
            # 3. MARCAR CHECKBOX (O Passo que faltava)
            # Procura todos os checkboxes da tela e marca eles
            checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            for cb in checkboxes:
                if not cb.isSelected():
                    forcar_clique(driver, cb)
            
            # 4. CLICAR EM EXPORTAR (Com Scroll)
            # Tenta achar o botão pelo valor 'Gerar' ou 'Exportar'
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "input[type='button'][value='Gerar']")
            except:
                btn = driver.find_element(By.CSS_SELECTOR, "input[type='button'][value='Exportar']")
            
            forcar_clique(driver, btn)
            
            # 5. LIDAR COM ALERTAS
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                print("   (Alerta aceito)")
            except:
                print("   (Download iniciado...)")
            
            time.sleep(15) # Tempo para o download terminar

        except Exception as e:
            print(f"   Erro neste período: {e}")

        data_atual = fim + timedelta(days=1)

    print(">> Finalizando...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ Erro Geral: {e}")
    if 'driver' in locals(): driver.quit()