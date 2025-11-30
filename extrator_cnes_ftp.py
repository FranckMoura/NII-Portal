import os
import ftplib
import time

# --- CONFIGURAÇÕES ---
ESTADO = 'MT'
PASTA_DESTINO = "arquivos"
PASTA_FTP_OFICIAL = '/dissemin/publicos/CNES/200508_/Dados'

print(f"🏥 --- EXTRATOR CNES V5 (LISTAGEM TOTAL) ---")
print(f"Conectando ao FTP do DATASUS...")

if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

try:
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    ftp.cwd(PASTA_FTP_OFICIAL)
    print(f"📂 Pasta acessada: {PASTA_FTP_OFICIAL}")
    
    # PASSO 1: BAIXAR A LISTA COMPLETA DE NOMES
    print("⏳ Obtendo lista de todos os arquivos (isso pode levar uns segundos)...")
    todos_arquivos = []
    ftp.retrlines('NLST', todos_arquivos.append)
    print(f"   -> O servidor tem {len(todos_arquivos)} arquivos no total.")

    def baixar_mais_recente(prefixo):
        print(f"\n[Procurando grupo: {prefixo} para {ESTADO}]")
        
        # Filtro Local (Python) - Ignora maiúsculas/minúsculas
        candidatos = [
            f for f in todos_arquivos 
            if f.upper().startswith(f"{prefixo}{ESTADO}") and f.lower().endswith('.dbc')
        ]
        
        if not candidatos:
            print(f"   ❌ Nenhum arquivo encontrado para {prefixo}{ESTADO}.")
            # Debug: Mostra o que tem lá parecido
            print(f"      Exemplos de arquivos na pasta: {todos_arquivos[:3]}")
            return

        # Ordena para pegar o último (mais recente)
        candidatos.sort()
        arquivo_alvo = candidatos[-1]
        
        print(f"   -> Encontrado: {arquivo_alvo}")
        
        caminho_local = os.path.join(PASTA_DESTINO, arquivo_alvo)
        try:
            print(f"   -> Baixando...", end="")
            with open(caminho_local, 'wb') as f:
                ftp.retrbinary(f"RETR {arquivo_alvo}", f.write)
            print(" ✅ Sucesso!")
        except Exception as e:
            print(f"\n   ❌ Erro ao baixar: {e}")

    # PASSO 2: FILTRAR E BAIXAR
    baixar_mais_recente('PF') # Profissionais
    baixar_mais_recente('LT') # Leitos
    baixar_mais_recente('EQ') # Equipamentos
    baixar_mais_recente('ST') # Estabelecimentos
    
    ftp.quit()
    print("\n🚀 Processo finalizado! Verifique a pasta 'arquivos'.")

except Exception as e:
    print(f"\n❌ Erro Geral: {e}")