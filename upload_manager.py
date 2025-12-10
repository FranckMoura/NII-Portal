import os
import json
import subprocess
from datetime import datetime

# --- CONFIGURAÇÕES ---
PASTA_ARQUIVOS = 'arquivos'
ARQUIVO_DB_JSON = 'dados.json'

print("--- INICIANDO GERENCIADOR DE UPLOAD NII (V5 - FINANCEIRO) ---")

# 1. Atualiza lista de downloads GERAIS (Mantido da versão anterior)
# (Isso gerencia os arquivos soltos da pasta 'arquivos', não mexe no financeiro)
lista_arquivos = []
if not os.path.exists(PASTA_ARQUIVOS): os.makedirs(PASTA_ARQUIVOS)

print(f"Lendo arquivos em '{PASTA_ARQUIVOS}'...")
for nome_arquivo in os.listdir(PASTA_ARQUIVOS):
    if nome_arquivo.startswith('.'): continue
    caminho_completo = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
    try:
        stats = os.stat(caminho_completo)
        tamanho_kb = round(stats.st_size / 1024, 2)
        data_modificacao = datetime.fromtimestamp(stats.st_mtime).strftime('%d/%m/%Y')
        tipo = "outro"
        icone = "📄"
        if nome_arquivo.lower().endswith('.pdf'): tipo, icone = "pdf", "📕"
        elif nome_arquivo.lower().endswith('.html'): tipo, icone = "html", "🌐"
        elif nome_arquivo.lower().endswith('.csv'): tipo, icone = "csv", "📊"
        elif nome_arquivo.lower().endswith('.parquet'): tipo, icone = "parquet", "📦"
        elif nome_arquivo.lower().endswith('.xls'): tipo, icone = "excel", "📗"

        lista_arquivos.append({
            "nome": nome_arquivo,
            "caminho": f"{PASTA_ARQUIVOS}/{nome_arquivo}",
            "tamanho": f"{tamanho_kb} KB",
            "data": data_modificacao,
            "tipo": tipo,
            "icone": icone
        })
    except: pass

with open(ARQUIVO_DB_JSON, 'w', encoding='utf-8') as f:
    json.dump(lista_arquivos, f, indent=4, ensure_ascii=False)

# 2. UPLOAD CIRÚRGICO (ATUALIZADO PARA FINANCEIRO)
print("\nEnviando para o Portal...")
try:
    # Lista de arquivos OBRIGATÓRIOS para o site funcionar
    arquivos_vitais = [
        "index.html",
        "financeiro.html",       # [NOVO] Módulo Financeiro
        "dados_financeiro.json", # [NOVO] Base de dados Financeira
        "painel_regulacao.html",
        "indicasus.html",
        "faturamento.html",
        "manuais.html",
        "indicadores.html",
        "dados.json",
        "css/",
        "js/",
        "img/",
        "arquivos/",             # Pasta de arquivos gerais
        "faturamento/"           # [NOVO] Pasta onde ficam os relatórios mensais gerados
    ]

    # Adiciona cada item vital (Arquivos e Pastas)
    for item in arquivos_vitais:
        if os.path.exists(item):
            print(f" -> Preparando: {item}")
            subprocess.run(["git", "add", item], check=False)
    
    # Força adicionar scripts Python (backup) em TODAS as pastas (recursivo)
    # Isso garante que o 'calculo_rateio_equipe.py' que está lá na pasta do mês seja salvo
    subprocess.run(["git", "add", "*.py"], check=False)
    subprocess.run(["git", "add", "**/*.py"], check=False) # Tenta pegar em subpastas

    # Commit e Push
    msg = f"Atualização Financeiro: {datetime.now().strftime('%d/%m %H:%M')}"
    
    # Verifica se tem algo para commitar
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
    
    if status:
        subprocess.run(["git", "commit", "-m", msg], check=True)
        print("   -> Commit realizado.")
        subprocess.run(["git", "push"], check=True)
        print("\n✅ [SUCESSO] Site atualizado! O módulo financeiro já deve estar no ar.")
    else:
        print("\nℹ️ [INFO] Nada mudou desde o último envio.")

except subprocess.CalledProcessError as e:
    print(f"\n❌ [ERRO NO GIT] {e}")
except Exception as e:
    print(f"\n❌ [ERRO GERAL] {e}")