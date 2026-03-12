import time
import os
import re
import base64
import winsound
import json
import pdfplumber
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 📡 RADAR SISREG V6 (ATALHO DIRETO) ---")
print(">> Rodando em segundo plano. Pressione Ctrl+C para parar.")

# --- CONFIGURAÇÕES ---
INTERVALO_VERIFICACAO = 5 
DT_INICIO = "14/02/2026"
DT_FIM = "28/02/2026"

SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
USUARIO = "046FRANCK"
SENHA = "515462"

NOME_BUCKET = "arquivos-faturamento"
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend"
PASTA_TEMP_PDF = os.path.join(PASTA_PROJETO, "temp_monitor")

if not os.path.exists(PASTA_TEMP_PDF):
    os.makedirs(PASTA_TEMP_PDF)

# --- CONEXÃO ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro Supabase: {e}")
    exit()

# --- FUNÇÕES ---
def tocar_alerta():
    try:
        for _ in range(3):
            winsound.Beep(1000, 200)
            time.sleep(0.1)
    except:
        pass

def salvar_pdf_headless(driver, caminho_arquivo):
    try:
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "landscape": False, "displayHeaderFooter": False, 
            "printBackground": True, "preferCSSPageSize": True
        })
        with open(caminho_arquivo, "wb") as f:
            f.write(base64.b64decode(pdf_data['data']))
        return True
    except:
        return False

def extrair_dados_rapido(caminho_arquivo):
    dados = {"cod_solicitacao": None, "cns": None}
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            texto = pdf.pages[0].extract_text() or ""
            m_sol = re.search(r'(?:Solicitação)[:\s\.]*(\d{9,})', texto)
            if m_sol:
                dados['cod_solicitacao'] = m_sol.group(1)
            m_cns = re.search(r'(?:Nacional de Saúde|CNS)[:\s\.]*(\d{15})', texto)
            if m_cns:
                dados['cns'] = m_cns.group(1)
    except:
        pass
    return dados

def processar_novidade(driver, linha, aih, nome):
    print(f"\n🔔 NOVIDADE DETECTADA: {nome}")
    try:
        link = linha.find_element(By.TAG_NAME, "a")
        driver.execute_script("arguments[0].scrollIntoView(true);", link)
        link.click()
        time.sleep(5) 

        janelas = driver.window_handles
        driver.switch_to.window(janelas[-1])

        nome_pdf = f"MONITOR_{aih}.pdf"
        caminho_pdf = os.path.join(PASTA_TEMP_PDF, nome_pdf)
        
        if salvar_pdf_headless(driver, caminho_pdf):
            dados_ocr = extrair_dados_rapido(caminho_pdf)
            
            with open(caminho_pdf, 'rb') as f:
                supabase.storage.from_(NOME_BUCKET).upload(
                    path=f"Fichas_Internacao/{nome_pdf}", file=f, 
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            link_publico = supabase.storage.from_(NOME_BUCKET).get_public_url(f"Fichas_Internacao/{nome_pdf}")

            reg = {
                "num_aih": aih,
                "nome_paciente": nome,
                "status": "APROVADO",
                "arquivo_pdf": link_publico,
                "data_atualizacao": datetime.now().isoformat()
            }
            if dados_ocr['cod_solicitacao']:
                reg['num_solicitacao'] = dados_ocr['cod_solicitacao']
            if dados_ocr['cns']:
                reg['cns'] = dados_ocr['cns']

            coluna_chave = "num_solicitacao" if dados_ocr['cod_solicitacao'] else "num_aih"
            supabase.table("regulacao").upsert(reg, on_conflict=coluna_chave).execute()
            
            tocar_alerta()
            print(f"✅ ALERTA ENVIADO: Paciente {nome} atualizado!")
            
            try:
                os.remove(caminho_pdf)
            except:
                pass

        driver.close()
        driver.switch_to.window(janelas[0])
        time.sleep(1)
        
    except Exception as e:
        print(f"❌ Erro ao processar novidade: {e}")
        # Recuperação de erro de janela
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

# --- NOVO NÚCLEO DE NAVEGAÇÃO ---
def ir_para_consultas_direto(driver):
    """
    Em vez de clicar no menu, descobre o link e vai direto.
    Isso evita problemas com Frames e Menus JS.
    """
    print(">> Buscando link direto de 'Ambulatorial'...")
    driver.switch_to.default_content()
    
    try:
        # Procura o link pelo texto visível (mais seguro que ID)
        link_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Ambulatorial"))
        )
        url_direta = link_elem.get_attribute("href")
        print(f"   -> Link encontrado: {url_direta}")
        
        # Vai direto para a URL (isso quebra os frames e carrega só a tabela, o que é ÓTIMO para robôs)
        driver.get(url_direta)
        return True
    except Exception as e:
        print(f"⚠️ Erro ao buscar link: {e}")
        return False

