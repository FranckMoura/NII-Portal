import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("ATUALIZADOR AUTOMÁTICO NII (V18 FINAL + POSTGRES)")
python_cmd = sys.executable 

def rodar(script):
    print(f"\n[AGUARDE] Iniciando: {script}...")
    if not os.path.exists(script):
        print(f"❌ ARQUIVO NÃO ENCONTRADO: {script}")
        return False
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    inicio = time.time()
    ret = subprocess.run([python_cmd, script], env=env)
    fim = time.time()
    
    if ret.returncode == 0:
        print(f"✅ SUCESSO! ({round(fim-inicio, 1)}s)")
        return True
    else:
        print(f"❌ FALHA NA EXECUÇÃO.")
        return False

# 1. Extração (V18 - A Perfeita)
if not rodar("extracao_sisreg_v18.py"):
    print("⚠️ Extração falhou. Continuando com dados antigos...")

# 2. Banco de Dados (PostgreSQL)
if not rodar("banco_dados_sisreg_postgres.py"):
    print("❌ Falha crítica no banco de dados. O processo será interrompido.")
    exit()

# 3. Dashboard (Gera HTML)
rodar("gerar_dashboard.py")

# 4. Upload (Git)
rodar("upload_manager.py")

imprimir_titulo("PROCESSO FINALIZADO")
print("   O site deve estar atualizado em 1 ou 2 minutos.")
time.sleep(5)