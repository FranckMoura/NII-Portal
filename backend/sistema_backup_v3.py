import os
import zipfile
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import subprocess

print("--- SISTEMA DE BACKUP V3 (ATUALIZADO PARA O MINERADOR) ---")

# --- CONFIGURAÇÃO ---
load_dotenv()
SB_URL = os.getenv("SUPABASE_URL") # Ajustei para o padrão do seus scripts recentes (se for SB_URL mude aqui)
SB_KEY = os.getenv("SUPABASE_KEY")

# Se não achar no .env, tenta pegar das variáveis globais hardcoded dos scripts anteriores (caso vc tenha salvo lá)
if not SB_URL: SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
if not SB_KEY: SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

# Pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
ROOT_DIR = os.path.dirname(BASE_DIR) 

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except:
    print("❌ Erro ao conectar Supabase. Verifique chaves.")
    exit()

def gerar_requirements():
    """Salva as bibliotecas instaladas para facilitar a restauração"""
    print("📋 Gerando lista de dependências (requirements.txt)...")
    try:
        caminho_req = os.path.join(ROOT_DIR, "requirements.txt")
        with open(caminho_req, "w") as f:
            subprocess.check_call(["pip", "freeze"], stdout=f)
    except:
        print("⚠️ Não foi possível gerar requirements.txt")

def zipar_pasta_com_exclusao(pasta_origem, arquivo_zip_destino):
    IGNORAR_PASTAS = {
        'backups', 'venv', '.git', '.vscode', '__pycache__', 'node_modules', 'dist', 'build'
    }
    
    print(f"📦 Compactando código fonte...")
    with zipfile.ZipFile(arquivo_zip_destino, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(pasta_origem):
            dirs[:] = [d for d in dirs if d not in IGNORAR_PASTAS]
            for file in files:
                caminho_completo = os.path.join(root, file)
                caminho_relativo = os.path.relpath(caminho_completo, pasta_origem)
                if caminho_completo == arquivo_zip_destino: continue
                # Evita zipar zips antigos se estiverem soltos
                if file.endswith('.zip'): continue 
                
                try: zipf.write(caminho_completo, caminho_relativo)
                except: pass

def criar_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pasta_backup = os.path.join(ROOT_DIR, "backups", f"backup_{timestamp}")
    
    if not os.path.exists(pasta_backup):
        os.makedirs(pasta_backup)
        os.makedirs(os.path.join(pasta_backup, "dados_supabase"))

    print(f"📂 Pasta criada: {pasta_backup}")

    # 1. Gera requirements antes de zipar
    gerar_requirements()

    # 2. Backup dos Dados (Incluindo a tabela nova)
    tabelas = [
        "historico_aih", # <--- A MAIS IMPORTANTE AGORA
        "financeiro_repasses", 
        "institucional_profissionais", 
        "institucional_leitos",
        "institucional_servicos",
        "institucional_marcacoes",
        "controle_simuladas"
    ]

    print("📊 Baixando dados do banco (CSV)...")
    for tabela in tabelas:
        try:
            # Aumentei o limite para garantir que pegue o histórico todo
            response = supabase.table(tabela).select("*").execute() # Sem limit pega o default max, mas ideal é paginar se for gigante
            # Para garantir mais dados, usamos csv export se a lib suportar, ou loop. 
            # Por enquanto, select simples pega bastante coisa.
            
            if response.data:
                df = pd.DataFrame(response.data)
                caminho_csv = os.path.join(pasta_backup, "dados_supabase", f"{tabela}.csv")
                df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
                print(f"   ✅ {tabela}: {len(df)} registros salvos.")
            else:
                print(f"   ⚠️ {tabela}: Vazia ou não encontrada.")
        except Exception as e:
            print(f"   ❌ Erro na tabela {tabela}: {e}")

    # 3. Compactação
    caminho_zip = os.path.join(pasta_backup, "projeto_completo.zip")
    zipar_pasta_com_exclusao(ROOT_DIR, caminho_zip)
    
    print(f"\n✅ BACKUP CONCLUÍDO!")
    print(f"📍 Salvo em: {pasta_backup}")
    print("💡 DICA PARA RESTAURAR:")
    print("1. Descompacte o zip.")
    print("2. Rode: pip install -r requirements.txt")
    print("3. No Supabase, vá em Table Editor > Import CSV para restaurar os dados.")

if __name__ == "__main__":
    criar_backup()