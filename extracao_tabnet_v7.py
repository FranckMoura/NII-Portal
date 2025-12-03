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
PASTA_DOWNLOADS_WIN = os.path.join(os.path.expanduser("~"), "Downloads")

print("--- ROBÔ TABNET V9 (MUDANÇA DE ABA) ---")

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
    
    # Salva a janela original (formulário) para referência
    janela_original = driver.current_window_handle
    
    wait.until(EC.presence_of_element_located((By.NAME, "Linha")))

    # --- 1. CONFIGURAÇÕES DO FORMULÁRIO ---
    print(">> Configurando Tabela...")
    
    # Linha e Coluna (Seleção segura por texto parcial)
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

    # Valores
    driver.execute_script("""
        var opcoes = document.getElementsByName('Incremento')[0].options;
        for (var i = 0; i < opcoes.length; i++) {
            var t = opcoes[i].text.toLowerCase();
            if (t.includes('val') && (t.includes('hosp') || t.includes('prof'))) {
                opcoes[i].selected = true;
            }
        }
    """)

    # Selecionar Hospital
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
    
    if not nome_encontrado:
        print("⚠️ Selecione MANUALMENTE o hospital agora (15s)...")
        time.sleep(15)

    # --- 2. GERAR TABELA (CLIQUE NO MOSTRA) ---
    print(">> Clicando em 'Mostra'...")
    driver.find_element(By.CLASS_NAME, "mostra").click()
    
    # --- 3. MUDANÇA DE ABA (O PULO DO GATO) ---
    print(">> Aguardando nova aba abrir...")
    time.sleep(3) # Dá tempo da nova janela abrir
    
    # Lista todas as janelas abertas
    todas_janelas = driver.window_handles
    
    # Troca para a nova janela (a que não é a original)
    for janela in todas_janelas:
        if janela != janela_original:
            driver.switch_to.window(janela)
            print("✅ Robô mudou o foco para a nova aba (Resultados).")
            break
            
    # --- 4. BAIXAR O CSV NA NOVA ABA ---
    print(">> Procurando botão CSV na nova aba...")
    
    # Tenta rolar até o fim, pois o botão fica lá embaixo
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    
    try:
        # Procura link que tenha .csv ou texto "Cópia como .CSV"
        link_csv = driver.find_element(By.XPATH, "//a[contains(@href, '.csv') or contains(text(), 'CSV')]")
        link_csv.click()
        print("   ✅ Botão CSV clicado!")
        
        print("   ⏳ Aguardando 10 segundos para download...")
        time.sleep(10)
        
        # --- 5. RECUPERAR O ARQUIVO ---
        arquivo_encontrado = None
        origem_final = ""

        # Verifica Pasta do Projeto
        local_files = [f for f in os.listdir(PASTA_PROJETO) if f.endswith('.csv')]
        if local_files:
            arquivo_encontrado = local_files[0]
            origem_final = os.path.join(PASTA_PROJETO, arquivo_encontrado)
        
        # Verifica Pasta Downloads (caso o Chrome ignore a config em nova aba)
        else:
            print("   ⚠️ Verificando pasta Downloads do Windows...")
            dl_files = [f for f in os.listdir(PASTA_DOWNLOADS_WIN) if f.endswith('.csv')]
            dl_files.sort(key=lambda x: os.path.getmtime(os.path.join(PASTA_DOWNLOADS_WIN, x)), reverse=True)
            
            if dl_files:
                arquivo_encontrado = dl_files[0]
                origem_final = os.path.join(PASTA_DOWNLOADS_WIN, arquivo_encontrado)

        # Move e Renomeia
        if arquivo_encontrado and os.path.exists(origem_final):
            if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)
            destino = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
            
            if os.path.exists(destino): os.remove(destino)
            shutil.copy2(origem_final, destino)
            
            # Limpeza
            if "Downloads" in origem_final:
                try: os.remove(origem_final)
                except: pass
                
            print(f"\n🏆 VITÓRIA! Arquivo salvo em: arquivos/{ARQUIVO_FINAL}")
        else:
            print("❌ ERRO: O arquivo não foi encontrado após o clique.")

    except Exception as e:
        print(f"❌ Erro ao tentar baixar: {e}")
        driver.save_screenshot("erro_aba_nova.png")

except Exception as e:
    print(f"❌ Erro Geral: {e}")

finally:
    # driver.quit()
    pass