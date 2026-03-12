import os
import subprocess
import sys

print("--- 🚀 ENVIANDO ARQUIVOS PARA O GITHUB (FORÇANDO MAIN) ---")

# --- CONFIGURAÇÕES ---
# Pasta raiz do projeto
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud"

# Link do seu repositório
URL_REPO = "https://github.com/franckmoura/NII-Portal.git"

# Mensagem automática
MENSAGEM = "Atualizacao automatica via Script Python"

def executar(comando):
    try:
        # Roda o comando no terminal e esconde erros comuns se já existirem
        subprocess.run(comando, cwd=PASTA_PROJETO, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        # Ignora erros de "já existe", mas avisa se for algo grave
        pass

try:
    print(f">> Preparando pasta: {PASTA_PROJETO}")
    
    # 1. Inicia o Git
    executar("git init")
    
    # 2. Configura o Repositório Remoto
    print(">> Conectando ao repositório...")
    try:
        subprocess.run(f"git remote add origin {URL_REPO}", cwd=PASTA_PROJETO, shell=True, check=True, stderr=subprocess.DEVNULL)
    except:
        # Se já existe, atualiza a URL
        subprocess.run(f"git remote set-url origin {URL_REPO}", cwd=PASTA_PROJETO, shell=True)

    # 3. Adiciona TODOS os arquivos
    print(">> Adicionando arquivos...")
    executar("git add .")
    
    # 4. Salva (Commit)
    print(">> Salvando versão...")
    # O comando abaixo só commita se houver mudanças
    subprocess.run(f'git commit -m "{MENSAGEM}"', cwd=PASTA_PROJETO, shell=True, stderr=subprocess.DEVNULL)

    # 5. Define a branch principal como MAIN (Isso corrige qualquer 'main1' ou 'master')
    executar("git branch -M main")

    # 6. Envia para a nuvem (Push Forçado)
    print(">> ENVIANDO PARA O GITHUB (Aguarde)...")
    # O --force garante que o GitHub aceite sua versão como a oficial
    executar("git push -u origin main --force")

    print("\n✅ SUCESSO! Site atualizado.")
    print(f"🔗 Acesse: https://franckmoura.github.io/NII-Portal")

except Exception as e:
    print(f"\n❌ ERRO: {e}")