import os
import subprocess
import glob

print("--- 🛠️ CORREÇÃO DE ERRO GIT (REMOÇÃO DE ARQUIVO GIGANTE) ---")

# Configuração da Branch (baseado no seu log, você usa 'main1')
BRANCH = "main1"

def run_git(command):
    print(f"   > git {command}")
    subprocess.run(f"git {command}", shell=True, check=False)

# 1. Desfazer o último commit (Soft Reset)
# Isso mantém as alterações nos arquivos, mas cancela o 'pacote' de envio que estava com o arquivo gigante
print("\n1. 🔙 Desfazendo o último commit problemático...")
run_git("reset --soft HEAD~1")

# 2. Localizar e Deletar o arquivo Gigante
print("\n2. 🗑️ Procurando e apagando o arquivo 'Profile-*.json'...")
arquivos_ruins = glob.glob("**/*Profile-*.json", recursive=True)

if arquivos_ruins:
    for arq in arquivos_ruins:
        try:
            # Remove do índice do Git
            run_git(f"reset HEAD \"{arq}\"")
            # Remove do computador
            os.remove(arq)
            print(f"   ✅ Arquivo DELETADO: {arq}")
        except Exception as e:
            print(f"   ⚠️ Erro ao deletar {arq}: {e}")
else:
    print("   (Nenhum arquivo 'Profile-*.json' encontrado na pasta atual. Talvez já tenha sido removido.)")

# 3. Atualizar .gitignore para prevenir reincidência
print("\n3. 🛡️ Blindando o .gitignore...")
try:
    with open(".gitignore", "a") as f:
        f.write("\n# Ignorar perfis de navegador e arquivos temporarios\n")
        f.write("Profile-*.json\n")
        f.write("*.log\n")
        f.write("**/*.db\n") # Ignora banco de dados local se houver
    print("   ✅ .gitignore atualizado.")
except Exception as e:
    print(f"   ⚠️ Erro ao editar .gitignore: {e}")

# 4. Tentar subir novamente
print("\n4. 🚀 Tentando enviar novamente (sem o peso morto)...")
run_git("add .")
run_git("commit -m 'Fix: Removendo arquivos temporarios grandes'")
run_git(f"push origin {BRANCH}")

print("\n🏁 Processo de correção finalizado!")