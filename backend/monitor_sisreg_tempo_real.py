import time
import os
import re
import base64
import winsound
import pdfplumber
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print(f"--- 🕵️ SENTINELA SISREG V2 (AUTO-RESTART) ---")
print(">> Monitoramento contínuo. Se o navegador fechar, ele reabre sozinho.")

# --- CONFIGURAÇÕES ---
DT_INICIO = "14/02/2026"  # Data de hoje
DT_FIM = "28/02/2026"     # Fim do mês
INTERVALO_MINUTOS = 5     # Tempo entre verificações

SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

USUARIO = "046FRANCK"
SENHA = "515462"
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend"
PASTA_TEMP_PDF = os.path.join(PASTA_PROJETO, "temp_monitor")

if not os.path.exists(PASTA_TEMP_PDF): os.makedirs(PASTA_TEMP_PDF)

# --- FUNÇÕES AUXILIARES ---
def limpar_nome(texto):
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def emitir_alerta(mensagem):
    print(f"\n🚨 {mensagem}")
    try: winsound.Beep(1000, 800)
    except: pass

def salvar_pdf_direto(driver, caminho_arquivo):
    try:
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "landscape": False, "displayHeaderFooter": False, 
            "printBackground": True, "preferCSSPageSize": True
        })
        with open(caminho_arquivo, "wb") as f:
            f.write(base64.b64decode(pdf_data['data']))
        return True
    except: return False

def extrair_dados_pdf(caminho_arquivo):
    dados = { "cns": None, "nome_mae": None, "cod_solicitacao": None, "procedimento": None }
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            texto = ""
            for page in pdf.pages: texto += page.extract_text() or ""
            
            m_cns = re.search(r'(?:Nacional de Saúde|CNS)[:\s\.]*(\d{15})', texto)
            if m_cns: dados['cns'] = m_cns.group(1)
            
            m_sol = re.search(r'(?:Solicitação)[:\s\.]*(\d{9,})', texto)
            if m_sol: dados['cod_solicitacao'] = m_sol.group(1)

            m_mae = re.search(r'(?:Mãe)[:\s\.]*(.+?)(?:\n|Município)', texto)
            if m_mae: dados['nome_mae'] = m_mae.group(1).strip()
            
            m_proc = re.search(r'(?:Procedimento)[:\s\.]*(\d{2}\.\d{2}\.\d{2}\.\d{3}-\d\s+-.+)', texto)
            if not m_proc: m_proc = re.search(r'(?:Procedimento)[:\s\.]*(.+?)(?:\n|Qtde)', texto)
            if m_proc: dados['procedimento'] = m_proc.group(1).strip()
    except: pass
    return dados

def atualizar_banco(supabase, caminho_pdf, nome_remoto, dados_base, dados_extra):
    try:
        id_busca = dados_extra.get('cod_solicitacao') or dados_base['aih']
        coluna_busca = "num_solicitacao" if dados_extra.get('cod_solicitacao') else "num_aih"
        
        # Verifica se já está aprovado
        res = supabase.table("regulacao").select("status").eq(coluna_busca, id_busca).execute()
        if res.data:
            if "APROVADO" in str(res.data[0].get('status', '')).upper():
                return False 

        # Upload
        with open(caminho_pdf, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto, file=f, file_options={"content-type": "application/pdf", "upsert": "true"}
            )
        link = supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)

        reg = {
            "num_aih": dados_base['aih'],
            "nome_paciente": dados_base['nome_paciente'],
            "status": "APROVADO",
            "arquivo_pdf": link,
            "data_atualizacao": datetime.now().isoformat(),
            "cns": dados_extra.get('cns'),
            "nome_mae": dados_extra.get('nome_mae'),
            "procedimento": dados_extra.get('procedimento')
        }
        if dados_extra.get('cod_solicitacao'): reg['num_solicitacao'] = dados_extra['cod_solicitacao']

        supabase.table("regulacao").upsert(reg, on_conflict=coluna_busca).execute()
        return True
    except Exception as e:
        print(f"Erro Banco: {e}")
        return False

def verificar_bloqueio(driver):
    try:
        alerta = driver.switch_to.alert
        if "bloqueado" in alerta.text.lower():
            alerta.accept()
            print("⛔ Bloqueio de horário. Pausando 10 min...")
            time.sleep(600)
            return True
        alerta.accept()
    except: pass
    return False

