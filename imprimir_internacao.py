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
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V43 - PREENCHIMENTO DE DATA UNIVERSAL) ---")

# --- VERIFICAÇÃO DE BIBLIOTECAS ---
try:
    import cv2
except ImportError:
    print("❌ AVISO: OpenCV não instalado.")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE AQUI
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
PASTA_PDF = os.path.join(PASTA_PROJETO, "Fichas_Internacao")
ARQUIVO_JSON_SITE = os.path.join(PASTA_PROJETO, "arquivos", "dados_sisreg.json")
ARQUIVO_CONTROLE = os.path.join(PASTA_PROJETO, "controle_aih.json")
IMAGEM_SETA = os.path.join(PASTA_PROJETO, "seta_proxima.png")

if not os.path.exists(PASTA_PDF): os.makedirs(PASTA_PDF)
pasta_json_dir = os.path.dirname(ARQUIVO_JSON_SITE)
if not os.path.exists(pasta_json_dir): os.makedirs(pasta_json_dir)

# --- FUNÇÕES ---
def carregar_memoria():
    if os.path.exists(ARQUIVO_CONTROLE):
        try:
            with open(ARQUIVO_CONTROLE, 'r') as f: return json.load(f)
        except: return []
    return []

def salvar_memoria(lista_aihs):
    with open(ARQUIVO_CONTROLE, 'w') as f: json.dump(lista_aihs, f)

def atualizar_json_do_portal(aih, nome_paciente, status, caminho_pdf_relativo):
    dados_site = []
    try:
        if os.path.exists(ARQUIVO_JSON_SITE):
            with open(ARQUIVO_JSON_SITE, 'r', encoding='utf-8') as f:
                dados_site = json.load(f)
    except: dados_site = []

    registro_existente = next((item for item in dados_site if item.get("aih") == aih), None)

    if registro_existente:
        registro_existente["arquivo_pdf"] = caminho_pdf_relativo
        if status: registro_existente["status"] = status
    else:
        novo_registro = {
            "data_visual": datetime.now().strftime("%d/%m/%Y"),
            "data_iso": datetime.now().strftime("%Y-%m-%d"),
            "paciente": nome_paciente,
            "cns": "-",
            "num_sol": "-",
            "aih": aih,
            "proc": "Internação",
            "status": status,
            "arquivo_pdf": caminho_pdf_relativo
        }
        dados_site.insert(0, novo_registro)
    
    with open(ARQUIVO_JSON_SITE, 'w', encoding='utf-8') as f:
        json.dump(dados_site, f, indent=4, ensure_ascii=False)

