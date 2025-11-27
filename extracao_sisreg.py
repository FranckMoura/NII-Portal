import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES DO USUÁRIO ---
USUARIO = "046FRANCK"
SENHA = "515462"  # <--- COLOCAR SUA SENHA AQUI
# Atualizei para o caminho que vi nos seus logs para facilitar
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

# Garante que a pasta existe
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

# Configura as datas (Do dia 1 do mês atual até hoje)
hoje = datetime.now()
data_fim = hoje.strftime("%d/%m/%Y")
data_inicio = hoje.replace(day=1).strftime("%d/%m/%Y")

print(f"--- Automação SISREG HBSH (Versão Final) ---")
print(f"Período: {data_inicio} até {data_fim}")
print(f"Salvando em: {PASTA_DOWNLOAD}")

# --- CONFIGURAÇÃO DO NAVEGADOR ---
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
    # 1. LOGIN
    print("1. Realizando Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "usuario")))

    driver.find_element(By.ID, "usuario").send_keys(USUARIO)
    driver.find_element(By.ID, "senha").send_keys(SENHA)
    driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    
    # 2. NAVEGAÇÃO
    print("2. Acessando Menu Exportador...")
    # Clica em Consulta Hosp
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    # Clica em Exportador
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a"))).click()

    # 3. ENTRAR NO FRAME (Correção: ID='f_main')
    print("3. Entrando no formulário...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "f_main")))
    
    # 4. PREENCHER DATAS (Via Javascript)
    print("4. Preenchendo datas...")
    wait.until(EC.presence_of_element_located((By.ID, "dtaIniSolic")))
    
    campo_inicio = driver.find_element(By.ID, "dtaIniSolic")
    driver.execute_script(f"arguments[0].value = '{data_inicio}';", campo_inicio)
    
    campo_fim = driver.find_element(By.ID, "dtaFimSolic")
    driver.execute_script(f"arguments[0].value = '{data_fim}';", campo_fim)
    print(f"   Datas definidas.")

    # 5. ROLAGEM E SELEÇÃO (Correção para encontrar botões escondidos)
    print("5. Selecionando opções...")
    
    # Rola até o final da página
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1) 

    # Pega todas as caixas de seleção da página
    checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
    
    if len(checkboxes) > 0:
        # Clica na primeira (Geralmente é 'Desmarcar Todos')
        checkboxes[0].click()
        print("   Primeiro checkbox clicado (Limpando seleção).")
        
        # Opcional: Clique aqui nos índices que você precisa.
        # Exemplo: Se precisar marcar o 5º item da lista, descomente abaixo:
        # if len(checkboxes) >= 5: checkboxes[4].click()
    else:
        print("   Aviso: Nenhuma caixa de seleção encontrada automaticamente.")

    # 6. EXPORTAR
    print("6. Clicando em Exportar...")
    time.sleep(1)
    
    try:
        # Tenta o botão padrão pelo valor
        driver.find_element(By.XPATH, "//input[@value='Exportar']").click()
        print("   Botão principal clicado.")
    except:
        print("   Botão principal não achado. Tentando plano B (último botão da página)...")
        botoes = driver.find_elements(By.TAG_NAME, "input")
        # Procura qualquer botão que tenha 'button' ou 'submit' no tipo
        for botao in reversed(botoes):
            if botao.get_attribute("type") in ["button", "submit"]:
                botao.click()
                print("   Cliquei num botão alternativo no final da página.")
                break

    print("   Aguardando download (20 segundos)...")
    time.sleep(20)

except Exception as e:
    print(f"\nERRO FATAL: {e}")
    # Salva print se der erro
    driver.save_screenshot("erro_final.png")

finally:
    print("\n--- Processo Finalizado ---")
    input("Pressione ENTER para fechar o navegador...")
    driver.quit()