# --- NÚCLEO DO ROBÔ (CICLO DE VIDA) ---
def rodar_robo():
    driver = None
    supabase = None
    
    try:
        # Conecta Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Inicia Browser
        print("\n>> Iniciando Navegador...")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-print-preview")
        # options.add_argument("--headless=new") # Descomente para rodar invisível
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)

        # Login
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
        verificar_bloqueio(driver)
        
        wait.until(EC.presence_of_element_located((By.NAME, "usuario"))).send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
        except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
        
        if verificar_bloqueio(driver): return # Reinicia se bloqueado

        print(">> Acessando Consultas...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/a"))).click()
        time.sleep(1)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='barraMenu']/ul/li[5]/ul/li[1]/a"))).click()
        time.sleep(5)

        # Loop de Varredura (Dentro da mesma sessão)
        ciclo = 1
        erros_consecutivos = 0
        
        while True:
            print(f"\n🔎 VARREDURA #{ciclo} - {datetime.now().strftime('%H:%M:%S')}")
            
            # Garante foco no frame correto
            driver.switch_to.default_content()
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            frame_ok = False
            for i in range(len(frames)):
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame(i)
                    if driver.find_elements(By.NAME, "data_inicio"):
                        frame_ok = True
                        break
                except: pass
            
            if not frame_ok:
                print("⚠️ Frame de dados não encontrado. Recarregando...")
                erros_consecutivos += 1
                if erros_consecutivos > 2: raise Exception("Falha estrutural na página")
                driver.refresh()
                time.sleep(5)
                continue

            erros_consecutivos = 0 # Reset se achou o frame

            # Preenche Datas
            try:
                driver.execute_script(f"document.getElementsByName('data_inicio')[0].value = '{DT_INICIO}'")
                driver.execute_script(f"document.getElementsByName('data_fim')[0].value = '{DT_FIM}'")
                
                # Clica em Pesquisar
                try: driver.find_element(By.NAME, "enviar").click()
                except: driver.find_element(By.XPATH, "//input[@value='PESQUISAR']").click()
            except:
                print("⚠️ Erro ao preencher/clicar. Sessão pode ter expirado.")
                raise Exception("Sessão Expirada")

            time.sleep(8)
            verificar_bloqueio(driver)

            # Analisa Tabela
            linhas = driver.find_elements(By.XPATH, "//tr[td[contains(@class,'text')]]")
            print(f"   -> Encontrados {len(linhas)} registros na página.")

            for linha in linhas:
                texto = linha.text.upper()
                if "AUTORIZADO" in texto or "APROVADO" in texto:
                    match_aih = re.search(r'(\d{12}-\d{1})|(\d{13})', texto)
                    if not match_aih: continue
                    aih = match_aih.group(0)

                    # Extrai nome
                    nome = "PACIENTE"
                    cols = linha.find_elements(By.TAG_NAME, "td")
                    for c in cols:
                        t = c.text.strip()
                        if len(t) > 5 and not t[0].isdigit() and "/" not in t and "APROV" not in t:
                            nome = limpar_nome(t)

                    # Verifica no banco antes de abrir
                    res = supabase.table("regulacao").select("arquivo_pdf").eq("num_aih", aih).execute()
                    if not (res.data and res.data[0].get('arquivo_pdf')):
                        print(f"🔔 BAIXANDO NOVIDADE: {nome}")
                        
                        try:
                            link_abrir = linha.find_element(By.TAG_NAME, "a")
                            driver.execute_script("arguments[0].scrollIntoView(true);", link_abrir)
                            link_abrir.click()
                            time.sleep(4)

                            janelas = driver.window_handles
                            driver.switch_to.window(janelas[-1])
                            
                            caminho_pdf = os.path.join(PASTA_TEMP_PDF, f"monitor_{aih}.pdf")
                            if salvar_pdf_direto(driver, caminho_pdf):
                                dados_extra = extrair_dados_pdf(caminho_pdf)
                                dados_base = { "aih": aih, "nome_paciente": nome, "status": "APROVADO" }
                                remoto = f"Fichas_Internacao/monitor_{aih}.pdf"
                                
                                if atualizar_banco(supabase, caminho_pdf, remoto, dados_base, dados_extra):
                                    emitir_alerta(f"NOVA APROVAÇÃO: {nome}")
                                
                                try: os.remove(caminho_pdf)
                                except: pass
                            
                            driver.close()
                            driver.switch_to.window(janelas[0])
                            
                            # Re-foca no frame após voltar da janela
                            driver.switch_to.default_content()
                            for i in range(len(frames)):
                                try:
                                    driver.switch_to.frame(i)
                                    if driver.find_elements(By.NAME, "data_inicio"): break
                                except: pass

                        except Exception as e:
                            print(f"Erro ao baixar: {e}")
                            if len(driver.window_handles) > 1:
                                driver.close()
                                driver.switch_to.window(janelas[0])

            print(f"💤 Dormindo {INTERVALO_MINUTOS} min...")
            time.sleep(INTERVALO_MINUTOS * 60)
            ciclo += 1
            
            # Recarrega a página a cada ciclo para evitar timeout
            driver.refresh()
            time.sleep(5)

    except Exception as e:
        print(f"❌ Erro na sessão: {e}")
    finally:
        if driver: 
            try: driver.quit()
            except: pass

# --- LOOP MESTRE (VIGIANDO O ROBÔ) ---
while True:
    try:
        rodar_robo()
    except KeyboardInterrupt:
        print("\n🛑 Monitoramento encerrado pelo usuário.")
        break
    except Exception as e:
        print(f"⚠️ Falha crítica: {e}")
    
    print("♻️ Reiniciando sentinela em 10 segundos...")
    time.sleep(10)