import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("SISTEMA DE GESTÃO E AUDITORIA NII (V21 - COMPLETO)")
python_cmd = sys.executable 

def rodar(script, obrigatorio=True):
    print(f"\n[AGUARDE] Executando: {script}...")
    if not os.path.exists(script):
        # Se não achar, tenta ver se está na pasta raiz
        if os.path.exists(os.path.join(os.getcwd(), script)):
            script = os.path.join(os.getcwd(), script)
        else:
            print(f"❌ ARQUIVO NÃO ENCONTRADO: {script}")
            return False
    
    # Força encoding UTF-8 para evitar erros de acentuação no Windows
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
# Baixa os dados novos do site do governo de forma 100% automática
rodar("extracao_sisreg_v18.py", obrigatorio=False)

# --- 2. CARGA SISREG -> POSTGRES (Banco de Dados) ---
# Salva o que baixou no banco de dados
rodar("banco_dados_sisreg_postgres.py")

# --- 3. IMPORTAÇÃO FINANCEIRA (Se houver arquivo novo) ---
# Atualiza a tabela de faturamento se encontrar o arquivo pDetAIH.csv
if os.path.exists("pDetAIH.csv"):
    print("\n[INFO] Arquivo de faturamento detectado. Atualizando banco...")
    rodar("importar_faturamento_v3.py", obrigatorio=False)
else:
    print("\n[INFO] Nenhum arquivo 'pDetAIH.csv' novo. Mantendo faturamento anterior.")

# --- 4. IMPORTAÇÃO HISTÓRICA TABNET (Se houver arquivo novo) ---
# Verifica se existe algum arquivo começando com 'sih_cnv' na pasta
arquivos_tabnet = [f for f in os.listdir(".") if f.startswith("sih_cnv") and f.endswith(".csv")]
if arquivos_tabnet:
    print(f"\n[INFO] Arquivo histórico TabNet detectado ({arquivos_tabnet[0]}). Importando...")
    rodar("importar_tabnet.py", obrigatorio=False)
else:
    print("\n[INFO] Nenhum arquivo do TabNet encontrado. Mantendo histórico anterior.")

# --- 5. AUDITORIA FINANCEIRA ---
# Gera o Excel com as perdas (Cruzamento Sisreg x Faturamento)
rodar("gerar_relatorio_financeiro_v2.py", obrigatorio=False)

# --- 6. GERAÇÃO DO SITE (Dashboard) ---
# Cria o HTML e JSON finais para o portal
rodar("gerar_dashboard.py")

# --- 7. UPLOAD (Sobe pra nuvem) ---
# Envia tudo para o GitHub
rodar("upload_manager.py")

imprimir_titulo("PROCESSO FINALIZADO COM SUCESSO!")
print("   Pode acessar o portal: https://franckmoura.github.io/NII-Portal/")
print("   Fechando em 10 segundos...")
time.sleep(10)