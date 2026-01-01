import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("SISTEMA DE GESTÃO E AUDITORIA NII (V25 - SQLite)")
python_cmd = sys.executable 

def rodar(script, obrigatorio=True):
    print(f"\n[AGUARDE] Executando: {script}...")
    
    caminho_script = os.path.join(os.getcwd(), script)
    if not os.path.exists(caminho_script):
        print(f"❌ ARQUIVO NÃO ENCONTRADO: {script}")
        if obrigatorio:
            print("   (Processo interrompido. Verifique o nome do arquivo.)")
            exit()
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
        if obrigatorio:
            print("   ⛔ ERRO CRÍTICO NA ETAPA OBRIGATÓRIA.")
            exit()
        return False

# --- 1. EXTRAÇÃO (Tenta rodar o V18 ou o script que tiver) ---
# Se você mudou o nome do extrator, ajuste a linha abaixo também.
if os.path.exists("extracao_sisreg_v18.py"):
    rodar("extracao_sisreg_v18.py", obrigatorio=True)
else:
    print("⚠️ Script de extração (v18) não encontrado. Pulando etapa...")

# --- 2. PROCESSAMENTO (AQUI ESTÁ A MUDANÇA) ---
# Agora chama o script com o nome correto
rodar("processar_dados_sisreg.py", obrigatorio=True)

# --- 3. IMPORTAÇÃO FINANCEIRA (Opcional) ---
if os.path.exists("pDetAIH.csv") and os.path.exists("importar_faturamento_v3.py"):
    print("\n[INFO] Verificando faturamento...")
    rodar("importar_faturamento_v3.py", obrigatorio=False)

# --- 4. UPLOAD (Gerencia o Git) ---
if os.path.exists("upload_manager_v6.py"):
    rodar("upload_manager_v6.py", obrigatorio=True)
elif os.path.exists("upload_manager.py"):
    rodar("upload_manager.py", obrigatorio=True)
else:
    print("❌ Script de Upload não encontrado.")

imprimir_titulo("PROCESSO FINALIZADO!")
print("   Acesse: https://franckmoura.github.io/NII-Portal/painel_regulacao.html")
print("   Fechando em 10 segundos...")
time.sleep(10)