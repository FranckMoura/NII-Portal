import time
import re
import os
import sys
import subprocess
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print("=====================================================")
print(" 🕵️‍♂️ MAESTRO & SENTINELA (Com Chave Composta Inteligente)")
print("=====================================================")

# --- CONFIGURAÇÕES PRINCIPAIS ---
USUARIO = "046FRANCK" 
SENHA = "212425"

# 🛑 MUDE PARA FALSE PARA VER O ROBÔ TRABALHANDO 🛑
MODO_INVISIVEL = False

# 👉 Quantidade de dias que o robô vai ler na tela a cada 30 min
DIAS_BUSCA = 30 

# Tempo de espera entre os ciclos de varredura (1800 segundos = 30 minutos)
TEMPO_ESPERA = 1800 

# --- SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
TABELA_DESTINO = "regulacao"  
TABELA_NOTIFICACOES = "notificacoes" 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    print("❌ Erro ao conectar no Supabase.")
    exit()

def configurar_navegador():
    chrome_options = Options()
    if MODO_INVISIVEL:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.page_load_strategy = 'eager' 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--log-level=3")
    
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=chrome_options)
    driver.set_page_load_timeout(300) 
    return driver

def focar_conteudo(driver):
    driver.switch_to.default_content()
    if driver.find_elements(By.XPATH, "//input[@value='PESQUISAR']") or driver.find_elements(By.CLASS_NAME, "lista"): 
        return True
    frames = driver.find_elements(By.TAG_NAME, "frame") + driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(frame)
            if driver.find_elements(By.XPATH, "//input[@value='PESQUISAR']") or driver.find_elements(By.CLASS_NAME, "lista"):
                return True
        except: pass
    return False

def limpar_string(texto):
    if not texto: return ""
    return re.sub(r'\s+', ' ', str(texto)).strip().upper()

