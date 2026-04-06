import ftplib
import os
import time

# ==========================================
# CONFIGURAÇÕES DO PROJETO (SP - Serviços Profissionais / Itens da Conta)
# ==========================================
FTP_HOST = "ftp.datasus.gov.br"
UF = "MT"
PREFIXO = "SP"  # Mudança de RD para SP (Serviços Profissionais)
EXTENSAO = ".dbc"
PASTA_DESTINO = "bases_spmt_brutas" # Pasta separada para não misturar com o RD

# Baixar dados de 2024 a 2026 (Como o SP é gigantesco, recomendo baixar menos anos históricos)
ANOS_PARA_BAIXAR = range(2024, 2027) 
MESES_PARA_BAIXAR = range(1, 13)

def conectar_ftp():
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login()
    return ftp

def iniciar_extracao():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)
        print(f"📁 Diretório '{PASTA_DESTINO}' criado para armazenar os arquivos de Serviços Profissionais (SP).")

    print(f"🔄 Conectando ao FTP do DataSUS...")
    ftp = conectar_ftp()

    for ano in ANOS_PARA_BAIXAR:
        pasta_ftp = "/dissemin/publicos/SIHSUS/200801_/Dados"
        
        try:
            ftp.cwd(pasta_ftp)
        except Exception as e:
            print(f"⚠️ Erro ao acessar a pasta {pasta_ftp}. Reconectando... Erro: {e}")
            ftp = conectar_ftp()
            ftp.cwd(pasta_ftp)

        ano_abrev = str(ano)[-2:]
        
        for mes in MESES_PARA_BAIXAR:
            if ano == 2026 and mes > 4: 
                continue

            mes_str = str(mes).zfill(2)
            nome_arquivo = f"{PREFIXO}{UF}{ano_abrev}{mes_str}{EXTENSAO}"
            caminho_local = os.path.join(PASTA_DESTINO, nome_arquivo)

            if os.path.exists(caminho_local):
                tamanho_local = os.path.getsize(caminho_local)
                if tamanho_local > 0:
                    print(f"⏭️ [OK] {nome_arquivo} já existe localmente.")
                    continue

            print(f"⬇️ Baixando {nome_arquivo} (Aviso: Arquivos SP são muito maiores que os RD)...")
            
            try:
                with open(caminho_local, "wb") as f:
                    ftp.retrbinary(f"RETR {nome_arquivo}", f.write)
            except Exception as e:
                print(f"❌ Arquivo {nome_arquivo} não encontrado no servidor ou erro de rede.")
                if os.path.exists(caminho_local):
                    os.remove(caminho_local) 
                time.sleep(1) 

    ftp.quit()
    print("\n🚀 Sincronização da base SP (Serviços Profissionais) concluída com sucesso!")

if __name__ == "__main__":
    print("--- 🏥 INICIANDO EXTRAÇÃO DE DADOS (ITENS SECUNDÁRIOS - SP) ---")
    iniciar_extracao()