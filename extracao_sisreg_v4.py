import time
import os
import sys
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. CONFIGURAÇÃO INICIAL ---
print(f"--- Iniciando Script de Extração (V6 - Retroativo 90 Dias) ---")
print(f"Hora atual do sistema: {datetime.now().strftime('%H:%M')}")

# TRAVA DE HORÁRIO (COMENTADA PARA TESTES)
# Se quiser ativar depois, tire o # das linhas abaixo
# hora_atual = datetime.now().hour
# if 7 <= hora_atual < 15:
#     print("⛔ SISTEMA BLOQUEADO PELO SISREG (Horário proibido: 07h às 15h).")
#     sys.exit()

# --- 2. CREDENCIAIS E CAMINHOS ---
USUARIO = "046FRANCK"
SENHA = "515462"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

# Garante que a pasta existe
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

# --- 3. CONFIGURAÇÃO DE DATAS (Retroativo) ---
hoje = datetime.now()
data_fim = hoje.strftime("%d/%m/%Y")

# Pega 90 dias para trás para garantir pendências antigas
data_inicio = (hoje - timedelta(days=90)).strftime("%d/%m/%Y")

print(f"Período de busca: {data_inicio} até {data_fim}")
print(f"Salvando em: {PASTA_DOWNLOAD}")

# --- 4. CONFIGURAÇÃO DO NAVEGADOR ---
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

# Inicializa o driver (Robô)
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
except Exception as e:
    print(f"❌ Erro ao abrir navegador: {e}")
    sys.exit()

try:
    # 5. LOGIN
    print(">> Acessando página de login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "usuario")))

    driver.find_element(By.ID, "usuario").send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # 6. NAVEGAÇÃO ATÉ O EXPORTADOR
    print(">> Navegando para o Exportador...")
    # Clica em Consulta Hosp (Menu)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    # Clica em Exportador (Submenu)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()

    # 7. ENTRAR NO FRAME DO FORMULÁRIO
    print(">> Entrando no formulário...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "f_main")))
    
    # 8. PREENCHER DATAS (Via Javascript)
    # Usamos JS porque o campo tem máscara e digitar direto costuma dar erro
    print(f">> Preenchendo datas...")
    wait.until(EC.presence_of_element_located((By.ID, "dtaIniSolic")))
    
    campo_inicio = driver.find_element(By.ID, "dtaIniSolic")
    driver.execute_script(f"arguments[0].value = '{data_inicio}';", campo_inicio)
    
    campo_fim = driver.find_element(By.ID, "dtaFimSolic")
    driver.execute_script(f"arguments[0].value = '{data_fim}';", campo_fim)
    
    # 9. SELEÇÃO DE CHECKBOXES
    print(">> Selecionando opções...")
    # Rola a tela para garantir que os elementos carregaram
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1) 

    # Clica na primeira caixa para desmarcar/marcar o padrão
    checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
    if len(checkboxes) > 0:
        checkboxes[0].click()
    
    # 10. CLICAR EM EXPORTAR
    print(">> Clicando em Exportar...")
    time.sleep(1)
    
    # Tenta achar o botão pelo valor 'Exportar'
    try:
        driver.find_element(By.XPATH, "//input[@value='Exportar']").click()
    except:
        # Plano B: Procura qualquer botão do tipo submit/button no final
        print("   (Botão padrão não achado, tentando alternativo...)")
        botoes = driver.find_elements(By.TAG_NAME, "input")
        for botao in reversed(botoes):
            if botao.get_attribute("type") in ["button", "submit"]:
                botao.click()
                print("   Botão alternativo clicado.")
                break

    # 11. AGUARDAR DOWNLOAD
    print(">> Aguardando download (30 segundos)...")
    # Esse tempo é necessário para o arquivo terminar de baixar antes de fechar o navegador
    time.sleep(30)

except Exception as e:
    print(f"\n❌ ERRO FATAL DURANTE A EXECUÇÃO: {e}")

finally:
    print("\n--- Processo Finalizado ---")
    try:
        driver.quit()
    except:
        pass