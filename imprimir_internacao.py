import time
import os
import re
import pyautogui  # <--- Biblioteca nova para controlar teclado
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V17 - SIMULADOR HUMANO) ---")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Configuração do PyAutoGUI (Segurança)
pyautogui.FAILSAFE = True # Se arrastar o mouse para o canto superior esquerdo, para tudo.
pyautogui.PAUSE = 1.0 # Pausa de 1s entre comandos para dar tempo ao sistema

def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def get_datas_mes_atual():
    hoje = datetime.now()
    return hoje.replace(day=1).strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def focar_frame_principal(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            if "Período" in driver.page_source or "Solicitacao" in driver.page_source: return True
        except: pass
    driver.switch_to.default_content()
    try: driver.switch_to.frame(1); return True
    except: return False

# Opções Padrão (Sem Kiosk, pois vamos usar a janela do Windows)
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    # --- LOGIN E NAVEGAÇÃO (Igual as versões anteriores) ---
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_frame_principal(driver)

    dt_ini, dt_fim = get_datas_mes_atual()
    try:
        inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
        if len(inputs) >= 2: inputs[0].clear(); inputs[0].send_keys(dt_ini); inputs[1].clear(); inputs[1].send_keys(dt_fim)
    except: pass

    try: driver.find_element(By.NAME, "enviar").click()
    except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
    time.sleep(5) 
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # --- TABELA ---
    tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
    if not tabelas: print("❌ Tabela não encontrada."); driver.quit(); exit()
    
    qtd_total = len(tabelas[-1].find_elements(By.TAG_NAME, "tr"))
    print(f">> Encontrados {qtd_total} registros.")

    pacientes_processados = 0
    
    for i in range(qtd_total):
        try:
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            tabela_dados = tabelas[-1]
            linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
            
            if i >= len(linhas): break
            linha = linhas[i]

            if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue
            colunas = linha.find_elements(By.TAG_NAME, "td")
            if len(colunas) < 4: continue

            pacientes_processados += 1
            
            # Nome Arquivo
            nome_arquivo = f"Ficha_{pacientes_processados}"
            alvo_clique = colunas[1]
            for col in colunas:
                txt = col.text.strip()
                if len(txt) > 3:
                    alvo_clique = col
                    if not txt[0].isdigit(): nome_arquivo = limpar_nome_arquivo(txt)
                    break
            
            print(f"\n--- Paciente #{pacientes_processados}: {nome_arquivo} ---")
            
            driver.execute_script("arguments[0].scrollIntoView(true);", alvo_clique)
            time.sleep(1)
            try: alvo_clique.click()
            except: driver.execute_script("arguments[0].click();", alvo_clique)
            
            time.sleep(5) # Espera carregar bem a ficha

            # --- SIMULAÇÃO HUMANA ---
            print("   -> Iniciando sequência de teclas...")
            
            # 1. Clica no meio da tela para garantir foco
            # Pega o tamanho da tela e clica no centro
            width, height = pyautogui.size()
            pyautogui.click(width/2, height/2)
            time.sleep(0.5)

            # 2. Ctrl + A (Selecionar Tudo)
            print("   -> Selecionando tudo (Ctrl+A)...")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(1)

            # 3. Ctrl + P (Imprimir)
            print("   -> Abrindo impressão (Ctrl+P)...")
            pyautogui.hotkey('ctrl', 'p')
            time.sleep(4) # Espera a janela de impressão do Windows abrir

            # 4. Enter (Confirmar Impressão/Salvar como PDF)
            print("   -> Confirmando...")
            pyautogui.press('enter')
            time.sleep(3) # Espera abrir a janela "Salvar Como"

            # 5. Digitar Nome e Salvar
            caminho_completo = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}.pdf")
            if os.path.exists(caminho_completo): 
                caminho_completo = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}_{int(time.time())}.pdf")
            
            print(f"   -> Salvando arquivo: {caminho_completo}")
            pyautogui.write(caminho_completo)
            time.sleep(1)
            pyautogui.press('enter')
            
            time.sleep(3) # Tempo para salvar o arquivo

            # Se por acaso abrir aquela telinha de "Substituir arquivo?", damos Enter de novo
            # pyautogui.press('enter') 

            print("   ✅ Arquivo salvo (Via Teclado).")

            # VOLTAR
            print("   -> Voltando...")
            driver.back()
            try: WebDriverWait(driver, 3).until(EC.alert_is_present()).accept()
            except: pass
            time.sleep(3)
            focar_frame_principal(driver)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        except Exception as e:
            print(f"❌ Erro Loop {i}: {e}")
            if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])
            focar_frame_principal(driver)

    print(f"✅ FIM! Todos processados.")
    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")