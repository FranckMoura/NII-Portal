import os
import ftplib
import time

# --- CONFIGURAÇÕES ---
ESTADO = 'MT'
PASTA_DESTINO = "arquivos"
# Caminho base (o corredor principal)
CAMINHO_BASE_FTP = '/dissemin/publicos/CNES/200508_/Dados'

print(f"🏥 --- EXTRATOR CNES V6 (NAVEGADOR DE PASTAS) ---")
print(f"Conectando ao FTP do DATASUS...")

if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

def baixar_do_grupo(ftp, sigla_grupo):
    """
    Entra na pasta do grupo (ex: PF), acha o arquivo de MT mais recente e baixa.
    """
    # Monta o caminho da sala específica (ex: .../Dados/PF)
    caminho_grupo = f"{CAMINHO_BASE_FTP}/{sigla_grupo}"
    
    print(f"\n[Acessando pasta: {sigla_grupo} ...]")
    
    try:
        ftp.cwd(caminho_grupo)
        
        # Lista arquivos da pasta
        arquivos = []
        ftp.retrlines('NLST', arquivos.append)
        
        # Filtra: Começa com a Sigla + Estado (ex: PFMT) e termina com .dbc
        candidatos = [
            f for f in arquivos 
            if f.upper().startswith(f"{sigla_grupo}{ESTADO}") and f.lower().endswith('.dbc')
        ]
        
        if not candidatos:
            print(f"   ❌ Nenhum arquivo de {ESTADO} encontrado nesta pasta.")
            return

        # Pega o último (mais recente)
        candidatos.sort()
        arquivo_alvo = candidatos[-1]
        
        print(f"   -> Encontrado: {arquivo_alvo}")
        
        caminho_local = os.path.join(PASTA_DESTINO, arquivo_alvo)
        
        # Baixa
        print(f"   -> Baixando...", end="")
        with open(caminho_local, 'wb') as f:
            ftp.retrbinary(f"RETR {arquivo_alvo}", f.write)
        print(" ✅ Sucesso!")
        
    except ftplib.error_perm:
        print(f"   ❌ Erro 550: A pasta '{sigla_grupo}' não existe ou está inacessível.")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

# --- EXECUÇÃO ---
try:
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    
    # Vamos navegar nas pastas principais
    baixar_do_grupo(ftp, 'PF') # Profissionais
    baixar_do_grupo(ftp, 'LT') # Leitos
    baixar_do_grupo(ftp, 'EQ') # Equipamentos
    baixar_do_grupo(ftp, 'ST') # Estabelecimentos (Habilitações)
    
    ftp.quit()
    print("\n🚀 Processo finalizado! Verifique a pasta 'arquivos'.")

except Exception as e:
    print(f"\n❌ Erro Geral de Conexão: {e}")