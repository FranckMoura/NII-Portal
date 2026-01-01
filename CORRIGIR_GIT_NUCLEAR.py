import os
import subprocess

print("--- ☢️ CORREÇÃO NUCLEAR DO GIT (RESET TOTAL DE HISTÓRICO) ---")

BRANCH = "main1"

def run_git(command):
    print(f"   > git {command}")
    subprocess.run(f"git {command}", shell=True)

# 1. Resetar para a origem (Desmancha todos os commits locais não enviados)
# --soft garante que seus arquivos (faturamento.html, json, etc) NÃO sejam apagados.
print("\n1. 🔙 Voltando o histórico para o estado do servidor...")
run_git(f"reset --soft origin/{BRANCH}")

# 2. Limpar o Index (Tira tudo da área de preparação)
print("\n2. 🧹 Limpando a área de preparação...")
run_git("reset")

# 3. Garantir que o arquivo gigante não seja rastreado nunca mais
print("\n3. 🛡️ Atualizando regras de bloqueio (.gitignore)...")
try:
    with open(".gitignore", "a") as f:
        f.write("\nProfile-*.json\n")
        f.write("*.log\n")
except: pass

# 4. Adicionar tudo (O Git vai ignorar o arquivo gigante se ele ainda existir, ou ignorar se já foi apagado)
print("\n4. ➕ Preparando arquivos limpos...")
run_git("add .")

# 5. Commit Novo
print("\n5. 💾 Criando um NOVO pacote de envio (limpo)...")
run_git('commit -m "Fix: Upload painel faturamento e correcao de git"')

# 6. Push
print("\n6. 🚀 Enviando agora...")
run_git(f"push origin {BRANCH}")

print("\n🏁 Verifique se apareceu 'Writing objects: 100%' acima.")