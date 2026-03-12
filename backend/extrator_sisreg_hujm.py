import time
import os
import calendar
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (VERSÃO CLIENTE - ÚLTIMOS 3 MESES) ---")

# --- CREDENCIAIS DO CLIENTE ---
USUARIO = "022820291grazielly-sol"
SENHA = "171717" 

# --- NOVA PASTA ISOLADA ---
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\downloads_cliente"

if not os.path.exists(PASTA_DOWNLOAD): 
    try:
        os.makedirs(PASTA_DOWNLOAD)
        print(f">> Pasta criada: {PASTA_DOWNLOAD}")
    except Exception as e:
        print(f"❌ Erro ao criar pasta: {e}")

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_setting_values.automatic_downloads": 1 
}
options.add_experimental_option("prefs", prefs)

# --- NOVA FUNÇÃO DATAS: Exatamente os últimos 3 meses ---
def gerar_ultimos_3_meses():
    periodos = []
    hoje = datetime.now()
    
    # Loop de 2 até 0 (Para pegar: Mês-2, Mês-1 e Mês Atual)
    for i in range(2, -1, -1):
        mes_alvo = hoje.month - i
        ano_alvo = hoje.year
        
        # Se o mês alvo for 0 ou negativo (ex: estamos em Jan e voltamos 2 meses), ajusta o ano
        if mes_alvo <= 0:
            mes_alvo += 12
            ano_alvo -= 1
            
        data_ini = datetime(ano_alvo, mes_alvo, 1)
        ultimo_dia = calendar.monthrange(ano_alvo, mes_alvo)[1]
        data_fim = datetime(ano_alvo, mes_alvo, ultimo_dia)
        periodos.append((data_ini, data_fim))
        
    return periodos

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
    
    try:
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except:
        driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    # --- NAVEGAÇÃO ---
    print(">> Navegando para Exportação...")
    try:
        try:
            menu_rel = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a")))
            menu_rel.click()
        except:
            driver.execute_script("document.querySelector('#barraMenu > ul > li:nth-child(5) > a').click();")
        
        time.sleep(1) 

        try:
            submenu = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a")))
            submenu.click()
        except:
            driver.execute_script("document.querySelector('#barraMenu > ul > li:nth-child(5) > ul > li:nth-child(3) > a').click();")
            
    except Exception as e:
        print(f"❌ Erro na navegação: {e}")
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/rel_exportacao_solicitacoes_amb")

    time.sleep(5) 

    # --- LOOP DE DOWNLOADS (Últimos 3 Meses) ---
    lista_periodos = gerar_ultimos_3_meses()
    print(f">> Iniciando download de {len(lista_periodos)} arquivos na pasta: {PASTA_DOWNLOAD}")

    for dt_ini, dt_fim in lista_periodos:
        d1 = dt_ini.strftime("%d/%m/%Y")
        d2 = dt_fim.strftime("%d/%m/%Y")
        print(f">> Baixando: {d1} a {d2}")

        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        iframe_found = False
        
        for i in range(len(frames)):
            driver.switch_to.default_content()
            try:
                driver.switch_to.frame(i)
                if len(driver.find_elements(By.NAME, "dtaIniSolic")) > 0:
                    iframe_found = True
                    break 
            except: pass
        
        if not iframe_found:
            print("   ❌ ERRO: Formulário não encontrado. Tentando recarregar a página...")
            driver.refresh()
            time.sleep(5)
            continue

        try:
            driver.execute_script(f"document.getElementsByName('dtaIniSolic')[0].value = '{d1}'")
            driver.execute_script(f"document.getElementsByName('dtaFimSolic')[0].value = '{d2}'")

            driver.execute_script("""
                var inputs = document.getElementsByTagName('input');
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].type == 'checkbox') inputs[i].checked = true;
                }
            """)
            
            print("   (Solicitando arquivo...)")
            driver.execute_script("if(typeof exportar == 'function') { exportar(); } else { document.getElementsByName('exp')[0].click(); }")

            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except:
                print("   (Download iniciado...)")

            time.sleep(15) 

        except Exception as e:
            print(f"   ❌ Erro técnico: {e}")

    print(">> Finalizando...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")
    if 'driver' in locals(): driver.quit()