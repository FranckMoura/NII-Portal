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

print(f"--- 2. AUTOMAÇÃO SISREG (V34 - APRENDIZAGEM DINÂMICA) ---")

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
    # Remove caracteres inválidos para nome de arquivo
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def get_datas_mes_atual():
    hoje = datetime.now()
    return hoje.replace(day=1).strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def focar_na_tabela_dados(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            if driver.find_elements(By.CLASS_NAME, "table_listagem"):
                return True
        except: pass
    driver.switch_to.default_content()
    return False

# --- SETUP ---
aihs_processadas_json = carregar_memoria()
print(f">> Memória JSON carregada: {len(aihs_processadas_json)} registros.")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 1.0
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

# Variáveis de Controle
posicao_botao_proxima = None 
qtd_linhas_anterior = -1

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

    focar_na_tabela_dados(driver)

    dt_ini, dt_fim = get_datas_mes_atual()
    try:
        inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
        if len(inputs) >= 2: inputs[0].clear(); inputs[0].send_keys(dt_ini); inputs[1].clear(); inputs[1].send_keys(dt_fim)
    except: pass

    try: driver.find_element(By.NAME, "enviar").click()
    except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
    time.sleep(5) 

    pagina_atual = 1
    
    while True:
        print(f"\n>>> PROCESSANDO PÁGINA {pagina_atual} <<<")
        
        # 1. LER TABELA
        focar_na_tabela_dados(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        if not tabelas:
            print(">> Tabela não encontrada. Fim (ou erro de carregamento).")
            # Tenta recuperar antes de desistir
            focar_na_tabela_dados(driver)
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            if not tabelas: break
        
        tabela_dados = tabelas[-1]
        linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0
        
        print(f">> Linhas nesta página: {qtd_total}")

        # --- PROCESSAMENTO ---
        for i in range(qtd_total):
            try:
                focar_na_tabela_dados(driver)
                tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
                linha = tabelas[-1].find_elements(By.TAG_NAME, "tr")[i]

                if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 6: continue 
                
                registros_pagina += 1
                match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', linha.text)
                
                if match_aih:
                    aih_encontrada = match_aih.group(0)
                    print(f"--- Pág {pagina_atual} | AIH {aih_encontrada}", end=" ")
                else: continue

                # --- VALIDAÇÃO REAL ---
                nome_arquivo_base = f"AIH_{aih_encontrada}"
                arquivo_existe = False
                for f in os.listdir(PASTA_DOWNLOAD):
                    if f.startswith(nome_arquivo_base) and f.endswith(".pdf"):
                        arquivo_existe = True
                        break

                if aih_encontrada in aihs_processadas_json and arquivo_existe:
                    print(f"-> [OK - JÁ EXISTE]")
                    continue
                
                print(f"-> [NOVA! IMPRIMINDO...]")

                # Nome
                nome_paciente = "PACIENTE"
                for col in colunas:
                    txt = col.text.strip()
                    if len(txt) > 5 and not txt[0].isdigit():
                        nome_paciente = limpar_nome_arquivo(txt); break
                
                nome_final = f"{nome_arquivo_base}_{nome_paciente}"

                # Highlight
                for col in colunas:
                    if aih_encontrada in col.text:
                        driver.execute_script("arguments[0].style.backgroundColor = 'yellow';", col)

                # Clique
                coluna_clique = colunas[1] 
                for col in colunas:
                    if len(col.text) > 4: coluna_clique = col; break

                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                time.sleep(1)
                coluna_clique.click()
                time.sleep(5) # Tempo para abrir a ficha

                # Impressão (Segura)
                width, height = pyautogui.size()
                pyautogui.click(width/2, height/2) # Foco
                
                pyautogui.hotkey('ctrl', 'a'); time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'p'); time.sleep(4) # Espera janela de impressão
                pyautogui.press('enter'); time.sleep(3) # Confirma imprimir
                
                caminho = os.path.join(PASTA_DOWNLOAD, f"{nome_final}.pdf")
                # Remove arquivo se já existir com mesmo nome exato para evitar "(1)"
                if os.path.exists(caminho):
                    try: os.remove(caminho)
                    except: pass
                
                pyautogui.write(caminho); time.sleep(2) # Escreve caminho devagar
                pyautogui.press('enter'); time.sleep(4) # Salva e espera gravar no disco

                # Salva memória
                if aih_encontrada not in aihs_processadas_json:
                    aihs_processadas_json.append(aih_encontrada)
                    salvar_memoria(aihs_processadas_json)

                driver.back()
                try: WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(3) # Espera lista voltar

            except Exception as e:
                print(f"❌ Erro: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0:
            print(">> Página vazia. Fim do processo.")
            break

        # --- 2. PAGINAÇÃO INTELIGENTE ---
        print(f">> Fim da página {pagina_atual}.")
        
        # VERIFICAÇÃO DE MUDANÇA DE LAYOUT
        if qtd_linhas_anterior != -1 and qtd_linhas_anterior != qtd_total:
            print(f"⚠️ AVISO: A página mudou de tamanho (Antes: {qtd_linhas_anterior} linhas, Agora: {qtd_total}).")
            print(">> O botão mudou de lugar. Preciso aprender a nova posição.")
            posicao_botao_proxima = None # Força re-aprender
        
        qtd_linhas_anterior = qtd_total

        # Prepara rolagem
        driver.switch_to.default_content()
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        if posicao_botao_proxima is None:
            # PRIMEIRA VEZ ou MUDOU DE LUGAR -> PEDE AJUDA
            print("\a") # Bip sonoro
            res = pyautogui.confirm(
                text=f'A tabela tem {qtd_total} linhas.\n\nColoque o mouse em cima do botão PRÓXIMA e dê OK.', 
                title='Ensinar Posição', 
                buttons=['OK (Mouse Posicionado)', 'Parar']
            )
            
            if res == 'Parar': break
            
            posicao_botao_proxima = pyautogui.position()
            print(f">> Nova posição gravada: {posicao_botao_proxima}")
            
            pyautogui.click()
            time.sleep(8)
            pagina_atual += 1
            
        else:
            # POSIÇÃO CONHECIDA
            print(f">> Clicando na posição {posicao_botao_proxima}...")
            pyautogui.moveTo(posicao_botao_proxima[0], posicao_botao_proxima[1], duration=0.5)
            pyautogui.click()
            time.sleep(8)
            pagina_atual += 1

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")