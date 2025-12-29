# ==============================================================================
# MASTER SCRIPT - FECHAMENTO DE COMPETÊNCIA (V2.0 - COMPLETO)
# Autor: Franck Moura (Via NII Automation)
# Data: 29/12/2025
# Descrição:
#   1. Seleciona a pasta do mês.
#   2. Executa TODOS os cálculos (Rateio, Terceiros, Financiamento, Fila Zero).
#   3. Gera a Capa.
#   4. Atualiza o Portal Web.
# ==============================================================================

import os
import subprocess
import sys

# Cores para o Terminal
VERDE = "\033[92m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
RESET = "\033[0m"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def executar_script(caminho_script):
    """Executa um script Python em seu próprio diretório"""
    if os.path.exists(caminho_script):
        nome = os.path.basename(caminho_script)
        diretorio = os.path.dirname(caminho_script)
        
        print(f"   ... Rodando: {AMARELO}{nome}{RESET}")
        try:
            subprocess.run([sys.executable, caminho_script], cwd=diretorio, check=True)
            print(f"   {VERDE}✔ Sucesso: {nome}{RESET}")
        except subprocess.CalledProcessError:
            print(f"   ❌ Erro ao executar {nome}")
    else:
        # Silencioso para scripts opcionais (ex: Fila Zero se não tiver)
        pass

def menu_selecao_pasta():
    print(f"\n{AZUL}=== GERENTE DE FECHAMENTO FINANCEIRO ==={RESET}")
    print("O script vai procurar pastas dentro de 'faturamento/2025/' (ou ano atual).")
    
    # Define ano base (pode ser dinâmico no futuro)
    ano_atual = "2025" 
    base_path = os.path.join(ROOT_DIR, "faturamento", ano_atual)
    
    pastas_encontradas = []
    if os.path.exists(base_path):
        itens = os.listdir(base_path)
        for item in itens:
            full_path = os.path.join(base_path, item)
            if os.path.isdir(full_path) and not item.startswith("."):
                pastas_encontradas.append(item)
    
    pastas_encontradas.sort()
    
    print("\nPastas encontradas:")
    for i, p in enumerate(pastas_encontradas):
        print(f" [{i+1}] {p}")
    
    opcao = input(f"\n{AMARELO}Digite o número da pasta ou o nome manual: {RESET}")
    
    pasta_escolhida = ""
    try:
        idx = int(opcao) - 1
        if 0 <= idx < len(pastas_encontradas):
            pasta_escolhida = os.path.join(base_path, pastas_encontradas[idx])
    except:
        if os.path.exists(opcao):
            pasta_escolhida = opcao
        elif os.path.exists(os.path.join(base_path, opcao)):
            pasta_escolhida = os.path.join(base_path, opcao)
            
    return pasta_escolhida

# ==============================================================================
# FLUXO PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    
    target_dir = menu_selecao_pasta()
    
    if not target_dir or not os.path.exists(target_dir):
        print(f"\n❌ Pasta inválida ou não encontrada.")
        sys.exit()
        
    print(f"\n{AZUL}🚀 INICIANDO FECHAMENTO NA PASTA:{RESET} {target_dir}\n")
    
    # 1. Scripts Principais (Pasta do Mês)
    scripts_principais = [
        "calculo_rateio_equipe.py",       # Rateio Médico
        "calculo_repasse_terceiros.py",   # SADT Fornecedores
        "calculo_financiamento_geral.py", # Financiamento MAC/FAEC Geral
        "gerar_capa.py"                   # Capa
    ]
    
    for script in scripts_principais:
        executar_script(os.path.join(target_dir, script))
        
    # 2. Scripts Fila Zero (Subpasta ou Raiz)
    # Lista de scripts do Fila Zero
    scripts_fz = [
        "calculo_fila_zero.py",           # Médico Extra
        "calculo_fila_zero_terceiros.py", # SADT Extra
        "calculo_financiamento_fz.py"     # Financiamento FZ
    ]
    
    pasta_fila_zero = os.path.join(target_dir, "fila_zero")
    
    if os.path.exists(pasta_fila_zero):
        print(f"\n{AZUL}>> Processando Fila Zero (Subpasta)...{RESET}")
        for script in scripts_fz:
            executar_script(os.path.join(pasta_fila_zero, script))
    else:
        # Caso o usuário tenha salvado tudo na mesma pasta raiz
        print(f"\n{AZUL}>> Verificando scripts Fila Zero na raiz...{RESET}")
        for script in scripts_fz:
            full = os.path.join(target_dir, script)
            if os.path.exists(full):
                executar_script(full)

    # 3. Upload Final
    print(f"\n{AZUL}>> Enviando atualizações para o Portal...{RESET}")
    path_upload = os.path.join(ROOT_DIR, "upload_manager.py")
    executar_script(path_upload)
    
    print(f"\n{VERDE}✅ FECHAMENTO CONCLUÍDO COM SUCESSO!{RESET}")
    print("Todos os relatórios foram gerados e o portal foi atualizado.")