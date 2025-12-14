import subprocess
import time
import os

print("="*50)
print("   🚀 ATUALIZADOR AUTOMÁTICO NII - SISREG")
print("="*50)

# Caminho do Python (tenta pegar o do sistema)
python_cmd = "python"

def rodar(script):
    print(f"\n[1/3] Iniciando: {script}...")
    if os.path.exists(script):
        retorno = subprocess.run([python_cmd, script])
        if retorno.returncode == 0:
            print(f"✅ {script} finalizado com sucesso.")
            return True
        else:
            print(f"❌ Erro ao rodar {script}.")
            return False
    else:
        print(f"❌ Arquivo não encontrado: {script}")
        return False

# 1. Extrair (Baixa CSVs)
if not rodar("extracao_sisreg_v5.py"): # ou o nome que você salvou o script de extração
    print("⚠️ Falha na extração. Continuando com dados existentes...")

# 2. Processar (Cria Parquet) - O MAIS IMPORTANTE
if not rodar("banco_dados_sisreg.py"):
    print("❌ Falha crítica no banco de dados. Parando.")
    exit()

# 3. Gerar Dashboard (Cria HTML/JSON)
rodar("gerar_dashboard.py")

# 4. Upload (Sobe pro site)
rodar("upload_manager.py")

print("\n" + "="*50)
print("🏁 PROCESSO CONCLUÍDO! ACESSE O PORTAL.")
print("="*50)
time.sleep(5)