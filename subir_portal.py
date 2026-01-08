import os
import subprocess
import time
from datetime import datetime

print("--- 🚀 SUBINDO ATUALIZAÇÕES PARA O NII-PORTAL ---")

# --- CONFIGURAÇÕES ---
# Caminho da pasta raiz do projeto
PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"

# --- FUNÇÕES ---
def executar_comando(comando):
    try:
        resultado = subprocess.run(comando, cwd=PASTA_PROJETO, text=True, capture_output=True, encoding='utf-8')
        if resultado.returncode == 0:
            print(f"✅ Sucesso: {' '.join(comando)}")
            return True
        else:
            print(f"⚠️ Aviso: {resultado.stderr}")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        return False

# --- EXECUÇÃO ---
if not os.path.exists(PASTA_PROJETO):
    print(f"❌ Erro: Pasta do projeto não encontrada: {PASTA_PROJETO}")
    exit()

print(f">> Acessando pasta: {PASTA_PROJETO}")
os.chdir(PASTA_PROJETO)

# 1. Verificar Status
print("\n>> Verificando arquivos modificados...")
executar_comando(["git", "status"])

# 2. Adicionar tudo (Incluindo o novo HTML e Excel na pasta natalidade)
print("\n>> Adicionando arquivos...")
executar_comando(["git", "add", "."])

# 3. Commit (Salvar versão)
data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
mensagem = f"Atualizacao Painel Natalidade - {data_hora}"
print(f"\n>> Salvando versão: '{mensagem}'")
executar_comando(["git", "commit", "-m", mensagem])

# 4. Push (Enviar para nuvem)
print("\n>> Enviando para o GitHub (Aguarde)...")
sucesso = executar_comando(["git", "push"])

if sucesso:
    print("\n" + "="*50)
    print("🎉 PORTAL ATUALIZADO COM SUCESSO!")
    print("="*50)
    print("⏳ Aguarde cerca de 1 a 2 minutos para o GitHub processar.")
    print("\n🔗 SEU NOVO PAINEL ESTARÁ DISPONÍVEL EM:")
    # Ajuste o link abaixo conforme onde você salvou o arquivo
    print("https://franckmoura.github.io/NII-Portal-1/natalidade/2025/painel_natalidade_final.html")
    print("="*50)
else:
    print("\n❌ Houve um erro ao enviar. Verifique sua conexão ou credenciais.")