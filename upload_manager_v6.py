import os
import subprocess
import datetime
import shutil

print("--- UPLOAD MANAGER NII (V6 - FORÇA BRUTA) ---")

PASTA_PROJETO = r"C:\Users\DELL\OneDrive\NII-Portal-1"
PASTA_ARQUIVOS_SITE = os.path.join(PASTA_PROJETO, "arquivos")

if not os.path.exists(PASTA_ARQUIVOS_SITE): os.makedirs(PASTA_ARQUIVOS_SITE)

# Copia o Excel financeiro para a pasta do site (para você baixar pelo portal se quiser)
excel_origem = os.path.join(PASTA_PROJETO, "RELATORIO_NAO_FATURADOS.xlsx")
excel_destino = os.path.join(PASTA_ARQUIVOS_SITE, "auditoria_financeira.xlsx")

if os.path.exists(excel_origem):
    shutil.copy2(excel_origem, excel_destino)
    print(">> Relatório Excel copiado para a pasta do site.")

def run_git(commands):
    try:
        result = subprocess.run(
            ["git"] + commands, 
            cwd=PASTA_PROJETO, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        if result.returncode != 0:
            print(f"   [GIT ERRO] {result.stderr}")
        return result.stdout
    except Exception as e:
        print(f"   [SISTEMA ERRO] {e}")
        return ""

print(">> Adicionando TODOS os arquivos novos...")
run_git(["add", "."]) # O segredo: adiciona tudo, inclusive os untracked

timestamp = datetime.datetime.now().strftime("%d/%m %H:%M")
msg = f"Atualização Completa: {timestamp}"

print(f">> Commitando: '{msg}'...")
run_git(["commit", "-m", msg])

print(">> Enviando para o GitHub (Push)...")
saida = run_git(["push", "origin", "main1"]) # Confirme se sua branch é main1 ou main

if "Enumerating objects" in saida or "Everything up-to-date" in saida:
    print("✅ UPLOAD CONCLUÍDO COM SUCESSO!")
else:
    print("⚠️ Verifique a saída acima.")