import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 🏥 EXTRAÇÃO TABNET V11 (COM TROCA DE JANELAS INTELIGENTE) ---")

CNES_ALVO = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_DOWNLOAD, "directory_upgrade": True}
options.add_experimental_option("prefs", prefs)

def garantir_hospital_selecionado(driver):
    """Garante que o Hospital Santa Helena está marcado."""
    try:
        # Tenta expandir se necessário
        try:
            if not driver.find_element(By.ID, "S7").is_displayed():
                driver.find_element(By.ID, "fig7").click()
                time.sleep(0.5)
        except: pass

        # Busca e seleciona via JS
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

    # Identifica a janela principal (Formulário)
    janela_principal = driver.current_window_handle

    # Descobre quantos meses existem
    select_periodos = Select(driver.find_element(By.ID, "A"))
    total_periodos = len(select_periodos.options)
    
    # Define quantos meses baixar (últimos 24)
    qtd_meses = 24
    indices = list(range(min(total_periodos, qtd_meses)))

    print(f">> Iniciando ciclo para os últimos {len(indices)} meses...")

    for i in indices:
        try:
            # 1. Garante que estamos na janela do formulário
            if driver.current_window_handle != janela_principal:
                driver.switch_to.window(janela_principal)
            
            # 2. Configura Filtros (Reaplicação para garantir)
            Select(driver.find_element(By.ID, "L")).select_by_visible_text("Procedimento")
            try: Select(driver.find_element(By.ID, "C")).select_by_visible_text("--Não-Ativa--")
            except: Select(driver.find_element(By.ID, "C")).select_by_index(0)
            
            # Conteúdos Múltiplos (Correção solicitada)
            select_conteudo = Select(driver.find_element(By.ID, "I"))
            driver.execute_script("var options = document.getElementById('I').options; for(var i=0; i<options.length; i++) { options[i].selected = false; }")
            for termo in ["aprovadas", "Valor total", "perman", "bitos", "mortalidade"]:
                for opt in select_conteudo.options:
                    if termo.lower() in opt.text.lower():
                        driver.execute_script("arguments[0].selected = true;", opt)
                        break
            
            garantir_hospital_selecionado(driver)

            # 3. Seleciona o Mês
            select_periodos = Select(driver.find_element(By.ID, "A"))
            driver.execute_script("var options = document.getElementById('A').options; for(var i=0; i<options.length; i++) { options[i].selected = false; }")
            
            nome_mes = select_periodos.options[i].text.strip().replace("/", "-")
            driver.execute_script(f"document.getElementById('A').options[{i}].selected = true;")
            
            print(f"   ⬇️ Processando: {nome_mes}...")

            # 4. CLIQUE E DETECÇÃO DE NOVA JANELA
            janelas_antes = driver.window_handles
            driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
            time.sleep(3) # Tempo para a nova janela abrir
            
            janelas_depois = driver.window_handles
            
            # Se abriu nova janela, muda para ela
            if len(janelas_depois) > len(janelas_antes):
                nova_janela = [j for j in janelas_depois if j not in janelas_antes][0]
                driver.switch_to.window(nova_janela)
                # print("      (Mudou para nova aba de resultados)")
            
            # 5. TELA DE RESULTADOS E DOWNLOAD
            try:
                # Espera tabela
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                
                # Rola até o fim
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Busca botão pelo XPath Exato fornecido por você
                link_csv = driver.find_element(By.XPATH, "/html/body/div/div/div[3]/table/tbody/tr/td[1]/a")
                
                # Baixa
                link_csv.click()
                
                # Monitora o arquivo
                timeout = 10
                inicio = time.time()
                while time.time() - inicio < timeout:
                    lista = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv"))
                    if lista:
                        recente = max(lista, key=os.path.getctime)
                        if (time.time() - os.path.getctime(recente)) < 15 and "tabnet_" not in recente:
                            # Renomeia
                            novo = os.path.join(PASTA_DOWNLOAD, f"tabnet_{CNES_ALVO}_{nome_mes}.csv")
                            if os.path.exists(novo): os.remove(novo)
                            os.rename(recente, novo)
                            print(f"      ✅ Sucesso!")
                            break
                    time.sleep(1)

            except Exception as e:
                print(f"      ⚠️ Erro ao baixar (talvez mês vazio): {e}")

            # 6. FECHA JANELA DE RESULTADOS E VOLTA
            if len(driver.window_handles) > 1:
                driver.close() # Fecha a aba de resultados
                driver.switch_to.window(janela_principal) # Volta pro form
            else:
                driver.back() # Se for mesma janela, só volta
                wait.until(EC.presence_of_element_located((By.ID, "L")))

            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Erro no loop: {e}")
            # Tenta recuperar o foco na principal
            try: driver.switch_to.window(janela_principal)
            except: pass
            driver.get(URL_TABNET)
            time.sleep(3)

    print("\n✅ Extração Finalizada! Verifique a pasta TABNET_Export.")
    driver.quit()

except Exception as e:
    print(f"❌ Erro Crítico: {e}")