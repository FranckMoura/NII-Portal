import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("SISTEMA DE GESTÃO E AUDITORIA NII (V20 - FINANCEIRO)")
python_cmd = sys.executable 

def rodar(script, obrigatorio=True):
    print(f"\n[AGUARDE] Executando: {script}...")
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
        if obrigatorio:
            print("   (Processo interrompido por segurança)")
            exit()
        return False

# --- 1. EXTRAÇÃO SISREG (Robô V18) ---
# Baixa os dados novos do site do governo
rodar("extracao_sisreg_v18.py", obrigatorio=False)

# --- 2. CARGA SISREG -> POSTGRES (Banco de Dados) ---
# Salva o que baixou no banco
rodar("banco_dados_sisreg_postgres.py")

# --- 3. IMPORTAÇÃO FINANCEIRA (Se houver arquivo novo) ---
# Atualiza a tabela de faturamento se você tiver colocado csv novo
if os.path.exists("pDetAIH.csv"):
    print("\n[INFO] Arquivo de faturamento detectado. Atualizando banco...")
    rodar("importar_faturamento_v3.py", obrigatorio=False)
else:
    print("\n[INFO] Nenhum arquivo 'pDetAIH.csv' novo. Mantendo faturamento anterior.")

# --- 4. AUDITORIA FINANCEIRA (O Pulo do Gato) ---
# Gera o Excel com as perdas
rodar("gerar_relatorio_financeiro_v2.py", obrigatorio=False)

# --- 5. GERAÇÃO DO SITE (Dashboard) ---
# Cria o HTML bonito
rodar("gerar_dashboard.py")

# --- 6. UPLOAD (Sobe pra nuvem) ---
rodar("upload_manager.py")

imprimir_titulo("PROCESSO FINALIZADO! VERIFIQUE O EXCEL GERADO.")
time.sleep(10)