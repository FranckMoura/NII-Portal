import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 🏥 EXTRAÇÃO TABNET V12 (HISTÓRICO COMPLETO 2008-2025) ---")

CNES_ALVO = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Limpeza opcional (se quiser apagar os testes anteriores, descomente abaixo)
# for f in glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv")): try: os.remove(f) except: pass

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_DOWNLOAD, "directory_upgrade": True}
options.add_experimental_option("prefs", prefs)

def garantir_hospital_selecionado(driver):
    """Garante que o Hospital Santa Helena está marcado."""
    try:
        try:
            if not driver.find_element(By.ID, "S7").is_displayed():
                driver.find_element(By.ID, "fig7").click()
                time.sleep(0.5)
        except: pass

        script_busca = f"""
        var select = document.getElementById('S7');
        for (var i = 0; i < select.options.length; i++) {{
            if (select.options[i].text.indexOf('{CNES_ALVO}') > -1) {{
                select.selectedIndex = i;
                return true;
            }}
        }}
        return false;
        """
        driver.execute_script(script_busca)
        return True
    except: return False

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    driver.get(URL_TABNET)
    driver.maximize_window()
    time.sleep(3)

    janela_principal = driver.current_window_handle

    # --- MAPEAMENTO TOTAL ---
    select_periodos = Select(driver.find_element(By.ID, "A"))
    total_opcoes = len(select_periodos.options)
    
    # PEGA TUDO! (Removemos o limite de 24 meses)
    indices = list(range(total_opcoes))

    print(f">> 📅 PERÍODO DETECTADO: {total_opcoes} meses disponíveis.")
    print(f">> Inciando extração completa (Isso pode levar cerca de 1 hora)...")

    for idx_loop, i in enumerate(indices):
        try:
            # Recupera foco
            if driver.current_window_handle != janela_principal:
                driver.switch_to.window(janela_principal)
            
            # --- FILTROS ---
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
            
            garantir_hospital_selecionado(driver)

            # --- SELEÇÃO DA DATA ---
            select_periodos = Select(driver.find_element(By.ID, "A"))
            driver.execute_script("var options = document.getElementById('A').options; for(var i=0; i<options.length; i++) { options[i].selected = false; }")
            
            nome_mes = select_periodos.options[i].text.strip().replace("/", "-")
            driver.execute_script(f"document.getElementById('A').options[{i}].selected = true;")
            
            print(f"   ⬇️ [{idx_loop+1}/{total_opcoes}] Processando: {nome_mes}...")

            # --- ENVIO ---
            janelas_antes = driver.window_handles
            driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
            time.sleep(3) 
            
            janelas_depois = driver.window_handles
            if len(janelas_depois) > len(janelas_antes):
                nova_janela = [j for j in janelas_depois if j not in janelas_antes][0]
                driver.switch_to.window(nova_janela)
            
            # --- DOWNLOAD ---
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # XPath Exato validado
                link_csv = driver.find_element(By.XPATH, "/html/body/div/div/div[3]/table/tbody/tr/td[1]/a")
                link_csv.click()
                
                # Espera arquivo
                timeout = 10
                inicio = time.time()
                sucesso = False
                while time.time() - inicio < timeout:
                    lista = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv"))
                    if lista:
                        recente = max(lista, key=os.path.getctime)
                        if (time.time() - os.path.getctime(recente)) < 15 and "tabnet_" not in recente:
                            novo = os.path.join(PASTA_DOWNLOAD, f"tabnet_{CNES_ALVO}_{nome_mes}.csv")
                            if os.path.exists(novo): os.remove(novo)
                            os.rename(recente, novo)
                            print(f"      ✅ Arquivo salvo!")
                            sucesso = True
                            break
                    time.sleep(1)
                
                if not sucesso:
                    print("      ⚠️ Download não iniciado (provavelmente sem dados).")

            except Exception as e:
                print(f"      ⚠️ Erro na tela de dados (mês vazio?): {e}")

            # --- LIMPEZA ---
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(janela_principal)
            else:
                driver.back()
                wait.until(EC.presence_of_element_located((By.ID, "L")))

            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Erro no loop {i}: {e}")
            try: driver.switch_to.window(janela_principal)
            except: pass
            driver.get(URL_TABNET)
            time.sleep(3)

    print("\n✅ EXTRAÇÃO COMPLETA DE 2008 A 2025 FINALIZADA!")
    driver.quit()

except Exception as e:
    print(f"❌ Erro Crítico: {e}")