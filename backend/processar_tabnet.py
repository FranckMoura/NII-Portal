import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 🏥 EXTRAÇÃO TABNET V15.1 (COLETOR SP - CORRIGIDO CNES) ---")

CNES_ALVO = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\tabnet_sp"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/spgmt.def"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

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
    
    select_periodos = Select(driver.find_element(By.ID, "A"))
    total_opcoes = len(select_periodos.options)
    indices = list(range(total_opcoes))

    print(f">> Iniciando extração DETALHADA de {total_opcoes} meses...")

    for idx_loop, i in enumerate(indices):
        try:
            if driver.current_window_handle != janela_principal:
                driver.switch_to.window(janela_principal)

            # 1. LINHA: Buscar inteligentemente por "Procedimento"
            select_linha = Select(driver.find_element(By.ID, "L"))
            for opt in select_linha.options:
                if "PROCEDIMENTO" in opt.text.upper():
                    select_linha.select_by_visible_text(opt.text)
                    break
            
            # 2. COLUNA: Não Ativa
            try: Select(driver.find_element(By.ID, "C")).select_by_visible_text("--Não-Ativa--")
            except: Select(driver.find_element(By.ID, "C")).select_by_index(0)

            # 3. CONTEÚDO: Seleciona Todas as colunas
            driver.execute_script("""
                var options = document.getElementById('I').options;
                for(var j=0; j<options.length; j++) {
                    options[j].selected = true;
                }
            """)

            # 4. HOSPITAL (A SUA LÓGICA ORIGINAL, MAS DINÂMICA)
            gaveta_cnes = None
            # Procura em qual 'S' (Select) o CNES do hospital está escondido
            for num in range(1, 15):
                script_procura = f"var s=document.getElementById('S{num}'); if(!s) return false; for(var k=0;k<s.length;k++){{ if(s.options[k].text.indexOf('{CNES_ALVO}')>-1) return true; }} return false;"
                tem_cnes = driver.execute_script(script_procura)
                if tem_cnes:
                    gaveta_cnes = num
                    break
            
            if gaveta_cnes:
                # Se a gaveta estiver fechada, clica no '+'
                try:
                    if not driver.find_element(By.ID, f"S{gaveta_cnes}").is_displayed():
                        driver.find_element(By.ID, f"fig{gaveta_cnes}").click()
                except: pass
                
                # A sua mágica original: Força o SelectedIndex
                script_busca = f"var s=document.getElementById('S{gaveta_cnes}'); for(var k=0;k<s.length;k++){{ if(s.options[k].text.indexOf('{CNES_ALVO}')>-1){{ s.selectedIndex=k; return true; }} }} return false;"
                driver.execute_script(script_busca)
            else:
                print("   ⚠️ ALERTA: CNES não encontrado na página! O download pode vir zerado ou de todo o estado.")

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

            print(f"   ⬇️ [{idx_loop+1}/{total_opcoes}] Baixando ITENS SECUNDÁRIOS: {nome_mes}...")

            janelas_antes = driver.window_handles
            driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
            time.sleep(2)

            sucesso = False
            conteudo_csv = ""
            
            janelas_depois = driver.window_handles
            if len(janelas_depois) > len(janelas_antes):
                nova_janela = [j for j in janelas_depois if j not in janelas_antes][0]
                driver.switch_to.window(nova_janela)
                conteudo_csv = driver.find_element(By.TAG_NAME, "body").text
                if "Procedimento" in conteudo_csv:
                    sucesso = True
                    driver.close()
                    driver.switch_to.window(janela_principal)
            
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

            if sucesso and conteudo_csv:
                conteudo_csv = "\n".join([line for line in conteudo_csv.split('\n') if line.strip() != ''])
                caminho_final = os.path.join(PASTA_DOWNLOAD, f"tabnet_sp_{CNES_ALVO}_{nome_mes}.csv")
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

    print("\n✅ EXTRAÇÃO DE PROCEDIMENTOS REALIZADOS (SP) CONCLUÍDA!")
    driver.quit()
    
except Exception as e: print(f"❌ Erro Crítico: {e}")