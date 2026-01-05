import time
import os
import glob
import shutil
import subprocess
import sys
import calendar
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Tenta importar o gerenciador de upload
try:
    sys.path.append(os.getcwd())
    import upload_manager
    TEM_UPLOAD_MANAGER = True
except ImportError:
    TEM_UPLOAD_MANAGER = False
    print("⚠️ AVISO: upload_manager.py não encontrado.")

print(f"--- 1. EXTRAÇÃO SISREG + ATUALIZAÇÃO (V21 - BASE V18) ---")

# --- SUAS CREDENCIAIS ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- CONFIRA SUA SENHA AQUI
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export" 

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Limpa downloads antigos para não confundir
for f in glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv")):
    try: os.remove(f) 
    except: pass

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

# --- FUNÇÃO AUXILIAR: Renomear Arquivos ---
meses_map = {1:'jan', 2:'fev', 3:'mar', 4:'abr', 5:'mai', 6:'jun', 7:'jul', 8:'ago', 9:'set', 10:'out', 11:'nov', 12:'dez'}

def esperar_renomear(pasta, mes, ano):
    print("   ⏳ Aguardando e renomeando arquivo...")
    tempo = 0
    while tempo < 60:
        # Pega arquivos CSV que NÃO começam com 'extracao_sisreg' (são os novos)
        arquivos = [f for f in glob.glob(os.path.join(pasta, "*.csv")) if "extracao_sisreg" not in os.path.basename(f)]
        
        if arquivos:
            arquivo_recente = max(arquivos, key=os.path.getctime)
            if not arquivo_recente.endswith(".crdownload"):
                time.sleep(1) # Garante que soltou o arquivo
                novo_nome = f"extracao_sisreg_{meses_map[mes]}_{ano}.csv"
                destino = os.path.join(pasta, novo_nome)
                
                if os.path.exists(destino): os.remove(destino)
                try:
                    shutil.move(arquivo_recente, destino)
                    print(f"   ✅ Renomeado para: {novo_nome}")
                    return True
                except: pass
        time.sleep(1)
        tempo += 1
    print("   ❌ Erro: Arquivo não apareceu.")
    return False

# --- FUNÇÃO DATAS ---
def gerar_periodos_meses(qtd_meses_atras=3):
    periodos = []
    hoje = datetime.now()
    for i in range(qtd_meses_atras, -1, -1):
        mes_alvo = hoje.month - i
        ano_alvo = hoje.year
        while mes_alvo <= 0:
            mes_alvo += 12
            ano_alvo -= 1
        data_ini = datetime(ano_alvo, mes_alvo, 1)
        ultimo_dia = calendar.monthrange(ano_alvo, mes_alvo)[1]
        data_fim = datetime(ano_alvo, mes_alvo, ultimo_dia)
        periodos.append((data_ini, data_fim))
    return periodos

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

    # --- NAVEGAÇÃO VIA MENU (Seu código V18 Original) ---
    print(">> Navegando para Exportação...")
    try:
        try:
            menu_rel = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a")))
            menu_rel.click()
        except:
            driver.execute_script("document.querySelector('#barraMenu > ul > li:nth-child(5) > a').click();")
        
        time.sleep(1)

        try:
            submenu = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[3]/a")))
            submenu.click()
        except:
            driver.execute_script("document.querySelector('#barraMenu > ul > li:nth-child(5) > ul > li:nth-child(3) > a').click();")
            
    except Exception as e:
        print(f"❌ Erro menu: {e}")
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/rel_exportacao_solicitacoes_amb")

    time.sleep(5) 

    # --- LOOP DE DOWNLOADS ---
    lista_periodos = gerar_periodos_meses(3)
    print(f">> Iniciando download de {len(lista_periodos)} arquivos...")

    for dt_ini, dt_fim in lista_periodos:
        d1 = dt_ini.strftime("%d/%m/%Y")
        d2 = dt_fim.strftime("%d/%m/%Y")
        print(f"\n>> Baixando: {d1} a {d2}")

        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        iframe_found = False
        
        for i in range(len(frames)):
            driver.switch_to.default_content()
            try:
                driver.switch_to.frame(i)
                if len(driver.find_elements(By.NAME, "dtaIniSolic")) > 0:
                    iframe_found = True
                    break 
            except: pass
        
        if not iframe_found:
            print("   ❌ ERRO: Formulário não encontrado. Refresh...")
            driver.refresh()
            time.sleep(5)
            continue

        try:
            driver.execute_script(f"document.getElementsByName('dtaIniSolic')[0].value = '{d1}'")
            driver.execute_script(f"document.getElementsByName('dtaFimSolic')[0].value = '{d2}'")

            driver.execute_script("""
                var inputs = document.getElementsByTagName('input');
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].type == 'checkbox') inputs[i].checked = true;
                }
            """)
            
            print("   (Solicitando...)")
            driver.execute_script("if(typeof exportar == 'function') { exportar(); } else { document.getElementsByName('exp')[0].click(); }")

            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except: pass

            # --- AQUI ESTÁ A MÁGICA: RENOMEAR ---
            # Usa o mês/ano da data inicial (dt_ini) para nomear o arquivo
            esperar_renomear(PASTA_DOWNLOAD, dt_ini.month, dt_ini.year)

        except Exception as e:
            print(f"   ❌ Erro técnico: {e}")

    print(">> Downloads finalizados. Fechando navegador...")
    time.sleep(2)
    driver.quit()

    # --- PARTE 2: PROCESSAMENTO E UPLOAD (NOVA) ---
    
    if TEM_UPLOAD_MANAGER:
        print("\n" + "="*40)
        print("📊 2. PROCESSANDO DADOS (UPLOAD MANAGER)")
        print("="*40)
        try:
            upload_manager.processar_arquivos()
            print("✅ Banco de dados atualizado!")
        except Exception as e:
            print(f"⚠️ Erro ao chamar função interna: {e}")
            subprocess.run([sys.executable, "upload_manager.py"], check=True)

    print("\n" + "="*40)
    print("☁️ 3. ENVIANDO PARA O PORTAL (GIT)")
    print("="*40)
    
    pasta_raiz = os.getcwd()
    subprocess.run("git add .", shell=True, cwd=pasta_raiz)
    subprocess.run(f'git commit -m "Atualizacao SISREG via V21 {datetime.now()}"', shell=True, cwd=pasta_raiz)
    subprocess.run("git push", shell=True, cwd=pasta_raiz)

    print("\n✅✅ SUCESSO TOTAL! DADOS ENVIADOS.")

except Exception as e:
    print(f"❌ ERRO GERAL: {e}")