def ciclo_monitoramento():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3") 
    
    driver = None
    
    try:
        print(">> Iniciando motor (Modo Silencioso)...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 30)

        # Login
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
        try:
            driver.switch_to.alert.accept()
        except:
            pass

        wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        try:
            driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
        
        # --- AQUI ESTÁ O TRUQUE DO V6 ---
        # Clica no menu principal para abrir a lista (se necessário)
        try:
            driver.find_element(By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a").click()
            time.sleep(1)
        except:
            pass

        # Pega o link e navega DIRETO (Adeus Frames!)
        if not ir_para_consultas_direto(driver):
            raise Exception("Não foi possível acessar a área de consultas.")
        
        time.sleep(5)

        # LOOP DE VARREDURA
        while True:
            # Como navegamos direto, não existem mais frames! A tabela está no 'default_content'
            
            # 2. Preenche e Pesquisa
            try:
                # Verifica se caiu na tela certa procurando o campo data
                if not driver.find_elements(By.NAME, "data_inicio"):
                    print("⚠️ Tela incorreta. Tentando navegar novamente...")
                    driver.back() # Tenta voltar caso tenha saido
                    time.sleep(2)
                    ir_para_consultas_direto(driver)
                    time.sleep(5)
                    continue

                # Preenche (Agora direto, sem switch_to.frame)
                driver.execute_script(f"document.getElementsByName('data_inicio')[0].value = '{DT_INICIO}'")
                driver.execute_script(f"document.getElementsByName('data_fim')[0].value = '{DT_FIM}'")
                
                try:
                    driver.find_element(By.NAME, "enviar").click()
                except:
                    driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
                
                time.sleep(5)
            except Exception as e:
                print(f"⚠️ Erro na pesquisa: {e}")
                driver.refresh()
                time.sleep(5)
                continue
            
            # 3. Analisa Resultados
            linhas = driver.find_elements(By.XPATH, "//tr[td[contains(@class,'text')]]")
            novidades_encontradas = 0
            
            for linha in linhas:
                txt = linha.text.upper()
                if "APROVADO" in txt or "AUTORIZADO" in txt:
                    match = re.search(r'(\d{12}-\d{1})|(\d{13})', txt)
                    if not match:
                        continue
                    aih = match.group(0)
                    
                    nome = "PACIENTE"
                    cols = linha.find_elements(By.TAG_NAME, "td")
                    for c in cols:
                        t = c.text.strip()
                        if len(t) > 5 and not t[0].isdigit() and "/" not in t and "APROV" not in t.upper():
                            nome = re.sub(r'[\\/*?:"<>|]', "", t).strip()

                    # Verifica Banco
                    res = supabase.table("regulacao").select("arquivo_pdf").eq("num_aih", aih).execute()
                    if not (res.data and len(res.data) > 0 and res.data[0]['arquivo_pdf']):
                        processar_novidade(driver, linha, aih, nome)
                        novidades_encontradas += 1
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Ciclo OK. {len(linhas)} registros. Novidades: {novidades_encontradas}")
            
            time.sleep(INTERVALO_VERIFICACAO * 60)
            driver.refresh()
            time.sleep(5)

    except Exception as e:
        print(f"⚠️ Erro Crítico: {e}")
    finally:
        if driver:
            driver.quit()

while True:
    try:
        ciclo_monitoramento()
    except KeyboardInterrupt:
        print("\n🛑 Parando...")
        break
    except:
        print("♻️ Reiniciando serviço em 10s...")
        time.sleep(10)