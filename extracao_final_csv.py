import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 🏥 EXTRAÇÃO TABNET V13 (MODO CSV PURO) ---")

CNES_ALVO = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

options = webdriver.ChromeOptions()
# options.add_argument("--headless") # Se quiser rodar escondido, descomente
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
    
    # Mapeia total de meses
    select_periodos = Select(driver.find_element(By.ID, "A"))
    total_opcoes = len(select_periodos.options)
    indices = list(range(total_opcoes))

    print(f">> Iniciando reparo de {total_opcoes} meses com formato CSV (;)...")

    for idx_loop, i in enumerate(indices):
        try:
            # Garante foco na janela principal
            if driver.current_window_handle != janela_principal:
                driver.switch_to.window(janela_principal)

            # --- 1. FILTROS ---
            Select(driver.find_element(By.ID, "L")).select_by_visible_text("Procedimento")
            try: Select(driver.find_element(By.ID, "C")).select_by_visible_text("--Não-Ativa--")
            except: Select(driver.find_element(By.ID, "C")).select_by_index(0)

            # Indicadores
            select_conteudo = Select(driver.find_element(By.ID, "I"))
            driver.execute_script("var options = document.getElementById('I').options; for(var i=0; i<options.length; i++) { options[i].selected = false; }")
            for termo in ["aprovadas", "Valor total", "perman", "bitos", "mortalidade"]:
                for opt in select_conteudo.options:
                    if termo.lower() in opt.text.lower():
                        driver.execute_script("arguments[0].selected = true;", opt)
                        break

            # Hospital (Expandir e Selecionar)
            try:
                if not driver.find_element(By.ID, "S7").is_displayed():
                    driver.find_element(By.ID, "fig7").click()
                    time.sleep(0.5)
            except: pass

            script_busca = f"var s=document.getElementById('S7'); for(var i=0;i<s.length;i++){{ if(s.options[i].text.indexOf('{CNES_ALVO}')>-1){{ s.selectedIndex=i; return true; }} }} return false;"
            driver.execute_script(script_busca)

            # Seleciona Data
            select_periodos = Select(driver.find_element(By.ID, "A"))
            driver.execute_script("var options = document.getElementById('A').options; for(var i=0; i<options.length; i++) { options[i].selected = false; }")
            nome_mes = select_periodos.options[i].text.strip().replace("/", "-")
            driver.execute_script(f"document.getElementById('A').options[{i}].selected = true;")
            
            # --- 2. O TRUQUE: FORÇAR FORMATO CSV (;) ---
            # Clica no radio button "Colunas separadas por ';'"
            # Geralmente é o input com value 'scsv' ou baseado no texto do label
            try:
                # Tenta pelo texto do label (mais seguro)
                driver.find_element(By.XPATH, "//label[contains(text(), ';')]").click()
            except:
                # Fallback se falhar
                try: driver.find_element(By.XPATH, "//input[@value='scsv']").click()
                except: print("   ⚠️ Aviso: Não foi possível selecionar formato CSV. Tentando padrão...")

            print(f"   ⬇️ [{idx_loop+1}/{total_opcoes}] Baixando: {nome_mes}...")

            # Clica Mostra
            janelas_antes = driver.window_handles
            driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
            time.sleep(2)

            # --- 3. CAPTURA DO CONTEÚDO ---
            # Quando selecionamos CSV, o TabNet geralmente abre o texto direto ou baixa um arquivo.
            
            conteudo_csv = ""
            sucesso = False
            
            # Verifica se abriu nova janela com o texto
            janelas_depois = driver.window_handles
            if len(janelas_depois) > len(janelas_antes):
                nova_janela = [j for j in janelas_depois if j not in janelas_antes][0]
                driver.switch_to.window(nova_janela)
                
                # Pega o texto da página (Body ou Pre)
                conteudo_csv = driver.find_element(By.TAG_NAME, "body").text
                
                if ";" in conteudo_csv and "Procedimento" in conteudo_csv:
                    sucesso = True
                    driver.close()
                    driver.switch_to.window(janela_principal)
            
            # Se não abriu janela, talvez tenha baixado um arquivo .csv ou .scsv
            if not sucesso:
                time.sleep(2) # Espera download
                lista = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.*")) # Pega qualquer extensão
                if lista:
                    recente = max(lista, key=os.path.getctime)
                    if (time.time() - os.path.getctime(recente)) < 10:
                        # Lê o arquivo baixado
                        with open(recente, 'r', encoding='latin-1') as f:
                            conteudo_csv = f.read()
                        sucesso = True
                        os.remove(recente) # Vamos salvar com o nome certo depois

            # --- 4. SALVAR ARQUIVO LIMPO ---
            if sucesso and conteudo_csv:
                caminho_final = os.path.join(PASTA_DOWNLOAD, f"tabnet_{CNES_ALVO}_{nome_mes}.csv")
                with open(caminho_final, 'w', encoding='latin-1') as f:
                    f.write(conteudo_csv)
                print(f"      ✅ Salvo CSV Puro!")
            else:
                print(f"      ❌ Falha ao capturar dados de {nome_mes}")
                # Volta se necessário
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(janela_principal)
                else:
                    driver.back()

            time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Erro no loop {i}: {e}")
            try: driver.switch_to.window(janela_principal)
            except: pass
            driver.get(URL_TABNET)
            time.sleep(3)

    print("\n✅ Extração Corrigida Finalizada!")
    driver.quit()

except Exception as e:
    print(f"❌ Erro Crítico: {e}")