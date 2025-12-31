import time
import os
import calendar
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print(f"--- ⏳ EXTRAÇÃO HISTÓRICA SISREG (2019 - HOJE) ---")
print("⚠️ AVISO: Isso vai baixar muitos arquivos. Não feche a janela.")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" 
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# --- CONFIGURAÇÃO CHROME ---
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_setting_values.automatic_downloads": 1
}
options.add_experimental_option("prefs", prefs)

# --- FUNÇÃO GERADORA DE DATAS (2019 ATÉ HOJE) ---
def gerar_intervalos_historicos(ano_inicio=2019):
    intervalos = []
    hoje = datetime.now()
    ano_atual = ano_inicio
    mes_atual = 1

    while True:
        # Data Inicial do Mês
        dt_ini = datetime(ano_atual, mes_atual, 1)
        
        # Se passamos da data de hoje, para.
        if dt_ini > hoje:
            break

        # Último dia do mês
        ultimo_dia = calendar.monthrange(ano_atual, mes_atual)[1]
        dt_fim = datetime(ano_atual, mes_atual, ultimo_dia)

        # Se o fim do mês for no futuro (ex: fim do mês atual), limita a hoje
        if dt_fim > hoje:
            dt_fim = hoje

        intervalos.append((dt_ini, dt_fim))

        # Avança para o próximo mês
        mes_atual += 1
        if mes_atual > 12:
            mes_atual = 1
            ano_atual += 1
            
    # Inverte para baixar do mais recente para o mais antigo (opcional, mas legal de ver)
    return intervalos[::-1] 

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
    
    try:
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except:
        driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()

    # --- NAVEGAÇÃO VIA MENU (Robusta) ---
    print(">> Navegando para Exportação...")
    try:
        # Tenta clicar no menu Relatórios
        try:
            menu_rel = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a")))
            menu_rel.click()
        except:
            driver.execute_script("document.querySelector('#barraMenu > ul > li:nth-child(5) > a').click();")
        
        time.sleep(1)

        # Tenta clicar no submenu Exportação
        try:
            submenu = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a")))
            submenu.click()
        except:
            driver.execute_script("document.querySelector('#barraMenu > ul > li:nth-child(5) > ul > li:nth-child(3) > a').click();")
            
    except Exception as e:
        print(f"❌ Erro na navegação do menu: {e}")
        # Backup
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/rel_exportacao_solicitacoes_amb")

    time.sleep(5)

    # --- LOOP HISTÓRICO ---
    lista_periodos = gerar_intervalos_historicos(2019)
    total = len(lista_periodos)
    print(f"\n>> 🚀 INICIANDO DOWNLOAD DE {total} ARQUIVOS (DE 2019 ATÉ AGORA)...\n")

    for i, (dt_ini, dt_fim) in enumerate(lista_periodos):
        d1 = dt_ini.strftime("%d/%m/%Y")
        d2 = dt_fim.strftime("%d/%m/%Y")
        print(f">> [{i+1}/{total}] Baixando: {d1} a {d2}")

        # 1. ENCONTRAR O IFRAME
        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        iframe_found = False
        
        for idx in range(len(frames)):
            driver.switch_to.default_content()
            try:
                driver.switch_to.frame(idx)
                if len(driver.find_elements(By.NAME, "dtaIniSolic")) > 0:
                    iframe_found = True
                    break 
            except: pass
        
        if not iframe_found:
            print("   ⚠️ Frame perdido. Tentando recuperar...")
            driver.refresh()
            time.sleep(5)
            continue

        try:
            # 2. PREENCHER DATAS
            driver.execute_script(f"document.getElementsByName('dtaIniSolic')[0].value = '{d1}'")
            driver.execute_script(f"document.getElementsByName('dtaFimSolic')[0].value = '{d2}'")

            # 3. MARCAR CHECKBOXES
            driver.execute_script("""
                var inputs = document.getElementsByTagName('input');
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].type == 'checkbox') inputs[i].checked = true;
                }
            """)
            
            # 4. EXPORTAR
            print("   (Solicitando...)")
            driver.execute_script("if(typeof exportar == 'function') { exportar(); } else { document.getElementsByName('exp')[0].click(); }")

            # 5. ALERTAS
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except: pass
            
            print("   ✅ OK! Aguardando próximo...")
            # Pausa um pouco maior para não travar o SISREG pelo excesso de pedidos
            time.sleep(10) 

        except Exception as e:
            print(f"   ❌ Falha neste mês: {e}")

    print("\n>> 🏁 MISSÃO CUMPRIDA! TODOS OS ARQUIVOS FORAM BAIXADOS.")
    time.sleep(5)
    driver.quit()

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")
    if 'driver' in locals(): driver.quit()