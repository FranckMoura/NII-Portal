import time
import os
import re
import json
import pyautogui
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V21 - PAGINAÇÃO NUMÉRICA) ---")

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

    focar_frame_principal(driver)

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
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # 1. PROCESSA TABELA
        tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
        if not tabelas: break
        
        qtd_total = len(tabelas[-1].find_elements(By.TAG_NAME, "tr"))
        
        for i in range(qtd_total):
            try:
                # Re-foca
                tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
                tabela_dados = tabelas[-1]
                linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
                if i >= len(linhas): break
                linha = linhas[i]

                if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 6: continue 

                # Identifica AIH
                match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', linha.text)
                
                if match_aih:
                    aih_encontrada = match_aih.group(0)
                    print(f"--- Pág {pagina_atual} | Linha {i}: AIH {aih_encontrada}", end=" ")
                else:
                    continue

                if aih_encontrada in aihs_processadas:
                    print(f"-> [JÁ IMPRESSA]")
                    continue
                
                print(f"-> [NOVA! IMPRIMINDO...]")

                # Nome Arquivo
                nome_arquivo = f"AIH_{aih_encontrada}"
                for col in colunas:
                    txt = col.text.strip()
                    if len(txt) > 5 and not txt[0].isdigit():
                        nome_arquivo = limpar_nome_arquivo(txt); break

                # Clica
                coluna_clique = colunas[1] 
                for col in colunas:
                    if len(col.text) > 4: coluna_clique = col; break

                driver.execute_script("arguments[0].scrollIntoView(true);", coluna_clique)
                time.sleep(1)
                try: coluna_clique.click()
                except: driver.execute_script("arguments[0].click();", coluna_clique)
                
                time.sleep(5)

                # Simula Ctrl+P
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
                focar_frame_principal(driver)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            except Exception as e:
                print(f"❌ Erro registro {i}: {e}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(driver.window_handles[0])
                focar_frame_principal(driver)

        # 2. TENTATIVA ROBUESTA DE VIRAR A PÁGINA
        print(">> Procurando próxima página...")
        
        proxima_pag_num = pagina_atual + 1
        paginou = False
        
        # Estratégia A: Buscar TODOS os links da página e ver se algum é o número "2", "3", etc.
        todos_links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in todos_links:
            try:
                txt = link.text.strip()
                # Se o texto do link for EXATAMENTE o número da próxima página
                if txt == str(proxima_pag_num):
                    print(f"   -> Link numérico '{txt}' encontrado! Clicando...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", link)
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(5)
                    paginou = True
                    pagina_atual += 1
                    break
                
                # Se for seta ">" ou "Próxima"
                if "Próxima" in txt or "Proxima" in txt or ">" in txt or "Pr&oacute;xima" in link.get_attribute("innerHTML"):
                    print(f"   -> Link de texto '{txt}' encontrado! Clicando...")
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(5)
                    paginou = True
                    pagina_atual += 1
                    break
            except: pass
        
        if not paginou:
             # Estratégia B: Procurar imagens de seta dentro de links
             try:
                 imgs = driver.find_elements(By.XPATH, "//a/img")
                 for img in imgs:
                     src = img.get_attribute("src") or ""
                     alt = img.get_attribute("alt") or ""
                     if "prox" in src.lower() or "next" in src.lower() or "avancar" in src.lower() or "seta" in src.lower():
                         print("   -> Imagem de seta encontrada! Clicando...")
                         pai_link = img.find_element(By.XPATH, "./..")
                         driver.execute_script("arguments[0].click();", pai_link)
                         time.sleep(5)
                         paginou = True
                         pagina_atual += 1
                         break
             except: pass

        if not paginou:
            print(">> Nenhuma outra página encontrada. FIM DO PROCESSO.")
            # DEBUG: Mostra o que ele viu no rodapé para a gente corrigir se falhar
            print("   (Links visíveis no rodapé para diagnóstico: ", end="")
            try:
                for l in todos_links[-10:]: # Mostra os ultimos 10 links da pagina
                    print(f"[{l.text}] ", end="")
            except: pass
            print(")")
            break 

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")