import time
import os
import json
import base64
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.print_page_options import PrintOptions
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V13 - IMPRESSÃO NATIVA) ---")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- FUNÇÃO DE LIMPEZA DE NOME (Para o arquivo) ---
def limpar_nome_arquivo(texto):
    # Remove caracteres proibidos no Windows e espaços extras
    limpo = re.sub(r'[\\/*?:"<>|]', "", texto)
    return limpo.strip()

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

# Opções simplificadas (Não precisa mais de Kiosk Printing nas prefs)
options = webdriver.ChromeOptions()
options.add_argument("--disable-print-preview")

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

    # --- TABELA ---
    tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
    if not tabelas:
        print("❌ Tabela não encontrada."); driver.quit(); exit()
    
    tabela_dados = tabelas[-1]
    linhas_totais = tabela_dados.find_elements(By.TAG_NAME, "tr")
    qtd_total = len(linhas_totais)
    print(f">> Encontrados {qtd_total} registros.")

    pacientes_processados = 0
    
    for i in range(qtd_total):
        try:
            # Re-localiza
            tabelas = driver.find_elements(By.CLASS_NAME, "table_listagem")
            tabela_dados = tabelas[-1]
            linhas = tabela_dados.find_elements(By.TAG_NAME, "tr")
            
            if i >= len(linhas): break
            linha = linhas[i]

            if "td_titulo_campo" in linha.get_attribute("innerHTML"): continue

            colunas = linha.find_elements(By.TAG_NAME, "td")
            if len(colunas) < 4: continue

            pacientes_processados += 1
            
            # Tenta pegar o nome do paciente para o arquivo
            nome_arquivo = f"Ficha_{pacientes_processados}"
            alvo_clique = colunas[1]
            
            for col in colunas:
                txt = col.text.strip()
                if len(txt) > 3:
                    alvo_clique = col
                    # Se parecer um nome (letras), usa no arquivo
                    if not txt[0].isdigit():
                        nome_arquivo = limpar_nome_arquivo(txt)
                    break
            
            print(f"\n--- Paciente #{pacientes_processados}: {nome_arquivo} ---")
            
            # Clica
            driver.execute_script("arguments[0].scrollIntoView(true);", alvo_clique)
            time.sleep(1)
            try: alvo_clique.click()
            except: driver.execute_script("arguments[0].click();", alvo_clique)
            
            time.sleep(4) # Carrega ficha

            # --- GERAÇÃO DE PDF NATIVA (SEM TRAVAR) ---
            print("   -> Gerando PDF via Selenium...")
            
            try:
                # Configurações do PDF
                print_op = PrintOptions()
                print_op.format = 'A4'
                
                # O Pulo do Gato: Gera o base64 sem abrir janela
                pdf_b64 = driver.print_page(print_op)
                
                # Salva o arquivo
                caminho_completo = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}.pdf")
                
                # Se já existir, adiciona numero para não substituir
                if os.path.exists(caminho_completo):
                    caminho_completo = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}_{int(time.time())}.pdf")

                with open(caminho_completo, "wb") as f:
                    f.write(base64.b64decode(pdf_b64))
                
                print(f"   ✅ Salvo em: {caminho_completo}")

            except Exception as e:
                print(f"   ❌ Erro ao gerar PDF: {e}")

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