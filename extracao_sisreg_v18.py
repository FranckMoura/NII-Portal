import time
import os
import glob
import calendar
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V19 - COM LIMPEZA AUTOMÁTICA) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" 
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- LIMPEZA DE ARQUIVOS ANTIGOS (CORREÇÃO DO ACÚMULO) ---
print(">> Limpando arquivos antigos da pasta de exportação...")
arquivos_velhos = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv"))
for f in arquivos_velhos:
    try:
        os.remove(f)
    except:
        pass
print(f"   Pasta limpa! Iniciando novos downloads...")

# --- CONFIGURAÇÃO CHROME ---
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_setting_values.automatic_downloads": 1
}
options.add_experimental_option("prefs", prefs)

# --- FUNÇÃO DATAS ---
def gerar_intervalos_mensais():
    hoje = datetime.today()
    intervalos = []
    # Gera datas para: Mês atual, e 3 meses para trás
    for i in range(3, -1, -1):
        data_mes = hoje - timedelta(days=i*30)
        primeiro_dia = data_mes.replace(day=1)
        ultimo_dia_num = calendar.monthrange(primeiro_dia.year, primeiro_dia.month)[1]
        ultimo_dia = data_mes.replace(day=ultimo_dia_num)
        
        fmt_d1 = primeiro_dia.strftime("%d/%m/%Y")
        fmt_d2 = ultimo_dia.strftime("%d/%m/%Y")
        intervalos.append((fmt_d1, fmt_d2))
    return intervalos

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print(">> Abrindo navegador...")
    driver.get("https://sisregiii.saude.gov.br/")
    driver.maximize_window()

    # LOGIN
    print(">> Fazendo Login...")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    driver.find_element(By.NAME, "entrar").click()

    # NAVEGAÇÃO
    print(">> Navegando para Exportação...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/cons_solicitacao_co.py")
    
    # DOWNLOAD DOS INTERVALOS
    intervalos = gerar_intervalos_mensais()
    print(f">> Iniciando download de {len(intervalos)} arquivos...")

    for d1, d2 in intervalos:
        print(f">> Baixando: {d1} a {d2}")
        
        try:
            # 1. PREENCHER DATAS
            driver.execute_script(f"document.getElementsByName('dtaIniSolic')[0].value = '{d1}'")
            driver.execute_script(f"document.getElementsByName('dtaFimSolic')[0].value = '{d2}'")

            # 2. MARCAR CHECKBOXES
            driver.execute_script("""
                var inputs = document.getElementsByTagName('input');
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].type == 'checkbox') inputs[i].checked = true;
                }
            """)
            
            # 3. EXPORTAR
            print("   (Solicitando arquivo...)")
            driver.execute_script("if(typeof exportar == 'function') { exportar(); } else { document.getElementsByName('exp')[0].click(); }")

            # 4. TRATAR ALERTAS
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except:
                print("   (Download iniciado...)")

            time.sleep(10) # Tempo para download

        except Exception as e:
            print(f"   ❌ Erro neste intervalo: {e}")
            # Tenta recuperar página se der erro
            driver.get("https://sisregiii.saude.gov.br/cgi-bin/cons_solicitacao_co.py")
            time.sleep(3)

    print(">> Finalizando...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ Erro Geral: {e}")
    if 'driver' in locals(): driver.quit()