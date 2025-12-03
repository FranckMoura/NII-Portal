import time
import os
import shutil
import pandas as pd
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
PASTA_TEMP = r"C:\Users\DELL\OneDrive\NII-Portal-1\Tabnet_Temp"
PASTA_FINAL = "arquivos"
ARQUIVO_FINAL = "tabnet_producao_detalhada.csv"
# Lista de meses para baixar (Ajuste conforme necessário)
MESES_ALVO = ["Jan/2025", "Fev/2025", "Mar/2025", "Abr/2025", "Mai/2025", "Jun/2025", "Jul/2025", "Ago/2025", "Set/2025", "Out/2025", "Nov/2025"]

print("--- ROBÔ TABNET V10 (LOOP MENSAL) ---")

# Prepara pastas
if os.path.exists(PASTA_TEMP): shutil.rmtree(PASTA_TEMP)
os.makedirs(PASTA_TEMP, exist_ok=True)
if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)

options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_TEMP}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

# Função para processar um mês
def baixar_mes(mes_texto):
    print(f"\n>> Iniciando extração: {mes_texto}...")
    driver.get(URL_TABNET)
    
    wait.until(EC.presence_of_element_located((By.NAME, "Linha")))

    # 1. CONFIGURAÇÃO (Linha=Procedimento, Coluna=Não Ativa)
    # Isso garante a tabela detalhada igual ao seu arquivo manual
    try:
        Select(driver.find_element(By.NAME, "Linha")).select_by_visible_text("Procedimento realizado")
    except:
        Select(driver.find_element(By.NAME, "Linha")).select_by_index(1) # Tenta o segundo item
        
    Select(driver.find_element(By.NAME, "Coluna")).select_by_visible_text("Não ativa")

    # 2. VALORES (SH, SP, Qtd)
    select_conteudo = driver.find_element(By.NAME, "Incremento")
    opcoes = select_conteudo.find_elements(By.TAG_NAME, "option")
    for opt in opcoes:
        txt = opt.text.lower()
        # Seleciona Valor Hosp, Valor Prof e Quantidade (AIH)
        if ("val" in txt and ("hosp" in txt or "prof" in txt)) or "aih aprov" in txt:
            if not opt.is_selected(): opt.click()

    # 3. SELECIONAR MÊS ESPECÍFICO
    select_arquivos = Select(driver.find_element(By.NAME, "Arquivos"))
    select_arquivos.deselect_all() # Limpa seleção padrão
    try:
        select_arquivos.select_by_visible_text(mes_texto)
    except:
        print(f"   ⚠️ Mês {mes_texto} não disponível no site. Pulando.")
        return False

    # 4. FILTRAR HOSPITAL
    # Script JS para achar e clicar no Santa Helena (Mais rápido e seguro)
    hospital_ok = driver.execute_script(f"""
        var sel = document.getElementsByName('SEstabelecimento')[0];
        sel.selectedIndex = -1;
        for (var i = 0; i < sel.options.length; i++) {{
            if (sel.options[i].text.includes('{MEU_CNES}')) {{
                sel.options[i].selected = true;
                return true;
            }}
        }}
        return false;
    """)
    
    if not hospital_ok:
        print("   ❌ Hospital não encontrado na lista.")
        return False

    # 5. BAIXAR
    driver.find_element(By.CLASS_NAME, "mostra").click()
    
    # Muda para a nova aba
    janela_original = driver.window_handles[0]
    driver.switch_to.window(driver.window_handles[-1])
    
    try:
        # Clica no CSV
        driver.find_element(By.XPATH, "//a[contains(@href, '.csv') or contains(text(), 'CSV')]").click()
        time.sleep(3)
        
        # Renomeia o arquivo baixado
        nome_final = f"producao_{mes_texto.replace('/', '_')}.csv"
        arquivos = [f for f in os.listdir(PASTA_TEMP) if f.endswith('.csv') and "producao_" not in f]
        
        if arquivos:
            os.rename(os.path.join(PASTA_TEMP, arquivos[0]), os.path.join(PASTA_TEMP, nome_final))
            print(f"   ✅ Download concluído: {nome_final}")
            
            driver.close() # Fecha a aba do relatório
            driver.switch_to.window(janela_original) # Volta pro formulário
            return True
            
    except Exception as e:
        print(f"   ❌ Erro ao baixar: {e}")
        driver.close()
        driver.switch_to.window(janela_original)
        return False

# --- EXECUÇÃO DO LOOP ---
try:
    for mes in MESES_ALVO:
        baixar_mes(mes)

    print("\n>> Consolidando arquivos...")
    # Junta todos os CSVs em um só
    lista_dfs = []
    for arquivo in os.listdir(PASTA_TEMP):
        if arquivo.endswith(".csv"):
            caminho = os.path.join(PASTA_TEMP, arquivo)
            try:
                # O TabNet usa ponto e virgula e encoding latin1
                df = pd.read_csv(caminho, sep=';', encoding='latin1', skiprows=3, skipfooter=1, engine='python')
                
                # Adiciona a coluna de competência baseada no nome do arquivo
                comp = arquivo.replace("producao_", "").replace(".csv", "").replace("_", "/")
                df['Competência'] = comp
                
                lista_dfs.append(df)
            except Exception as e:
                print(f"   ⚠️ Erro ao ler {arquivo}: {e}")

    if lista_dfs:
        df_final = pd.concat(lista_dfs)
        caminho_final = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
        df_final.to_csv(caminho_final, index=False, sep=';', encoding='utf-8-sig')
        print(f"🏆 SUCESSO! Arquivo consolidado salvo em: {caminho_final}")
        print(f"   Total de registros: {len(df_final)}")
    else:
        print("❌ Nenhum dado foi baixado.")

except Exception as e:
    print(f"❌ Erro Geral: {e}")

finally:
    try: driver.quit()
    except: pass