def rodar_ciclo_monitoramento():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Iniciando patrulha de {DIAS_BUSCA} dias...")
    driver = None
    
    try:
        print("   🧠 Puxando memória do banco (Tabela Regulação)...")
        # AGORA PUXAMOS PROCEDIMENTO E CLÍNICA PARA A CHAVE COMPOSTA
        res_db = supabase.table(TABELA_DESTINO).select("num_solicitacao, nome_paciente, status, num_aih, procedimento, nome_clinica").execute()
        
        mapa_pacientes = {}
        for r in res_db.data:
            if r.get('nome_paciente') and r.get('num_solicitacao'):
                nome_limpo = limpar_string(r['nome_paciente'])
                
                # Permite múltiplos pedidos para o mesmo paciente
                if nome_limpo not in mapa_pacientes:
                    mapa_pacientes[nome_limpo] = []
                    
                mapa_pacientes[nome_limpo].append({
                    'num_solicitacao': r['num_solicitacao'],
                    'status': (r.get('status') or 'PENDENTE').upper(),
                    'num_aih': r.get('num_aih'),
                    'procedimento': limpar_string(r.get('procedimento')),
                    'clinica': limpar_string(r.get('nome_clinica'))
                })

        driver = configurar_navegador()
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
        time.sleep(3)

        print("   🔑 Autenticando...")
        driver.find_element(By.NAME, "usuario").send_keys(USUARIO)
        driver.find_element(By.NAME, "senha").send_keys(SENHA)
        try: driver.find_element(By.CSS_SELECTOR, "input[type='image']").click()
        except: driver.find_element(By.CSS_SELECTOR, "div.form-no-lbl > input").click()
        time.sleep(3)

        print("   🧭 Acessando tela HTML de pesquisa...")
        driver.get("https://sisregiii.saude.gov.br/cgi-bin/cons_aih") 
        time.sleep(4)
        focar_conteudo(driver)

        hoje = datetime.now()
        dias_atras = hoje - timedelta(days=DIAS_BUSCA)
        d1 = dias_atras.strftime("%d/%m/%Y")
        d2 = hoje.strftime("%d/%m/%Y")

        try:
            driver.execute_script(f"document.getElementsByName('dt_inicial_sol')[0].value = '{d1}';")
            driver.execute_script(f"document.getElementsByName('dt_final_sol')[0].value = '{d2}';")
            btn = driver.find_element(By.XPATH, "//input[@value='PESQUISAR']")
            driver.execute_script("arguments[0].click();", btn)
        except Exception as e:
            print(f"   ❌ Falha ao pesquisar: {e}")
            return

        print("   ⏳ Lendo páginas e analisando status...")
        time.sleep(8) 
        
        atualizados = 0
        lote_atualizacao = []
        lote_notificacoes = []
        pagina_atual = 1

        while True:
            focar_conteudo(driver)
            linhas = driver.find_elements(By.XPATH, "//table[contains(@class, 'lista')]//tr[td]")
            
            if not linhas: break

            pacientes_lidos_na_pagina = 0
            pacientes_cruzados_com_banco = 0

            for linha in linhas:
                if "Usuário" in linha.text: continue
                cols = linha.find_elements(By.TAG_NAME, "td")
                if len(cols) < 7: continue 
                
                pacientes_lidos_na_pagina += 1
                
                # DADOS DA TELA
                nome_paciente = limpar_string(cols[1].text)
                proc_tela = limpar_string(cols[2].text)
                clinica_tela = limpar_string(cols[3].text)
                texto_aih = cols[5].text.strip()
                texto_status = cols[6].text.strip().upper()
                
                if nome_paciente in mapa_pacientes:
                    lista_solicitacoes = mapa_pacientes[nome_paciente]
                    req_alvo = None
                    
                    # O DETETIVE: Encontra o pedido exato do paciente
                    if len(lista_solicitacoes) == 1:
                        req_alvo = lista_solicitacoes[0]
                    else:
                        codigo_proc_tela = proc_tela.split('-')[0].strip() if '-' in proc_tela else proc_tela[:10]
                        for req in lista_solicitacoes:
                            if codigo_proc_tela in req['procedimento']:
                                req_alvo = req
                                break
                        if not req_alvo:
                            for req in lista_solicitacoes:
                                if clinica_tela in req['clinica'] or req['clinica'] in clinica_tela:
                                    req_alvo = req
                                    break
                    
                    if req_alvo:
                        pacientes_cruzados_com_banco += 1
                        status_banco = req_alvo['status']
                        
                        status_tela = "PENDENTE"
                        if "AUTORIZAD" in texto_status or "APROVAD" in texto_status: status_tela = "APROVADO"
                        elif "NEGAD" in texto_status or "CANCELAD" in texto_status or "DEVOLVID" in texto_status: status_tela = "NEGADO"

                        if status_tela != status_banco and status_tela != "PENDENTE":
                            registro_update = {
                                "num_solicitacao": req_alvo['num_solicitacao'],
                                "status": status_tela,
                                "data_atualizacao": datetime.now().isoformat()
                            }
                            if "*" not in texto_aih and len(texto_aih) > 5:
                                registro_update["num_aih"] = re.sub(r'[^0-9]', '', texto_aih)

                            lote_atualizacao.append(registro_update)
                            
                            lote_notificacoes.append({
                                "paciente": nome_paciente,
                                "num_solicitacao": req_alvo['num_solicitacao'],
                                "status_novo": status_tela
                            })

                            # Atualiza a memória local para não disparar duplicado
                            req_alvo['status'] = status_tela
                            atualizados += 1

            print(f"      📄 Página {pagina_atual} processada: Lidos={pacientes_lidos_na_pagina} | Achados no Banco={pacientes_cruzados_com_banco}")

            try:
                script_js = f"""
                var totalPaginas = 1;
                var inputPagina = document.querySelector("input[name='txtPagina']");
                if (inputPagina && inputPagina.nextSibling) {{
                    var texto = inputPagina.parentElement.innerText;
                    var match = texto.match(/de (\\d+)/); 
                    if (match) totalPaginas = parseInt(match[1]);
                }}
                
                if ({pagina_atual} < totalPaginas) {{
                    if (typeof exibirPagina === 'function') {{
                        exibirPagina({pagina_atual}, totalPaginas);
                        return true;
                    }}
                }}
                return false;
                """
                sucesso_mudanca = driver.execute_script(script_js)

                if sucesso_mudanca:
                    pagina_atual += 1
                    time.sleep(6) 
                else:
                    print("      🏁 Fim das páginas atingido.")
                    break
            except Exception as e:
                print(f"      🏁 Erro ao tentar mudar de página ({e})")
                break

        if lote_atualizacao:
            print(f"   🔔 Disparando {atualizados} atualizações/notificações para o Painel...")
            
            for reg in lote_atualizacao:
                id_sol = reg.pop('num_solicitacao') 
                supabase.table(TABELA_DESTINO).update(reg).eq('num_solicitacao', id_sol).execute()

            supabase.table(TABELA_NOTIFICACOES).insert(lote_notificacoes).execute()
            print("   ✅ Banco atualizado com sucesso!")
        else:
            print("   💤 Nenhuma mudança de status nova encontrada nesta varredura.")

    except Exception as e:
        print(f"   ⚠️ Ciclo interrompido por erro técnico: {e}")
        
    finally:
        if driver: driver.quit()


