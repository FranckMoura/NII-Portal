import os
import subprocess

print("--- 🛠️ CORREÇÃO DEFINITIVA DO GIT (V2) ---")

# Seu branch atual (confirmei pelo seu log que é 'main1')
BRANCH = "main1"

def run_git(command):
    print(f"   > git {command}")
    # shell=True no Windows funciona melhor com aspas duplas para mensagens
    subprocess.run(f"git {command}", shell=True)

# 1. Reset Misto (O segredo da limpeza)
# Isso desfaz os commits locais E tira tudo da área de preparação (staging),
# obrigando o Git a olhar para o que realmente tem na pasta agora.
print("\n1. 🧹 Limpando a memória do Git (Reset)...")
run_git("reset") 

# 2. Adicionar apenas o que existe
# Como você já deletou o arquivo gigante manualmente, o 'add .' vai ignorá-lo
print("\n2. ➕ Re-adicionando arquivos válidos...")
run_git("add .")

# 3. Commit com sintaxe segura para Windows
print("\n3. 💾 Salvando alterações (Commit)...")
# Usando aspas duplas internas para evitar erro de pathspec
run_git('commit -m "Fix: Remocao de arquivos grandes e limpeza"')

# 4. Enviar
print("\n4. 🚀 Enviando para o GitHub (Push)...")
run_git(f"push origin {BRANCH}")

print("\n🏁 Se apareceu 'Writing objects: 100%' sem erros vermelhos de 'remote rejected', DEU CERTO!")