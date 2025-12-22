import time
import os
import re
import json
import pyautogui
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V27 - BUSCA RIGOROSA DE DADOS) ---")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"
ARQUIVO_CONTROLE = r"C:\Users\DELL\OneDrive\NII-Portal-1\controle_aih.json"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- FUNÇÕES ---
def carregar_memoria():
    if os.path.exists(ARQUIVO_CONTROLE):
        try:
            with open(ARQUIVO_CONTROLE, 'r') as f: return json.load(f)
        except: return []
    return []

def salvar_memoria(lista_aihs):
    with open(ARQUIVO_CONTROLE, 'w') as f: json.dump(lista_aihs, f)

def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def get_datas_mes_atual():
    hoje = datetime.now()
    return hoje.replace(day=1).strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def focar_no_frame_de_dados(driver):
    """
    Entra em cada frame e verifica se contém DADOS REAIS (Texto 'AIH' ou 'Paciente').
    Não aceita frames vazios ou só com menus.
    """
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    
    # 1. Varre frames procurando palavras-chave
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            src = driver.page_source
            # Só aceita se tiver indicio de ser a lista de dados
            if "table_listagem" in src and ("AIH" in src or "Paciente" in src or "Solicitação" in src):
                return True
        except: pass
    
    # 2. Tenta frame 1 padrão (Fallback)
    driver.switch_to.default_content()
    try: driver.switch_to.frame(1); return True
    except: return False

# --- SETUP ---
aihs_processadas = carregar_memoria()
print(f">> Memória: {len(aihs_processadas)} AIHs já salvas.")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 1.0
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    # LOGIN
    print(">> Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_no_frame_de_dados(driver)

    dt_ini, dt_fim = get_datas_mes_atual()
    try:
        inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
        if len(inputs) >= 2: inputs[0].clear(); inputs[0].send_keys(dt_ini); inputs[1].clear(); inputs[1].send_keys(dt_fim)
    except: pass

    try: driver.find_element(By.NAME, "enviar").click()
    except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
    time.sleep(5) 

    # --- LOOP DE PÁGINAS ---
    pagina_atual = 1
    
    while True:
        print(f"\n>>> PROCESSANDO PÁGINA {pagina_atual} <<<")
        
        # Garante foco no frame certo
        focar_no_frame_de_dados(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        
        # Se não achou tabela, tenta recarregar o foco uma vez
        if not tabelas:
            print(">> Tabela não visível. Tentando refocar...")
            focar_no_frame_de_dados(driver)
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        
        if not tabelas:
            print(">> Erro crítico: Tabela de dados sumiu.")
            break
        
        # Pega sempre a última tabela (a de dados)
        tabela_dados = tabelas[-1]
        linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0

        # --- PROCESSAMENTO ---
        for i in range(qtd_total):
            try:
                # Re-foca (Crucial para não perder referência)
                focar_no_frame_de_dados(driver)
                tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
                tabela_dados = tabelas[-1]
                linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
                
                if i >= len(linhas): break
                linha = linhas[i]

                # Filtros
                if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 6: continue 
                
                registros_pagina += 1

                # Busca AIH
                match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', linha.text)
                if match_aih:
                    aih_encontrada = match_aih.group(0)
                    print(f"--- Pág {pagina_atual} | Linha {i}: AIH {aih_encontrada}", end=" ")
                else:
                    # print(".") # Debug silencioso
                    continue

                if aih_encontrada in aihs_processadas:
                    print(f"-> [JÁ IMPRESSA]")
                    continue
                
                print(f"-> [NOVA!]")

                # Nome Arquivo
                nome_arquivo = f"AIH_{aih_encontrada}"
                for col in colunas:
                    txt = col.text.strip()
                    if len(txt) > 5 and not txt[0].isdigit():
                        nome_arquivo = limpar_nome_arquivo(txt); break
                
                # Highlight Amarelo
                for col in colunas:
                    if aih_encontrada in col.text:
                        driver.execute_script("arguments[0].style.backgroundColor = 'yellow';", col)
                        break

                # Clica
                coluna_clique = colunas[1] 
                for col in colunas:
                    if len(col.text) > 4: coluna_clique = col; break

                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                time.sleep(1)
                try: coluna_clique.click()
                except: driver.execute_script("arguments[0].click();", coluna_clique)
                
                time.sleep(5)

                # Impressão Manual
                width, height = pyautogui.size()
                pyautogui.click(width/2, height/2)
                time.sleep(0.5)

                pyautogui.hotkey('ctrl', 'a'); time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'p'); time.sleep(4)
                pyautogui.press('enter'); time.sleep(3)
                
                caminho = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}.pdf")
                if os.path.exists(caminho): caminho = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}_{int(time.time())}.pdf")
                
                pyautogui.write(caminho); time.sleep(1)
                pyautogui.press('enter'); time.sleep(3)

                aihs_processadas.append(aih_encontrada)
                salvar_memoria(aihs_processadas)

                driver.back()
                try: WebDriverWait(driver, 3).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro registro {i}: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0:
            print(">> Página vazia detectada (nenhum registro válido).")
            # Não dá break aqui, tenta achar paginação mesmo assim, 
            # as vezes a tabela tá vazia mas tem links embaixo

        # --- PAGINAÇÃO VISUAL (V27) ---
        print(f">> Procurando página {pagina_atual + 1}...")
        focar_no_frame_de_dados(driver)
        
        paginou = False
        prox_num = str(pagina_atual + 1)
        
        # 1. Tenta achar link com o NÚMERO EXATO (Prioridade)
        try:
            # XPath poderoso: procura link que o texto seja "2" (e ignora espaços)
            btn_num = driver.find_elements(By.XPATH, f"//a[normalize-space(text())='{prox_num}']")
            if btn_num:
                print(f"   -> Link numérico '{prox_num}' encontrado! Clicando...")
                driver.execute_script("arguments[0].scrollIntoView(true);", btn_num[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn_num[0])
                time.sleep(6) # Mais tempo pra carregar
                paginou = True
                pagina_atual += 1
        except: pass

        # 2. Se não achou número, tenta "Próxima" ou Seta
        if not paginou:
            try:
                btns_prox = driver.find_elements(By.XPATH, "//a[contains(text(),'Próxima') or contains(text(),'>') or .//img[contains(@src,'prox')]]")
                if btns_prox:
                    print(f"   -> Link 'Próxima' encontrado! Clicando...")
                    driver.execute_script("arguments[0].click();", btns_prox[0])
                    time.sleep(6)
                    paginou = True
                    pagina_atual += 1
            except: pass

        if not paginou:
            print(f">> Não encontrei link para página {pagina_atual + 1}. FIM.")
            break

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")