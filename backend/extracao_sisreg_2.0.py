import time
import os
import re
import json
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 🤖 ROBÔ SISREG V62 (CLIQUE DUPLO + IMPRESSÃO CORRIGIDA) ---")

# --- CONFIGURAÇÕES ---
# CREDENCIAIS CORRETAS (PERFIL EXECUTANTE)
USUARIO = "20325223FRANCK"
SENHA = "515462"

FORCAR_RE_DOWNLOAD = True 

SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\downloads"
if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Conexão Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    print("⚠️ Modo Offline (Supabase não conectado).")

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--kiosk-printing")

prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "savefile.default_directory": PASTA_DOWNLOAD,
    "printing.print_preview_sticky_settings.appState": json.dumps({
        "recentDestinations": [{"id": "Save as PDF", "origin": "local", "account": ""}],
        "selectedDestinationId": "Save as PDF",
        "version": 2
    })
}
options.add_experimental_option("prefs", prefs)

# --- FUNÇÃO DE IMPRESSÃO OTIMIZADA ---
def salvar_pdf(driver, nome_arquivo):
    print(f"   🖨️ PDF: {nome_arquivo}...", end="")
    try:
        # Tenta focar no frame da ficha antes de imprimir
        # A ficha geralmente abre num frame chamado 'ficha' ou similar
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            # Se tiver só 1 frame visível agora, deve ser a ficha
            if len(frames) == 1: driver.switch_to.frame(frames[0])
        except: pass

        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "landscape": False, 
            "displayHeaderFooter": False, 
            "printBackground": True,
            "paperWidth": 8.27, 
            "paperHeight": 11.69,
            "scale": 0.8, # Reduz um pouco para caber tudo e não cortar
            "marginTop": 0.4,
            "marginBottom": 0.4
        })
        with open(os.path.join(PASTA_DOWNLOAD, nome_arquivo), "wb") as f:
            f.write(base64.b64decode(pdf_data['data']))
        print(" OK!")
        return True
    except Exception as e:
        print(f" FALHA ({e})")
        return False

def limpar_nome_arquivo(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def encontrar_e_focar_frame_com_filtro(driver):
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "frame") + driver.find_elements(By.TAG_NAME, "iframe")
    
    if driver.find_elements(By.XPATH, "//select[.//option[contains(text(), 'Eletiva')]]"): return True

    for frame in frames:
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(frame)
            if driver.find_elements(By.XPATH, "//select[.//option[contains(text(), 'Eletiva')]]"):
                return True
        except: pass
    return False

# --- SETUP ---
try:
    print(">> Inicializando...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    actions = ActionChains(driver) # Importante para Double Click
    
    # 1. LOGIN
    print(">> Login...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    try: wait.until(EC.presence_of_element_located((By.ID, "barraMenu")))
    except: print("⚠️ Menu demorou...")

    # 2. NAVEGAÇÃO
    print(">> Navegando...")
    driver.switch_to.default_content()
    time.sleep(2)

    try:
        menu_principal = driver.find_element(By.XPATH, "//*[@id='barraMenu']//a[contains(text(), 'Consultas') or contains(text(), 'Relatórios')]")
        driver.execute_script("arguments[0].click();", menu_principal)
        time.sleep(1)
        submenu = driver.find_element(By.XPATH, "//a[contains(text(), 'AIH Gerada')]")
        driver.execute_script("arguments[0].click();", submenu)
    except:
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/cons_aih_gerada")

    time.sleep(5)

    # 3. FILTRO
    print(">> Filtro: Eletiva...")
    if not encontrar_e_focar_frame_com_filtro(driver):
        driver.refresh(); time.sleep(5); encontrar_e_focar_frame_com_filtro(driver)

    try:
        select_elem = driver.find_element(By.XPATH, "//select[.//option[contains(text(), 'Eletiva')]]")
        Select(select_elem).select_by_visible_text("Eletiva")
    except: pass

    try: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
    except: print("❌ Botão Pesquisar sumiu!")

    time.sleep(8)

    # 4. LOOP
    pagina_atual = 1
    
    while True:
        print(f"\n>>> PROCESSANDO PÁGINA {pagina_atual} <<<")
        encontrar_e_focar_frame_com_filtro(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        linhas = driver.find_elements(By.XPATH, "//table[contains(@class, 'lista')]//tr[td] | //form//table//tr[@onmouseover]")
        qtd_total = len(linhas)
        registros_pagina = 0

        print(f">> Linhas: {qtd_total}")
        if qtd_total == 0: break

        for i in range(qtd_total):
            try:
                encontrar_e_focar_frame_com_filtro(driver)
                linhas_at = driver.find_elements(By.XPATH, "//table[contains(@class, 'lista')]//tr[td] | //form//table//tr[@onmouseover]")
                if i >= len(linhas_at): break
                
                linha = linhas_at[i]
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 3: continue 
                registros_pagina += 1
                
                txt = linha.text
                match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', txt)
                aih = match_aih.group(0) if match_aih else f"REG_{i}"
                nome = limpar_nome_arquivo(colunas[2].text) if len(colunas) > 2 else "PACIENTE"

                print(f"[{i+1}] {aih}...", end="")
                
                # Highlight para debug visual
                driver.execute_script("arguments[0].style.backgroundColor = 'yellow';", linha)

                # --- AÇÃO CORRIGIDA: CLIQUE DUPLO ---
                actions.double_click(linha).perform()
                time.sleep(2)

                # Tenta clicar no botão ficha (caso o double click não tenha aberto direto)
                try:
                    btn_ficha = driver.find_element(By.ID, "fichaInternacao")
                    if btn_ficha.is_displayed():
                        btn_ficha.click()
                except: pass
                
                time.sleep(4) # Espera carregar

                # PDF
                salvar_pdf(driver, f"AIH_{aih}_{nome}.pdf")

                # Voltar
                encontrar_e_focar_frame_com_filtro(driver)
                try: driver.find_element(By.XPATH, "//input[@value='VOLTAR']").click()
                except: driver.back()
                time.sleep(3)

            except Exception as e:
                print(f"❌ Erro: {e}")
                driver.back(); time.sleep(2)

        if registros_pagina == 0: break

        # Paginação
        print(f">> Próxima...")
        encontrar_e_focar_frame_com_filtro(driver)
        try:
            btn_prox = driver.find_elements(By.XPATH, "//img[contains(@src, 'prox')]/parent::a")
            if btn_prox:
                driver.execute_script("arguments[0].click();", btn_prox[0])
                time.sleep(8)
                pagina_atual += 1
            else:
                print("⚠️ Fim.")
                break
        except: break

    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")