# ==========================================================
# 🧠 O CÉREBRO: ORQUESTRADOR GERAL (MAESTRO)
# ==========================================================
print("\n⚙️ Maestro de Automação Ativado. Pressione CTRL+C para parar.")

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOADS = os.path.join(PASTA_BASE, "downloads")
SCRIPT_EXTRACAO = os.path.join(PASTA_BASE, "extrator_sisreg_v18.py")
SCRIPT_PROCESSAMENTO = os.path.join(PASTA_BASE, "processador_regulacao_v21.py")
PYTHON_EXEC = sys.executable

dia_atual = datetime.now().day
extracao_realizada_hoje = False

while True:
    try:
        agora = datetime.now()

        # 1. Reseta a memória se virou o dia (meia-noite)
        if agora.day != dia_atual:
            extracao_realizada_hoje = False
            dia_atual = agora.day

        # 2. RODA O MONITORAMENTO SILENCIOSO (Sentinela Diurno)
        rodar_ciclo_monitoramento()

        # 3. VERIFICA SE É HORA DA EXTRAÇÃO PESADA (Corujão CSV)
        # Horário liberado em Cuiabá é após as 16:00. 
        if agora.hour >= 16 and not extracao_realizada_hoje:
            print(f"\n[🕒 {agora.strftime('%H:%M:%S')}] INICIANDO ROTINA DE FIM DE EXPEDIENTE (CSV)...")
            
            # Limpa a pasta de downloads
            print("   🧹 Limpando arquivos CSV antigos da pasta...")
            if os.path.exists(PASTA_DOWNLOADS):
                for arquivo in glob.glob(os.path.join(PASTA_DOWNLOADS, "*.csv")):
                    try: os.remove(arquivo)
                    except: pass

            # Executa a Extração
            if os.path.exists(SCRIPT_EXTRACAO):
                print("   🚜 Acionando o Trator de Extração...")
                subprocess.run([PYTHON_EXEC, SCRIPT_EXTRACAO], check=True)
            else:
                print(f"   ⚠️ Script não encontrado: {SCRIPT_EXTRACAO}")

            # Executa o Processamento
            if os.path.exists(SCRIPT_PROCESSAMENTO):
                print("   🗄️ Acionando o Processador de Dados...")
                subprocess.run([PYTHON_EXEC, SCRIPT_PROCESSAMENTO], check=True)
            else:
                print(f"   ⚠️ Script não encontrado: {SCRIPT_PROCESSAMENTO}")

            print("   ✅ Rotina de fim de expediente concluída com sucesso!")
            extracao_realizada_hoje = True # Marca que já fez hoje

        # 4. DORME ATÉ O PRÓXIMO CICLO
        print(f"\n💤 Ciclo finalizado. O Maestro vai dormir por {TEMPO_ESPERA // 60} minutos...")
        time.sleep(TEMPO_ESPERA)

    except KeyboardInterrupt:
        print("\n🛑 Maestro desligado pelo usuário.")
        break
    except Exception as e:
        print(f"\n❌ Erro fatal no orquestrador: {e}")
        time.sleep(60)