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

print(f"--- 2. AUTOMAÇÃO SISREG (V16 - EXPANSÃO NUCLEAR) ---")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- ATUALIZE AQUI
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

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

# Opções Padrão
options = webdriver.ChromeOptions()
options.add_argument("--disable-print-preview")
options.add_argument("--start-maximized")

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
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

    try: driver.find_element(By.NAME, "enviar").click()
    except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()

    time.sleep(5) 
    print(">> Rolando página...")
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
            
            # Nome do Arquivo
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
            
            time.sleep(4) 

            # --- O PULO DO GATO NUCLEAR: FORÇAR TUDO A SE EXPANDIR ---
            print("   -> Aplicando expansão forçada de layout...")
            
            driver.execute_script("""
                // 1. Oculta menus e imagens desnecessárias
                var style = document.createElement('style');
                style.innerHTML = `
                    #barraMenu, .noprint, input, img, .td_titulo_botoes { display: none !important; }
                    * { overflow: visible !important; height: auto !important; max-height: none !important; }
                `;
                document.head.appendChild(style);

                // 2. Varre todos os elementos e remove scroll
                var all = document.getElementsByTagName("*");
                for (var i=0, max=all.length; i < max; i++) {
                    all[i].style.overflow = "visible";
                }
            """)
            
            time.sleep(2) # Espera o layout "explodir"

            # --- GERAR PDF NATIVO ---
            print("   -> Gerando PDF Completo...")
            
            print_op = PrintOptions()
            print_op.format = 'A4'
            print_op.background = True
            # print_op.scale = 0.8 # DICA: Se ainda cortar, descomente essa linha para reduzir o zoom
            
            pdf_b64 = driver.print_page(print_op)
            
            caminho_pdf = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}.pdf")
            if os.path.exists(caminho_pdf): caminho_pdf = os.path.join(PASTA_DOWNLOAD, f"{nome_arquivo}_{int(time.time())}.pdf")

            with open(caminho_pdf, "wb") as f:
                f.write(base64.b64decode(pdf_b64))
            
            print(f"   ✅ PDF Salvo: {caminho_pdf}")

            # VOLTAR (Precisamos recarregar a página pois destruímos o layout)
            print("   -> Voltando (Recarregando)...")
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