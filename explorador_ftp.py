import ftplib

print(f"🕵️ --- EXPLORADOR DE CAMINHOS DATASUS ---")
print(f"Conectando...")

try:
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    
    # Vamos tentar entrar na pasta "Pai" do CNES
    pasta_pai = '/dissemin/publicos/CNES'
    print(f"📂 Entrando em: {pasta_pai}")
    ftp.cwd(pasta_pai)
    
    print("✅ Sucesso! Listando o que tem aqui dentro:")
    print("-" * 40)
    
    arquivos = []
    ftp.retrlines('NLST', arquivos.append)
    
    for f in arquivos:
        print(f"   📂 {f}")
        
    print("-" * 40)
    print("Compare a lista acima com o nome '200508_+'.")
    print("Provavelmente o nome mudou ou agora existe uma pasta 'Dados' direto.")
    
    ftp.quit()

except Exception as e:
    print(f"❌ Erro: {e}")