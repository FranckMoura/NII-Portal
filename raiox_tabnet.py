import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print("--- 🕵️ RAIO-X DE FRAMES (CAÇADOR DE BOTÕES) ---")

CNES_ALVO = "2311682"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def procurar_botao(contexto_nome):
    """Procura o botão no contexto atual e imprime se achar"""
    print(f"   🔎 Procurando no contexto: {contexto_nome}...")
    
    # Lista de estratégias de busca
    candidatos = []
    candidatos += driver.find_elements(By.XPATH, "//a[contains(text(), 'CSV')]")
    candidatos += driver.find_elements(By.XPATH, "//a[contains(text(), 'csv')]")
    candidatos += driver.find_elements(By.CSS_SELECTOR, ".botao_opcao a")
    
    if candidatos:
        print(f"   🎉 EUREKA! Encontrado(s) {len(candidatos)} botão(ões) em: {contexto_nome}")
        for btn in candidatos:
            print(f"      -> Texto: '{btn.text}' | HREF: {btn.get_attribute('href')}")
        return True
    return False

try:
    print(">> 1. Acessando e Configurando...")
    driver.get(URL_TABNET)
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)
    time.sleep(2)

    # Configuração Padrão
    Select(driver.find_element(By.ID, "L")).select_by_visible_text("Procedimento")
    try: Select(driver.find_element(By.ID, "C")).select_by_visible_text("--Não-Ativa--")
    except: Select(driver.find_element(By.ID, "C")).select_by_index(0)
    
    # Seleciona AIH
    driver.execute_script("arguments[0].selectedIndex = 0;", driver.find_element(By.ID, "I"))
    
    # Seleciona Hospital
    if not driver.find_element(By.ID, "S7").is_displayed():
        driver.find_element(By.ID, "fig7").click()
        time.sleep(1)
    
    driver.execute_script(f"""
    var s = document.getElementById('S7');
    for(var i=0; i<s.options.length; i++) {{
        if(s.options[i].text.indexOf('{CNES_ALVO}') > -1) {{ s.selectedIndex = i; }}
    }}
    """)
    
    print(">> 2. Gerando Resultados...")
    driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
    
    # --- MOMENTO HÍBRIDO ---
    print("\n" + "="*50)
    print("🚦 PAUSA PARA INTERAÇÃO HUMANA")
    print("Verifique se a tabela de resultados apareceu no navegador.")
    print("Se o botão de download estiver visível, volte aqui.")
    input("👉 Pressione ENTER no teclado para iniciar a caçada...")
    print("="*50 + "\n")

    # 1. Busca na Página Principal (Top Level)
    encontrou = procurar_botao("Página Principal (Top)")
    
    # 2. Busca em Frames
    if not encontrou:
        frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
        print(f"\n>> Encontrados {len(frames)} frames/iframes na página. Investigando um por um...")
        
        for i in range(len(frames)):
            try:
                # É preciso voltar pro topo antes de entrar no próximo frame
                driver.switch_to.default_content()
                
                # Entra no frame
                driver.switch_to.frame(i)
                
                # Busca lá dentro
                if procurar_botao(f"FRAME Índice {i}"):
                    print(f"   ✅ O BOTÃO ESTÁ NO FRAME {i}!")
                    break
            except Exception as e:
                print(f"   ⚠️ Erro ao acessar frame {i}: {e}")

    # Retorna ao topo
    driver.switch_to.default_content()
    
    print("\n🏁 Fim da varredura.")
    input("Pressione ENTER para fechar o navegador...")

except Exception as e:
    print(f"❌ ERRO: {e}")
finally:
    driver.quit()