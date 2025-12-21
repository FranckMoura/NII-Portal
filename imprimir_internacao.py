import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- 2. AUTOMAÇÃO SISREG (V6 - BOTÃO ENVIAR) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- COLOQUE SUA SENHA
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Fichas_Internacao"

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- CONFIGURAÇÃO KIOSK PRINTING ---
print_settings = {
    "recentDestinations": [{"id": "Save as PDF", "origin": "local", "account": ""}],
    "selectedDestinationId": "Save as PDF",
    "version": 2,
    "isHeaderFooterEnabled": False
}
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "printing.print_preview_sticky_settings.appState": json.dumps(print_settings),
    "savefile.default_directory": PASTA_DOWNLOAD
}
options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", prefs)
options.add_argument('--kiosk-printing')
options.add_argument("--disable-print-preview")

def get_datas_mes_atual():
    hoje = datetime.now()
    primeiro_dia = hoje.replace(day=1).strftime("%d/%m/%Y")
    dia_atual = hoje.strftime("%d/%m/%Y")
    return primeiro_dia, dia_atual

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
    # Menu 5
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
    time.sleep(1)
    # Submenu 1
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
    time.sleep(5)

    # --- FRAME ---
    print(">> Localizando Frame...")
    driver.switch_to.default_content()
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    iframe_target = None
    
    for i in range(len(frames)):
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(i)
            # Busca visual pelo texto
            if "Período da Solicitação" in driver.page_source or "Periodo da Solicitacao" in driver.page_source:
                iframe_target = i
                print(f"   ✅ Frame encontrado: {i}")
                break
        except: pass
    
    if iframe_target is None: iframe_target = 1 # Fallback
    driver.switch_to.default_content()
    driver.switch_to.frame(iframe_target)

    # --- PREENCHER DATAS ---
    dt_ini, dt_fim = get_datas_mes_atual()
    print(f">> Datas: {dt_ini} a {dt_fim}")
    
    try:
        # Tenta pegar os inputs que estão na mesma linha (tr) do texto "Período..."
        inputs_data = driver.find_elements(By.XPATH, "//*[contains(text(),'Período')]/ancestor::tr//input[@type='text']")
        if len(inputs_data) >= 2:
            inputs_data[0].clear(); inputs_data[0].send_keys(dt_ini)
            inputs_data[1].clear(); inputs_data[1].send_keys(dt_fim)
            print("   ✅ Datas preenchidas via âncora.")
        else:
            # Fallback manual se a âncora falhar (mas o log disse que funcionou)
            driver.find_element(By.NAME, "dtaIniSolic").send_keys(dt_ini)
            driver.find_element(By.NAME, "dtaFimSolic").send_keys(dt_fim)
    except Exception as e:
        print(f"   ❌ Erro Data: {e}")

    # --- PREENCHER STATUS (Melhoria) ---
    print(">> Status...")
    try:
        # Tenta achar QUALQUER select na página, já que o nome varia
        selects = driver.find_elements(By.TAG_NAME, "select")
        status_selecionado = False
        
        for sel in selects:
            try:
                s = Select(sel)
                # Verifica se este select tem a opção 'AUTORIZADO'
                for opt in s.options:
                    if "AUTORIZADO" in opt.text.upper() or "APROVADO" in opt.text.upper():
                        s.select_by_visible_text(opt.text)
                        print(f"   ✅ Filtro aplicado: {opt.text} (no combo '{sel.get_attribute('name')}')")
                        status_selecionado = True
                        break
                if status_selecionado: break
            except: pass
            
        if not status_selecionado: print("   ⚠️ Filtro 'Autorizado' não encontrado. Buscando tudo.")
    except:
        print("   ⚠️ Erro ao buscar selects.")

    # --- CLICAR EM PESQUISAR (CORREÇÃO FINAL) ---
    print(">> Clicando em PESQUISAR...")
    try:
        # Busca EXATA baseada no seu log de erro: name='enviar'
        btn_pesquisar = driver.find_element(By.NAME, "enviar")
        
        # Garante que está visível
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_pesquisar)
        time.sleep(1)
        
        # Clica via JS para garantir
        driver.execute_script("arguments[0].click();", btn_pesquisar)
        print("   ✅ Botão 'enviar' clicado com sucesso!")
        
    except Exception as e:
        print(f"   ❌ Erro ao clicar no botão 'enviar': {e}")
        # Tentativa desesperada: clicar no input com value='PESQUISAR'
        try:
            driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
            print("   ✅ Botão 'PESQUISAR' (Value) clicado.")
        except:
            raise Exception("Botão irrecuperável.")

    time.sleep(5) # Espera a tabela carregar

    # --- IMPRESSÃO ---
    print(">> Listando resultados...")
    
    # Tenta achar a tabela
    linhas = driver.find_elements(By.CSS_SELECTOR, "table.listagem tr")
    # Se não achou listagem, tenta tabela genérica com borda (comum no sisreg)
    if len(linhas) <= 1: 
        linhas = driver.find_elements(By.CSS_SELECTOR, "table[border='1'] tr")

    print(f">> Encontrados {len(linhas)-1} registros.")
    
    janela_principal = driver.current_window_handle
    count = 0

    for i in range(1, len(linhas)): # Pula cabeçalho
        try:
            linha = linhas[i]
            
            # Procura ícone de imprimir
            # 1. Tenta input image
            btns = linha.find_elements(By.CSS_SELECTOR, "input[src*='print']")
            # 2. Tenta imagem dentro de link
            if not btns: btns = linha.find_elements(By.CSS_SELECTOR, "a img[src*='print']")
            # 3. Tenta input com name='imprimir'
            if not btns: btns = linha.find_elements(By.CSS_SELECTOR, "input[name*='imprimir']")

            if btns:
                el = btns[0]
                # Se pegou a imagem dentro do link, sobe para o link
                if el.tag_name == 'img': 
                    try: el = el.find_element(By.XPATH, "./..")
                    except: pass
                
                print(f"   -> Imprimindo item {i}...")
                
                # Scroll e Click JS
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                try: el.click()
                except: driver.execute_script("arguments[0].click();", el)
                
                time.sleep(3) # Espera popup

                # Gerencia Popup
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    # Comando de impressão Kiosk
                    driver.execute_script("window.print();")
                    time.sleep(3) # Tempo para salvar
                    
                    driver.close() # Fecha popup
                    driver.switch_to.window(janela_principal)
                    
                    # Re-entra no frame
                    driver.switch_to.default_content()
                    driver.switch_to.frame(iframe_target)
                    count += 1
                else:
                    print("      ⚠️ Popup não abriu.")
            else:
                # Debug: mostra o que tem na linha se não achar botão
                # print(f"      [Debug] Linha {i} sem botão de print.") 
                pass

        except Exception as e:
            print(f"      ❌ Erro na linha {i}: {e}")
            # Recuperação de janela
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(janela_principal)
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe_target)

    print(f"✅ FIM! {count} impressões realizadas.")
    time.sleep(2)
    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")