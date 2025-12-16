import subprocess
import time
import os
import sys

def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("SISTEMA DE GESTÃO E AUDITORIA NII (V22 - FINAL)")
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
            print("   (Processo interrompido por segurança)")
            exit()
        return False

# --- 1. EXTRAÇÃO SISREG (Robô V18) ---
# Baixa os dados do site (se falhar, o processo continua com dados antigos)
rodar("extracao_sisreg_v18.py", obrigatorio=False)

# --- 2. CARGA SISREG -> POSTGRES (Banco de Dados) ---
# Atualiza a tabela do Sisreg no banco
rodar("banco_dados_sisreg_postgres.py")

# --- 3. IMPORTAÇÃO FINANCEIRA (Se houver arquivo novo) ---
# Verifica se existe pDetAIH.csv para atualizar o faturamento
if os.path.exists("pDetAIH.csv"):
    print("\n[INFO] Arquivo de faturamento detectado. Atualizando banco...")
    rodar("importar_faturamento_v3.py", obrigatorio=False)
else:
    print("\n[INFO] Nenhum arquivo 'pDetAIH.csv' novo. Mantendo faturamento anterior.")

# --- 4. IMPORTAÇÃO HISTÓRICA TABNET (Se houver arquivo novo) ---
# Verifica se existe algum CSV do TabNet (sih_cnv...)
arquivos_tabnet = [f for f in os.listdir(".") if f.startswith("sih_cnv") and f.endswith(".csv")]
if arquivos_tabnet:
    print(f"\n[INFO] Arquivo histórico TabNet detectado ({arquivos_tabnet[0]}). Importando...")
    rodar("importar_tabnet.py", obrigatorio=False)
else:
    print("\n[INFO] Nenhum arquivo do TabNet encontrado. Mantendo histórico anterior.")

# --- 5. AUDITORIA FINANCEIRA (Relatório Excel) ---
# Gera o relatório de perdas (IMPORTANTE: Requer gerar_relatorio_financeiro_v2.py salvo)
rodar("gerar_relatorio_financeiro_v2.py", obrigatorio=False)

# --- 6. GERAÇÃO DO SITE (Dashboard HTML) ---
# Cria as páginas web
rodar("gerar_dashboard.py")

# --- 7. UPLOAD (Sobe pra nuvem) ---
# Usa a V6 que força a inclusão de arquivos novos
rodar("upload_manager_v6.py")

imprimir_titulo("PROCESSO FINALIZADO COM SUCESSO!")
print("   Acesse: https://franckmoura.github.io/NII-Portal/")
print("   Fechando em 10 segundos...")
time.sleep(10)