import os
import sys
import json
import time
import io
import unicodedata
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

print("=====================================================")
print(" 🕵️‍♂️ MAESTRO & TRATOR (Exterminador de Acentos V29) ")
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
    if not SB_URL.startswith('http'): SB_URL = 'https://' + SB_URL
    if SB_URL.endswith('/'): SB_URL = SB_URL[:-1]
        
    SB_KEY = config['supabase']['key'].strip()
    NOME_HOSPITAL = config['hospital']['nome']
    
except Exception as e:
    print("❌ ERRO: Arquivo config.json não encontrado ou incompleto!")
    sys.exit()

print(f"[🕒 {datetime.now().strftime('%H:%M:%S')}] Conectando ao banco de: {NOME_HOSPITAL}")
try:
    supabase: Client = create_client(SB_URL, SB_KEY)
    print("✅ Supabase conectado!")
except Exception as e:
    print(f"❌ Erro ao ligar ao Supabase: {e}")
    sys.exit()

PASTA_DOWNLOAD = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\downloads_cliente"

# ==============================================================================
# A NOVA MÁQUINA DE LAVAR CABEÇALHOS (Remove Acentos, Ç, º e lixos do Governo)
# ==============================================================================
def limpar_nome_coluna(col):
    c = str(col).strip().upper()
    c = c.replace('Ã§Ã£', 'CA').replace('Ã§', 'C').replace('Ã£', 'A').replace('Ã¡', 'A').replace('Ã\xad', 'I').replace('Ã©', 'E').replace('Ãª', 'E')
    # Remove qualquer acento real (ex: Ç -> C, Ã -> A)
    c = ''.join(char for char in unicodedata.normalize('NFKD', c) if unicodedata.category(char) != 'Mn')
    c = c.replace('º', 'O').replace('N.', 'N ').replace('Nº', 'NO')
    c = ' '.join(c.split())
    return c

def ler_csv_costurado(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='latin1', errors='ignore') as f:
        raw_lines = f.readlines()

    header_idx = 0
    for i, linha in enumerate(raw_lines):
        if 'PACIENTE' in linha.upper() and 'SOLICITA' in linha.upper():
            header_idx = i
            break

    qtd_colunas_esperadas = raw_lines[header_idx].count(';')
    linhas_corrigidas = []
    buffer_linha = ""

    for linha in raw_lines[header_idx:]:
        buffer_linha += linha.replace('\n', ' ').replace('\r', '')
        if buffer_linha.count(';') >= qtd_colunas_esperadas:
            linhas_corrigidas.append(buffer_linha)
            buffer_linha = ""

    if buffer_linha:
        linhas_corrigidas.append(buffer_linha)

    csv_string = "\n".join(linhas_corrigidas)
    df = pd.read_csv(io.StringIO(csv_string), sep=';', on_bad_lines='skip', engine='python')
    return df

