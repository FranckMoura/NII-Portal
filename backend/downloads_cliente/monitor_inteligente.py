import os
import sys
import json
import time
import csv
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

print("=====================================================")
print(" 🕵️‍♂️ MAESTRO & TRATOR (Automação HUJM - Versão Final) ")
print("=====================================================")

if getattr(sys, 'frozen', False): 
    app_path = os.path.dirname(sys.executable)
else: 
    app_path = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(app_path, "config.json")

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    SB_URL = config['supabase']['url'].strip()
    if not SB_URL.startswith('http'):
        SB_URL = 'https://' + SB_URL
    if SB_URL.endswith('/'):
        SB_URL = SB_URL[:-1]
        
    SB_KEY = config['supabase']['key'].strip()
    NOME_HOSPITAL = config['hospital']['nome']
    
except FileNotFoundError:
    print("❌ ERRO: Arquivo config.json não encontrado na pasta!")
    time.sleep(5)
    sys.exit()
except KeyError as e:
    print(f"❌ ERRO: Configuração incompleta no config.json. Falta a chave: {e}")
    time.sleep(5)
    sys.exit()

print(f"[🕒 {datetime.now().strftime('%H:%M:%S')}] Conectando ao banco seguro de: {NOME_HOSPITAL}")
try:
    supabase: Client = create_client(SB_URL, SB_KEY)
    print("✅ Ligação com Supabase estabelecida com sucesso!")
except Exception as e:
    print(f"❌ Erro ao ligar ao Supabase: {e}")
    sys.exit()

PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\downloads_cliente"

if not os.path.exists(PASTA_DOWNLOAD):
    print(f"⚠️ A pasta {PASTA_DOWNLOAD} não existe. Execute a extração primeiro.")
    sys.exit()

def limpar_nome_coluna(col):
    c = str(col).strip().upper()
    c = c.replace('Ã§Ã£', 'CA').replace('Ã§', 'C').replace('Ã£', 'A').replace('Ã¡', 'A').replace('Ã\xad', 'I').replace('Ã©', 'E').replace('Ãª', 'E')
    return c

