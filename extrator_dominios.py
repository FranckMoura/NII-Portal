import os
import ftplib

# --- CONFIGURAÇÕES ---
PASTA_DESTINO = "arquivos"
# Caminho da pasta de tabelas auxiliares
PASTA_FTP_DOMINIOS = '/dissemin/publicos/CNES/200508_/Auxiliar'

print(f"📚 --- EXTRATOR DE DOMÍNIOS V2 (BUSCA AUTOMÁTICA) ---")
print(f"Conectando ao FTP...")

if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

try:
    ftp = ftplib.FTP('ftp.datasus.gov.br')
    ftp.login()
    ftp.cwd(PASTA_FTP_DOMINIOS)
    
    # 1. LISTAR TUDO QUE TEM NA PASTA
    print(f"📂 Acessando: {PASTA_FTP_DOMINIOS}")
    todos_arquivos = []
    ftp.retrlines('NLST', todos_arquivos.append)
    
    def encontrar_e_baixar(termo_chave, nome_final_desejado):
        print(f"\n   🔍 Procurando arquivo de '{termo_chave}'...", end="")
        
        # Procura qualquer arquivo que contenha o termo (ignorando maiusculas/minusculas)
        # e que termine em .dbc
        candidatos = [f for f in todos_arquivos if termo_chave.lower() in f.lower() and f.lower().endswith('.dbc')]
        
        if not candidatos:
            print(" ❌ Não encontrado.")
            return
        
        # Pega o menor nome (geralmente tb_cbo.dbc é melhor que tb_cbo_antigo.dbc)
        candidatos.sort(key=len)
        arquivo_real = candidatos[0]
        
        print(f" Encontrado: {arquivo_real}")
        
        # Baixa e já renomeia para o nome padrão que o conversor espera (TB_CBO.dbc)
        caminho_local = os.path.join(PASTA_DESTINO, nome_final_desejado)
        
        try:
            with open(caminho_local, 'wb') as f:
                ftp.retrbinary(f"RETR {arquivo_real}", f.write)
            print(f"      ✅ Baixado como: {nome_final_desejado}")
        except Exception as e:
            print(f"      ❌ Erro ao baixar: {e}")

    # 2. BAIXAR OS DICIONÁRIOS
    encontrar_e_baixar('CBO', 'TB_CBO.dbc')
    encontrar_e_baixar('EQUIPAMENTO', 'TB_EQUIPAMENTO.dbc')
    encontrar_e_baixar('LEITO', 'TB_LEITO.dbc')
    
    ftp.quit()
    print("\n🚀 Dicionários baixados na pasta 'arquivos'!")
    print("⚠️ PRÓXIMO PASSO: Abra o TabWin e expanda esses 3 arquivos para .DBF.")

except Exception as e:
    print(f"\n❌ Erro Geral: {e}")