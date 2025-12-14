import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V13 - MENU + JS) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- COLOQUE SUA SENHA AQUI
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

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    # --- LOGIN ---
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    
    # Tenta clicar no botão de entrar de forma genérica
    try:
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except:
        driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # --- NAVEGAÇÃO VIA MENU (IGUAL AO V4) ---
    # Isso é crucial para criar a sessão correta
    print(">> Navegando pelo Menu...")
    try:
        # Menu Relatórios
        menu1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a")))
        menu1.click()
        time.sleep(1)
        
        # Submenu Exportação
        menu2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a")))
        menu2.click()
    except Exception as e:
        print(f"❌ Erro no menu: {e}")
        driver.quit()
        exit()

    time.sleep(5) # Espera o iframe carregar

    # --- LOOP DE DATAS ---
    hoje = datetime.now()
    data_atual = hoje - timedelta(days=90)
    
    print(">> Iniciando downloads...")

    while data_atual < hoje:
        fim = data_atual + timedelta(days=29)
        if fim > hoje: fim = hoje
        
        d1 = data_atual.strftime("%d/%m/%Y")
        d2 = fim.strftime("%d/%m/%Y")
        print(f">> Baixando período: {d1} a {d2}")

        # 1. ENTRAR NO IFRAME
        driver.switch_to.default_content()
        try:
            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
        except:
            print("   (Aviso: Iframe não encontrado, tentando direto...)")

        try:
            # 2. ROLAR A TELA (Para o checkbox aparecer no DOM)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 3. PREENCHER DATAS (Digitação normal, que você disse que funcionava)
            dt_ini = wait.until(EC.element_to_be_clickable((By.NAME, "data_inicio")))
            dt_ini.clear()
            dt_ini.send_keys(d1)
            time.sleep(0.5)
            
            dt_fim = driver.find_element(By.NAME, "data_fim")
            dt_fim.clear()
            dt_fim.send_keys(d2)
            time.sleep(0.5)

            # 4. CHECKBOX (O PULO DO GATO - VIA JS)
            # Encontra todos os checkboxes e clica neles via código, ignorando se estão escondidos
            checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            count = 0
            for cb in checkboxes:
                if not cb.is_selected():
                    # O 'execute_script' clica mesmo se o elemento estiver coberto por outro
                    driver.execute_script("arguments[0].click();", cb)
                    count += 1
            if count > 0: print(f"   (Checkboxes marcados via JS: {count})")

            # 5. BOTÃO GERAR (VIA JS)
            # Tenta achar o botão e clicar via código
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "input[value='Gerar']")
                driver.execute_script("arguments[0].click();", btn)
            except:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, "input[value='Exportar']")
                    driver.execute_script("arguments[0].click();", btn)
                except:
                    print("   ❌ Botão Gerar não encontrado via CSS.")

            # 6. ALERTAS
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                print("   (Alerta aceito)")
            except:
                print("   (Download iniciado...)")

            time.sleep(15) # Espera baixar

        except Exception as e:
            print(f"   ❌ Erro neste período: {e}")

        data_atual = fim + timedelta(days=1)

    print(">> Finalizando...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")
    if 'driver' in locals(): driver.quit()