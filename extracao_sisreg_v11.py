import time
import os
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 1. EXTRAÇÃO SISREG (V11 - DIAGNÓSTICO) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- INSIRA SUA SENHA AQUI
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

# Função auxiliar para clicar de qualquer jeito
def clicar_seguro(driver, locator_type, locator_value):
    try:
        elem = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((locator_type, locator_value)))
        elem.click()
        return True
    except:
        try:
            # Tenta via Javascript se o clique normal falhar
            elem = driver.find_element(locator_type, locator_value)
            driver.execute_script("arguments[0].click();", elem)
            return True
        except Exception as e:
            print(f"   [FALHA AO CLICAR] {locator_value}: {e}")
            return False

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    # --- LOGIN ---
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    # Preenche usuário
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        # Clica no botão de entrar (procura por qualquer input do tipo image ou submit)
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except:
        # Tenta seletor alternativo se o acima falhar
        driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    print(">> Login enviado. Verificando acesso...")
    time.sleep(3)

    # --- NAVEGAÇÃO ---
    print(">> Tentando acessar o menu...")
    # Tenta URL direta primeiro (mais rápido e menos propenso a erro de menu)
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/rel_exportacao_solicitacoes_amb")
    
    # Verifica se carregou a página certa
    if "Exportação" not in driver.title and "exportacao" not in driver.current_url:
        print("   Aviso: URL direta falhou. Tentando via menu...")
        # Lógica de menu aqui se precisar
    
    time.sleep(3)

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

        # 1. TENTA ENTRAR NO IFRAME (Onde o formulário mora)
        driver.switch_to.default_content() # Reseta
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        if len(frames) > 0:
            print(f"   (Encontrados {len(frames)} iframes. Entrando no primeiro...)")
            driver.switch_to.frame(0)
        
        # 2. PREENCHIMENTO (Com diagnóstico)
        try:
            # Data Inicio
            dt_ini = wait.until(EC.presence_of_element_located((By.NAME, "data_inicio")))
            dt_ini.clear()
            dt_ini.send_keys(d1)
            
            # Data Fim
            dt_fim = driver.find_element(By.NAME, "data_fim")
            dt_fim.clear()
            dt_fim.send_keys(d2)

            # Checkbox (Marca todos)
            checks = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            count_checks = 0
            for c in checks:
                if not c.is_selected():
                    try:
                        c.click()
                        count_checks += 1
                    except: pass
            print(f"   (Marcados {count_checks} checkboxes)")

            # Botão Gerar
            print("   Clicando em Gerar...")
            clicou = False
            # Tenta vários seletores para o botão
            seletores = [
                "input[value='Gerar']",
                "input[value='Exportar']",
                "input[name='bt_gerar']",
                ".botao"
            ]
            
            for sel in seletores:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, sel)
                    # Scroll até o botão
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    btn.click()
                    clicou = True
                    print(f"   (Botão clicado usando seletor: {sel})")
                    break
                except: continue
            
            if not clicou:
                print("   ❌ ERRO: Botão Gerar não encontrado!")
                raise Exception("Botão sumiu")

            # Alertas
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                alerta = driver.switch_to.alert
                print(f"   [ALERTA DO SITE] {alerta.text}")
                alerta.accept()
            except:
                print("   (Sem alertas. Download deve iniciar.)")

            time.sleep(15) # Espera download

        except Exception as e:
            print(f"   ❌ ERRO NESTE PERÍODO: {e}")
            # Tira print da tela para debug (salva na pasta do projeto)
            driver.save_screenshot(f"erro_sisreg_{d1.replace('/','-')}.png")
            print("   (Print do erro salvo na pasta)")

        data_atual = fim + timedelta(days=1)

    print(">> Finalizando...")
    time.sleep(5)
    driver.quit()
    print("✅ Extração Concluída!")

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")
    if 'driver' in locals(): driver.quit()