import os
import zipfile
import datetime

def criar_backup():
    # 1. Configurações
    nome_projeto = "NII_Portal_V_ESTAVEL"
    data_hoje = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    nome_arquivo = f"{nome_projeto}_{data_hoje}.zip"
    
    pasta_origem = os.getcwd()
    pasta_destino = os.path.join(pasta_origem, "_BACKUPS")
    
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
        
    caminho_completo_zip = os.path.join(pasta_destino, nome_arquivo)

    print(f"--- 📦 INICIANDO BACKUP DE SEGURANÇA ---")
    print(f"Origem: {pasta_origem}")
    print(f"Destino: {caminho_completo_zip}")

    # 2. Pastas para IGNORAR (Não precisamos salvar lixo)
    ignorar = [
        "_BACKUPS",       # Não fazer backup do backup
        ".git",           # Histórico do git (pesado e desnecessário no zip)
        "__pycache__",    # Lixo do Python
        ".vscode"         # Configurações do editor
    ]

    # 3. Compactação
    try:
        with zipfile.ZipFile(caminho_completo_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(pasta_origem):
                # Remove pastas ignoradas da lista para não entrar nelas
                dirs[:] = [d for d in dirs if d not in ignorar]
                
                for file in files:
                    if file == nome_arquivo: continue # Não zipar a si mesmo
                    
                    caminho_absoluto = os.path.join(root, file)
                    caminho_relativo = os.path.relpath(caminho_absoluto, pasta_origem)
                    
                    print(f"   -> Compactando: {caminho_relativo}")
                    zipf.write(caminho_absoluto, caminho_relativo)
        
        print(f"\n✅ BACKUP CONCLUÍDO COM SUCESSO!")
        print(f"   Arquivo salvo em: {caminho_completo_zip}")
        print("   Guarde este arquivo em um Pen Drive ou HD Externo se possível.")

    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")

if __name__ == "__main__":
    criar_backup()