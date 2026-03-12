import os
import zipfile
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import subprocess
import time

print("--- SISTEMA DE BACKUP V5 (COM PAGINAÇÃO) ---")
print(">> Baixa tabelas gigantes em pedaços para evitar erros de conexão.")

# --- CONFIGURAÇÃO ---
load_dotenv()
SB_URL = os.getenv("SB_URL") or "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = os.getenv("SB_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
ROOT_DIR = os.path.dirname(BASE_DIR) 

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except:
    print("❌ Erro de Conexão. Verifique chaves.")
    exit()

def gerar_requirements():
    print("📋 Gerando requirements.txt...")
    try:
        with open(os.path.join(ROOT_DIR, "requirements.txt"), "w") as f:
            subprocess.check_call(["pip", "freeze"], stdout=f)
    except: pass

def zipar_codigo(pasta_origem, arquivo_zip):
    IGNORAR = {'backups', 'venv', '.git', '.vscode', '__pycache__', 'node_modules', 'dist', 'build'}
    print(f"📦 Zipando código fonte...")
    with zipfile.ZipFile(arquivo_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(pasta_origem):
            dirs[:] = [d for d in dirs if d not in IGNORAR]
            for file in files:
                abs_path = os.path.join(root, file)
                # Ignora o próprio zip e arquivos CSV soltos para não duplicar
                if abs_path == arquivo_zip or file.endswith('.zip') or file.endswith('.csv'): continue
                zipf.write(abs_path, os.path.relpath(abs_path, pasta_origem))

def baixar_tabela_paginada(tabela, tamanho_lote=1000):
    """Baixa dados em chunks para não estourar a memória ou conexão"""
    todos_dados = []
    inicio = 0
    
    while True:
        try:
            # Baixa do registro 'inicio' até 'inicio + tamanho_lote'
            res = supabase.table(tabela).select("*").range(inicio, inicio + tamanho_lote - 1).execute()
            
            dados = res.data
            if not dados:
                break # Acabou
            
            todos_dados.extend(dados)
            
            # Se baixou menos que o limite, é porque acabou
            if len(dados) < tamanho_lote:
                break
                
            inicio += tamanho_lote
            print(f"      ↳ Baixado lote: {inicio} registros...", end='\r')
            
        except Exception as e:
            print(f"      ⚠️ Falha no lote {inicio}: {e}")
            break
            
    return todos_dados

def obter_todas_tabelas():
    return [
        "historico_aih", 
        "financeiro_repasses", 
        "institucional_profissionais", 
        "institucional_leitos",
        "institucional_servicos",
        "institucional_marcacoes",
        "controle_simuladas",
        "regulacao"
    ]

def criar_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pasta_backup = os.path.join(ROOT_DIR, "backups", f"backup_{timestamp}")
    pasta_dados = os.path.join(pasta_backup, "banco_de_dados")
    
    os.makedirs(pasta_dados, exist_ok=True)
    print(f"📂 Backup iniciado: {pasta_backup}")

    gerar_requirements()

    tabelas = obter_todas_tabelas()
    print("📊 Baixando tabelas (Modo Paginado)...")
    
    for tabela in tabelas:
        try:
            dados = baixar_tabela_paginada(tabela)
            
            if dados:
                df = pd.DataFrame(dados)
                caminho_csv = os.path.join(pasta_dados, f"{tabela}.csv")
                df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
                print(f"   ✅ {tabela}: {len(df)} registros totais.")
            else:
                print(f"   ⚠️ {tabela}: Vazia.")
        except Exception as e:
            if "404" not in str(e): 
                print(f"   ❌ Erro crítico em {tabela}: {e}")

    zipar_codigo(ROOT_DIR, os.path.join(pasta_backup, "codigo_projeto.zip"))
    
    print(f"\n✅ BACKUP V5 COMPLETO!")
    print(f"📍 Pasta: backups/backup_{timestamp}")

if __name__ == "__main__":
    criar_backup()