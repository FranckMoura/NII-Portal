import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"
MEU_CNES = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Tabnet_Export"
PASTA_FINAL = "arquivos"
ARQUIVO_FINAL = "tabnet_producao_detalhada.csv"

print("--- ROBÔ TABNET V5 (SELEÇÃO INTELIGENTE) ---")

if os.path.exists(PASTA_DOWNLOAD):
    try: shutil.rmtree(PASTA_DOWNLOAD)
    except: pass
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_DOWNLOAD}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

try:
    print(">> Acessando TabNet MT...")
    driver.get(URL_TABNET)
    driver.maximize_window()
    
    # Espera carregar o campo "Linha"
    wait.until(EC.presence_of_element_located((By.NAME, "Linha")))

    # --- FUNÇÃO AUXILIAR DE SELEÇÃO SEGURA ---
    def selecionar_por_texto_parcial(nome_campo, texto_parcial):
        try:
            select_elem = Select(driver.find_element(By.NAME, nome_campo))
            for opt in select_elem.options:
                if texto_parcial.lower() in opt.text.lower():
                    opt.click()
                    print(f"   ✅ Campo '{nome_campo}': Selecionado '{opt.text}'")
                    return True
            print(f"   ⚠️ Aviso: Não encontrei '{texto_parcial}' em '{nome_campo}'")
            return False
        except Exception as e:
            print(f"   ❌ Erro ao selecionar em '{nome_campo}': {e}")
            return False

    # --- 1. CONFIGURAR TABELA ---
    print(">> Configurando Tabela...")
    
    # Linha: Procura por "Comp" (evita erro de acento em Competência)
    selecionar_por_texto_parcial("Linha", "Comp")
    
    # Coluna: Procura por "Proced" (Procedimento realizado)
    selecionar_por_texto_parcial("Coluna", "Proced")

    # Conteúdo: Selecionar Valores
    print(">> Selecionando Valores...")
    select_conteudo = driver.find_element(By.NAME, "Incremento")
    opcoes = select_conteudo.find_elements(By.TAG_NAME, "option")
    
    for opt in opcoes:
        txt = opt.text.lower()
        # Marca Valor SH e SP
        if "val" in txt and ("hosp" in txt or "prof" in txt):
            if not opt.is_selected():
                opt.click()
                print(f"   -> Marcado: {opt.text}")

    # --- 2. FILTRAR HOSPITAL ---
    print(f">> Filtrando Santa Helena ({MEU_CNES})...")
    
    select_hospital = Select(driver.find_element(By.NAME, "SEstabelecimento"))
    select_hospital.deselect_all()
    
    hospital_found = False
    for opt in select_hospital.options:
        # Busca pelo código no texto ou valor
        if MEU_CNES in opt.text or MEU_CNES in opt.get_attribute("value"):
            opt.click()
            print(f"   ✅ Hospital Selecionado: {opt.text.strip()}")
            hospital_found = True
            break
            
    if not hospital_found:
        print("⚠️ AVISO: Hospital não encontrado automaticamente.")
        print("   -> SELECIONE MANUALMENTE AGORA (15s)...")
        time.sleep(15)

    # --- 3. EXECUTAR ---
    print(">> Gerando dados...")
    driver.find_element(By.CLASS_NAME, "mostra").click()
    
    # --- 4. BAIXAR CSV ---
    print(">> Procurando Download...")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    
    try:
        # Clica no link que tem ".csv" ou texto "CSV"
        driver.find_element(By.XPATH, "//a[contains(@href, '.csv') or contains(text(), 'CSV')]").click()
        
        print(">> Baixando...")
        time.sleep(5)
        
        if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)
        
        arquivos = [f for f in os.listdir(PASTA_DOWNLOAD) if f.endswith('.csv')]
        if arquivos:
            origem = os.path.join(PASTA_DOWNLOAD, arquivos[0])
            destino = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
            
            if os.path.exists(destino): os.remove(destino)
            shutil.move(origem, destino)
            print(f"✅ SUCESSO TOTAL! Arquivo salvo em: arquivos/{ARQUIVO_FINAL}")
        else:
            print("❌ Erro: Download não iniciou.")
            
    except Exception as e:
        print(f"❌ Erro no download: {e}")

except Exception as e:
    print(f"❌ Erro Geral: {e}")

finally:
    # driver.quit() 
    pass