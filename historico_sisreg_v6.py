import time
import os
import calendar
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- SUA SENHA AQUI
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

# Configuração do Período
ANO_INICIO = 2019
ANO_FIM = 2025
MES_FINAL_2025 = 11

print("--- CARGA HISTÓRICA SISREG (VERSÃO 6 - ANTI-ALERTA) ---")
print(f"De: Jan/{ANO_INICIO} até Nov/{ANO_FIM}")

os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def esperar_download_e_renomear(ano, mes):
    nome_final = f"SISREG_{ano}_{mes:02d}.csv"
    caminho_final = os.path.join(PASTA_DOWNLOAD, nome_final)
    
    if os.path.exists(caminho_final):
        print(f"   [OK] Arquivo {nome_final} já existe.")
        return True

    print("   [..] Aguardando download...")
    for _ in range(60):
        arquivos = os.listdir(PASTA_DOWNLOAD)
        csvs = [f for f in arquivos if f.endswith('.csv') and 'SISREG_' not in f]
        if csvs:
            arquivo_baixado = os.path.join(PASTA_DOWNLOAD, csvs[0])
            try:
                if os.path.getsize(arquivo_baixado) > 0:
                    time.sleep(2)
                    shutil.move(arquivo_baixado, caminho_final)
                    print(f"   [Sucesso] Salvo como: {nome_final}")
                    return True
            except:
                pass
        time.sleep(1)
    print("   [Aviso] Download não detectado (sem dados?).")
    return False

def navegar_para_exportador():
    """Função que clica nos menus para chegar no formulário"""
    print("   -> Navegando pelo menu...")
    wait = WebDriverWait(driver, 15)
    driver.switch_to.default_content()
    menu1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a")))
    menu1.click()
    menu2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a")))
    menu2.click()
    print("   -> Menu clicado.")

def tentar_marcar_e_exportar():
    """Tenta marcar o checkbox e exportar. Se der alerta, tenta corrigir."""
    wait = WebDriverWait(driver, 5)
    
    # Tentativa 1: Marcar e Clicar
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        if checkboxes: checkboxes[0].click()
        
        time.sleep(1)
        driver.find_element(By.XPATH, "//input[@value='Exportar']").click()
    except Exception as e:
        # Se falhar o clique normal, tenta via JS
        try:
            driver.execute_script("document.querySelector('input[value=\"Exportar\"]').click()")
        except:
            pass

    # VERIFICAÇÃO DE ALERTA (O PULO DO GATO)
    try:
        # Espera um pouquinho pra ver se aparece o alerta
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        texto_alerta = alert.text
        print(f"   [ALERTA DETECTADO] O site disse: '{texto_alerta}'")
        alert.accept() # Clica em OK no alerta
        
        if "Informe pelo menos um item" in texto_alerta:
            print("   -> Corrigindo: Tentando marcar o checkbox novamente...")
            time.sleep(1)
            # Tenta marcar de novo (as vezes o primeiro clique desmarcou em vez de marcar)
            checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            if checkboxes: checkboxes[0].click()
            time.sleep(1)
            # Clica em Exportar de novo
            driver.find_element(By.XPATH, "//input[@value='Exportar']").click()
            
    except TimeoutException:
        # Se não apareceu alerta nenhum, é porque deu certo (ou deu outro erro)
        pass

try:
    # 1. LOGIN
    print("1. Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "usuario")))
    driver.find_element(By.ID, "usuario").send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    time.sleep(3)

    # 2. NAVEGAÇÃO INICIAL
    print("2. Acessando Exportador...")
    navegar_para_exportador()
    
    # 3. LOOP HISTÓRICO
    for ano in range(ANO_INICIO, ANO_FIM + 1):
        for mes in range(1, 13):
            
            if ano == 2025 and mes > MES_FINAL_2025:
                break
                
            print(f"\n>> MÊS: {mes:02d}/{ano}")
            
            # --- GARANTIA DE NAVEGAÇÃO ---
            driver.switch_to.default_content()
            try:
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "f_main")))
                driver.find_element(By.ID, "dtaIniSolic")
            except Exception:
                print("   [Info] Perdemos o formulário. Navegando novamente...")
                navegar_para_exportador()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "f_main")))

            # Datas
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            data_ini = f"01/{mes:02d}/{ano}"
            data_fim = f"{ultimo_dia}/{mes:02d}/{ano}"
            
            wait.until(EC.presence_of_element_located((By.ID, "dtaIniSolic")))
            driver.execute_script(f"document.getElementById('dtaIniSolic').value = '{data_ini}';")
            driver.execute_script(f"document.getElementById('dtaFimSolic').value = '{data_fim}';")
            
            # AÇÃO DE EXPORTAR (COM TRATAMENTO DE ALERTA)
            tentar_marcar_e_exportar()

            # Monitora download
            esperar_download_e_renomear(ano, mes)
            time.sleep(1)

except Exception as e:
    print(f"\n❌ ERRO GERAL: {e}")
    # Tenta aceitar alerta se ele ficou travado na tela
    try: 
        driver.switch_to.alert.accept()
    except: 
        pass

finally:
    input("\nFim do processo. Pressione ENTER...")
    driver.quit()