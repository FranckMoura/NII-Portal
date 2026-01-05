import time
import os
import glob
import shutil
import calendar
import subprocess
import sys
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Tenta importar o gerenciador de upload
try:
    sys.path.append(os.getcwd()) # Garante que acha o arquivo na pasta raiz
    import upload_manager
    TEM_UPLOAD_MANAGER = True
except ImportError:
    TEM_UPLOAD_MANAGER = False
    print("⚠️ AVISO: upload_manager.py não encontrado. O processamento de dados será pulado.")

print(f"--- 🔄 EXTRAÇÃO SISREG + ATUALIZAÇÃO PORTAL (V19 - FULL) ---")

# --- CONFIGURAÇÕES ---
USUARIO = "046FRANCK"
SENHA = "515462" # <--- VERIFIQUE SUA SENHA
# Define a pasta exata onde os arquivos serão salvos
PASTA_RAIZ = os.getcwd()
PASTA_DOWNLOAD = os.path.join(PASTA_RAIZ, "SISREG_Export")

if not os.path.exists(PASTA_DOWNLOAD): os.makedirs(PASTA_DOWNLOAD)

# Limpa a pasta de downloads antes de começar para evitar confusão
for f in glob.glob(os.path.join(PASTA_DOWNLOAD, "*.csv")):
    os.remove(f)

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

# --- FUNÇÃO AUXILIAR: Mapeia abreviação de mês ---
meses_map = {
    1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr', 5: 'mai', 6: 'jun',
    7: 'jul', 8: 'ago', 9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
}

def esperar_download_e_renomear(pasta, mes, ano):
    """
    Espera um novo arquivo .csv aparecer na pasta e renomeia ele imediatamente
    para o formato padrão que o portal entende.
    """
    print("   ⏳ Aguardando download finalizar...")
    tempo_esgotado = 0
    while tempo_esgotado < 60:
        # Busca arquivos CSV recentes que não tenham o nome 'extracao_sisreg'
        arquivos = [f for f in glob.glob(os.path.join(pasta, "*.csv")) if "extracao_sisreg" not in f]
        
        if arquivos:
            arquivo_recente = max(arquivos, key=os.path.getctime)
            # Verifica se o arquivo terminou de baixar (não é .crdownload)
            if not arquivo_recente.endswith(".crdownload"):
                nome_padrao = f"extracao_sisreg_{meses_map[mes]}_{ano}.csv"
                destino = os.path.join(pasta, nome_padrao)
                
                # Remove se já existir um antigo com esse nome
                if os.path.exists(destino): os.remove(destino)
                
                shutil.move(arquivo_recente, destino)
                print(f"   ✅ Arquivo renomeado para: {nome_padrao}")
                return True
        
        time.sleep(1)
        tempo_esgotado += 1
    
    print("   ❌ Erro: Download demorou demais ou falhou.")
    return False

# --- FLUXO PRINCIPAL ---
try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    # 1. LOGIN
    print(">> Fazendo Login...")
    driver.get("https://sisregiii.saude.gov.br/")
    
    # Lógica de Login (Adaptada do seu V18)
    driver.execute_script(f"document.getElementsByName('usuario')[0].value = '{USUARIO}'")
    driver.execute_script(f"document.getElementsByName('senha')[0].value = '{SENHA}'")
    driver.execute_script("document.getElementsByName('entrar')[0].click()")
    
    # Espera carregar e escolhe perfil se necessário
    time.sleep(3)
    try:
        if "Escolha um perfil" in driver.page_source:
            driver.execute_script("document.getElementsByTagName('a')[0].click()")
    except: pass

    # 2. NAVEGAR PARA AMBULATORIAL -> RELATORIOS -> SOLICITAÇÕES
    print(">> Navegando para Exportação...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/relatorios/solicitacoes_co.pl")

    # 3. LOOP DE DOWNLOAD (Últimos 4 meses)
    print(">> Iniciando ciclo de downloads...")
    data_atual = datetime.now()
    
    # Loop reverso: Mês atual, Mês passado, etc.
    for i in range(3, -1, -1):
        data_ref = data_atual - timedelta(days=i*30)
        mes = data_ref.month
        ano = data_ref.year
        
        # Define datas inicio/fim
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        d1 = f"01/{mes:02d}/{ano}"
        d2 = f"{ultimo_dia}/{mes:02d}/{ano}"
        
        print(f"\n>> Processando: {d1} a {d2}")

        # Recarrega a página para limpar filtros
        driver.refresh()
        time.sleep(2)

        try:
            # Preenche Datas
            driver.execute_script(f"document.getElementsByName('dtaIniSolic')[0].value = '{d1}'")
            driver.execute_script(f"document.getElementsByName('dtaFimSolic')[0].value = '{d2}'")

            # Marca Checkboxes
            driver.execute_script("""
                var inputs = document.getElementsByTagName('input');
                for(var i=0; i<inputs.length; i++) {
                    if(inputs[i].type == 'checkbox') inputs[i].checked = true;
                }
            """)
            
            # Clica em Exportar
            print("   (Solicitando...)")
            driver.execute_script("if(typeof exportar == 'function') { exportar(); } else { document.getElementsByName('exp')[0].click(); }")

            # Lida com alertas
            try:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except: pass
            
            # --- O PULO DO GATO: Espera e Renomeia ---
            esperar_download_e_renomear(PASTA_DOWNLOAD, mes, ano)

        except Exception as e:
            print(f"   ❌ Erro ao baixar período: {e}")

    print("\n>> Fechando navegador...")
    driver.quit()

    # 4. PROCESSAMENTO DE DADOS (Upload Manager)
    if TEM_UPLOAD_MANAGER:
        print("\n" + "="*40)
        print("📊 2. PROCESSANDO DADOS (ATUALIZANDO BANCO DE DADOS)")
        print("="*40)
        try:
            # Chama a função principal do seu upload_manager
            upload_manager.processar_arquivos() 
            print("✅ Banco de dados atualizado com sucesso!")
        except AttributeError:
            # Caso o upload_manager não tenha a função exata, tentamos rodar como script
            print("⚠️ Executando upload_manager como script...")
            subprocess.run([sys.executable, "upload_manager.py"], check=True)

    # 5. SINCRONIZAÇÃO GIT
    print("\n" + "="*40)
    print("☁️ 3. ENVIANDO PARA O PORTAL (GIT PUSH)")
    print("="*40)
    
    comandos = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"Atualizacao SISREG automatica {datetime.now().strftime('%d/%m/%Y')}"],
        ["git", "push"]
    ]
    
    for cmd in comandos:
        print(f"Executando: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=PASTA_RAIZ, shell=True)

    print("\n✅✅ CICLO COMPLETO FINALIZADO! O PORTAL DEVE ATUALIZAR EM BREVE.")

except Exception as e:
    print(f"\n❌ ERRO FATAL: {e}")