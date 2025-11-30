import ftplib
import os

# --- CONFIGURAÇÕES ---
ESTADO = 'MT'
PASTA_ALVO = '/dissemin/publicos/CNES/200508_+/Dados'

print(f"🕵️ --- RAIO-X DO FTP DATASUS ---")
print(f"Conectando ao servidor...")

try:
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    print("✅ Login realizado.")
    
    print(f"📂 Tentando entrar na pasta: {PASTA_ALVO}")
    ftp.cwd(PASTA_ALVO)
    print("✅ Pasta encontrada! Listando arquivos recentes do MT...")
    
    # Lista todos os arquivos da pasta
    todos_arquivos = []
    ftp.retrlines('NLST', todos_arquivos.append)
    
    # Filtra apenas os do seu estado (MT) e que parecem ser de 2024/2025
    arquivos_mt = [f for f in todos_arquivos if ESTADO in f and ('24' in f or '25' in f)]
    
    # Ordena para ver os mais recentes no final
    arquivos_mt.sort()
    
    print(f"\n📄 Encontrei {len(arquivos_mt)} arquivos recentes para {ESTADO}.")
    print("--- ÚLTIMOS 15 ARQUIVOS DISPONÍVEIS ---")
    for arq in arquivos_mt[-15:]:
        print(f"   -> {arq}")
        
    print("\n------------------------------------------------")
    if len(arquivos_mt) > 0:
        print("DICA: Copie o nome exato do arquivo mais recente da lista acima (ex: STMT2409.dbc)")
        print("e use esse mês/ano no seu extrator.")
    else:
        print("❌ Estranho... Nenhum arquivo com 'MT' e '24/25' foi achado.")
        
    ftp.quit()

except Exception as e:
    print(f"\n❌ ERRO FATAL: {e}")