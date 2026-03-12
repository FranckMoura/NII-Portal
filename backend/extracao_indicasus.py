import time
import os
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print("--- ROBÔ INDICASUS V8 (FORMATO XLS) ---")

# CREDENCIAIS
USUARIO_INDICASUS = "046.941.841-99"
SENHA_INDICASUS = "@ntoniO22"

PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\IndicaSus_Export"
PASTA_FINAL = "arquivos"
# MUDANÇA AQUI: Agora salvamos como XLS
ARQUIVO_FINAL = "Indicasus.xls"
PASTA_DOWNLOADS_WIN = os.path.join(os.path.expanduser("~"), "Downloads")

# Prepara pastas
if os.path.exists(PASTA_DOWNLOAD):
    try: shutil.rmtree(PASTA_DOWNLOAD)
    except: pass
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)
if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 40)

    # 1. LOGIN
    print(">> Acessando site...")
    driver.get("https://sistemas.saude.mt.gov.br/")
    driver.maximize_window()

    try: wait.until(EC.invisibility_of_element_located((By.ID, "btnFecharLoading")))
    except: pass

    try:
        driver.find_element(By.XPATH, "//button[contains(text(), '×')]").click()
        time.sleep(1)
    except: pass

    print(">> Logando...")
    wait.until(EC.presence_of_element_located((By.ID, "CPF")))
    driver.find_element(By.ID, "CPF").send_keys(USUARIO_INDICASUS)
    campo_senha = driver.find_element(By.ID, "Senha")
    campo_senha.send_keys(SENHA_INDICASUS)
    time.sleep(1)
    campo_senha.send_keys(Keys.RETURN)
    
    print(">> Aguardando sistema...")
    time.sleep(10)

    # 2. NAVEGAÇÃO
    print(">> Acessando Módulo Internação...")
    driver.get("https://sistemas.saude.mt.gov.br/Administracao/InternacaoGeral?limpar=1")
    
    # 3. EXPORTAÇÃO
    print(">> Procurando botão de exportar...")
    btn_exportar = wait.until(EC.presence_of_element_located((By.ID, "exportFormInternacaoGeral")))
    
    print(">> Clicando em baixar...")
    driver.execute_script("arguments[0].click();", btn_exportar)
    
    # Clique de garantia no ícone
    time.sleep(2)
    try:
        driver.find_element(By.XPATH, "//*[@id='exportFormInternacaoGeral']//span").click()
    except: pass

    # 4. ESPERA INTELIGENTE
    print(">> Aguardando download...")
    
    tempo_maximo = 300
    tempo_decorrido = 0
    arquivo_encontrado = None
    origem_final = ""
    
    while tempo_decorrido < tempo_maximo:
        # Verifica pasta do projeto (.xls ou .csv)
        # O Indicasus as vezes baixa como .xls, as vezes .csv dependendo da versão
        arquivos_proj = [f for f in os.listdir(PASTA_DOWNLOAD) if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        
        if arquivos_proj:
            if os.path.getsize(os.path.join(PASTA_DOWNLOAD, arquivos_proj[0])) > 0:
                arquivo_encontrado = arquivos_proj[0]
                origem_final = os.path.join(PASTA_DOWNLOAD, arquivo_encontrado)
                print(f"\n   ✅ Arquivo no projeto: {arquivo_encontrado}")
                break
        
        # Verifica Downloads Windows
        arquivos_win = [f for f in os.listdir(PASTA_DOWNLOADS_WIN) if ("Indica" in f or "Internacao" in f) and not f.endswith('.crdownload')]
        if arquivos_win:
            caminhos_win = [os.path.join(PASTA_DOWNLOADS_WIN, f) for f in arquivos_win]
            arquivo_mais_novo = max(caminhos_win, key=os.path.getmtime)
            
            if (time.time() - os.path.getmtime(arquivo_mais_novo)) < 180:
                if os.path.getsize(arquivo_mais_novo) > 0:
                    arquivo_encontrado = os.path.basename(arquivo_mais_novo)
                    origem_final = arquivo_mais_novo
                    print(f"\n   ✅ Arquivo em Downloads: {arquivo_encontrado}")
                    break

        time.sleep(5)
        tempo_decorrido += 5
        print(f"   ⏳ {tempo_decorrido}s...", end="\r")

    # 5. MOVER E FINALIZAR
    if arquivo_encontrado and os.path.exists(origem_final):
        time.sleep(2)
        destino = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
        
        if os.path.exists(destino): os.remove(destino)
        
        shutil.copy2(origem_final, destino)
        
        if "Downloads" in origem_final:
            try: os.remove(origem_final)
            except: pass
            
        print(f"\n\n🏆 SUCESSO! Salvo em: arquivos/{ARQUIVO_FINAL}")
    else:
        print("\n\n❌ Erro: Tempo esgotado.")

except Exception as e:
    print(f"\n❌ Erro Geral: {e}")

finally:
    try: driver.quit()
    except: pass