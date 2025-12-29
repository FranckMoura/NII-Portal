# ==============================================================================
# GERENCIADOR DE UPLOAD NII PORTAL (V6.0 - GIT ROBUSTO)
# Autor: Franck Moura (Via NII Automation)
# Data: 29/12/2025
# Descrição: Sincroniza arquivos locais com o GitHub Pages.
#            Correção: Força 'git add --all' e detecta branch automaticamente.
# ==============================================================================

import os
import subprocess
import sys
from datetime import datetime

# Cores para o terminal
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
RESET = "\033[0m"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_command(command, description):
    """Executa comando no terminal e trata erros"""
    print(f" -> {description}...", end=" ", flush=True)
    try:
        # cwd=ROOT_DIR garante que o comando rode na pasta certa
        result = subprocess.run(
            command, 
            cwd=ROOT_DIR, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"{VERDE}OK{RESET}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        # Se for erro de "nothing to commit", ignoramos (não é erro crítico)
        if "nothing to commit" in e.stdout or "nothing to commit" in e.stderr:
            print(f"{AMARELO}Nada novo para enviar.{RESET}")
            return True, "Nada novo"
        
        print(f"{VERMELHO}FALHOU{RESET}")
        print(f"\n   ERRO DETALHADO:\n   {e.stderr}")
        return False, e.stderr

def get_current_branch():
    """Descobre o nome da branch atual (ex: main ou main1)"""
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'], 
            cwd=ROOT_DIR, 
            capture_output=True, 
            text=True
        )
        branch = result.stdout.strip()
        if branch: return branch
        return "main" # Fallback
    except:
        return "main"

# ==============================================================================
# FLUXO PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{VERDE}--- SINCRONIZADOR NII PORTAL (V6.0) ---{RESET}")
    print(f"Pasta Raiz: {ROOT_DIR}\n")

    # 1. Identificar Branch
    branch_atual = get_current_branch()
    print(f"📡 Branch detectada: {AMARELO}{branch_atual}{RESET}\n")

    # 2. Adicionar TUDO (A etapa que faltava/falhou)
    # git add --all garante que novos arquivos, modificados e deletados sejam processados
    sucesso_add, _ = run_command(['git', 'add', '--all'], "Adicionando arquivos (Staging)")
    
    if sucesso_add:
        # 3. Commit (Empacotar)
        data_hora = datetime.now().strftime("%d/%m %H:%M")
        msg_commit = f"Atualizacao Automatica: {data_hora}"
        sucesso_commit, _ = run_command(['git', 'commit', '-m', msg_commit], "Criando pacote (Commit)")

        # 4. Push (Enviar)
        # Se o commit passou (ou se não tinha nada mas tem commits pendentes), tenta o push
        print(f" -> Enviando para nuvem (Push)...", end=" ", flush=True)
        try:
            subprocess.run(['git', 'push', 'origin', branch_atual], cwd=ROOT_DIR, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{VERDE}SUCESSO TOTAL! 🚀{RESET}")
            print("\n✅ Seu portal foi atualizado. Aguarde 1 ou 2 minutos para refletir no site.")
        except subprocess.CalledProcessError as e:
            print(f"{VERMELHO}ERRO NO ENVIO{RESET}")
            print("   Verifique sua conexão com a internet ou credenciais do Git.")
    
    print("\n---------------------------------------------------")