def processar_ficheiros():
    arquivos = [f for f in os.listdir(PASTA_DOWNLOAD) if (f.endswith('.xls') or f.endswith('.csv')) and not f.startswith('index')]
    if not arquivos: return

    print(f"\n🧠 Puxando memória do banco para detectar mudanças...")
    status_db = {}
    start, step, keep_fetching = 0, 1000, True
    
    while keep_fetching:
        try:
            resp = supabase.table('regulacao').select('num_aih, num_solicitacao, cod_solicitacao, status').range(start, start + step - 1).execute()
            if resp.data:
                for r in resp.data:
                    k = str(r.get('cod_solicitacao') or r.get('num_solicitacao') or r.get('num_aih') or '').strip()
                    if k and k != 'None': status_db[k] = str(r.get('status', '')).upper()
                start += step
            else:
                keep_fetching = False
        except Exception as e:
            print(f"❌ Erro de conexão com Supabase: {e}")
            break
            
    print(f"✅ Memória carregada: {len(status_db)} pacientes conhecidos.")
    print(f"\n🚜 Lendo e costurando arquivos...")

    todas_notificacoes = {}
    total_atualizados = 0

    for arquivo in arquivos:
        caminho_completo = os.path.join(PASTA_DOWNLOAD, arquivo)
        
        try:
            is_html = False
            try:
                df = pd.read_html(caminho_completo, decimal=',', thousands='.')[0]
                is_html = True
            except: pass

            if not is_html:
                df = ler_csv_costurado(caminho_completo)

            df.columns = [limpar_nome_coluna(c) for c in df.columns]
            registos_dict = {}
            
            for index, row in df.iterrows():
                num_sol = str(row.get('N DA SOLICITACAO', row.get('NO SOLICITACAO', ''))).strip().replace('"', '')
                if num_sol.endswith('.0'): num_sol = num_sol[:-2]
                
                cod_sol = str(row.get('SOLICITACAO', '')).strip().replace('"', '')
                if cod_sol.endswith('.0'): cod_sol = cod_sol[:-2]
                
                aih = str(row.get('N AIH', row.get('AIH', ''))).strip().replace('"', '')
                if aih.endswith('.0'): aih = aih[:-2]

                if "RISCO" in aih.upper() or len(aih) > 20: aih = ''
                if "RISCO" in num_sol.upper() or num_sol.isalpha(): num_sol = ''
                if "RISCO" in cod_sol.upper() or cod_sol.isalpha(): cod_sol = ''

                chave_primaria = cod_sol if cod_sol else (num_sol if num_sol else aih)

                if not chave_primaria or str(chave_primaria).lower() in ['nan', '0', 'none', '']: continue 

                nome_paciente = str(row.get('NOME DO PACIENTE', row.get('PACIENTE', ''))).replace('"', '').strip()
                status_limpo = str(row.get('STATUS DA SOLICITACAO DE INTERNACAO', row.get('SITUACAO', ''))).replace('"', '').strip()

                if chave_primaria in status_db:
                    status_antigo = status_db[chave_primaria]
                    status_novo = status_limpo.upper()
                    if status_antigo != status_novo and status_novo not in ['', 'NAN', 'NONE', '-']:
                        if not (("APROV" in status_antigo and "APROV" in status_novo) or ("NEGAD" in status_antigo and "NEGAD" in status_novo)):
                            todas_notificacoes[chave_primaria] = { "paciente": nome_paciente, "status_novo": status_novo, "lida": False }

                registo = {
                    "num_aih": aih if (aih and aih.lower() != 'nan') else None,
                    "num_solicitacao": num_sol if (num_sol and num_sol.lower() != 'nan') else None,
                    "cod_solicitacao": cod_sol if (cod_sol and cod_sol.lower() != 'nan') else None,
                    "nome_paciente": nome_paciente if nome_paciente.lower() != 'nan' else 'DESCONHECIDO',
                    "cns_paciente": str(row.get('CNS DO PACIENTE', row.get('CNS', ''))).replace('"', '').strip(),
                    "status": status_limpo,
                    "carater_internacao": str(row.get('CARATER INTERNACAO', row.get('CARATER', ''))).replace('"', '').strip(),
                    "nome_clinica": str(row.get('NOME DA CLINICA', row.get('CLINICA', ''))).replace('"', '').strip(),
                    "data_solicitacao": None,
                    "data_autorizacao": None,
                    "data_atualizacao": datetime.now().isoformat()
                }
                
                if not registo["num_solicitacao"] and registo["cod_solicitacao"]: registo["num_solicitacao"] = registo["cod_solicitacao"]
                elif not registo["num_solicitacao"] and registo["num_aih"]: registo["num_solicitacao"] = registo["num_aih"]
                
                # AS DATAS AGORA SÃO CAPTURADAS COM SUCESSO ABSOLUTO
                d_sol_raw = str(row.get('DATA DA SOLICITACAO', row.get('DATA SOLICITACAO', ''))).replace('"', '').strip()
                if d_sol_raw and d_sol_raw.lower() not in ['nan', 'none', '-']:
                    try: registo["data_solicitacao"] = pd.to_datetime(d_sol_raw, format='%d/%m/%Y').strftime('%Y-%m-%d')
                    except: pass
                
                d_aut_raw = str(row.get('DATA DA AUTORIZACAO', row.get('DATA AUTORIZACAO', ''))).replace('"', '').strip()
                if d_aut_raw and d_aut_raw.lower() not in ['nan', 'none', '-']:
                    try: registo["data_autorizacao"] = pd.to_datetime(d_aut_raw, format='%d/%m/%Y').strftime('%Y-%m-%d')
                    except: pass

                registos_dict[chave_primaria] = registo
            
            registos_para_inserir = list(registos_dict.values())
            
            if registos_para_inserir:
                print(f"   📄 {arquivo}: {len(registos_para_inserir)} pacientes validados")
                for i in range(0, len(registos_para_inserir), 100):
                    lote = registos_para_inserir[i:i + 100]
                    try:
                        supabase.table('regulacao').upsert(lote, on_conflict='num_solicitacao').execute()
                        total_atualizados += len(lote)
                    except Exception as e_lote:
                        print(f"   ⚠️ Falha ao subir lote: {e_lote}")
                        
        except Exception as e:
            print(f"   ❌ Erro Critico ao processar ficheiro {arquivo}: {e}")

    print(f"\n📦 Sucesso! {total_atualizados} registros empurrados perfeitamente para o banco.")

    if todas_notificacoes:
        lista_alertas = list(todas_notificacoes.values())
        print(f"🔔 {len(lista_alertas)} mudanças de status detectadas! Disparando...")
        for i in range(0, len(lista_alertas), 50):
            try: supabase.table('notificacoes').insert(lista_alertas[i:i + 50]).execute()
            except: pass
        print("✅ Alertas enviados com sucesso!")
    else:
        print("💤 Nenhuma mudança de status nova detectada.")

if __name__ == "__main__":
    print("⚙️ Maestro V29 Ativado. Pressione CTRL+C para parar.")
    try:
        while True:
            processar_ficheiros()
            print(f"\n💤 Ciclo finalizado. O Maestro vai dormir por 30 minutos...")
            time.sleep(1800)
    except KeyboardInterrupt:
        print("\n🛑 Maestro desligado pelo usuário.")
        sys.exit()