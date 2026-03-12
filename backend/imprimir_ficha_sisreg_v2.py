import time
import os
import re
import json
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 3. AUTOMAÇÃO SISREG (V60 - EXECUTANTE / AIH GERADA) ---")

# --- CONFIGURAÇÕES ---
FORCAR_RE_DOWNLOAD = False  # Se False, pula o que já salvou

# --- SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

# --- LOGIN ---
USUARIO = "20325223FRANCK" # Novo Usuário
SENHA = "515462"

PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend"
PASTA_TEMP_PDF = os.path.join(PASTA_PROJETO, "temp_fichas")
ARQUIVO_CACHE = os.path.join(PASTA_PROJETO, "cache_downloads_aih.json")

if not os.path.exists(PASTA_TEMP_PDF): os.makedirs(PASTA_TEMP_PDF)

# --- CACHE LOCAL ---
def carregar_cache():
    if os.path.exists(ARQUIVO_CACHE):
        try:
            with open(ARQUIVO_CACHE, 'r') as f: return set(json.load(f))
        except: return set()
    return set()

def salvar_cache(conjunto):
    try:
        with open(ARQUIVO_CACHE, 'w') as f: json.dump(list(conjunto), f)
    except: pass

CACHE_LOCAL = carregar_cache()
print(f"📂 Cache carregado: {len(CACHE_LOCAL)} AIHs já processadas.")

# Conexão Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    print("❌ Erro Supabase.")
    exit()

# --- PDF VIA ENGINE (RÁPIDO) ---
def gerar_pdf_cdp(driver, caminho_saida):
    try:
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "paperWidth": 8.27, "paperHeight": 11.69,
            "marginTop": 0.4, "marginBottom": 0.4, "marginLeft": 0.4, "marginRight": 0.4
        })
        with open(caminho_saida, "wb") as f:
            f.write(base64.b64decode(pdf_data['data']))
        return True
    except Exception as e:
        print(f"❌ Erro CDP: {e}")
        return False

def enviar_para_nuvem(caminho_local, nome_remoto):
    try:
        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto, file=f,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except: return None

def limpar_nome(txt): return re.sub(r'[\\/*?:"<>|]', "", txt).strip()

def focar_frame_principal(driver):
    driver.switch_to.default_content()
    try:
        frames = driver.find_elements(By.TAG_NAME, "frame")
        for f in frames:
            if "main" in f.get_attribute("name") or "principal" in f.get_attribute("name"):
                driver.switch_to.frame(f); return True
        if len(frames) > 0: driver.switch_to.frame(1); return True
    except: pass
    return False

# --- EXECUÇÃO ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

try:
    print(">> Acessando Sisreg...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    
    # Login
    try:
        wait.until(EC.element_to_be_clickable((By.NAME, "usuario"))).send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: pass

    # --- NAVEGAÇÃO NOVA (CONSULTAS -> AIH GERADA) ---
    print(">> Navegando: Consultas > AIH Gerada...")
    try:
        focar_frame_principal(driver)
        driver.switch_to.default_content()
        driver.switch_to.frame("menu") 
        
        # Procura link "Consultas" (Geralmente menu 4 ou 5)
        # Vamos tentar clicar pelo Texto para ser mais garantido
        consultas = driver.find_element(By.XPATH, "//a[contains(text(), 'Consultas')]")
        consultas.click()
        time.sleep(1)
        
        # Clica em "AIH gerada"
        aih_gerada = driver.find_element(By.XPATH, "//a[contains(text(), 'AIH gerada') or contains(text(), 'AIH Gerada')]")
        aih_gerada.click()
        time.sleep(3)
        
    except Exception as e:
        print(f"⚠️ Erro navegação automática: {e}")
        print(">> Por favor, navegue manualmente até a tela 'AIH GERADA' agora!")
        time.sleep(10)

    # --- PESQUISA (SEM DATA) ---
    focar_frame_principal(driver)
    print(">> Clicando em PESQUISAR...")
    try:
        # Tenta clicar no botão de pesquisar
        btn_pesquisar = driver.find_element(By.XPATH, "//input[@type='button' and @value='PESQUISAR'] | //input[@name='enviar']")
        btn_pesquisar.click()
    except:
        print("⚠️ Botão Pesquisar não encontrado via código. Clique manualmente se necessário.")
    
    time.sleep(5) 

    pagina = 1
    while True:
        print(f"\n>>> LENDO PÁGINA {pagina} <<<")
        focar_frame_principal(driver)
        
        # Procura a tabela de resultados
        linhas = driver.find_elements(By.XPATH, "//table[@class='table_listagem']//tr[td]") 
        
        print(f">> Encontradas {len(linhas)} linhas na tabela.")
        
        for i in range(len(linhas)):
            try:
                # Refresh elementos
                focar_frame_principal(driver)
                linhas_atual = driver.find_elements(By.XPATH, "//table[@class='table_listagem']//tr[td]")
                if i >= len(linhas_atual): break
                
                linha = linhas_atual[i]
                texto = linha.text
                
                # Regex AIH (Formato comum: XXXXXX-X ou XXXXXXXXXXXXX)
                match = re.search(r'(\d{13})|(\d{12}-\d)', texto)
                if not match: continue
                
                aih = match.group(0)
                
                if not FORCAR_RE_DOWNLOAD and aih in CACHE_LOCAL:
                    continue
                
                print(f"\n📥 Processando AIH: {aih}")
                
                # Extrai nome paciente (Coluna 3 geralmente)
                cols = linha.find_elements(By.TAG_NAME, "td")
                nome_paciente = "PACIENTE"
                if len(cols) > 2: nome_paciente = limpar_nome(cols[2].text)

                # Clica no link da AIH ou Lupa (geralmente o primeiro link da linha)
                link = linha.find_element(By.TAG_NAME, "a")
                driver.execute_script("arguments[0].click();", link)
                
                time.sleep(3) # Carrega detalhe
                
                # --- GERAÇÃO E UPLOAD ---
                nome_arq = f"AIH_{aih}_{nome_paciente}.pdf"
                caminho_local = os.path.join(PASTA_TEMP_PDF, nome_arq)
                
                if gerar_pdf_cdp(driver, caminho_local):
                    url = enviar_para_nuvem(caminho_local, f"Fichas_Executante/{nome_arq}")
                    if url:
                        # Salva
                        reg = {"num_aih": aih, "nome_paciente": nome_paciente, "status": "Gerada", "arquivo_pdf": url}
                        supabase.table("regulacao").upsert(reg, on_conflict="num_aih").execute()
                        
                        CACHE_LOCAL.add(aih)
                        salvar_cache(CACHE_LOCAL)
                        print(f"✅ Salvo!")
                        os.remove(caminho_local)
                
                # Volta
                driver.back()
                time.sleep(2)

            except Exception as e:
                print(f"Erro linha {i}: {e}")
                driver.back()
                time.sleep(2)

        # Paginação
        print(">> Verificando próxima página...")
        focar_frame_principal(driver)
        try:
            prox = driver.find_element(By.XPATH, "//a[contains(text(), '>') or contains(@href, 'Proxima')]")
            prox.click()
            pagina += 1
            time.sleep(5)
        except:
            print("Fim da paginação.")
            break

except Exception as e:
    print(f"ERRO FATAL: {e}")
finally:
    driver.quit()