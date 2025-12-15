import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("--- RAIO-X DO SISREG ---")
print("Este script serve para mapear a estrutura da página.")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- COLOQUE SUA SENHA

options = webdriver.ChromeOptions()
# Removemos o headless para você ver a tela
prefs = {"download.prompt_for_download": False}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()

try:
    # 1. Login Automático (para agilizar)
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    time.sleep(2)
    
    try:
        driver.find_element(By.NAME, "usuario").send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except:
        driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    print("\n" + "="*60)
    print("   🛑 PAUSA PARA VOCÊ NAVEGAR 🛑")
    print("="*60)
    print("1. Vá no navegador que abriu.")
    print("2. Navegue MANUALMENTE até a tela de 'Exportação de Solicitações'.")
    print("3. Certifique-se de que os campos de DATA estão visíveis na tela.")
    print("4. VOLTE AQUI e pressione ENTER para tirar o Raio-X.")
    print("="*60)
    
    input(">> Pressione ENTER aqui quando estiver pronto...")

    print("\n📸 Tirando Raio-X da página principal...")
    conteudo_completo = "--- HTML PRINCIPAL ---\n"
    conteudo_completo += driver.page_source + "\n\n"

    # Procura IFRAMES (Janelas dentro de janelas)
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"🔎 Encontrados {len(iframes)} iframes (janelas internas).")

    for i, frame in enumerate(iframes):
        print(f"   -> Lendo Iframe {i+1}...")
        try:
            driver.switch_to.default_content()
            # Precisamos reencontrar os frames porque o DOM pode ter mudado
            frames_novos = driver.find_elements(By.TAG_NAME, "iframe")
            driver.switch_to.frame(frames_novos[i])
            
            conteudo_completo += f"--- CONTEÚDO DO IFRAME {i} ---\n"
            conteudo_completo += driver.page_source + "\n\n"
            
            # Tenta achar os campos chaves para avisar você
            if "data_inicio" in driver.page_source:
                print("      ✅ ACHAMOS! O formulário está neste Iframe!")
                conteudo_completo += "!!! AQUI ESTA O FORMULARIO !!!\n"
        except Exception as e:
            conteudo_completo += f"--- ERRO AO LER IFRAME {i}: {e} ---\n"

    # Salva o arquivo
    nome_arquivo = "RAIO_X_PAGINA.txt"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo_completo)

    print("\n" + "="*60)
    print(f"✅ SUCESSO! Arquivo '{nome_arquivo}' gerado.")
    print("👉 Anexe este arquivo no chat para eu corrigir o script.")
    print("="*60)

except Exception as e:
    print(f"❌ Erro: {e}")

finally:
    # Não fecha o navegador imediatamente para você ver se deu certo
    print("Pode fechar o navegador.")