import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

print("--- 🩺 ROBÔ CIRURGIÃO: CORREÇÃO DE DATA DE NASCIMENTO ---")

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
USUARIO_INDICASUS = "046.941.841-99"
SENHA_INDICASUS = "@ntoniO22"

try: 
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar Supabase: {e}"); exit()

# 1. Puxa do banco quem tem data de nascimento suspeita (2024, 2025 ou 2026)
print(">> Consultando banco de dados por anomalias...")
pacientes_com_erro = []
try:
    res = supabase.table("indicasus_leitos").select("nome_paciente, data_internacao").gte("data_nascimento", "2024-01-01").execute()
    # Remove duplicados (pois o paciente tem várias diárias)
    vistos = set()
    for p in res.data:
        chave = (p['nome_paciente'], p['data_internacao'])
        if chave not in vistos:
            vistos.add(chave)
            pacientes_com_erro.append(p)
            
    print(f"⚠️ Encontrados {len(pacientes_com_erro)} pacientes com Data de Nascimento suspeita.")
    if len(pacientes_com_erro) == 0:
        print("Tudo certo! Saindo."); exit()
except Exception as e:
    print(f"Erro ao ler banco: {e}"); exit()

options = webdriver.ChromeOptions()
try:
    print(">> Abrindo navegador...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    driver.get("https://sistemas.saude.mt.gov.br/")
    driver.maximize_window()
    try: driver.find_element(By.XPATH, "//button[contains(text(), '×')]").click()
    except: pass

    wait.until(EC.presence_of_element_located((By.ID, "CPF"))).send_keys(USUARIO_INDICASUS)
    driver.find_element(By.ID, "Senha").send_keys(SENHA_INDICASUS + Keys.RETURN)
    time.sleep(5)

    print(">> Corrigindo pacientes um a um...")
    for idx, pac in enumerate(pacientes_com_erro):
        nome = pac['nome_paciente']
        print(f"[{idx+1}/{len(pacientes_com_erro)}] Corrigindo {nome}...")
        
        # Pesquisa diretamente o paciente
        driver.get("https://sistemas.saude.mt.gov.br/Administracao/InternacaoGeral?limpar=1")
        try: wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading"))) 
        except: pass
        
        driver.find_element(By.ID, "btnFiltro").click()
        time.sleep(1)
        driver.execute_script("document.getElementById('DataInternacaoInicial').value = ''; document.getElementById('DataInternacaoFinal').value = '';")
        
        js_busca = f"""
        var inputs = document.querySelectorAll('input[type="text"]');
        for(var i=0; i<inputs.length; i++) {{
            if(inputs[i].id.toLowerCase().includes('nome')) inputs[i].value = '{nome}';
        }}
        """
        driver.execute_script(js_busca)
        driver.execute_script("$('select').selectpicker('val', 'Todos'); $('select').selectpicker('refresh');")
        driver.find_element(By.ID, "btnFiltrar").click()
        
        try: wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading"))) 
        except: pass
        time.sleep(2)
        
        try:
            # Clica no botão de edição
            btn = driver.find_element(By.XPATH, "//*[@id='resultadoInternacaoGeral']/tbody/tr[1]//a[contains(@class, 'btn-warning')]")
            driver.get(btn.get_attribute("href"))
            time.sleep(2)
            
            # A caçada precisa e absoluta da Data de Nascimento
            dt_nasc_certa = None
            # Procura especificamente o campo com ID ou Name que seja exatamente a data de nascimento do paciente
            js_nasc = """
            var inps = document.querySelectorAll('input');
            for(var i=0; i<inps.length; i++) {
                var n = (inps[i].name || '').toLowerCase();
                var id = (inps[i].id || '').toLowerCase();
                if(n === 'datanascimento' || id === 'datanascimento' || n === 'paciente.datanascimento') {
                    return inps[i].value;
                }
            }
            return null;
            """
            valor_nasc = driver.execute_script(js_nasc)
            
            if valor_nasc and len(valor_nasc) == 10:
                # Converte dd/mm/yyyy para yyyy-mm-dd
                from datetime import datetime
                dt_nasc_certa = datetime.strptime(valor_nasc, "%d/%m/%Y").strftime("%Y-%m-%d")
                
                # UPDATE no banco de dados!
                supabase.table("indicasus_leitos").update({"data_nascimento": dt_nasc_certa}).eq("nome_paciente", nome).eq("data_internacao", pac['data_internacao']).execute()
                print(f"  ✅ Corrigido para: {dt_nasc_certa}")
            else:
                print("  ⚠️ Campo de nascimento não encontrado na página.")
                
        except Exception as e:
            print(f"  ❌ Falha ao abrir/corrigir perfil: {e}")

    print("\n🎉 CORREÇÃO CONCLUÍDA!")

except Exception as e:
    print(f"Erro Crítico: {e}")
finally:
    try: driver.quit()
    except: pass