def processar_ficheiros():
    arquivos = [f for f in os.listdir(PASTA_DOWNLOAD) if (f.endswith('.xls') or f.endswith('.csv')) and not f.startswith('index')]
    
    if not arquivos:
        print(">> Nenhum ficheiro novo encontrado na pasta para processar.")
        return

    print(f"\n🧠 Puxando memória do banco (Tabela Regulação) para detectar mudanças...")
    status_db = {}
    keep_fetching = True
    start = 0
    step = 1000
    
    # Baixa o status de todos os pacientes que já estão no banco para comparar depois
    while keep_fetching:
        resp = supabase.table('regulacao').select('num_aih, num_solicitacao, status').range(start, start + step - 1).execute()
        data = resp.data
        if data:
            for r in data:
                k = r.get('num_aih') or r.get('num_solicitacao')
                if k:
                    status_db[str(k).strip()] = str(r.get('status', '')).upper()
            start += step
            print(f"   ... memorizando {start} registros...")
        if not data or len(data) < step:
            keep_fetching = False
            
    print(f"✅ Memória carregada: {len(status_db)} pacientes conhecidos.")
    print(f"\n🚜 Lendo arquivos e analisando status...")

    todas_notificacoes = {}
    total_pacientes_atualizados = 0

    for arquivo in arquivos:
        caminho_completo = os.path.join(PASTA_DOWNLOAD, arquivo)
        
        try:
            is_html = False
            try:
                df = pd.read_html(caminho_completo, decimal=',', thousands='.')[0]
                is_html = True
            except: pass

            if not is_html:
                with open(caminho_completo, 'r', encoding='latin1', errors='ignore') as f:
                    linhas = f.readlines()
                header_idx = 0
                for i, linha in enumerate(linhas):
                    if 'PACIENTE' in linha.upper() or 'SOLICITA' in linha.upper():
                        header_idx = i
                        break
                df = pd.read_csv(caminho_completo, sep=';', encoding='latin1', skiprows=header_idx, on_bad_lines='skip', quoting=csv.QUOTE_NONE, engine='python')

            df.columns = [limpar_nome_coluna(c) for c in df.columns]
            registos_dict = {}
            
            for index, row in df.iterrows():
                cod_sol = str(row.get('N. DA SOLICITACAO', row.get('SOLICITACAO', row.get('Nº SOLICITACAO', '')))).strip().replace('"', '')
                aih = str(row.get('N. AIH', row.get('AIH', ''))).strip().replace('"', '')
                
                if cod_sol.endswith('.0'): cod_sol = cod_sol[:-2]
                if aih.endswith('.0'): aih = aih[:-2]

                palavras_proibidas = ['APROVAD', 'PENDENT', 'DEVOLVID', 'NEGAD', 'CANCELAD']
                if any(p in cod_sol.upper() for p in palavras_proibidas) or cod_sol.isalpha():
                    cod_sol = ''

                chave_primaria = aih if (aih and aih.lower() != 'nan' and aih != '0' and aih != '') else cod_sol

                if not chave_primaria or chave_primaria.lower() in ['nan', '0', '']: continue 

                cod_sol_db = cod_sol if (cod_sol and cod_sol.lower() not in ['nan', '0', '']) else None
                nome_paciente = str(row.get('NOME DO PACIENTE', row.get('PACIENTE', ''))).replace('"', '').strip()
                status_limpo = str(row.get('STATUS DA SOLICITACAO DE INTERNACAO', row.get('SITUACAO', ''))).replace('"', '').strip()

                # ========================================================
                # O CÉREBRO SENTINELA (DETECTA MUDANÇAS PARA NOTIFICAR)
                # ========================================================
                if chave_primaria in status_db:
                    status_antigo = status_db[chave_primaria]
                    status_novo_upper = status_limpo.upper()
                    
                    # Se o status mudou, gera o alerta para o sininho do HTML
                    if status_antigo != status_novo_upper and status_novo_upper not in ['', 'NAN', 'NONE', '-']:
                        # Ignora se mudou apenas uma letra mas o significado é o mesmo (ex: Aprovado vs Aprovada)
                        if not (("APROV" in status_antigo and "APROV" in status_novo_upper) or ("NEGAD" in status_antigo and "NEGAD" in status_novo_upper)):
                            todas_notificacoes[chave_primaria] = {
                                "paciente": nome_paciente,
                                "status_novo": status_novo_upper,
                                "lida": False
                            }
                # ========================================================

                registo = {
                    "num_aih": chave_primaria,
                    "num_solicitacao": cod_sol_db,
                    "nome_paciente": nome_paciente,
                    "cns_paciente": str(row.get('CNS DO PACIENTE', row.get('CNS', ''))).replace('"', '').strip(),
                    "status": status_limpo,
                    "carater_internacao": str(row.get('CARATER INTERNACAO', row.get('CARATER', ''))).replace('"', '').strip(),
                    "nome_clinica": str(row.get('NOME DA CLINICA', row.get('CLINICA', ''))).replace('"', '').strip(),
                    "data_atualizacao": datetime.now().isoformat()
                }
                
                d_sol_raw = row.get('DATA DA SOLICITACAO', row.get('DATA SOLICITACAO', ''))
                try:
                    if pd.notna(d_sol_raw) and str(d_sol_raw).strip() != '':
                        registo["data_solicitacao"] = pd.to_datetime(str(d_sol_raw).replace('"', '').strip(), format='%d/%m/%Y', errors='coerce').strftime('%Y-%m-%d')
                except: pass
                
                d_aut_raw = row.get('DATA DA AUTORIZACAO', row.get('DATA AUTORIZACAO', ''))
                try:
                    if pd.notna(d_aut_raw) and str(d_aut_raw).strip() != '':
                        registo["data_autorizacao"] = pd.to_datetime(str(d_aut_raw).replace('"', '').strip(), format='%d/%m/%Y', errors='coerce').strftime('%Y-%m-%d')
                except: pass

                registos_dict[chave_primaria] = registo
            
            registos_para_inserir = list(registos_dict.values())
            
            if registos_para_inserir:
                print(f"   📄 {arquivo}: Lidos={len(registos_para_inserir)} pacientes")
                lote_tamanho = 100
                for i in range(0, len(registos_para_inserir), lote_tamanho):
                    lote = registos_para_inserir[i:i + lote_tamanho]
                    try:
                        supabase.table('regulacao').upsert(lote).execute()
                        total_pacientes_atualizados += len(lote)
                    except Exception as e_lote:
                        pass
                        
        except Exception as e:
            print(f"   ❌ Erro ao processar ficheiro {arquivo}: {e}")

    print(f"\n📦 Processamento concluído. {total_pacientes_atualizados} registros atualizados no banco.")

    # Dispara as notificações encontradas!
    if todas_notificacoes:
        lista_alertas = list(todas_notificacoes.values())
        print(f"🔔 {len(lista_alertas)} mudanças de status detectadas! Enviando alertas para o painel...")
        
        # Envia de 50 em 50 para o painel
        for i in range(0, len(lista_alertas), 50):
            lote_alertas = lista_alertas[i:i + 50]
            try:
                supabase.table('notificacoes').insert(lote_alertas).execute()
            except Exception as e:
                print(f"Erro ao disparar sino: {e}")
                
        print("✅ Alertas enviados com sucesso! O painel vai notificar os usuários.")
    else:
        print("💤 Nenhuma mudança de status encontrada nesta varredura.")

if __name__ == "__main__":
    print("⚙️ Maestro de Automação Ativado. Pressione CTRL+C para parar.")
    try:
        while True:
            print(f"\n[🕒 {datetime.now().strftime('%H:%M:%S')}] Iniciando patrulha...")
            processar_ficheiros()
            print(f"\n💤 Ciclo finalizado. O Maestro vai dormir por 30 minutos...")
            time.sleep(1800) # Dorme por 30 minutos (1800 segundos)
    except KeyboardInterrupt:
        print("\n🛑 Maestro desligado pelo usuário.")
        sys.exit()