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

# Lista de meses para baixar
MESES_ALVO = [
    "Jan/2025", "Fev/2025", "Mar/2025", "Abr/2025", "Mai/2025", 
    "Jun/2025", "Jul/2025", "Ago/2025", "Set/2025", "Out/2025", "Nov/2025"
]

print("--- ROBÔ TABNET V11 (SELEÇÃO FLEXÍVEL) ---")

# Prepara pastas
if os.path.exists(PASTA_TEMP):
    try: shutil.rmtree(PASTA_TEMP, ignore_errors=True)
    except: pass

os.makedirs(PASTA_TEMP, exist_ok=True)
if not os.path.exists(PASTA_FINAL): os.makedirs(PASTA_FINAL)

# Configurações do Navegador
options = webdriver.ChromeOptions()
prefs = {"download.default_directory": PASTA_TEMP}
options.add_experimental_option("prefs", prefs)

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
except Exception as e:
    print(f"❌ Erro ao abrir navegador: {e}")
    exit()

wait = WebDriverWait(driver, 20)

# --- FUNÇÃO PARA SELEÇÃO INTELIGENTE ---
def selecionar_inteligente(nome_campo, textos_tentativa, indice_fallback=None):
    try:
        select_elem = Select(driver.find_element(By.NAME, nome_campo))
        
        # Tenta achar por texto parcial
        for texto in textos_tentativa:
            for opt in select_elem.options:
                if texto.lower() in opt.text.lower():
                    opt.click()
                    print(f"   ✅ {nome_campo}: Selecionado '{opt.text}'")
                    return True
        
        # Se não achou por texto, tenta pelo índice
        if indice_fallback is not None and len(select_elem.options) > indice_fallback:
            select_elem.select_by_index(indice_fallback)
            print(f"   ⚠️ {nome_campo}: Selecionado por índice {indice_fallback} ('{select_elem.first_selected_option.text}')")
            return True
            
        print(f"   ❌ {nome_campo}: Nenhuma opção válida encontrada.")
        return False
    except Exception as e:
        print(f"   ❌ Erro ao selecionar {nome_campo}: {e}")
        return False

# --- FUNÇÃO PARA BAIXAR UM MÊS ---
def baixar_mes(mes_texto):
    print(f"\n>> Iniciando extração: {mes_texto}...")
    
    try:
        driver.get(URL_TABNET)
        wait.until(EC.presence_of_element_located((By.NAME, "Linha")))

        # 1. CONFIGURAÇÃO DA TABELA
        # Linha: Tenta 'Competência', fallback índice 0
        selecionar_inteligente("Linha", ["Compet"], 0)
        
        # Coluna: Tenta 'Procedimento', 'Grupo', fallback índice 1
        # Tenta "Não ativa" primeiro para evitar erro se só quiser lista simples, 
        # mas queremos detalhe por procedimento, então tentamos Procedimento primeiro
        # Se falhar, tenta "Não ativa"
        if not selecionar_inteligente("Coluna", ["Procedimento realizado", "Grupo procedimento"]):
             selecionar_inteligente("Coluna", ["Não ativa"], 0)

        # 2. SELECIONAR VALORES (SP, SH, QTD)
        driver.execute_script("""
            var opcoes = document.getElementsByName('Incremento')[0].options;
            for (var i = 0; i < opcoes.length; i++) {
                var t = opcoes[i].text.toLowerCase();
                if ((t.includes('val') && (t.includes('hosp') || t.includes('prof'))) || t.includes('aih aprov')) {
                    opcoes[i].selected = true;
                }
            }
        """)

        # 3. SELECIONAR O MÊS
        select_arquivos = Select(driver.find_element(By.NAME, "Arquivos"))
        select_arquivos.deselect_all()
        
        try:
            select_arquivos.select_by_visible_text(mes_texto)
        except:
            print(f"   ⚠️ Mês {mes_texto} não disponível no site. Pulando.")
            return False

        # 4. FILTRAR HOSPITAL
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

        # 5. GERAR E BAIXAR
        driver.find_element(By.CLASS_NAME, "mostra").click()
        
        # Muda para a nova aba
        janela_original = driver.window_handles[0]
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            
            try:
                driver.find_element(By.XPATH, "//a[contains(@href, '.csv') or contains(text(), 'CSV')]").click()
                time.sleep(3) 
                
                lista_arquivos = [f for f in os.listdir(PASTA_TEMP) if f.endswith('.csv') and "producao_" not in f]
                if lista_arquivos:
                    ultimo_arquivo = max([os.path.join(PASTA_TEMP, f) for f in lista_arquivos], key=os.path.getmtime)
                    nome_novo = f"producao_{mes_texto.replace('/', '_')}.csv"
                    
                    destino_renomeado = os.path.join(PASTA_TEMP, nome_novo)
                    if os.path.exists(destino_renomeado): os.remove(destino_renomeado)
                        
                    os.rename(ultimo_arquivo, destino_renomeado)
                    print(f"   ✅ Download concluído: {nome_novo}")
                    
                    driver.close()
                    driver.switch_to.window(janela_original)
                    return True
                else:
                    print("   ❌ Erro: Arquivo CSV não apareceu na pasta.")
                    driver.close()
                    driver.switch_to.window(janela_original)
                    return False

            except Exception as e:
                print(f"   ❌ Erro ao clicar no CSV (Tabela vazia?): {e}")
                driver.close()
                driver.switch_to.window(janela_original)
                return False
        else:
            print("   ❌ Nova aba não abriu.")
            return False

    except Exception as e:
        print(f"   ❌ Erro geral no mês {mes_texto}: {e}")
        return False

# --- LOOP PRINCIPAL ---
try:
    for mes in MESES_ALVO:
        baixar_mes(mes)

    print("\n>> Consolidando arquivos...")
    lista_dfs = []
    
    for arquivo in os.listdir(PASTA_TEMP):
        if arquivo.startswith("producao_") and arquivo.endswith(".csv"):
            caminho = os.path.join(PASTA_TEMP, arquivo)
            try:
                # O TabNet costuma usar encoding 'latin1' ou 'ISO-8859-1'
                df = pd.read_csv(caminho, sep=';', encoding='latin1', skiprows=3, skipfooter=1, engine='python')
                
                comp = arquivo.replace("producao_", "").replace(".csv", "").replace("_", "/")
                df['Competência'] = comp
                
                lista_dfs.append(df)
                print(f"   + Adicionado: {comp}")
            except Exception as e:
                print(f"   ⚠️ Erro ao ler {arquivo}: {e}")

    if lista_dfs:
        df_final = pd.concat(lista_dfs)
        caminho_final = os.path.join(PASTA_FINAL, ARQUIVO_FINAL)
        
        df_final.to_csv(caminho_final, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n🏆 SUCESSO TOTAL! Arquivo consolidado salvo em:\n   {caminho_final}")
        print(f"   Total de registros importados: {len(df_final)}")
    else:
        print("\n❌ Nenhum dado foi baixado com sucesso.")

except Exception as e:
    print(f"\n❌ Erro Fatal: {e}")

finally:
    try: driver.quit()
    except: pass