from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"

options = webdriver.ChromeOptions()
# options.add_argument("--headless") # Comentado para você ver acontecendo
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

print("--- RAIO-X DO TABNET ---")
try:
    driver.get(URL_TABNET)
    print(f"Título: {driver.title}")
    
    # Lista todos os SELECTS (Caixas de seleção)
    selects = driver.find_elements(By.TAG_NAME, "select")
    print(f"\nEncontrados {len(selects)} campos de seleção:")
    print("-" * 40)
    
    for s in selects:
        nome = s.get_attribute("name")
        id_elem = s.get_attribute("id")
        # Tenta pegar o rótulo (label) perto dele
        try:
            # Pega o texto visível da primeira opção para termos uma pista
            primeira_opcao = s.find_element(By.TAG_NAME, "option").text
        except:
            primeira_opcao = "Vazio"
            
        print(f"Nome: '{nome}' | ID: '{id_elem}' | Exemplo: '{primeira_opcao}'")

    print("-" * 40)
    print("Tire um print ou copie essa lista para mim!")

except Exception as e:
    print(f"Erro: {e}")

finally:
    driver.quit()