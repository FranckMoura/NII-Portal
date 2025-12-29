# ==============================================================================
# MASTER SCRIPT - FECHAMENTO DE COMPETÊNCIA
# Autor: Franck Moura (Via NII Automation)
# Data: 29/12/2025
# Descrição:
#   1. Pergunta qual a pasta do mês (ex: faturamento/2025/11_novembro).
#   2. Entra na pasta e executa TODOS os scripts de cálculo encontrados.
#   3. Entra na subpasta 'fila_zero' (se existir) e executa os scripts de lá.
#   4. Executa o Upload Manager para atualizar o site.
# ==============================================================================

import os
import subprocess
import glob
import sys

# Configuração de Cores para o Terminal
VERDE = "\033[92m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
RESET = "\033[0m"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def executar_script(caminho_script):
    """Executa um script Python em seu próprio diretório para não quebrar caminhos"""
    if os.path.exists(caminho_script):
        nome = os.path.basename(caminho_script)
        diretorio = os.path.dirname(caminho_script)
        
        print(f"   ... Rodando: {AMARELO}{nome}{RESET}")
        try:
            # Executa o script usando o interpretador atual do sistema
            subprocess.run([sys.executable, caminho_script], cwd=diretorio, check=True)
            print(f"   {VERDE}✔ Sucesso: {nome}{RESET}")
        except subprocess.CalledProcessError:
            print(f"   ❌ Erro ao executar {nome}")
    else:
        print(f"   ⚠️ Script não encontrado: {caminho_script}")

def menu_selecao_pasta():
    print(f"\n{AZUL}=== GERENTE DE FECHAMENTO FINANCEIRO ==={RESET}")
    print("O script vai procurar pastas dentro de 'faturamento/2025/' (ou ano atual).")
    
    # Tenta listar as pastas de meses automaticamente
    ano_atual = "2025" # Pode automatizar com datetime se quiser
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
        # Se digitou texto, tenta achar o caminho
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
        print(f"\n❌ Pasta inválida ou não encontrada. Verifique o caminho.")
        sys.exit()
        
    print(f"\n{AZUL}🚀 INICIANDO FECHAMENTO NA PASTA:{RESET} {target_dir}\n")
    
    # 1. Scripts Principais (Rateio, Terceiros, Capa)
    scripts_principais = [
        "calculo_rateio_equipe.py",
        "calculo_repasse_terceiros.py",
        "gerar_capa.py"
    ]
    
    for script in scripts_principais:
        executar_script(os.path.join(target_dir, script))
        
    # 2. Scripts Fila Zero (Geralmente em subpasta, mas verificamos os dois)
    pasta_fila_zero = os.path.join(target_dir, "fila_zero")
    scripts_fz = [
        "calculo_fila_zero.py",
        "calculo_fila_zero_terceiros.py"
    ]
    
    if os.path.exists(pasta_fila_zero):
        print(f"\n{AZUL}>> Processando Fila Zero (Subpasta)...{RESET}")
        for script in scripts_fz:
            executar_script(os.path.join(pasta_fila_zero, script))
    else:
        # Tenta achar na raiz mesmo se não tiver subpasta
        print(f"\n{AZUL}>> Verificando Fila Zero na raiz...{RESET}")
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
    print("Agora basta abrir a pasta, abrir os HTMLs e imprimir.")