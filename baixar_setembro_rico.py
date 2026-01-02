import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 🏥 RESGATE CIRÚRGICO V2: SETEMBRO 2025 (COM PAUSAS) ---")

CNES_ALVO = "2311682"
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\TABNET_Export"
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"
MES_ALVO_TXT = "Set/2025" 

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_DOWNLOAD}
options.add_experimental_option("prefs", prefs)

try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL_TABNET)
    driver.maximize_window()
    time.sleep(4) # Espera carregar bem

    # 1. LINHA: Procedimento
    Select(driver.find_element(By.ID, "L")).select_by_visible_text("Procedimento")
    time.sleep(1) # Respira

    # 2. COLUNA: Não Ativa
    try: Select(driver.find_element(By.ID, "C")).select_by_visible_text("--Não-Ativa--")
    except: Select(driver.find_element(By.ID, "C")).select_by_index(0)
    time.sleep(1)

    # 3. CONTEÚDO: SELECIONAR TUDO (Modo Rico)
    print(">> Selecionando todas as colunas...")
    driver.execute_script("""
        var select = document.getElementById('I');
        for (var j = 0; j < select.options.length; j++) {
            select.options[j].selected = true;
        }
    """)
    time.sleep(2) # Espera o site processar a seleção múltipla

    # 4. HOSPITAL
    try: 
        fig7 = driver.find_element(By.ID, "fig7")
        if fig7.is_displayed(): fig7.click()
    except: pass
    time.sleep(1)
    
    print(f">> Buscando Hospital {CNES_ALVO}...")
    driver.execute_script(f"var s=document.getElementById('S7'); for(var k=0;k<s.length;k++){{ if(s.options[k].text.indexOf('{CNES_ALVO}')>-1){{ s.selectedIndex=k; }} }}")
    time.sleep(2)

    # 5. PERÍODO: SETEMBRO 2025
    print(f">> Selecionando Mês: {MES_ALVO_TXT}...")
    select_periodos = Select(driver.find_element(By.ID, "A"))
    
    # Desmarca tudo
    driver.execute_script("var s=document.getElementById('A'); for(var k=0; k<s.options.length; k++){s.options[k].selected=false;}")
    
    # Marca Setembro
    found = False
    for i, opt in enumerate(select_periodos.options):
        if MES_ALVO_TXT in opt.text:
            driver.execute_script(f"document.getElementById('A').options[{i}].selected = true;")
            found = True
            break
    
    if not found:
        print("❌ Mês não encontrado!")
        driver.quit(); exit()
    
    time.sleep(2) # Espera seleção

    # 6. FORMATO: CSV (;) - AQUI ESTAVA O ERRO
    print(">> Selecionando formato CSV...")
    try:
        # Tenta pelo texto do label (mais seguro)
        driver.find_element(By.XPATH, "//label[contains(text(), ';')]").click()
    except:
        try:
            # Tenta pelo valor do input
            driver.find_element(By.XPATH, "//input[@value='scsv']").click()
        except:
            print("⚠️ Aviso: Botão CSV não achado. Tentando seguir assim mesmo...")

    time.sleep(1)

    # 7. BAIXAR
    print(f">> Clicando em MOSTRA...")
    driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Mostra')]").click()
    
    # Espera o processamento (pode demorar 10s para arquivo grande)
    time.sleep(10)

    # 8. CAPTURA DO ARQUIVO
    # Se abriu janela de texto
    conteudo = ""
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
        conteudo = driver.find_element(By.TAG_NAME, "body").text
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    
    # Se baixou arquivo (o mais provável no modo CSV)
    if "Procedimento" not in conteudo:
        lista = glob.glob(os.path.join(PASTA_DOWNLOAD, "*.*"))
        if lista:
            recente = max(lista, key=os.path.getctime)
            # Verifica se o arquivo é novo (menos de 30s)
            if (time.time() - os.path.getctime(recente)) < 30:
                with open(recente, 'r', encoding='latin-1') as f:
                    conteudo = f.read()
                try: os.remove(recente)
                except: pass

    # 9. SALVA
    if "Procedimento" in conteudo:
        nome_final = os.path.join(PASTA_DOWNLOAD, "tabnet_2311682_Set-2025.csv")
        with open(nome_final, 'w', encoding='latin-1') as f:
            f.write(conteudo)
        print(f"✅ SUCESSO! Arquivo salvo: {nome_final}")
        
        # Validação Rápida
        if "Valor servi" in conteudo or "Val serv" in conteudo:
            print("   🌟 Qualidade: RICO (Contém colunas detalhadas)")
        else:
            print("   ⚠️ Qualidade: Pobre (Faltam colunas - Verifique o site)")
            
    else:
        print("❌ Falha: Conteúdo vazio ou erro no download.")

    driver.quit()

except Exception as e:
    print(f"❌ Erro: {e}")