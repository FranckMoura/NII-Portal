import os
import json
import subprocess
from datetime import datetime

# --- CONFIGURAÇÕES ---
PASTA_ARQUIVOS = 'arquivos'
ARQUIVO_DB = 'dados.json'

print("--- INICIANDO GERENCIADOR DE UPLOAD NII ---")

# 1. Escanear a pasta de arquivos
lista_arquivos = []

# Verifica se a pasta existe
if not os.path.exists(PASTA_ARQUIVOS):
    os.makedirs(PASTA_ARQUIVOS)
    print(f"Pasta '{PASTA_ARQUIVOS}' criada. Coloque seus arquivos lá!")

print(f"Lendo arquivos em '{PASTA_ARQUIVOS}'...")

for nome_arquivo in os.listdir(PASTA_ARQUIVOS):
    # Ignora arquivos ocultos ou de sistema
    if nome_arquivo.startswith('.'): continue

    caminho_completo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
    
    # Pega informações do arquivo
    stats = os.stat(caminho_completo)
    tamanho_kb = round(stats.st_size / 1024, 2)
    data_modificacao = datetime.fromtimestamp(stats.st_mtime).strftime('%d/%m/%Y')
    
    # Define o ícone baseado na extensão
    tipo = "outro"
    icone = "📄"
    if nome_arquivo.lower().endswith('.pdf'):
        tipo = "pdf"
        icone = "📕" # Ícone de livro vermelho
    elif nome_arquivo.lower().endswith('.html'):
        tipo = "html"
        icone = "🌐" # Ícone de globo

    # Adiciona na lista
    lista_arquivos.append({
        "nome": nome_arquivo,
        "caminho": f"{PASTA_ARQUIVOS}/{nome_arquivo}",
        "tamanho": f"{tamanho_kb} KB",
        "data": data_modificacao,
        "tipo": tipo,
        "icone": icone
    })

# 2. Salvar no "Banco de Dados" (JSON)
with open(ARQUIVO_DB, 'w', encoding='utf-8') as f:
    json.dump(lista_arquivos, f, indent=4, ensure_ascii=False)

print(f"Base de dados atualizada com {len(lista_arquivos)} arquivos.")

# 3. Upload para o GitHub (Automação Git)
# Nota: Você precisa ter o Git instalado e configurado nesta pasta
print("\nEnviando para o Portal...")
try:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Atualização automática: {datetime.now()}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("\n[SUCESSO] Arquivos enviados! O portal atualizará em alguns minutos.")
except Exception as e:
    print(f"\n[ERRO NO GIT] {e}")
    print("Verifique se você configurou o git init e o remote corretamente.")