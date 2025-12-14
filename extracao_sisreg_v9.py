import time
import os
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V10 - BASEADO NO V4) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- INSIRA SUA SENHA AQUI
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Configuração do Navegador
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
    
    wait.until(EC.presence_of_element_located((By.ID, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # --- NAVEGAÇÃO ---
    print(">> Navegando para o Exportador...")
    # Menu Relatórios
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    # Submenu Exportação
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()
    
    time.sleep(3) # Tempo para carregar a página

    # --- LOOP DE DATAS ---
    hoje = datetime.now()
    data_atual_loop = hoje - timedelta(days=90) # Baixa últimos 90 dias
    
    print(">> Iniciando downloads...")

    while data_atual_loop < hoje:
        fim_bloco = data_atual_loop + timedelta(days=29)
        if fim_bloco > hoje: fim_bloco = hoje
        
        d1 = data_atual_loop.strftime("%d/%m/%Y")
        d2 = fim_bloco.strftime("%d/%m/%Y")
        print(f">> Baixando período: {d1} a {d2}")

        # 1. ENTRAR NO IFRAME (Fundamental, igual ao V4)
        driver.switch_to.default_content()
        try:
            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
        except:
            print("   (Aviso: Iframe não encontrado, tentando direto...)")

        # 2. ROLAR A TELA (O que faltava)
        # Rola até o fim para garantir que campos e checkboxes estejam visíveis
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        try:
            # 3. PREENCHER DATAS (Digitando, igual ao V4)
            # Data Inicio
            inp_ini = wait.until(EC.element_to_be_clickable((By.NAME, "data_inicio")))
            inp_ini.clear()
            inp_ini.send_keys(d1)
            time.sleep(0.5)
            
            # Data Fim
            inp_fim = driver.find_element(By.NAME, "data_fim")
            inp_fim.clear()
            inp_fim.send_keys(d2)
            time.sleep(0.5)

            # 4. CHECKBOX (Novo Requisito)
            # Procura qualquer checkbox na tela e marca
            checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            for cb in checkboxes:
                try:
                    if not cb.is_selected():
                        cb.click()
                except:
                    # Se não der pra clicar normal, força via JS, mas só no checkbox
                    driver.execute_script("arguments[0].click();", cb)
            
            # 5. BOTÃO GERAR/EXPORTAR
            try:
                # Tenta achar o botão. Às vezes o ID muda, então pegamos pelo tipo
                btn = driver.find_element(By.CSS_SELECTOR, "input[type='button'][value='Gerar']")
                btn.click()
            except:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, "input[type='button'][value='Exportar']")
                    btn.click()
                except:
                    print("   ❌ Botão 'Gerar' não encontrado.")

            # 6. ALERTAS E ESPERA (Paciência do V4)
            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                print("   (Alerta aceito)")
            except:
                pass

            print("   Aguardando download (15s)...")
            time.sleep(15) # Espera o arquivo baixar

        except Exception as e:
            print(f"   Erro neste período: {e}")

        data_atual_loop = fim_bloco + timedelta(days=1)

    print(">> Ciclo finalizado.")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ Erro Geral: {e}")
    if 'driver' in locals(): driver.quit()