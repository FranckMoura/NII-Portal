import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 🏥 EXTRAÇÃO TABNET V14 (COLETOR TOTAL - TODAS AS COLUNAS) ---")

CNES_ALVO = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Limpeza opcional: Remove os arquivos "pobres" antigos para não misturar
# print(">> Limpando arquivos antigos...")
# for f in glob.glob(os.path.join(PASTA_DOWNLOAD, "tabnet_*.csv")):
#     try: os.remove(f)
#     except: pass

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_DOWNLOAD}
options.add_experimental_option("prefs", prefs)

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.get(URL_TABNET)
    driver.maximize_window()
    time.sleep(3)

    janela_principal = driver.current_window_handle
    
    # Mapeia meses
    select_periodos = Select(driver.find_element(By.ID, "A"))
    total_opcoes = len(select_periodos.options)
    indices = list(range(total_opcoes))

    print(f">> Iniciando extração RICA de {total_opcoes} meses...")

    for idx_loop, i in enumerate(indices):
        try:
            if driver.current_window_handle != janela_principal:
                driver.switch_to.window(janela_principal)

            # 1. LINHA: Procedimento
            Select(driver.find_element(By.ID, "L")).select_by_visible_text("Procedimento")
            
            # 2. COLUNA: Não Ativa
            try: Select(driver.find_element(By.ID, "C")).select_by_visible_text("--Não-Ativa--")
            except: Select(driver.find_element(By.ID, "C")).select_by_index(0)

            # 3. CONTEÚDO: SELECIONAR TUDO (O GRANDE SEGREDO) 💎
            # Executa JS para marcar todas as opções da lista de conteúdo
            driver.execute_script("""
                var options = document.getElementById('I').options;
                for(var j=0; j<options.length; j++) {
                    options[j].selected = true;
                }
            """)

            # 4. HOSPITAL
            try:
                if not driver.find_element(By.ID, "S7").is_displayed():
                    driver.find_element(By.ID, "fig7").click()
            except: pass
            
            script_busca = f"var s=document.getElementById('S7'); for(var k=0;k<s.length;k++){{ if(s.options[k].text.indexOf('{CNES_ALVO}')>-1){{ s.selectedIndex=k; return true; }} }} return false;"
            driver.execute_script(script_busca)

            # 5. DATA
            select_periodos = Select(driver.find_element(By.ID, "A"))
            driver.execute_script("var options = document.getElementById('A').options; for(var k=0; k<options.length; k++) { options[k].selected = false; }")
            nome_mes = select_periodos.options[i].text.strip().replace("/", "-")
            driver.execute_script(f"document.getElementById('A').options[{i}].selected = true;")
            
            # 6. FORMATO: CSV (;)
            try: driver.find_element(By.XPATH, "//label[contains(text(), ';')]").click()
            except: 
                try: driver.find_element(By.XPATH, "//input[@value='scsv']").click()
                except: pass

            print(f"   ⬇️ [{idx_loop+1}/{total_opcoes}] Baixando RICO: {nome_mes}...")

            # MOSTRA
            janelas_antes = driver.window_handles
            driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
            time.sleep(2)

            # CAPTURA
            sucesso = False
            conteudo_csv = ""
            
            # Verifica nova janela (Texto direto)
            janelas_depois = driver.window_handles
            if len(janelas_depois) > len(janelas_antes):
                nova_janela = [j for j in janelas_depois if j not in janelas_antes][0]
                driver.switch_to.window(nova_janela)
                conteudo_csv = driver.find_element(By.TAG_NAME, "body").text
                if "Procedimento" in conteudo_csv:
                    sucesso = True
                    driver.close()
                    driver.switch_to.window(janela_principal)
            
            # Verifica download de arquivo
            if not sucesso:
                time.sleep(3)
                lista = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.*"))
                if lista:
                    recente = max(lista, key=os.path.getctime)
                    if (time.time() - os.path.getctime(recente)) < 15:
                        with open(recente, 'r', encoding='latin-1') as f:
                            conteudo_csv = f.read()
                        sucesso = True
                        try: os.remove(recente) 
                        except: pass

            # SALVA COM NOME PADRÃO
            if sucesso and conteudo_csv:
                # Remove linhas vazias extras
                conteudo_csv = "\n".join([line for line in conteudo_csv.split('\n') if line.strip() != ''])
                
                caminho_final = os.path.join(PASTA_DOWNLOAD, f"tabnet_{CNES_ALVO}_{nome_mes}.csv")
                with open(caminho_final, 'w', encoding='latin-1') as f:
                    f.write(conteudo_csv)
            else:
                print(f"      ❌ Falha no download de {nome_mes}")
                if len(driver.window_handles) > 1: driver.close(); driver.switch_to.window(janela_principal)
                else: driver.back()

        except Exception as e:
            print(f"   ❌ Erro: {e}")
            driver.get(URL_TABNET)
            time.sleep(3)

    print("\n✅ EXTRAÇÃO RICA CONCLUÍDA!")
    driver.quit()
    
except Exception as e: print(f"❌ Erro Crítico: {e}")