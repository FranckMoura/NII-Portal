import ftplib
import os
import time

print("--- 🏥 RETOMANDO DOWNLOAD BLINDADO DO AMBULATÓRIO (SIA/SUS) ---")

# ==========================================
# CONFIGURAÇÕES DO PROJETO
# ==========================================
FTP_HOST = "ftp.datasus.gov.br"
UF = "MT"
PREFIXO = "PA"
EXTENSAO = ".dbc"
PASTA_DESTINO = "bases_pamt_brutas"

ANOS_PARA_BAIXAR = range(2000, 2027) 
MESES_PARA_BAIXAR = range(1, 13)

def conectar_ftp():
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login()
    return ftp

def iniciar_extracao():
    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)

    print(f"🔄 Conectando ao FTP do DataSUS...")
    ftp = conectar_ftp()

    for ano in ANOS_PARA_BAIXAR:
        # Define a base da pasta sem o "Dados"
        if ano < 2008:
            base_pasta = "/dissemin/publicos/SIASUS/199407_200712"
        else:
            base_pasta = "/dissemin/publicos/SIASUS/200801_"

        ano_abrev = str(ano)[-2:]
        
        for mes in MESES_PARA_BAIXAR:
            if ano == 2026 and mes > 4: 
                continue

            mes_str = str(mes).zfill(2)
            nome_arquivo = f"{PREFIXO}{UF}{ano_abrev}{mes_str}{EXTENSAO}"
            nome_arquivo_maiusculo = f"{PREFIXO}{UF}{ano_abrev}{mes_str}.DBC"
            caminho_local = os.path.join(PASTA_DESTINO, nome_arquivo)

            # Pula os anos que você já baixou com sucesso (2000 a 2007)
            if os.path.exists(caminho_local) and os.path.getsize(caminho_local) > 0:
                print(f"⏭️ [OK] {nome_arquivo} já baixado.")
                continue

            print(f"⬇️ Baixando {nome_arquivo}...")
            
            sucesso = False
            # O "Pulo do Gato": Usar caminhos absolutos tentando todas as variações malucas do DATASUS
            tentativas_paths = [
                f"{base_pasta}/Dados/{nome_arquivo}",
                f"{base_pasta}/dados/{nome_arquivo}",
                f"{base_pasta}/Dados/{nome_arquivo_maiusculo}",
                f"{base_pasta}/dados/{nome_arquivo_maiusculo}"
            ]

            for caminho_remoto in tentativas_paths:
                try:
                    with open(caminho_local, "wb") as f:
                        ftp.retrbinary(f"RETR {caminho_remoto}", f.write)
                    sucesso = True
                    break # Deu certo! Sai do loop de tentativas.
                except Exception:
                    pass # Falhou? Segue para o próximo formato.

            if not sucesso:
                print(f"❌ Ficheiro não existe no Ministério da Saúde: {nome_arquivo}")
                if os.path.exists(caminho_local):
                    os.remove(caminho_local)
                
                # Se o FTP nos derrubar por excesso de negações, reconecta silenciosamente
                try:
                    ftp.voidcmd("NOOP")
                except:
                    ftp = conectar_ftp()

            # Pausa de segurança para não tomar "ban" de IP do Governo
            time.sleep(0.5) 

    ftp.quit()
    print("\n🚀 Download Ambulatorial (PA) concluído com sucesso!")

if __name__ == "__main__":
    iniciar_extracao()