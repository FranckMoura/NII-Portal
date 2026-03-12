import subprocess
import os
import sys
import time

# --- CONFIGURAÇÃO DE CAMINHOS ---
# Pega o diretório onde este arquivo (atualizar_tudo.py) está localizado
PASTA_BACKEND = os.path.dirname(os.path.abspath(__file__))

# Define os caminhos exatos dos scripts vizinhos
SCRIPT_EXTRACAO = os.path.join(PASTA_BACKEND, "extracao_sisreg_v18.py")
SCRIPT_PROCESSAMENTO = os.path.join(PASTA_BACKEND, "processar_regulacao_v21.py")

# Usa o mesmo executável Python que está rodando este script agora
PYTHON_EXEC = sys.executable

def rodar_etapa(nome, caminho_script):
    print(f"\n🚀 Iniciando: {nome}...")
    print(f"   📂 Arquivo: {caminho_script}")
    
    if not os.path.exists(caminho_script):
        print(f"   ❌ ERRO CRÍTICO: Arquivo não encontrado: {caminho_script}")
        return False

    try:
        # check=True faz o python lançar erro se o script falhar
        subprocess.run([PYTHON_EXEC, caminho_script], check=True)
        print(f"   ✅ {nome} concluído com sucesso.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro ao rodar {nome}. Código de saída: {e.returncode}")
        return False
    except Exception as e:
        print(f"   ❌ Erro inesperado: {e}")
        return False

def main():
    print("=== 🔄 ATUALIZADOR MESTRE (V2 - Caminhos Absolutos) ===")
    
    inicio = time.time()

    # 1. Rodar Extração
    if not rodar_etapa("Extração (Robô)", SCRIPT_EXTRACAO):
        print("\n⛔ Parando execução devido a erro na extração.")
        return

    # 2. Rodar Processamento
    if not rodar_etapa("Processamento (Banco)", SCRIPT_PROCESSAMENTO):
        print("\n⛔ Parando execução devido a erro no processamento.")
        return

    fim = time.time()
    tempo_total = round(fim - inicio, 2)
    
    print(f"\n=== ✨ TUDO ATUALIZADO EM {tempo_total} SEGUNDOS! ===")

if __name__ == "__main__":
    main()