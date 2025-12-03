import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
URL_TABNET = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/qgmt.def"
MEU_CNES = "2311682"
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1\Tabnet_Export"
PASTA_FINAL = "arquivos"
ARQUIVO_FINAL = "tabnet_producao_detalhada.csv"
# Caminho padrão de Downloads do Windows (Fallback)
PASTA_DOWNLOADS_WIN = os.path.join(os.path.expanduser("~"), "Downloads")

print("--- ROBÔ TABNET V8 (DOWNLOAD BLINDADO) ---")

# Prepara pasta temporária
if os.path.exists(PASTA_PROJETO):
    try: shutil.rmtree(PASTA_PROJETO)
    except: pass
os.makedirs(PASTA_PROJETO, exist_ok=True)

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_PROJETO}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

try:
    print(">> Acessando TabNet...")
    driver.get(URL_TABNET)
    driver.maximize_window()
    wait.until(EC.presence_of_element_located((By.NAME, "Linha")))

    # --- 1. CONFIGURAÇÕES ---
    print(">> Configurando Tabela...")
    # JS para selecionar sem erro de acentuação
    driver.execute_script("""
        var selects = document.getElementsByTagName('select');
        for(var i=0; i<selects.length; i++) {
            if(selects[i].name == 'Linha') {
                for(var j=0; j<selects[i].options.length; j++) {
                    if(selects[i].options[j].text.includes('Compet')) selects[i].options[j].selected = true;
                }
            }
            if(selects[i].name == 'Coluna') {
                for(var j=0; j<selects[i].options.length; j++) {
                    if(selects[i].options[j].text.includes('Procedimento realizado')) selects[i].options[j].selected = true;
                }
            }
        }
    """)

    print(">> Selecionando Valores...")
    driver.execute_script("""
        var opcoes = document.getElementsByName('Incremento')[0].options;
        for (var i = 0; i < opcoes.length; i++) {
            var t = opcoes[i].text.toLowerCase();
            if (t.includes('val') && (t.includes('hosp') || t.includes('prof'))) {
                opcoes[i].selected = true;
            }
        }
    """)

    # --- 2. SELECIONAR HOSPITAL ---
    print(f">> Selecionando CNES {MEU_CNES}...")
    nome_encontrado = driver.execute_script(f"""
        var sel = document.getElementsByName('SEstabelecimento')[0];
        sel.selectedIndex = -1;
        for (var i = 0; i < sel.options.length; i++) {{
            if (sel.options[i].text.includes('{MEU_CNES}')) {{
                sel.options[i].selected = true;
                return sel.options[i].text;
            }}
        }}
        return null;
    """)

    if nome_encontrado:
        print(f"   ✅ Selecionado: {nome_encontrado}")
    else:
        print("⚠️ AVISO: Hospital não encontrado via script. Selecione MANUALMENTE agora (15s)!")
        time.sleep(15)

    # --- 3. GERAR E BAIXAR ---
    print(">> Gerando dados...")
    driver.find_element(By.CLASS_NAME, "mostra").click()
    
    print(">> Aguardando tabela...")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    
    print(">> Tentando baixar CSV...")
    # Tenta clicar e retorna se achou o botão
    clicou = driver.execute_script("""
        var links = document.getElementsByTagName('a');
        for (var i = 0; i < links.length; i++) {
            if (links[i].href.toLowerCase().includes('.csv') || links[i].innerText.includes('CSV')) {
                links[i].click();
                return true;
            }
        }
        return false;
    """)
    
    if clicou:
        print("   ✅ Botão CSV encontrado e clicado!")
        print("   ⏳ Aguardando 10 segundos para download...")
        time.sleep(10)
        
        # --- 4. CAÇA AO ARQUIVO PERDIDO ---
        arquivo_encontrado = None
        origem_final = ""

        # Verifica na pasta do projeto
        local_files = [f for f in os.listdir(PASTA_PROJETO) if f.endswith('.csv')]
        if local_files:
            arquivo_encontrado = local_files[0]
            origem_final = os.path.join(PASTA_PROJETO, arquivo_encontrado)
            print(f"   📂 Arquivo encontrado na pasta do projeto: {arquivo_encontrado}")
        
        # Se não achou, verifica na pasta Downloads do Windows
        else:
            print("   ⚠️ Não estava na pasta do projeto. Verificando Downloads...")
            dl_files = [f for f in os.listdir(PASTA_DOWNLOADS_WIN) if f.endswith('.csv')]
            # Ordena por data modificação (pega o mais recente)
            dl_files.sort(key=lambda x: os.path.getmtime(os.path.join(PASTA_DOWNLOADS_WIN, x)), reverse=True)
            
            if dl_files:
                # Pega o mais recente (provavelmente o que acabamos de baixar)
                arquivo_encontrado = dl_files[0]
                origem_final = os.path.join(PASTA_DOWNLOADS_WIN, arquivo_encontrado)
                print(f"   📂 Arquivo encontrado em Downloads: {arquivo_encontrado}")

        # Move para o destino final
        if arquivo_encontrado and os.path.exists(origem_final):
            if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)
            destino = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
            
            if os.path.exists(destino): os.remove(destino)
            shutil.copy2(origem_final, destino) # Copy2 preserva metadados
            
            # Se estava no Downloads, podemos deletar o original pra não acumular lixo (opcional)
            if "Downloads" in origem_final:
                try: os.remove(origem_final)
                except: pass
                
            print(f"\n🏆 VITÓRIA! Arquivo salvo em: arquivos/{ARQUIVO_FINAL}")
            print("Agora podemos atualizar o faturamento.html!")
        else:
            print("❌ ERRO CRÍTICO: O arquivo não foi encontrado em lugar nenhum.")

    else:
        print("❌ ERRO: Botão de download CSV não foi encontrado na página de resultados.")
        print("   Dica: Verifique se a tabela apareceu na tela do navegador.")

except Exception as e:
    print(f"❌ Erro Geral: {e}")

finally:
    # driver.quit() 
    pass