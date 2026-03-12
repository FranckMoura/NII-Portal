import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print("--- ⛏️ GARIMPEIRO V40 (MODO IMPARÁVEL) ---")
print(">> Se travar (CAPTCHA/Rede), ele PAUSA e espera você resolver.")

# --- CONFIGURAÇÕES ---
USUARIO = "20325223FRANCK" 
SENHA = "515462"

# --- SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
TABELA_DESTINO = "historico_aih"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    print("⚠️ Supabase Offline.")
    supabase = None

# --- FUNÇÕES ---

def esperar(segundos):
    time.sleep(segundos)

def limpar_texto(texto):
    if not texto: return None
    return re.sub(r'[\\/*?:"<>|]', "", texto).strip()

def formatar_data(data_str):
    if not data_str: return None
    data_str = data_str.split('-')[0].strip()
    data_str = data_str.replace('.', '/')
    try: return datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except: return None

def focar_conteudo(driver):
    driver.switch_to.default_content()
    if driver.find_elements(By.CLASS_NAME, "lista"): return True
    frames = driver.find_elements(By.TAG_NAME, "frame") + driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(frame)
            if driver.find_elements(By.CLASS_NAME, "lista"): return True
        except: pass
    return False

def detectar_pagina(driver):
    if focar_conteudo(driver):
        try:
            val = driver.find_element(By.NAME, "txtPagina").get_attribute("value")
            if val.isdigit(): return int(val)
        except: pass
    return 0

def pegar_valor_abaixo_rotulo(ficha, texto_rotulo, indice_coluna=0):
    try:
        rotulo = ficha.find_element(By.XPATH, f".//td[contains(., '{texto_rotulo}')]")
        tr_valor = rotulo.find_element(By.XPATH, "./parent::tr/following-sibling::tr[1]")
        celulas = tr_valor.find_elements(By.TAG_NAME, "td")
        if len(celulas) > indice_coluna:
            return celulas[indice_coluna].text.strip()
        elif celulas:
            return celulas[0].text.strip()
    except:
        return None
    return None

def extrair_dados_completo(driver, aih, nome, proc):
    dados = {
        "num_aih": aih, "nome_paciente": nome, "procedimento": proc,
        "num_solicitacao": None, "cid_principal": None, "municipio_residencia": None,
        "data_internacao": None, "data_alta": None, "motivo_alta": None, "cns": None,
        "nome_mae": None, "data_nascimento": None, "sexo": None, "raca_cor": None,
        "telefone": None, "nome_medico_solicitante": None, "laudo_clinico": None,
        "data_solicitacao": None, "data_autorizacao": None, "carater_internacao": None
    }
    
    try:
        wait = WebDriverWait(driver, 5)
        ficha = wait.until(EC.visibility_of_element_located((By.ID, "fichaInternacao")))
        texto_full = ficha.text

        # 1. Identificação
        dados['nome_mae'] = pegar_valor_abaixo_rotulo(ficha, "Nome da M", 0)
        dados['sexo'] = pegar_valor_abaixo_rotulo(ficha, "Sexo:", 0)
        dados['raca_cor'] = pegar_valor_abaixo_rotulo(ficha, "Sexo:", 1)
        raw_nasc = pegar_valor_abaixo_rotulo(ficha, "Data de Nascimento:", 0)
        if raw_nasc: dados['data_nascimento'] = raw_nasc.split('(')[0].strip()

        # 2. Localização
        mun = pegar_valor_abaixo_rotulo(ficha, "Município de Residência", 1)
        if mun and "BRASIL" not in mun: dados['municipio_residencia'] = mun
        else: dados['municipio_residencia'] = pegar_valor_abaixo_rotulo(ficha, "Município de Residência", 0)
        dados['telefone'] = pegar_valor_abaixo_rotulo(ficha, "Telefone(s):", 0)

        # 3. Clínico
        dados['nome_medico_solicitante'] = pegar_valor_abaixo_rotulo(ficha, "Nome do M", 1)
        dados['laudo_clinico'] = pegar_valor_abaixo_rotulo(ficha, "Principais Sinais e Sintomas", 0)
        dados['carater_internacao'] = pegar_valor_abaixo_rotulo(ficha, "Caráter", 0)

        # 4. Auditoria
        m_sol = re.search(r'C[oó]digo Solicita[cç][aã]o[:\s]*(\d+)', texto_full)
        if m_sol: dados['num_solicitacao'] = m_sol.group(1)

        raw_dt_sol = pegar_valor_abaixo_rotulo(ficha, "Data de Solicita", 1)
        if raw_dt_sol: dados['data_solicitacao'] = formatar_data(raw_dt_sol)
        
        raw_dt_aut = pegar_valor_abaixo_rotulo(ficha, "Data de Autoriza", 1)
        if raw_dt_aut: dados['data_autorizacao'] = formatar_data(raw_dt_aut)

        # 5. Legado
        cns_raw = pegar_valor_abaixo_rotulo(ficha, "CNS:")
        if cns_raw: dados['cns'] = re.sub(r'[^\d]', '', cns_raw)

        m_dt_int = re.search(r'Data d[ae] Interna[cç][aã]o.*?(\d{2}[\./]\d{2}[\./]\d{4})', texto_full, re.IGNORECASE)
        if m_dt_int: dados['data_internacao'] = formatar_data(m_dt_int.group(1))
        
        m_alta = re.search(r'Data d[ae] Alta.*?(\d{2}[\./]\d{2}[\./]\d{4})', texto_full, re.IGNORECASE)
        if m_alta: dados['data_alta'] = formatar_data(m_alta.group(1))

    except: pass
    return dados

