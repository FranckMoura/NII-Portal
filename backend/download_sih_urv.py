import ftplib
import os
import time

# ==========================================
# CONFIGURAÇÕES DO PROJETO (SIH/SUS - MT)
# ==========================================
FTP_HOST = "ftp.datasus.gov.br"
UF = "MT"
PREFIXO = "RD"  # RD = AIH Reduzida (Contém os valores SH, SP, SADT necessários)
EXTENSAO = ".dbc"
PASTA_DESTINO = "bases_rdmt_brutas"

# Definindo o período faltante para a ação da URV (2000 até a data atual em 2026)
ANOS_PARA_BAIXAR = range(2000, 2027) 
MESES_PARA_BAIXAR = range(1, 13)

def conectar_ftp():
    """Estabelece e retorna a conexão com o FTP do DataSUS."""
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login()
    return ftp

def iniciar_extracao():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
        print(f"📁 Diretório '{PASTA_DESTINO}' criado para armazenar os arquivos.")

    print(f"🔄 Conectando ao FTP do DataSUS...")
    ftp = conectar_ftp()

    for ano in ANOS_PARA_BAIXAR:
        # A inteligência de roteamento de pastas do DataSUS
        if ano < 2008:
            pasta_ftp = "/dissemin/publicos/SIHSUS/199201_200712/Dados"
        else:
            pasta_ftp = "/dissemin/publicos/SIHSUS/200801_/Dados"
        
        try:
            ftp.cwd(pasta_ftp)
        except Exception as e:
            print(f"⚠️ Erro ao acessar a pasta {pasta_ftp}. Reconectando... Erro: {e}")
            ftp = conectar_ftp()
            ftp.cwd(pasta_ftp)

        ano_abrev = str(ano)[-2:] # Ex: 2024 vira 24
        
        for mes in MESES_PARA_BAIXAR:
            # Em 2026, não tenta baixar meses que ainda não ocorreram/foram processados
            if ano == 2026 and mes > 4: 
                continue

            mes_str = str(mes).zfill(2)
            nome_arquivo = f"{PREFIXO}{UF}{ano_abrev}{mes_str}{EXTENSAO}"
            caminho_local = os.path.join(PASTA_DESTINO, nome_arquivo)

            # Evita baixar o que já foi baixado (útil caso a conexão caia)
            if os.path.exists(caminho_local):
                tamanho_local = os.path.getsize(caminho_local)
                if tamanho_local > 0:
                    print(f"⏭️ [OK] {nome_arquivo} já existe localmente.")
                    continue

            print(f"⬇️ Baixando {nome_arquivo}...")
            
            try:
                with open(caminho_local, "wb") as f:
                    ftp.retrbinary(f"RETR {nome_arquivo}", f.write)
            except Exception as e:
                print(f"❌ Arquivo {nome_arquivo} não encontrado no servidor ou erro de rede.")
                if os.path.exists(caminho_local):
                    os.remove(caminho_local) # Remove arquivo corrompido/vazio
                time.sleep(1) # Pausa de segurança para não ser bloqueado pelo firewall do DataSUS

    ftp.quit()
    print("\n🚀 Sincronização da base histórica concluída com sucesso!")

if __name__ == "__main__":
    print("--- 🏥 INICIANDO EXTRAÇÃO DE DADOS (DIFERENÇA URV) ---")
    iniciar_extracao()