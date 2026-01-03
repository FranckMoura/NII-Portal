import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("SISTEMA DE GESTÃO E AUDITORIA NII (V26 - INTEGRADO)")
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

# ==============================================================================
# 1. MÓDULO REGULAÇÃO (SISREG)
# ==============================================================================
imprimir_titulo("ETAPA 1: REGULAÇÃO (SISREG)")

# Tenta rodar o extrator do SISREG se existir (pode ser pulado se não houver credenciais)
if os.path.exists("extracao_sisreg_v18.py"):
    rodar("extracao_sisreg_v18.py", obrigatorio=False)
else:
    print("⚠️ Script de extração SISREG não encontrado ou ignorado. Seguindo...")

# Processamento do SISREG (Gera os JSONs da Regulação)
rodar("processar_dados_sisreg.py", obrigatorio=False)


# ==============================================================================
# 2. MÓDULO FATURAMENTO (TABNET / SIH)
# ==============================================================================
imprimir_titulo("ETAPA 2: FATURAMENTO (TABNET)")

# Nota: O 'extrator_tabnet.py' não roda aqui pois demora 40min.
# Deve ser rodado manualmente apenas quando houver nova competência.

# Processamento do TabNet (Lê os CSVs da pasta TABNET_Export e gera dados_tabnet.json)
if os.path.exists("processar_tabnet.py"):
    rodar("processar_tabnet.py", obrigatorio=True)
else:
    print("❌ Script 'processar_tabnet.py' não encontrado!")


# ==============================================================================
# 3. PUBLICAÇÃO (GIT / GITHUB PAGES)
# ==============================================================================
imprimir_titulo("ETAPA 3: PUBLICAÇÃO E UPLOAD")

if os.path.exists("upload_manager.py"):
    rodar("upload_manager.py", obrigatorio=True)
else:
    print("❌ Script 'upload_manager.py' não encontrado. Não foi possível publicar.")

print("\n" + "="*60)
print("🏁 PROCESSO GERAL FINALIZADO COM SUCESSO!")
print("="*60 + "\n")