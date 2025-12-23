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

print(f"--- 2. AUTOMAÇÃO SISREG (V39 - RESTAURAÇÃO FUNCIONAL + PORTAL) ---")

# --- VERIFICAÇÃO DE BIBLIOTECAS ---
try:
    import cv2
    print(">> Biblioteca OpenCV detectada. O reconhecimento visual funcionará.")
except ImportError:
    print("❌ AVISO: OpenCV não instalado. O modo visual pode falhar. (pip install opencv-python)")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
PASTA_PDF = os.path.join(PASTA_PROJETO, "Fichas_Internacao")
ARQUIVO_JSON_SITE = os.path.join(PASTA_PROJETO, "arquivos", "dados_sisreg.json")
ARQUIVO_CONTROLE = os.path.join(PASTA_PROJETO, "controle_aih.json") # Volta a usar o nome original que funcionava
IMAGEM_SETA = os.path.join(PASTA_PROJETO, "seta_proxima.png")

# Cria pastas se não existirem
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

def atualizar_json_do_portal(novo_registro):
    dados_site = []
    try:
        if os.path.exists(ARQUIVO_JSON_SITE):
            with open(ARQUIVO_JSON_SITE, 'r', encoding='utf-8') as f:
                dados_site = json.load(f)
    except:
        dados_site = []

    # Remove registro antigo para evitar duplicata
    dados_site = [d for d in dados_site if d.get('aih') != novo_registro['aih']]
    dados_site.insert(0, novo_registro)
    
    with open(ARQUIVO_JSON_SITE, 'w', encoding='utf-8') as f:
        json.dump(dados_site, f, indent=4, ensure_ascii=False)

def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def get_datas_mes_atual():
    hoje = datetime.now()
    return hoje.replace(day=1).strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")

def focar_na_tabela_dados(driver):
    # A VERSÃO SIMPLES DA V36 QUE FUNCIONOU
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
if not os.path.exists(IMAGEM_SETA):
    print(f"⚠️ ATENÇÃO: Falta a imagem 'seta_proxima.png' na pasta {PASTA_PROJETO}!")

aihs_processadas_json = carregar_memoria()
print(f">> Memória JSON carregada: {len(aihs_processadas_json)} registros.")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 1.0
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

