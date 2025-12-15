import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("--- INSPETOR UNIVERSAL SISREG ---")
print("Vamos listar TODOS os campos da tela para descobrir os nomes corretos.")

# --- CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- COLOQUE SUA SENHA

options = webdriver.ChromeOptions()
prefs = {"download.prompt_for_download": False}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()

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

    # PAUSA
    print("\n" + "="*60)
    print("   🛑 PAUSA PARA NAVEGAÇÃO 🛑")
    print("="*60)
    print("1. Vá no Chrome.")
    print("2. Navegue até a tela onde tem 'Período da Solicitação'.")
    print("3. VOLTE AQUI e pressione ENTER.")
    print("="*60)
    
    input(">> Pressione ENTER para inspecionar...")

    print("\n🕵️‍♂️ INICIANDO VARREDURA TOTAL...")
    
    # Função para listar inputs de um contexto (página ou iframe)
    def listar_inputs(driver, nome_contexto):
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if len(inputs) > 0:
            print(f"\n--- ENCONTRADOS NO {nome_contexto} ---")
            print(f"Total de inputs: {len(inputs)}")
            for i, inp in enumerate(inputs):
                try:
                    tipo = inp.get_attribute("type")
                    nome = inp.get_attribute("name")
                    id_elem = inp.get_attribute("id")
                    valor = inp.get_attribute("value")
                    visivel = inp.is_displayed()
                    
                    # Filtra só o que interessa (Texto ou Data)
                    if tipo in ['text', 'date', 'hidden', 'checkbox', 'button', 'submit']:
                        print(f"   [{i}] Tipo: {tipo} | Name: '{nome}' | ID: '{id_elem}' | Visível: {visivel}")
                except:
                    pass

    # 1. Varre a página principal
    driver.switch_to.default_content()
    listar_inputs(driver, "PÁGINA PRINCIPAL")

    # 2. Varre todos os iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"\n🔎 Encontrados {len(iframes)} iframes. Entrando neles...")

    for index, frame in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(index)
            
            # Verifica se tem o texto "Período" neste iframe
            corpo_texto = driver.find_element(By.TAG_NAME, "body").text
            if "Período" in corpo_texto or "Solicitação" in corpo_texto:
                print(f"\n✅✅✅ PISTAS ENCONTRADAS NO IFRAME {index}! (Contém texto 'Período')")
            
            listar_inputs(driver, f"IFRAME {index}")
            
        except Exception as e:
            print(f"Erro ao ler iframe {index}: {e}")

    print("\n" + "="*60)
    print("FIM DA ANÁLISE. Copie o resultado acima e me mande!")
    print("="*60)
    input("Pressione ENTER para fechar...")

except Exception as e:
    print(f"Erro: {e}")
finally:
    driver.quit()