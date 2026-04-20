import ftplib
import os

# ==========================================
# CONFIGURAÇÕES DO PROJETO (CNES)
# ==========================================
FTP_HOST = "ftp.datasus.gov.br"
UF = "MT"
PASTA_DESTINO = "bases_cnes_brutas"

# Sistema Inteligente: Tenta baixar o mais recente. Se não existir (Erro 550), tenta o mês anterior!
COMPETENCIAS = ["2603", "2602", "2601", "2512", "2511"] 

def conectar_ftp():
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login()
    return ftp

def baixar_arquivo(ftp, pasta_base, prefixo):
    # A pasta do CNES é dividida por prefixos: /Dados/ST, /Dados/PF
    pasta_alvo = f"{pasta_base}/{prefixo}"
    
    try:
        ftp.cwd(pasta_alvo)
    except Exception as e:
        print(f"⚠️ Erro ao acessar a subpasta {pasta_alvo}: {e}")
        return None

    for comp in COMPETENCIAS:
        nome_arquivo = f"{prefixo}{UF}{comp}.dbc"
        caminho_local = os.path.join(PASTA_DESTINO, nome_arquivo)
        
        if os.path.exists(caminho_local) and os.path.getsize(caminho_local) > 0:
            print(f"⏭️ [OK] {nome_arquivo} já existe localmente.")
            return nome_arquivo

        print(f"⬇️ Tentando baixar {nome_arquivo}...")
        try:
            with open(caminho_local, "wb") as f:
                ftp.retrbinary(f"RETR {nome_arquivo}", f.write)
            print(f"✅ Sucesso! {nome_arquivo} encontrado e baixado.")
            return nome_arquivo # Se achou o arquivo, para a busca (sai do loop)
        except ftplib.error_perm:
            # Erro 550 significa que o Datasus ainda não publicou este mês
            print(f"⏳ {nome_arquivo} não encontrado (provável atraso do Datasus). Tentando o mês anterior...")
            if os.path.exists(caminho_local):
                os.remove(caminho_local)
        except Exception as e:
            print(f"❌ Erro de rede ao baixar {nome_arquivo}: {e}")
            if os.path.exists(caminho_local):
                os.remove(caminho_local)
            
    print(f"⚠️ Nenhum arquivo recente encontrado para {prefixo}{UF}.")
    return None

def iniciar_extracao_cnes():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
        print(f"📁 Diretório '{PASTA_DESTINO}' criado.")

    print(f"🔄 Conectando ao FTP do DataSUS...")
    ftp = conectar_ftp()
    pasta_base = "/dissemin/publicos/CNES/200508_/Dados"

    # Baixa ST (Estabelecimentos / Laboratórios)
    arquivo_st = baixar_arquivo(ftp, pasta_base, "ST")
    
    # Volta para a raiz e reconecta para evitar "Timeouts" do servidor do Governo
    ftp.quit()
    ftp = conectar_ftp()
    
    # Baixa PF (Profissionais Pessoa Física)
    arquivo_pf = baixar_arquivo(ftp, pasta_base, "PF")

    ftp.quit()
    
    if arquivo_st and arquivo_pf:
        print("\n🚀 DOWNLOAD CNES CONCLUÍDO COM SUCESSO!")
        print(f"Os arquivos baixados foram: {arquivo_st} e {arquivo_pf}")
    else:
        print("\n⚠️ Ocorreu um problema ao baixar um dos arquivos do CNES.")

if __name__ == "__main__":
    print("--- 🏥 INICIANDO DOWNLOAD DO CADASTRO CNES (BUSCA INTELIGENTE) ---")
    iniciar_extracao_cnes()