# Variáveis de Controle
posicao_manual_backup = None 
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
            print(">> Tabela não encontrada. Tentando refocar...")
            focar_na_tabela_dados(driver)
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            if not tabelas:
                print(">> Tabela realmente não encontrada. Fim.")
                break
        
        tabela_dados = tabelas[-1]
        linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
        qtd_total = len(linhas)
        registros_pagina = 0
        primeira_aih_desta_pagina = None

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
                    if primeira_aih_desta_pagina is None: primeira_aih_desta_pagina = aih_encontrada
                    print(f"--- Pág {pagina_atual} | AIH {aih_encontrada}", end=" ")
                else: continue

                # Extração para o Portal (NOVO)
                nome_paciente = "PACIENTE"
                status_estimado = "Pendente"
                cns_estimado = "-"
                procedimento_estimado = "Internação"

                for col in colunas:
                    txt = col.text.strip()
                    if len(txt) > 5 and not txt[0].isdigit() and not "/" in txt:
                        nome_paciente = limpar_nome_arquivo(txt)
                    if "AUTORIZADO" in txt.upper() or "APROVADO" in txt.upper(): status_estimado = "Aprovado"
                    elif "NEGADO" in txt.upper() or "CANCELADO" in txt.upper(): status_estimado = "Negado"

                # Validação Real
                nome_arquivo_base = f"AIH_{aih_encontrada}_{nome_paciente}"
                nome_arquivo_pdf = f"{nome_arquivo_base}.pdf"
                caminho_completo_pdf = os.path.join(PASTA_PDF, nome_arquivo_pdf)
                
                # Checagem "burra": vê se tem algum arquivo começando com a AIH na pasta
                arquivo_existe = False
                for f in os.listdir(PASTA_PDF):
                    if f.startswith(f"AIH_{aih_encontrada}") and f.endswith(".pdf"):
                        arquivo_existe = True
                        nome_arquivo_pdf = f # Usa o nome real que está na pasta
                        break

                if aih_encontrada in aihs_processadas_json and arquivo_existe:
                    print(f"-> [OK - JÁ EXISTE]")
                    # Atualiza o portal mesmo assim para garantir links
                    dados_exportacao = {
                        "data_visual": datetime.now().strftime("%d/%m/%Y"),
                        "data_iso": datetime.now().strftime("%Y-%m-%d"),
                        "paciente": nome_paciente,
                        "cns": cns_estimado,
                        "num_sol": "-",
                        "aih": aih_encontrada,
                        "proc": procedimento_estimado,
                        "status": status_estimado,
                        "arquivo_pdf": f"Fichas_Internacao/{nome_arquivo_pdf}"
                    }
                    atualizar_json_do_portal(dados_exportacao)
                    continue
                
                print(f"-> [NOVA! IMPRIMINDO...]")

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
                
                # Salva JSON Portal
                dados_exportacao = {
                    "data_visual": datetime.now().strftime("%d/%m/%Y"),
                    "data_iso": datetime.now().strftime("%Y-%m-%d"),
                    "paciente": nome_paciente,
                    "cns": cns_estimado,
                    "num_sol": "-",
                    "aih": aih_encontrada,
                    "proc": procedimento_estimado,
                    "status": status_estimado,
                    "arquivo_pdf": f"Fichas_Internacao/{nome_arquivo_pdf}"
                }
                atualizar_json_do_portal(dados_exportacao)

                driver.back()
                try: WebDriverWait(driver, 5).until(EC.alert_is_present()).accept()
                except: pass
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])

        if registros_pagina == 0:
            print(">> Página vazia. Fim.")
            break

        # VERIFICAÇÃO DE MUDANÇA DE LAYOUT (Reseta manual backup)
        if qtd_linhas_anterior != -1 and qtd_linhas_anterior != qtd_total:
             print("⚠️ Layout mudou! Resetando posição manual se houver.")
             posicao_manual_backup = None
        qtd_linhas_anterior = qtd_total

        # 2. PAGINAÇÃO HÍBRIDA
        print(f">> Procurando PRÓXIMA página...")
        
        driver.switch_to.default_content()
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        paginou = False

        # TENTATIVA 1: VISUAL (OpenCV)
        if os.path.exists(IMAGEM_SETA):
            try:
                # Tenta achar com 90% de confiança
                posicao = pyautogui.locateCenterOnScreen(IMAGEM_SETA, confidence=0.9)
                if not posicao:
                    # Tenta achar com 70% (mais flexível)
                    posicao = pyautogui.locateCenterOnScreen(IMAGEM_SETA, confidence=0.7)
                
                if posicao:
                    print(f"   -> [VISUAL] Seta encontrada em {posicao}. Clicando...")
                    pyautogui.moveTo(posicao)
                    time.sleep(0.5)
                    pyautogui.click()
                    paginou = True
            except Exception as e:
                print(f"   -> Erro no visual: {e}")

        # TENTATIVA 2: MANUAL BACKUP (Se visual falhar)
        if not paginou:
            print("⚠️ Visual falhou ou imagem não encontrada.")
            
            if posicao_manual_backup:
                print(f"   -> [MANUAL] Usando posição conhecida {posicao_manual_backup}...")
                pyautogui.moveTo(posicao_manual_backup)
                pyautogui.click()
                paginou = True
            else:
                # PEDE AJUDA
                print("\a")
                res = pyautogui.confirm(
                    text=f'O robô não achou a imagem da seta.\n\n1. Ponha o mouse sobre o botão PRÓXIMA.\n2. Não mexa.\n3. Dê OK.', 
                    title='Ajuda Manual', 
                    buttons=['OK', 'Parar']
                )
                if res == 'Parar': break
                
                posicao_manual_backup = pyautogui.position()
                print(f"   -> [MANUAL] Nova posição aprendida: {posicao_manual_backup}")
                pyautogui.click()
                paginou = True
        
        if paginou:
            time.sleep(8)
            pagina_atual += 1
        else:
            print(">> Não foi possível avançar. Fim.")
            break

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")