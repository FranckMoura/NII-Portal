import os
import subprocess
import time

print("--- 🚑 DESTRAVANDO UPLOAD DO GITHUB ---")
print("O arquivo 'dados_sisreg.db' é muito grande e travou o envio.")
print("Vamos removê-lo do Git (mas manter no seu PC) e tentar de novo.\n")

def run_git(command):
    print(f">> Executando: {command}")
    os.system(f"git {command}")

# 1. Desfaz o último commit (o empacotamento que falhou) mas mantem os arquivos
run_git("reset --soft HEAD~1")

# 2. Remove o arquivo gigante da 'área de espera' do Git
# (Isso não apaga do seu computador, só tira da fila de upload)
print(">> Removendo arquivo gigante da fila...")
run_git("rm --cached dados_sisreg.db")

# 3. Cria/Atualiza o .gitignore para bloquear arquivos .db futuros
print(">> Criando regra de bloqueio (.gitignore)...")
try:
    with open(".gitignore", "a") as f:
        f.write("\n# Ignorar bancos de dados locais pesados\n")
        f.write("*.db\n")
        f.write("*.sqlite\n")
        f.write("*.zip\n")
    print("✅ Arquivo .gitignore atualizado.")
except Exception as e:
    print(f"⚠️ Erro ao criar .gitignore: {e}")

# 4. Refaz o processo de Upload (Usando seu script V6)
print("\n>> Reiniciando o Upload Manager V6...")
# Chama o script de upload que já temos, agora sem o peso morto
subprocess.run(["python", "upload_manager_v6.py"])

print("\n🎉 PROCESSO DE CORREÇÃO FINALIZADO!")
print("Tente acessar o site em alguns minutos.")
time.sleep(5)