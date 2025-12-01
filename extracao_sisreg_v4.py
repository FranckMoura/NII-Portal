import time
import os
import sys
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. CONFIGURAÇÃO INICIAL ---
print(f"--- Iniciando Script de Extração (V8 - Auto-Correção) ---")
print(f"Hora atual: {datetime.now().strftime('%H:%M')}")

# --- 2. CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

# --- 3. CONFIGURAÇÃO DO NAVEGADOR ---
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
except Exception as e:
    print(f"❌ Erro ao abrir navegador: {e}")
    sys.exit()

# --- FUNÇÃO DE DOWNLOAD BLINDADA ---
def baixar_bloco(data_ini, data_fim):
    print(f"\n   >>> Baixando bloco: {data_ini} até {data_fim}")
    
    # Garante foco no frame principal
    driver.switch_to.default_content()
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "f_main")))
    except:
        pass

    # Preenche datas
    wait.until(EC.presence_of_element_located((By.ID, "dtaIniSolic")))
    c_ini = driver.find_element(By.ID, "dtaIniSolic")
    driver.execute_script(f"arguments[0].value = '{data_ini}';", c_ini)
    
    c_fim = driver.find_element(By.ID, "dtaFimSolic")
    driver.execute_script(f"arguments[0].value = '{data_fim}';", c_fim)
    
    # Rola para o fim
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    
    # Tenta Clicar no Exportar (Primeira Tentativa)
    try:
        # Tenta achar checkboxes para ter referência
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        
        # Clica no botão Exportar
        botao_exportar = driver.find_element(By.XPATH, "//input[@value='Exportar']")
        botao_exportar.click()
        
        # --- A MÁGICA DA CORREÇÃO DE ERRO ---
        # Verifica imediatamente se apareceu o alerta de "Selecione um item"
        try:
            # Espera 1 segundo para ver se o alerta aparece
            WebDriverWait(driver, 2).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            texto_alerta = alert.text
            
            if "Informe pelo menos um item" in texto_alerta:
                print("       ⚠️ Alerta detectado: Nenhum item selecionado.")
                alert.accept() # Fecha o alerta
                
                print("       🔄 Corrigindo seleção...")
                if len(checkboxes) > 0:
                    checkboxes[0].click() # Clica para selecionar tudo
                    time.sleep(1)
                    botao_exportar.click() # Tenta exportar de novo
                    print("       ✅ Reenviado com sucesso.")
            else:
                # Se for outro alerta, só aceita
                alert.accept()
                
        except:
            # Se não deu alerta nenhum, é porque deu certo de primeira!
            pass

    except Exception as e:
        print(f"       ❌ Erro na interação: {e}")

    print("       Aguardando download (15s)...")
    time.sleep(15)

# --- FLUXO PRINCIPAL ---
try:
    # Login
    print(">> Acessando página de login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "usuario")))

    driver.find_element(By.ID, "usuario").send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # Navegação
    print(">> Navegando para o Exportador...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()

    # Loop de Datas
    print(">> Iniciando Loop de Extração...")
    
    hoje = datetime.now()
    data_final_geral = hoje
    data_atual_loop = hoje - timedelta(days=90)
    
    while data_atual_loop < data_final_geral:
        fim_bloco = data_atual_loop + timedelta(days=29)
        if fim_bloco > data_final_geral: fim_bloco = data_final_geral
            
        str_ini = data_atual_loop.strftime("%d/%m/%Y")
        str_fim = fim_bloco.strftime("%d/%m/%Y")
        
        baixar_bloco(str_ini, str_fim)
        
        data_atual_loop = fim_bloco + timedelta(days=1)

except Exception as e:
    print(f"\n❌ ERRO FATAL: {e}")

finally:
    print("\n--- Processo Finalizado ---")
    try:
        driver.quit()
    except:
        pass