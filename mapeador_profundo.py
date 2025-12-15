import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("--- MAPEADOR DE IFRAMES SISREG ---")
print("Vamos descobrir onde o formulário está escondido.")

# --- CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- COLOQUE SUA SENHA

options = webdriver.ChromeOptions()
prefs = {"download.prompt_for_download": False}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()

# --- FUNÇÃO RECURSIVA DE BUSCA ---
def caçar_elemento(driver, caminho_atual=[]):
    # 1. Procura o elemento NESTE nível
    if len(driver.find_elements(By.NAME, "data_inicio")) > 0:
        return caminho_atual # BINGO! Achamos.

    # 2. Se não achou, procura iframes aqui dentro
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    
    for i, frame in enumerate(iframes):
        # Tenta entrar no iframe
        try:
            driver.switch_to.frame(i)
            # Chama a função de novo (Recursão) para procurar lá dentro
            resultado = caçar_elemento(driver, caminho_atual + [i])
            
            if resultado is not None:
                return resultado # Se achou lá dentro, retorna o caminho!
            
            # Se não achou, volta para o pai e tenta o próximo irmão
            driver.switch_to.parent_frame()
        except:
            driver.switch_to.parent_frame()
            
    return None # Não achou em lugar nenhum deste ramo

try:
    # LOGIN
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    time.sleep(2)
    
    try:
        driver.find_element(By.NAME, "usuario").send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        try:
            driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    except:
        pass

    # PAUSA PARA VOCÊ
    print("\n" + "="*60)
    print("   🛑 HORA DE VOCÊ TRABALHAR 🛑")
    print("="*60)
    print("1. Vá no Chrome.")
    print("2. Navegue até aparecerem os campos 'Data Início' e 'Fim'.")
    print("3. QUANDO ESTIVER VENDO OS CAMPOS, volte aqui.")
    print("4. Pressione ENTER.")
    print("="*60)
    
    input(">> Pressione ENTER para iniciar o rastreamento...")

    print("\n🕵️‍♂️ Iniciando varredura profunda...")
    
    # Garante que começa do topo
    driver.switch_to.default_content()
    
    # Inicia a caça
    caminho_do_tesouro = caçar_elemento(driver, [])

    print("\n" + "="*60)
    if caminho_do_tesouro:
        print(f"✅✅✅ ACHEI! O FORMULÁRIO ESTÁ AQUI: {caminho_do_tesouro}")
        print(f"Significa: Entre no Iframe {caminho_do_tesouro[0]}, depois no {caminho_do_tesouro[1]}...")
    else:
        print("❌ Não encontrei o campo 'data_inicio' em nenhum lugar (nem escondido).")
        print("Tem certeza que ele estava na tela?")
    print("="*60)

    # Mantém aberto pra você ver o resultado
    input("Pressione ENTER para fechar...")

except Exception as e:
    print(f"Erro: {e}")
finally:
    driver.quit()