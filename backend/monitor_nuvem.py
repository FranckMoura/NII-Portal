import time
import re
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print("=====================================================")
print(" 🕵️‍♂️ SENTINELA NUVEM (GitHub Actions)")
print("=====================================================")

USUARIO = os.environ.get("SISREG_USER", "046FRANCK")
SENHA = os.environ.get("SISREG_PASS", "212425")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://voweywtzoldwfhgkniup.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

TABELA_DESTINO = "regulacao"  
TABELA_NOTIFICACOES = "notificacoes" 
DIAS_BUSCA = 30 

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    print("❌ Erro ao conectar no Supabase.")
    exit()

def configurar_navegador():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # OBRIGATÓRIO NA NUVEM
    chrome_options.page_load_strategy = 'eager' 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox") # OBRIGATÓRIO NA NUVEM (LINUX)
    chrome_options.add_argument("--disable-dev-shm-usage") # OBRIGATÓRIO NA NUVEM
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

def limpar_nome_para_cruzamento(nome):
    if not nome: return ""
    return re.sub(r'\s+', ' ', str(nome)).strip().upper()

def rodar_ciclo_monitoramento():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Iniciando patrulha de {DIAS_BUSCA} dias...")
    driver = None
    
    try:
        print("   🧠 Puxando memória do banco (Tabela Regulação)...")
        res_db = supabase.table(TABELA_DESTINO).select("num_solicitacao, nome_paciente, status, num_aih").execute()
        
        mapa_pacientes = {}
        for r in res_db.data:
            if r.get('nome_paciente') and r.get('num_solicitacao'):
                nome_limpo = limpar_nome_para_cruzamento(r['nome_paciente'])
                mapa_pacientes[nome_limpo] = {
                    'num_solicitacao': r['num_solicitacao'],
                    'status': (r.get('status') or 'PENDENTE').upper(),
                    'num_aih': r.get('num_aih')
                }

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
                nome_bruto_tela = cols[1].text
                nome_paciente = limpar_nome_para_cruzamento(nome_bruto_tela)
                texto_status = cols[6].text.strip().upper()
                texto_aih = cols[5].text.strip()
                
                if nome_paciente in mapa_pacientes:
                    pacientes_cruzados_com_banco += 1
                    db_info = mapa_pacientes[nome_paciente]
                    status_banco = db_info['status']
                    
                    status_tela = "PENDENTE"
                    if "AUTORIZAD" in texto_status or "APROVAD" in texto_status: status_tela = "APROVADO"
                    elif "NEGAD" in texto_status or "CANCELAD" in texto_status or "DEVOLVID" in texto_status: status_tela = "NEGADO"

                    if status_tela != status_banco and status_tela != "PENDENTE":
                        registro_update = {
                            "num_solicitacao": db_info['num_solicitacao'],
                            "status": status_tela,
                            "data_atualizacao": datetime.now().isoformat()
                        }
                        if "*" not in texto_aih and len(texto_aih) > 5:
                            registro_update["num_aih"] = re.sub(r'[^0-9]', '', texto_aih)

                        lote_atualizacao.append(registro_update)
                        
                        lote_notificacoes.append({
                            "paciente": nome_paciente,
                            "num_solicitacao": db_info['num_solicitacao'],
                            "status_novo": status_tela
                        })

                        mapa_pacientes[nome_paciente]['status'] = status_tela
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
            print("   💤 Nenhuma mudança de status encontrada nesta varredura.")

    except Exception as e:
        print(f"   ⚠️ Ciclo interrompido por erro técnico: {e}")
        
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    rodar_ciclo_monitoramento()