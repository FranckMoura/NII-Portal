import time
import os
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. TRAVA DE HORÁRIO (SEGURANÇA SISREG) ---
# O sistema bloqueia extração entre 07:00 e 15:00.
hora_atual = datetime.now().hour
print(f"--- Iniciando Script de Extração ---")
print(f"Hora atual do sistema: {datetime.now().strftime('%H:%M')}")

if 7 <= hora_atual < 15:
    print("⛔ SISTEMA BLOQUEADO PELO SISREG (Horário proibido: 07h às 15h).")
    print("O script será encerrado agora para evitar erros de acesso.")
    time.sleep(5)
    sys.exit() # Encerra o script imediatamente

# --- 2. CONFIGURAÇÕES DO USUÁRIO ---
USUARIO = "046FRANCK"
SENHA = "515462"  # <--- COLOQUE SUA SENHA AQUI
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

# Garante que a pasta existe
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

# Configura as datas (Do dia 1 do mês atual até hoje)
hoje = datetime.now()
data_fim = hoje.strftime("%d/%m/%Y")
data_inicio = hoje.replace(day=1).strftime("%d/%m/%Y")

print(f"Status: Horário permitido. Iniciando automação...")
print(f"Período: {data_inicio} até {data_fim}")
print(f"Salvando em: {PASTA_DOWNLOAD}")

# --- 3. CONFIGURAÇÃO DO NAVEGADOR ---
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

# Inicializa o driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # 4. LOGIN
    print(">> Acessando página de login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "usuario")))

    driver.find_element(By.ID, "usuario").send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # 5. NAVEGAÇÃO
    print(">> Navegando para o Exportador...")
    # Clica em Consulta Hosp
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    # Clica em Exportador
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()

    # 6. ENTRAR NO FRAME (ID='f_main')
    print(">> Entrando no formulário (Frame)...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "f_main")))
    
    # 7. PREENCHER DATAS (Via Javascript)
    print(">> Preenchendo datas...")
    wait.until(EC.presence_of_element_located((By.ID, "dtaIniSolic")))
    
    campo_inicio = driver.find_element(By.ID, "dtaIniSolic")
    driver.execute_script(f"arguments[0].value = '{data_inicio}';", campo_inicio)
    
    campo_fim = driver.find_element(By.ID, "dtaFimSolic")
    driver.execute_script(f"arguments[0].value = '{data_fim}';", campo_fim)
    
    # 8. ROLAGEM E SELEÇÃO
    print(">> Selecionando opções...")
    # Rola até o final da página
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1) 

    # Pega todas as caixas de seleção da página e clica na primeira (Desmarcar Todos)
    checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
    if len(checkboxes) > 0:
        checkboxes[0].click()
    else:
        print("   Aviso: Nenhuma caixa de seleção encontrada automaticamente.")

    # 9. EXPORTAR
    print(">> Clicando em Exportar...")
    time.sleep(1)
    
    try:
        # Tenta o botão padrão pelo valor
        driver.find_element(By.XPATH, "//input[@value='Exportar']").click()
        print("   Botão principal clicado.")
    except:
        print("   Botão principal não achado. Tentando plano B...")
        botoes = driver.find_elements(By.TAG_NAME, "input")
        for botao in reversed(botoes):
            if botao.get_attribute("type") in ["button", "submit"]:
                botao.click()
                print("   Cliquei num botão alternativo no final da página.")
                break

    print(">> Aguardando download (20 segundos)...")
    time.sleep(20)

except Exception as e:
    print(f"\n❌ ERRO FATAL: {e}")
    driver.save_screenshot("erro_sisreg_final.png")

finally:
    print("\n--- Processo Finalizado ---")
    # Fecha o navegador se não houver erro grave de horário
    try:
        driver.quit()
    except:
        pass