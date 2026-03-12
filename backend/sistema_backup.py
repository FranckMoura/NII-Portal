import os
import zipfile
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

print("--- SISTEMA DE BACKUP V2 (COM FILTRO INTELIGENTE) ---")

# --- CONFIGURAÇÃO ---
load_dotenv()
SB_URL = os.getenv("SB_URL")
SB_KEY = os.getenv("SB_KEY")

# Pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # backend/
ROOT_DIR = os.path.dirname(BASE_DIR) # Pasta raiz do projeto

if not SB_URL or not SB_KEY: exit("❌ Configure o .env")
supabase: Client = create_client(SB_URL, SB_KEY)

def zipar_pasta_com_exclusao(pasta_origem, arquivo_zip_destino):
    """Compacta a pasta ignorando lixo (backups antigos, venv, git)"""
    
    # LISTA NEGRA: Pastas que NÃO devem entrar no zip
    IGNORAR_PASTAS = {
        'backups',      # Não fazer backup do backup (loop infinito)
        'venv',         # Ambiente virtual (muito pesado)
        '.git',         # Histórico do git
        '.vscode',      # Configurações do editor
        '__pycache__',  # Cache do Python
        'node_modules'  # Caso use Node
    }

    print(f"📦 Iniciando compactação em: {arquivo_zip_destino}")
    
    with zipfile.ZipFile(arquivo_zip_destino, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(pasta_origem):
            # 1. Remove pastas ignoradas da lista de navegação
            # (Modificar 'dirs' in-place impede o os.walk de entrar nelas)
            dirs[:] = [d for d in dirs if d not in IGNORAR_PASTAS]

            for file in files:
                # Caminho completo do arquivo no disco
                caminho_completo = os.path.join(root, file)
                
                # Caminho relativo (como vai aparecer dentro do zip)
                caminho_relativo = os.path.relpath(caminho_completo, pasta_origem)
                
                # Evita tentar zipar o próprio arquivo zip se ele estiver sendo salvo dentro da origem
                if caminho_completo == arquivo_zip_destino:
                    continue
                
                try:
                    zipf.write(caminho_completo, caminho_relativo)
                except Exception as e:
                    print(f"   ⚠️ Aviso: Não foi possível zipar {file}: {e}")

    print("   📦 Compactação finalizada.")

def criar_backup():
    # 1. Criar pasta com Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pasta_backup = os.path.join(ROOT_DIR, "backups", f"backup_{timestamp}")
    
    if not os.path.exists(pasta_backup):
        os.makedirs(pasta_backup)
        os.makedirs(os.path.join(pasta_backup, "dados_supabase"))

    print(f"📂 Pasta criada: {pasta_backup}")

    # 2. Backup dos Dados do Supabase (CSV)
    tabelas = [
        "financeiro_repasses", 
        "institucional_profissionais", 
        "institucional_leitos",
        "institucional_servicos",
        "institucional_marcacoes"
    ]

    print("📊 Baixando dados do banco...")
    for tabela in tabelas:
        try:
            response = supabase.table(tabela).select("*").limit(10000).execute()
            if response.data:
                df = pd.DataFrame(response.data)
                caminho_csv = os.path.join(pasta_backup, "dados_supabase", f"{tabela}.csv")
                df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
                print(f"   ✅ {tabela}: {len(df)} registros.")
            else:
                print(f"   ⚠️ {tabela}: Vazia.")
        except Exception as e:
            print(f"   ❌ Erro tabela {tabela}: {e}")

    # 3. Compactação Segura
    caminho_zip = os.path.join(pasta_backup, "codigo_fonte_completo.zip")
    zipar_pasta_com_exclusao(ROOT_DIR, caminho_zip)
    
    print(f"\n✅ BACKUP CONCLUÍDO COM SUCESSO!")
    print(f"📍 Local: {pasta_backup}")

if __name__ == "__main__":
    criar_backup()