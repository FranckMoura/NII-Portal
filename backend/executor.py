import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Carregar os passos gravados
with open('automacao.json', 'r') as f:
    passos = json.load(f)

driver = webdriver.Chrome()
driver.get("https://www.google.com") # Mesma URL inicial

print("--- INICIANDO AUTOMATIZAÇÃO ---")

try:
    for passo in passos:
        seletor = passo['seletor']
        acao = passo['acao']
        
        print(f"Executando: {acao} em {seletor}")
        
        try:
            # Espera o elemento aparecer (máximo 10 segundos)
            elemento = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
            )
            
            # Destaca o elemento (Borda vermelha) para você ver o que ele vai clicar
            driver.execute_script("arguments[0].style.border='3px solid red'", elemento)
            time.sleep(0.5) 
            
            if acao == "click":
                elemento.click()
            
            # Pequena pausa entre ações
            time.sleep(2)
            
        except Exception as e:
            print(f"Erro ao tentar interagir com {seletor}: {e}")

    print("Automação concluída.")
    time.sleep(5)

finally:
    driver.quit()