def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def focar_na_tabela_dados(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            # Procura inputs de data ou tabela
            if driver.find_elements(By.CLASS_NAME, "table_listagem") or driver.find_elements(By.NAME, "data_inicio"):
                return True
        except: pass
    driver.switch_to.default_content()
    return False

def get_datas_mes_atual():
    hoje = datetime.now()
    return hoje.replace(day=1).strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def verificar_bloqueio_horario(driver):
    try:
        alerta = driver.switch_to.alert
        texto = alerta.text
        if "bloqueado" in texto.lower() and "horas" in texto.lower():
            print(f"⛔ BLOQUEIO DETECTADO: {texto}")
            alerta.accept()
            return True
        alerta.accept() 
    except NoAlertPresentException:
        pass
    return False

def preencher_datas_robustamente(driver, dt_ini, dt_fim):
    """Tenta de tudo para preencher a data."""
    print(f">> Tentando preencher datas: {dt_ini} a {dt_fim}...")
    
    sucesso = False
    
    # TENTATIVA 1: Pelo Name (Padrão do Sisreg)
    try:
        driver.find_element(By.NAME, "data_inicio").clear()
        driver.find_element(By.NAME, "data_inicio").send_keys(dt_ini)
        driver.find_element(By.NAME, "data_fim").clear()
        driver.find_element(By.NAME, "data_fim").send_keys(dt_fim)
        print("   -> Datas preenchidas via NAME.")
        sucesso = True
    except: pass

    if not sucesso:
        # TENTATIVA 2: Pelo Label 'Período'
        try:
            inputs = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
            if len(inputs) >= 2:
                inputs[0].clear(); inputs[0].send_keys(dt_ini)
                inputs[1].clear(); inputs[1].send_keys(dt_fim)
                print("   -> Datas preenchidas via XPATH (Período).")
                sucesso = True
        except: pass

    if not sucesso:
        # TENTATIVA 3: Força Bruta JavaScript
        try:
            driver.execute_script(f"document.getElementsByName('data_inicio')[0].value = '{dt_ini}'")
            driver.execute_script(f"document.getElementsByName('data_fim')[0].value = '{dt_fim}'")
            print("   -> Datas preenchidas via JAVASCRIPT.")
            sucesso = True
        except: pass
    
    return sucesso

# --- SETUP ---
aihs_processadas_json = carregar_memoria()
print(f">> Memória JSON carregada: {len(aihs_processadas_json)} registros.")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 1.0
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    if verificar_bloqueio_horario(driver): driver.quit(); exit()

    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    if verificar_bloqueio_horario(driver): driver.quit(); exit()

    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    focar_na_tabela_dados(driver)

    # --- PREENCHIMENTO DE DATA ---
    dt_ini, dt_fim = get_datas_mes_atual()
    preencher_datas_robustamente(driver, dt_ini, dt_fim)

    # Clica em Pesquisar
    try: driver.find_element(By.NAME, "enviar").click()
    except: 
        try: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
        except: pass
    
    print(">> Pesquisando...")
    time.sleep(8) # Tempo maior para o site processar a busca

    pagina_atual = 1
    
    while True:
        if verificar_bloqueio_horario(driver): break

        print(f"\n>>> PROCESSANDO PÁGINA {pagina_atual} <<<")
        
        focar_na_tabela_dados(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        if not tabelas:
            print(">> Tabela não encontrada (ou busca sem resultados).")
            break
        
        tabela_dados = tabelas[-1]
        linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0

        print(f">> Linhas nesta página: {qtd_total}")

        # Se tiver poucas linhas (só cabeçalho), tenta re-preencher data e buscar de novo
        if qtd_total < 5 and pagina_atual == 1:
            print("⚠️ Parece vazio! Tentando preencher data novamente...")
            preencher_datas_robustamente(driver, dt_ini, dt_fim)
            try: driver.find_element(By.NAME, "enviar").click()
            except: pass
            time.sleep(8)
            # Recarrega elementos
            focar_na_tabela_dados(driver)
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            if tabelas:
                linhas = tabelas[-1].find_elements(By.TAG_NAME, "tr")
                qtd_total = len(linhas)
                print(f">> Nova contagem de linhas: {qtd_total}")

        for i in range(qtd_total):
            try:
                focar_na_tabela_dados(driver)
                tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
                if not tabelas: break
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

                # Extração
                nome_paciente = "PACIENTE"
                status_estimado = "Pendente"
                for col in colunas:
                    txt = col.text.strip()
                    if len(txt) > 5 and not txt[0].isdigit() and not "/" in txt:
                        nome_paciente = limpar_nome_arquivo(txt)
                    if "AUTORIZADO" in txt.upper() or "APROVADO" in txt.upper(): status_estimado = "Aprovado"
                    elif "NEGADO" in txt.upper() or "CANCELADO" in txt.upper(): status_estimado = "Negado"

                nome_arquivo_base = f"AIH_{aih_encontrada}_{nome_paciente}"
                nome_arquivo_pdf = f"{nome_arquivo_base}.pdf"
                caminho_completo_pdf = os.path.join(PASTA_PDF, nome_arquivo_pdf)
                caminho_relativo_site = f"Fichas_Internacao/{nome_arquivo_pdf}"

                # Verifica existência
                arquivo_existe = False
                for f in os.listdir(PASTA_PDF):
                    if f.startswith(f"AIH_{aih_encontrada}") and f.endswith(".pdf"):
                        arquivo_existe = True
                        caminho_relativo_site = f"Fichas_Internacao/{f}"
                        break

                if aih_encontrada in aihs_processadas_json and arquivo_existe:
                    print(f"-> [OK - JÁ EXISTE]")
                    atualizar_json_do_portal(aih_encontrada, nome_paciente, status_estimado, caminho_relativo_site)
                    continue
                
                print(f"-> [NOVA! IMPRIMINDO...]")

                # Highlight e Clique
                for col in colunas:
                    if aih_encontrada in col.text:
                        driver.execute_script("arguments[0].style.backgroundColor = 'yellow';", col)

                coluna_clique = colunas[1] 
                for col in colunas:
                    if len(col.text) > 4: coluna_clique = col; break

                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                time.sleep(1)
                coluna_clique.click()
                time.sleep(5)

                # Impressão
                width, height = pyautogui.size()
                pyautogui.click(width/2, height/2)
                pyautogui.hotkey('ctrl', 'a'); time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'p'); time.sleep(4)
                pyautogui.press('enter'); time.sleep(3)
                
                if os.path.exists(caminho_completo_pdf):
                    try: os.remove(caminho_completo_pdf)
                    except: pass
                
                pyautogui.write(caminho_completo_pdf); time.sleep(2)
                pyautogui.press('enter'); time.sleep(4)

                if aih_encontrada not in aihs_processadas_json:
                    aihs_processadas_json.append(aih_encontrada)
                    salvar_memoria(aihs_processadas_json)
                
                atualizar_json_do_portal(aih_encontrada, nome_paciente, status_estimado, caminho_relativo_site)

                driver.back()
                try: WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0:
            print(">> Página vazia.")
            break

        # --- PAGINAÇÃO VISUAL ---
        print(f">> Procurando PRÓXIMA página...")
        driver.switch_to.default_content()
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        paginou = False
        if os.path.exists(IMAGEM_SETA):
            try:
                try: posicao = pyautogui.locateCenterOnScreen(IMAGEM_SETA, confidence=0.85)
                except: posicao = pyautogui.locateCenterOnScreen(IMAGEM_SETA)
                
                if posicao:
                    print(f"   -> [VISUAL] Clicando em {posicao}...")
                    pyautogui.moveTo(posicao); time.sleep(0.5); pyautogui.click()
                    paginou = True
            except: pass

        if not paginou:
            print(">> Fim do processo.")
            break
        
        time.sleep(8)
        pagina_atual += 1

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")