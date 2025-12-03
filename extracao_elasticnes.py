import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-1\Elastic_Export"
PASTA_FINAL = "arquivos"
ARQUIVO_FINAL = "producao_detalhada.csv"

print("--- ROBÔ ELASTICNES (PRODUÇÃO - SEMI-AUTOMÁTICO) ---")

# --- 1. PREPARAÇÃO DA PASTA (BLINDADA CONTRA ERROS) ---
# Tenta limpar a pasta, mas se o OneDrive bloquear, segue a vida
if os.path.exists(PASTA_DOWNLOAD):
    try:
        # ignore_errors=True impede que o script pare se um arquivo estiver travado
        shutil.rmtree(PASTA_DOWNLOAD, ignore_errors=True)
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível limpar totalmente a pasta temporária. Continuando assim mesmo...")

# Cria a pasta se ela não existir (ou recria se foi apagada)
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

# --- 2. CONFIGURAÇÃO DO NAVEGADOR ---
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": PASTA_DOWNLOAD,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print(">> Acessando site...")
    driver.get("https://elasticnes.saude.gov.br/producao-consolidada")
    driver.maximize_window()
    
    # --- 3. INTERAÇÃO MANUAL ---
    print("\n🛑 PAUSA PARA AÇÃO MANUAL:")
    print("1. O navegador abriu.")
    print("2. Por favor, filtre MANUALMENTE:")
    print("   - Estado: Mato Grosso")
    print("   - Estabelecimento: Hospital Santa Helena")
    print("   - Competências: Jan a Nov (ou o período desejado)")
    print("3. Clique no botão de EXPORTAR (CSV).")
    print(">> O script está vigiando a pasta de download. Assim que o arquivo cair, ele assume.")
    
    # Loop infinito (com limite de segurança) esperando o arquivo aparecer
    tempo_espera = 0
    arquivo_encontrado = None
    
    while tempo_espera < 120: # Espera até 2 minutos você fazer o processo
        arquivos = [f for f in os.listdir(PASTA_DOWNLOAD) if f.endswith('.csv')]
        
        if arquivos:
            arquivo_encontrado = arquivos[0]
            # Verifica se o arquivo terminou de baixar (tamanho > 0 e não é .crdownload)
            if not arquivo_encontrado.endswith('.crdownload'):
                print(f"\n✅ Arquivo detectado: {arquivo_encontrado}")
                break
        
        time.sleep(2)
        tempo_espera += 2
        
    if not arquivo_encontrado:
        print("\n❌ Tempo esgotado! Nenhum arquivo foi baixado.")
        driver.quit()
        exit()

    # Espera mais um pouco só para garantir que o download finalizou a gravação no disco
    time.sleep(3)

    # --- 4. MOVER ARQUIVO ---
    origem = os.path.join(PASTA_DOWNLOAD, arquivo_encontrado)
    destino = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
    
    # Se já existir um arquivo antigo lá, apaga para substituir
    if os.path.exists(destino):
        try:
            os.remove(destino)
        except:
            pass

    shutil.move(origem, destino)
    print(f"✅ Arquivo movido com sucesso para: {destino}")
    print(">> Agora abra este arquivo no Excel e veja se as colunas 'Valor Profissional' e 'Valor Hospitalar' existem.")

except Exception as e:
    print(f"\n❌ Erro Geral: {e}")

finally:
    # Fecha o navegador
    try:
        driver.quit()
    except:
        pass