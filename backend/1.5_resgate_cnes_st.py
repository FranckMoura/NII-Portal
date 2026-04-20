import ftplib
import os

FTP_HOST = "ftp.datasus.gov.br"
UF = "MT"
PASTA_DESTINO = "bases_cnes_brutas"

# Forçamos a busca pela última competência de 2025 (mais estável)
COMPETENCIAS = ["2512", "2511", "2510"]

def conectar_ftp():
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login()
    return ftp

def resgatar_st():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)

    print(f"🔄 Conectando ao FTP do DataSUS para resgatar ST (Estabelecimentos)...")
    ftp = conectar_ftp()
    pasta_alvo = "/dissemin/publicos/CNES/200508_/Dados/ST"
    ftp.cwd(pasta_alvo)

    for comp in COMPETENCIAS:
        nome_arquivo = f"ST{UF}{comp}.dbc"
        caminho_local = os.path.join(PASTA_DESTINO, nome_arquivo)
        
        print(f"⬇️ Baixando {nome_arquivo}...")
        try:
            with open(caminho_local, "wb") as f:
                ftp.retrbinary(f"RETR {nome_arquivo}", f.write)
            print(f"✅ Sucesso! {nome_arquivo} baixado.")
            break
        except Exception as e:
            print(f"❌ Erro ao baixar {nome_arquivo}: {e}")
            if os.path.exists(caminho_local): os.remove(caminho_local)

    ftp.quit()

if __name__ == "__main__":
    resgatar_st()