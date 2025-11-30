import ftplib

# --- CAMINHO QUE ESTAMOS INVESTIGANDO ---
PASTA_ALVO = '/dissemin/publicos/CNES/200508_/Auxiliar'

print(f"🕵️ --- RAIO-X DA PASTA AUXILIAR ---")
print(f"Conectando...")

try:
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    
    print(f"📂 Entrando em: {PASTA_ALVO}")
    try:
        ftp.cwd(PASTA_ALVO)
    except:
        print("❌ A pasta 'Auxiliar' não existe nesse caminho!")
        ftp.quit()
        exit()
    
    print("✅ Pasta acessada! Baixando lista de arquivos...")
    
    arquivos = []
    ftp.retrlines('NLST', arquivos.append)
    
    print(f"\n📄 Encontrei {len(arquivos)} arquivos. Aqui estão eles:")
    print("-" * 40)
    
    # Mostra tudo para a gente achar o ouro
    for f in arquivos:
        print(f"   📂 {f}")
        
    print("-" * 40)
    print("Procure na lista acima nomes parecidos com:")
    print("- tb_cbo / cbo")
    print("- tb_equipamento / equip")
    print("- tb_leito / leito")
    
    ftp.quit()

except Exception as e:
    print(f"❌ Erro: {e}")