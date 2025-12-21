import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V11 - CLIQUE NA CÉLULA) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- CONFIGURAÇÃO CHROME ---
print_settings = {
    "recentDestinations": [{"id": "Save as PDF", "origin": "local", "account": ""}],
    "selectedDestinationId": "Save as PDF",
    "version": 2,
    "isHeaderFooterEnabled": False
}
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "printing.print_preview_sticky_settings.appState": json.dumps(print_settings),
    "savefile.default_directory": PASTA_DOWNLOAD
}
options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", prefs)
options.add_argument('--kiosk-printing')
options.add_argument("--disable-print-preview")

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

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.maximize_window()

    # --- LOGIN ---
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    # --- NAVEGAÇÃO ---
    print(">> Navegando...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_frame_principal(driver)

    # --- FILTROS ---
    dt_ini, dt_fim = get_datas_mes_atual()
    print(f">> Filtrando: {dt_ini} a {dt_fim}")
    try:
        inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
        if len(inputs) >= 2: inputs[0].clear(); inputs[0].send_keys(dt_ini); inputs[1].clear(); inputs[1].send_keys(dt_fim)
    except: pass

    print(">> Clicando em Pesquisar...")
    try: driver.find_element(By.NAME, "enviar").click()
    except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()

    time.sleep(5) 
    print(">> Rolando página...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # --- LOCALIZAR TABELA ---
    print(">> Analisando tabela...")
    tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
    if not tabelas:
        print("❌ Tabela não encontrada.")
        driver.quit(); exit()
    
    tabela_dados = tabelas[-1]
    
    # Pega todas as linhas
    linhas_totais = tabela_dados.find_elements(By.TAG_NAME, "tr")
    qtd_total = len(linhas_totais)
    print(f">> Tabela tem {qtd_total} linhas (incluindo cabeçalhos).")

    # --- LOOP INTELIGENTE ---
    pacientes_processados = 0
    
    for i in range(qtd_total):
        try:
            # Re-localiza a tabela e linhas para evitar StaleElement
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            tabela_dados = tabelas[-1]
            linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
            
            if i >= len(linhas): break
            linha = linhas[i]

            # 1. VERIFICA SE É CABEÇALHO (PULA SE FOR)
            # O log mostrou que o cabeçalho tem class="td_titulo_campo"
            if "td_titulo_campo" in linha.get_attribute("innerHTML"):
                # print(f"   (Linha {i} é cabeçalho - Pulando)")
                continue

            # 2. PROCURA CÉLULA CLICÁVEL
            colunas = linha.find_elements(By.TAG_NAME, "td")
            
            # Se tiver poucas colunas, provavelmente não é um paciente
            if len(colunas) < 4: continue

            pacientes_processados += 1
            print(f"\n--- Processando Paciente #{pacientes_processados} (Linha {i}) ---")

            # Tenta clicar na coluna do PACIENTE ou PROCEDIMENTO ou AIH
            # Geralmente colunas do meio têm texto mais relevante. Vamos tentar a 3ª ou 4ª coluna.
            alvo_clique = None
            
            # Estratégia: Clica na primeira coluna que tenha texto grande (evita checkbox vazio)
            for col in colunas:
                texto = col.text.strip()
                if len(texto) > 3: # Se tem texto visível (Nome, AIH, etc)
                    alvo_clique = col
                    print(f"   -> Alvo identificado: '{texto[:20]}...'")
                    break
            
            if not alvo_clique:
                # Fallback: clica na segunda coluna
                alvo_clique = colunas[1]

            # CLIQUE
            driver.execute_script("arguments[0].scrollIntoView(true);", alvo_clique)
            time.sleep(1)
            # Força o clique no elemento
            try: alvo_clique.click()
            except: driver.execute_script("arguments[0].click();", alvo_clique)
            
            time.sleep(4) # Carrega ficha

            # --- DENTRO DA FICHA (ROTINA DE IMPRESSÃO) ---
            print("   -> Buscando botão imprimir...")
            btn_print = None
            seletores = ["input[value='Imprimir']", "input[src*='print']", "img[src*='print']", "a[href*='print']", "input[name='bt_imprimir']"]
            
            for sel in seletores:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elems:
                        btn_print = elems[0]; break
                except: pass
            
            if btn_print:
                print("   -> Imprimindo...")
                driver.execute_script("arguments[0].click();", btn_print)
                time.sleep(3)
                
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.execute_script("window.print();")
                    time.sleep(3)
                    driver.close()
                    driver.switch_to.window(driver.current_window_handle)
                else:
                    driver.execute_script("window.print();")
                    time.sleep(3)
                print("   ✅ Arquivo Salvo.")
            else:
                print("   ⚠️ Botão imprimir não encontrado nesta tela.")
            
            # VOLTAR
            print("   -> Voltando...")
            driver.back()
            try: WebDriverWait(driver, 3).until(EC.alert_is_present()).accept()
            except: pass
            time.sleep(3)
            focar_frame_principal(driver)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        except Exception as e:
            # Erros na iteração não param o script
            # print(f"   (Pulo de linha: {e})")
            # Se perdeu o foco, tenta voltar
            if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])
            focar_frame_principal(driver)

    print(f"✅ FIM! {pacientes_processados} pacientes verificados.")
    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")