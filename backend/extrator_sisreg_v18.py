import time
import os
import calendar
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V18 - NUVEM HEADLESS) ---")

USUARIO = os.environ.get("SISREG_USER", "046FRANCK")
SENHA = os.environ.get("SISREG_PASS", "212425")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOAD = os.path.join(BASE_DIR, "downloads")

if not os.path.exists(PASTA_DOWNLOAD): 
    try:
        os.makedirs(PASTA_DOWNLOAD)
        print(f">> Pasta criada: {PASTA_DOWNLOAD}")
    except Exception as e:
        print(f"❌ Erro ao criar pasta: {e}")

# --- A MÁGICA ESTÁ AQUI: CONFIGURAÇÃO CHROME INVISÍVEL ---
options = webdriver.ChromeOptions()
options.add_argument("--headless=new") 
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")

prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_setting_values.automatic_downloads": 1 
}
options.add_experimental_option("prefs", prefs)

def gerar_periodos_desde_2025():
    periodos = []
    data_atual = datetime.now()
    
    ano_inicio = 2026
    mes_inicio = 1
    
    ano_fim = data_atual.year
    mes_fim = data_atual.month
    
    for ano in range(ano_inicio, ano_fim + 1):
        mes_start = mes_inicio if ano == ano_inicio else 1
        mes_end = mes_fim if ano == ano_fim else 12
        
        for mes in range(mes_start, mes_end + 1):
            data_ini = datetime(ano, mes, 1)
            if ano == ano_fim and mes == mes_fim:
                data_fim = data_atual
            else:
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                data_fim = datetime(ano, mes, ultimo_dia)
                
            periodos.append((data_ini, data_fim))
    return periodos

try:
    print(">> Abrindo navegador na Nuvem...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    
    try:
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except:
        driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

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
        print(f"❌ Erro na navegação do menu, tentando URL direta...")
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/rel_exportacao_solicitacoes_amb")

    time.sleep(5) 

    lista_periodos = gerar_periodos_desde_2025()
    print(f">> Iniciando download de {len(lista_periodos)} arquivos...")

    for dt_ini, dt_fim in lista_periodos:
        d1 = dt_ini.strftime("%d/%m/%Y")
        d2 = dt_fim.strftime("%d/%m/%Y")
        print(f"\n>> Baixando período: {d1} a {d2}")

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
            print("   ❌ ERRO: Formulário não encontrado. Recarregando...")
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
            
            print("   (Solicitando arquivo ao servidor...)")
            driver.execute_script("if(typeof exportar == 'function') { exportar(); } else { document.getElementsByName('exp')[0].click(); }")

            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except:
                print("   (Download iniciado...)")

            time.sleep(15) # Tempo extra garantido para o download na nuvem

        except Exception as e:
            print(f"   ❌ Erro técnico: {e}")

    print("\n>> Finalizando extração...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída e Pronta para Processamento!")

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")
    if 'driver' in locals(): driver.quit()
