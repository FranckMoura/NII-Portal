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

# --- CONFIGURAÇÕES ---
print(f"--- 1. INICIANDO EXTRAÇÃO SISREG (V5 - COM LIMPEZA) ---")
USUARIO = "046FRANCK"
SENHA = "515462" # <--- INSIRA SUA SENHA AQUI SE NÃO TIVER SALVA
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- LIMPEZA PRÉVIA (CRUCIAL) ---
# Apaga CSVs antigos para não misturar dados de ontem com hoje
print(">> Limpando arquivos antigos da pasta de exportação...")
arquivos_velhos = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv"))
for f in arquivos_velhos:
    try:
        os.remove(f)
    except: pass
print(f">> Pasta limpa. Iniciando downloads...")

# --- NAVEGADOR ---
options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_DOWNLOAD, "download.prompt_for_download": False, "directory_upgrade": True}
options.add_experimental_option("prefs", prefs)

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    # LOGIN
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    
    wait.until(EC.presence_of_element_located((By.ID, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # NAVEGAÇÃO
    print(">> Acessando Exportador...")
    # Tenta navegar pelo menu ou URL direta se possível
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()
    except:
        print(">> Menu mudou? Tentando acesso direto...")
        # Adicione URL direta aqui se souber, senão segue o erro
        pass

    # LOOP DE DATAS (Últimos 90 dias)
    hoje = datetime.now()
    data_atual_loop = hoje - timedelta(days=90)
    
    while data_atual_loop < hoje:
        fim_bloco = data_atual_loop + timedelta(days=29)
        if fim_bloco > hoje: fim_bloco = hoje
        
        d_ini = data_atual_loop.strftime("%d/%m/%Y")
        d_fim = fim_bloco.strftime("%d/%m/%Y")
        print(f">> Baixando período: {d_ini} a {d_fim}")

        # Preenche formulário
        driver.switch_to.default_content()
        try:
            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
        except: pass

        wait.until(EC.presence_of_element_located((By.NAME, "data_inicio"))).clear()
        driver.find_element(By.NAME, "data_inicio").send_keys(d_ini)
        driver.find_element(By.NAME, "data_fim").clear()
        driver.find_element(By.NAME, "data_fim").send_keys(d_fim)
        
        # Clica em Gerar
        driver.find_element(By.CSS_SELECTOR, "input[type='button'][value='Gerar']").click()
        time.sleep(3) # Espera download iniciar
        
        data_atual_loop = fim_bloco + timedelta(days=1)

    print(">> Downloads finalizados (aguardando conclusão)...")
    time.sleep(10)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ Erro na extração: {e}")
    if 'driver' in locals(): driver.quit()