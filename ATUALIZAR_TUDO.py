import subprocess
import time
import os
import sys

# --- CONFIGURAÇÃO VISUAL ---
def imprimir_titulo(texto):
    print("\n" + "="*60)
    print(f"   🚀 {texto}")
    print("="*60)

imprimir_titulo("ATUALIZADOR AUTOMÁTICO NII (SISREG + POSTGRESQL)")

# Detecta o Python do sistema
python_cmd = sys.executable 

def rodar_etapa(script_nome, descricao):
    print(f"\n[AGUARDE] Iniciando: {descricao}...")
    print(f"          Arquivo: {script_nome}")
    
    if not os.path.exists(script_nome):
        print(f"❌ ERRO FATAL: O arquivo '{script_nome}' não foi encontrado.")
        return False

    inicio = time.time()
    # Roda o script e espera terminar
    processo = subprocess.run([python_cmd, script_nome])
    fim = time.time()
    
    tempo = round(fim - inicio, 1)

    if processo.returncode == 0:
        print(f"✅ SUCESSO! Etapa concluída em {tempo}s.")
        return True
    else:
        print(f"❌ ERRO: Falha na execução de '{script_nome}'.")
        return False

# --- 1. EXTRAÇÃO (Baixa os dados do site) ---
# Usa a versão V10 que corrigimos (com scroll e checkbox)
if not rodar_etapa("extracao_sisreg_v10.py", "Extração de Dados do SISREG"):
    print("\n⚠️ A extração falhou. Deseja continuar com os arquivos antigos?")
    resp = input("Digite 'S' para continuar ou 'N' para parar: ").upper()
    if resp != 'S':
        exit()

# --- 2. BANCO DE DADOS (Limpa, processa e salva no Postgres) ---
# Usa o novo script que conecta no PostgreSQL
if not rodar_etapa("banco_dados_sisreg_postgres.py", "Atualização do Banco de Dados (PostgreSQL)"):
    print("❌ Parando o processo para evitar dados corrompidos.")
    exit()

# --- 3. DASHBOARD (Gera o HTML/JSON final) ---
if not rodar_etapa("gerar_dashboard.py", "Geração do Painel Web"):
    print("❌ Erro ao gerar o HTML do painel.")
    exit()

# --- 4. UPLOAD (Sobe para o GitHub) ---
if not rodar_etapa("upload_manager.py", "Sincronização com o Portal"):
    print("❌ Erro no upload.")
    exit()

imprimir_titulo("PROCESSO FINALIZADO COM SUCESSO!")
print("   Pode acessar o portal agora.")
print("   Fechando em 10 segundos...")
time.sleep(10)