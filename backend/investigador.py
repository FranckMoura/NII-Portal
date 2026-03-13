import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("--- 🕵️‍♂️ INVESTIGADOR DE CÓDIGO FONTE INDICASUS V2 ---")

USUARIO = "046.941.841-99"
SENHA = "@ntoniO22"

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

try:
    print(">> Fazendo login...")
    driver.get("https://sistemas.saude.mt.gov.br/")
    driver.maximize_window()
    
    try: wait.until(EC.invisibility_of_element_located((By.ID, "btnFecharLoading")))
    except: pass
    try: driver.find_element(By.XPATH, "//button[contains(text(), '×')]").click()
    except: pass

    wait.until(EC.presence_of_element_located((By.ID, "CPF"))).send_keys(USUARIO)
    driver.find_element(By.ID, "Senha").send_keys(SENHA + Keys.RETURN)
    time.sleep(5)

    print(">> Acessando Internações...")
    driver.get("https://sistemas.saude.mt.gov.br/Administracao/InternacaoGeral?limpar=1")
    time.sleep(5) # Espera extra para a página estabilizar

    print(">> Filtrando Fevereiro...")
    driver.find_element(By.ID, "btnFiltro").click()
    time.sleep(2)
    driver.execute_script("document.getElementById('DataInternacaoInicial').value = '01/02/2026';")
    driver.find_element(By.ID, "btnFiltrar").click()
    time.sleep(5) # Espera a tabela carregar os dados

    # Pega os pacientes e procura o primeiro que tenha nome
    linhas = driver.find_elements(By.XPATH, "//*[@id='resultadoInternacaoGeral']/tbody/tr")
    
    nome_paciente = ""
    url_paciente = ""
    
    for linha in linhas:
        colunas = linha.find_elements(By.TAG_NAME, "td")
        if len(colunas) > 0:
            texto_nome = colunas[0].text.strip()
            if texto_nome and "Nenhum" not in texto_nome:
                nome_paciente = texto_nome
                url_paciente = linha.find_element(By.XPATH, ".//a[contains(@class, 'btn-warning')]").get_attribute("href")
                break

    if not nome_paciente:
        print("❌ Não consegui achar o nome do paciente na tabela. A tela pode estar diferente.")
        driver.quit()
        exit()

    print(f"\n>> Entrando no perfil de: {nome_paciente}")
    driver.get(url_paciente)
    time.sleep(5) # Espera a ficha do paciente carregar toda

    print("📸 TIRANDO FOTO DA TELA...")
    driver.save_screenshot("debug_tela_paciente.png") # Salva na pasta atual
    
    print("📝 EXTRAINDO TEXTO DA PÁGINA...")
    corpo_da_pagina = driver.find_element(By.TAG_NAME, "body").text
    
    with open("debug_texto_paciente.txt", "w", encoding="utf-8") as f: # Salva na pasta atual
        f.write(corpo_da_pagina)
        
    print("\n✅ INVESTIGAÇÃO CONCLUÍDA!")
    print("-> Verifique a pasta onde você rodou o script. Os arquivos estão lá!")

except Exception as e:
    print(f"Erro: {e}")
finally:
    driver.quit()