# --- MOTOR ---
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.maximize_window()
actions = ActionChains(driver)

print(">> Acessando login...")
driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
esperar(3)

# LOGIN
try:
    print(f">> Logando como {USUARIO}...")
    driver.find_element(By.NAME, "usuario").send_keys(USUARIO)
    driver.find_element(By.NAME, "senha").send_keys(SENHA)
    try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
    except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
    esperar(3)
except:
    print("❌ Falha no login automático. Faça manual.")

# PAUSA CYBORG
print("\n" + "="*60)
print("🛑 MODO CYBORG")
print("1. Vá em Consultas > AIH Gerada > Filtre > Pesquise.")
print("2. Vá para a página onde parou.")
print("="*60)
input(">> APERTE ENTER PARA INICIAR...")

print("\n🚀 ROBÔ INICIADO!")

paginas_processadas = 0
total_atualizados = 0

try:
    while True:
        pag_atual = detectar_pagina(driver)
        print(f"\n>>> PROCESSANDO PÁGINA {pag_atual} <<<")
        
        focar_conteudo(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        linhas = driver.find_elements(By.XPATH, "//table[contains(@class, 'lista')]//tr[td]")
        if not linhas:
            print(">> Fim da lista detectada (ou erro).")
            # Aqui também pode ser um momento de pausa se for um erro de carregamento
            # mas geralmente se não tem linhas, é o fim mesmo ou a sessão caiu.
            
        count = len(linhas)
        for i in range(count):
            try:
                focar_conteudo(driver)
                linhas = driver.find_elements(By.XPATH, "//table[contains(@class, 'lista')]//tr[td]")
                if i >= len(linhas): break
                
                linha = linhas[i]
                if "Usuário" in linha.text: continue
                
                cols = linha.find_elements(By.TAG_NAME, "td")
                if len(cols) < 6: continue
                
                nome = limpar_texto(cols[1].text)
                proc = limpar_texto(cols[2].text)
                aih_raw = cols[5].text
                aih = re.sub(r'[^0-9]', '', aih_raw)
                
                print(f"[{i+1}/{count}] {nome}...", end="")
                
                # Check DB
                processar = True
                if supabase:
                    res = supabase.table(TABELA_DESTINO).select("*").eq("num_aih", aih).execute()
                    if res.data:
                        d = res.data[0]
                        # Critério Big Data
                        tem_mae = d.get('nome_mae') and len(d.get('nome_mae')) > 3
                        tem_carater = d.get('carater_internacao')
                        tem_cns = d.get('cns') and len(d.get('cns')) > 10
                        
                        if tem_mae and tem_carater and tem_cns:
                            print(" [OK] Pula.")
                            processar = False
                        else:
                            print(" [ATUALIZAR]...", end="")
                
                if processar:
                    driver.execute_script("arguments[0].scrollIntoView(true);", linha)
                    try: linha.click()
                    except: driver.execute_script("arguments[0].click();", linha)
                    esperar(1.5)
                    
                    try:
                        if driver.find_elements(By.ID, "fichaInternacao"):
                            dados = extrair_dados_completo(driver, aih, nome, proc)
                            
                            if dados['num_solicitacao']:
                                if supabase:
                                    dados['data_mineracao'] = datetime.now().isoformat()
                                    dados['status'] = 'APROVADO'
                                    supabase.table(TABELA_DESTINO).upsert(dados, on_conflict="num_aih").execute()
                                    
                                    tipo = (dados['carater_internacao'] or "?")[:3]
                                    print(f" ✅ Salvo! (Tipo:{tipo} | Sol:{dados['num_solicitacao']})")
                                    total_atualizados += 1
                                else:
                                    print(" (Lido)")
                            else:
                                print(" ❌ Falha leitura.")
                            
                            focar_conteudo(driver)
                            btns = driver.find_elements(By.XPATH, "//input[@value='VOLTAR']")
                            if btns: btns[0].click()
                            else: driver.back()
                            esperar(1)
                    except:
                        driver.back(); esperar(1)

            except:
                driver.back(); esperar(1)

        paginas_processadas += 1

        # --- NAVEGAÇÃO SEGURA COM PAUSA ---
        print(">> Próxima página...")
        focar_conteudo(driver)
        setas = driver.find_elements(By.XPATH, "//img[contains(@src, 'prox') or contains(@src, 'direita')]/parent::a")
        
        navegacao_sucesso = False
        
        if setas:
            # Tenta clicar
            try: driver.execute_script("arguments[0].click();", setas[0])
            except: setas[0].click()
            esperar(4)
            
            # Verifica se mudou
            if detectar_pagina(driver) != pag_atual:
                navegacao_sucesso = True
            else:
                print("⚠️ Travou. Tentando de novo...")
                focar_conteudo(driver)
                setas = driver.find_elements(By.XPATH, "//img[contains(@src, 'prox') or contains(@src, 'direita')]/parent::a")
                if setas: 
                    driver.execute_script("arguments[0].click();", setas[0])
                    esperar(5)
                    if detectar_pagina(driver) != pag_atual:
                        navegacao_sucesso = True

        # SE FALHAR (CAPTCHA ou FIM) -> PAUSA PARA HUMANO
        if not navegacao_sucesso:
            print("\n" + "!"*60)
            print("🛑 ATENÇÃO HUMANO! O robô não conseguiu avançar.")
            print("Pode ser:")
            print("1. Fim da lista (Verifique se acabaram as páginas).")
            print("2. CAPTCHA apareceu.")
            print("3. Erro de carregamento.")
            print("-" * 60)
            print(">> AÇÃO: Vá ao navegador e resolva.")
            print(">> Se tiver mais páginas, avance manualmente para a próxima.")
            print(">> Se acabou, pode fechar o script.")
            print("!"*60)
            input(">> APERTE ENTER AQUI QUANDO ESTIVER NA PRÓXIMA PÁGINA PARA CONTINUAR...")
            print("🚀 Retomando...")
            # O loop vai reiniciar, ler a página atual e continuar

except Exception as e:
    print(f"❌ Erro Geral: {e}")

finally:
    print(f"\n📊 RESUMO: {paginas_processadas} págs | {total_atualizados} salvos.")
    if driver: driver.quit()