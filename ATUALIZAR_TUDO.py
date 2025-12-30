import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("SISTEMA DE GESTÃO E AUDITORIA NII (V24 - PROTEGIDO)")
python_cmd = sys.executable 

def rodar(script, obrigatorio=True):
    print(f"\n[AGUARDE] Executando: {script}...")
    
    # Verifica se o arquivo existe na pasta atual
    caminho_script = os.path.join(os.getcwd(), script)
    if not os.path.exists(caminho_script):
        print(f"❌ ARQUIVO NÃO ENCONTRADO: {script}")
        if obrigatorio:
            print("   (Processo interrompido. Verifique se salvou o arquivo na pasta correta.)")
            exit()
        return False
    
    # Configura encoding para evitar erro de acentuação no Windows
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
            print("   (O processo foi abortado para evitar dados corrompidos.)")
            exit()
        return False

# --- 1. EXTRAÇÃO SISREG (Robô V18) ---
# MUDANÇA IMPORTANTE: Agora é OBRIGATÓRIO.
rodar("extracao_sisreg_v18.py", obrigatorio=True)

# --- 3. IMPORTAÇÃO FINANCEIRA (Se houver arquivo novo) ---
if os.path.exists("pDetAIH.csv"):
    print("\n[INFO] Arquivo de faturamento detectado. Atualizando banco...")
    rodar("importar_faturamento_v3.py", obrigatorio=False)
else:
    print("\n[INFO] Nenhum arquivo 'pDetAIH.csv' novo. Mantendo faturamento anterior.")

# --- 7. UPLOAD (Sobe pra nuvem) ---
# Envia HTML, JSON e a pasta Fichas_Internacao para o GitHub
# Nota: Verifique se o nome do seu arquivo é upload_manager.py ou upload_manager_v6.py
# Se der erro de "Arquivo não encontrado", mude o nome abaixo.
if os.path.exists("upload_manager_v6.py"):
    rodar("upload_manager_v6.py", obrigatorio=True)
elif os.path.exists("upload_manager.py"):
    rodar("upload_manager.py", obrigatorio=True)
else:
    print("❌ Script de Upload não encontrado.")

imprimir_titulo("PROCESSO FINALIZADO COM SUCESSO!")
print("   Acesse: https://franckmoura.github.io/NII-Portal/painel_regulacao.html")
print("   Fechando em 10 segundos...")
time.sleep(10)