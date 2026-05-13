import time
import os
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

print("--- 🚜 ROBÔ SISREG: EXTRATOR 100% AUTOMATIZADO (V36 - SMART DATES E ALERTAS) ---")

# --- CREDENCIAIS SISREG ---
USUARIO_SISREG = "20325223FRANCK"
SENHA_SISREG = "212425"

# --- LÓGICA DE DATAS AUTOMÁTICAS (DIA 01 ATÉ HOJE) ---
hoje = datetime.now()
dia_01 = hoje.replace(day=1).strftime("%d/%m/%Y")
dia_atual = hoje.strftime("%d/%m/%Y")
print(f"📅 Período configurado automaticamente: {dia_01} a {dia_atual}")

options = webdriver.ChromeOptions()
print(">> Abrindo navegador...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20) 

def fechar_alertas(navegador):
    """Verifica se há pop-ups na tela e clica em OK"""
    try:
        alerta = navegador.switch_to.alert
        texto_alerta = alerta.text
        print(f"  ⚠️ Fechando pop-up do SISREG: '{texto_alerta}'")
        alerta.accept()
        time.sleep(1)
    except NoAlertPresentException:
        pass

try:
    # 1. LOGIN AUTOMÁTICO
    print(">> Fazendo login no SISREG III...")
    driver.get("https://sisregiii.saude.gov.br/cgi-bin/index?logout=1")
    driver.maximize_window()

    wait.until(EC.presence_of_element_located((By.ID, "usuario"))).send_keys(USUARIO_SISREG)
    driver.find_element(By.ID, "senha").send_keys(SENHA_SISREG)
    
    btn_entrar = driver.find_element(By.XPATH, "//*[@id='conteudoFull']/div[1]/div[1]/div[8]/input")
    driver.execute_script("arguments[0].click();", btn_entrar)
    
    # 2. ACESSAR MENU (Altera Motivo)
    print(">> Acessando o menu de pesquisa...")
    menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(translate(text(), 'altera motivo', 'ALTERA MOTIVO'), 'ALTERA MOTIVO')]")))
    driver.execute_script("arguments[0].click();", menu)
    
    # 3. ENTRAR NO FRAME
    print(">> Entrando no Frame do SISREG...")
    wait.until(EC.frame_to_be_available_and_switch_to_it("f_principal"))
    time.sleep(2)

    # 4. PREENCHIMENTO INTELIGENTE (MAXLENGTH = 10)
    print(">> Identificando campos de data e inserindo o período...")
    inputs_texto = driver.find_elements(By.XPATH, "//input[@type='text']")
    
    # Só pega inputs que estão visíveis E que o limite de caracteres seja 10 (padrão de datas)
    inputs_data = [inp for inp in inputs_texto if inp.is_displayed() and inp.get_attribute("maxlength") == "10"]
    
    if len(inputs_data) >= 2:
        # Usamos Keys para preencher e limpar, garantindo que o sistema ative as máscaras JS
        inputs_data[0].clear()
        driver.execute_script(f"arguments[0].value = '{dia_01}';", inputs_data[0])
        
        inputs_data[1].clear()
        driver.execute_script(f"arguments[0].value = '{dia_atual}';", inputs_data[1])
    else:
        print("⚠️ Aviso: Não encontrei 2 campos com formato de data. Tentando forçar os dois primeiros...")
        # Plano B: Pega os dois primeiros que não sejam muito grandes (ignora CNS)
        inputs_curtos = [inp for inp in inputs_texto if inp.is_displayed() and (inp.get_attribute("maxlength") is None or int(inp.get_attribute("maxlength")) < 15)]
        if len(inputs_curtos) >= 2:
            driver.execute_script(f"arguments[0].value = '{dia_01}';", inputs_curtos[0])
            driver.execute_script(f"arguments[0].value = '{dia_atual}';", inputs_curtos[1])

    print(">> Pesquisando...")
    try:
        btn_pesquisar = wait.until(EC.presence_of_element_located((By.NAME, "pesquisar")))
        driver.execute_script("arguments[0].click();", btn_pesquisar)
        time.sleep(1)
        fechar_alertas(driver) # Se houver alerta de data, ele fecha e segue
    except UnexpectedAlertPresentException:
        fechar_alertas(driver)
    
    # 5. EXTRAÇÃO DA TABELA (COM PAGINAÇÃO)
    print(">> Iniciando varredura e cópia das páginas...")
    dados_totais = []
    pagina_atual = 1

    while True:
        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it("f_principal"))
        time.sleep(3) # Tempo para o banco do SISREG responder e montar a tabela
        
        print(f" 📖 Extraindo dados da Página {pagina_atual}...")
        
        try:
            linhas = driver.find_elements(By.XPATH, "//table//tr")
            linhas_extraidas = 0
            
            for linha in linhas:
                colunas = linha.find_elements(By.XPATH, "./th | ./td")
                if len(colunas) > 4: 
                    dados_linha = [col.text.strip() for col in colunas]
                    dados_totais.append(dados_linha)
                    linhas_extraidas += 1
            
            print(f"    ✔️ {linhas_extraidas} linhas copiadas desta página.")

            try:
                # Tenta achar a setinha pra direita
                btn_proxima = driver.find_element(By.XPATH, "//a[img[contains(@alt, 'Proxima') or contains(@src, 'proxima')]]")
                driver.execute_script("arguments[0].click();", btn_proxima)
                pagina_atual += 1
            except:
                print("\n✅ Fim da paginação. Última página alcançada.")
                break

        except UnexpectedAlertPresentException:
            fechar_alertas(driver)
            break
        except Exception as e:
            print(f"⚠️ Erro ao ler a tabela na página {pagina_atual}: {e}")
            break

    # 6. SALVAR EM EXCEL COM PANDAS
    print(f"\n💾 Consolidando os dados em Excel...")
    if len(dados_totais) > 0:
        df = pd.DataFrame(dados_totais)
        df = df.drop_duplicates() 
        
        nome_arquivo = f"Extracao_SISREG_FilaZero_{hoje.strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(nome_arquivo, index=False, header=False) 
        
        print("=======================================================")
        print(f"🎉 SUCESSO ABSOLUTO!")
        print(f"📊 Arquivo gerado: {nome_arquivo} com {len(df)} registros totais.")
        print("=======================================================")
    else:
        print("⚠️ Nenhuma linha de paciente foi extraída. Verifique se há dados nessa data.")

except Exception as e:
    print(f"\n❌ Erro Crítico: {e}")
finally:
    try:
        driver.quit()
    except:
        pass