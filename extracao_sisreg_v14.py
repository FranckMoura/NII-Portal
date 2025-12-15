import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V15 - MODO HÍBRIDO) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- COLOQUE SUA SENHA
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
    driver.maximize_window()

    # --- LOGIN ---
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    time.sleep(2)
    
    try:
        driver.find_element(By.NAME, "usuario").send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        # Tenta clicar no botão de entrar
        try:
            driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    except:
        print("   (Faça o login manualmente se falhar)")

    # --- PAUSA ESTRATÉGICA ---
    print("\n" + "="*60)
    print("   🛑 AGUARDANDO NAVEGAÇÃO MANUAL 🛑")
    print("="*60)
    print("1. Vá no Chrome que abriu.")
    print("2. Navegue pelos menus até chegar na tela 'Exportação de Solicitações'.")
    print("3. Quando os campos de DATA estiverem visíveis, volte aqui.")
    print("4. Pressione ENTER para o robô começar a baixar.")
    print("="*60)
    
    input(">> Pressione ENTER aqui quando estiver na tela certa...")
    print(">> Assumindo o controle em 3 segundos...")
    time.sleep(3)

    # --- LOOP DE DATAS ---
    hoje = datetime.now()
    data_atual = hoje - timedelta(days=90)
    
    print(">> Iniciando downloads automatizados...")

    while data_atual < hoje:
        fim = data_atual + timedelta(days=29)
        if fim > hoje: fim = hoje
        
        d1 = data_atual.strftime("%d/%m/%Y")
        d2 = fim.strftime("%d/%m/%Y")
        print(f">> Baixando período: {d1} a {d2}")

        # 1. LOCALIZAR O FORMULÁRIO (Mesmo esquema do Raio-X)
        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        iframe_found = False
        
        # Procura onde está o campo data_inicio
        for i in range(len(frames)):
            driver.switch_to.default_content()
            try:
                driver.switch_to.frame(i)
                if len(driver.find_elements(By.NAME, "data_inicio")) > 0:
                    iframe_found = True
                    break # Paramos no iframe certo
            except: pass
        
        if not iframe_found:
            print("   ❌ ERRO: Você saiu da tela de exportação? Não achei o formulário.")
            # Tenta continuar caso seja um erro momentâneo
            driver.switch_to.default_content()
            time.sleep(2)
            continue

        try:
            # 2. INJEÇÃO DE DADOS (Javascript)
            # Preenche datas
            driver.execute_script(f"document.getElementsByName('data_inicio')[0].value = '{d1}'")
            driver.execute_script(f"document.getElementsByName('data_fim')[0].value = '{d2}'")

            # Marca checkbox
            driver.execute_script("""
                var inputs = document.getElementsByTagName('input');
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].type == 'checkbox') inputs[i].checked = true;
                }
            """)
            
            # 3. EXPORTAR
            print("   (Solicitando arquivo...)")
            driver.execute_script("exportar();")

            # 4. TRATA ALERTAS
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                alerta = driver.switch_to.alert
                print(f"   [ALERTA] {alerta.text}")
                alerta.accept()
            except:
                print("   (Download iniciado...)")

            # Espera o download (SISREG é lento)
            time.sleep(15)

        except Exception as e:
            print(f"   ❌ Erro técnico: {e}")

        data_atual = fim + timedelta(days=1)

    print(">> Finalizando...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")