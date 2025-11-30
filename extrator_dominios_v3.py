import os
import ftplib
import zipfile

# --- CONFIGURAÇÕES ---
PASTA_DESTINO = "arquivos"
PASTA_FTP_DOMINIOS = '/dissemin/publicos/CNES/200508_/Auxiliar'
ARQUIVO_ALVO = 'TAB_CNES.zip'

print(f"📚 --- EXTRATOR DE DOMÍNIOS V3 (ZIP) ---")

if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

try:
    # 1. BAIXAR O ZIP
    print(f"1. Conectando ao FTP...")
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    ftp.cwd(PASTA_FTP_DOMINIOS)
    
    caminho_zip = os.path.join(PASTA_DESTINO, ARQUIVO_ALVO)
    
    print(f"   -> Baixando {ARQUIVO_ALVO} (Isso pode demorar um pouco)...", end="")
    with open(caminho_zip, 'wb') as f:
        ftp.retrbinary(f"RETR {ARQUIVO_ALVO}", f.write)
    print(f" ✅ Baixado!")
    
    ftp.quit()

    # 2. EXTRAIR O ZIP
    print(f"2. Extraindo arquivos importantes...")
    with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
        # Lista para conferir o que tem dentro
        arquivos_no_zip = zip_ref.namelist()
        
        # Vamos extrair apenas os dicionários que precisamos para não lotar a pasta
        # (O ZIP tem muitos arquivos, focamos nestes três)
        alvos = ['tb_cbo.dbc', 'tb_equipamento.dbc', 'tb_leito.dbc']
        
        for arquivo in arquivos_no_zip:
            # Verifica se o arquivo é um dos que queremos (ignorando maiusculas/minusculas)
            if any(alvo in arquivo.lower() for alvo in alvos):
                zip_ref.extract(arquivo, PASTA_DESTINO)
                print(f"   -> Extraído: {arquivo}")

    # 3. LIMPEZA
    # Opcional: Remove o ZIP para economizar espaço
    os.remove(caminho_zip)
    print("\n🚀 Dicionários (.dbc) prontos na pasta 'arquivos'!")
    print("⚠️ PRÓXIMO PASSO: Vá ao TabWin e converta esses 3 arquivos para .DBF.")

except Exception as e:
    print(f"\n❌ Erro: {e}")