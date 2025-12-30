import subprocess
import os
import sys
import glob
import json

print("--- 🚑 REPARO DE EMERGÊNCIA DO PORTAL ---")

python_cmd = sys.executable 
base_dir = os.getcwd()
pasta_export = os.path.join(base_dir, "SISREG_Export")
pasta_arquivos = os.path.join(base_dir, "arquivos")
arquivo_json = os.path.join(pasta_arquivos, "dados_sisreg.json")

# 1. VERIFICAÇÃO DE ARQUIVO
print(f"\n1. Verificando pasta: {pasta_export}")
csvs = glob.glob(os.path.join(pasta_export, "*.csv"))

if not csvs:
    print("❌ ERRO CRÍTICO: Nenhum arquivo .csv encontrado dentro de 'SISREG_Export'!")
    print("   -> Mova o arquivo '2311682....csv' para dentro da pasta 'SISREG_Export' agora.")
    input("   -> Pressione ENTER depois de mover o arquivo...")
    # Tenta de novo
    csvs = glob.glob(os.path.join(pasta_export, "*.csv"))
    if not csvs:
        print("   Ainda vazio. Desistindo.")
        exit()

print(f"   ✅ Arquivo encontrado: {os.path.basename(csvs[0])}")

# 2. RODAR O PROCESSAMENTO DO BANCO
print("\n2. Processando dados (Gerando JSON)...")
subprocess.run([python_cmd, "banco_dados_sisreg_postgres.py"])

# 3. CONFERÊNCIA FINAL
if os.path.exists(arquivo_json):
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    qtd = len(dados)
    print(f"\n   📊 O arquivo JSON foi gerado com {qtd} registros.")
    if qtd == 0:
        print("   ⚠️ AVISO: O arquivo está vazio (0 registros). Verifique o CSV.")
    else:
        print("   ✅ Tudo pronto para o site!")
else:
    print("   ❌ O JSON não foi criado. Algo deu errado no script do banco.")

# 4. UPLOAD
print("\n3. Enviando para o Portal...")
if os.path.exists("upload_manager_v6.py"):
    subprocess.run([python_cmd, "upload_manager_v6.py"])
elif os.path.exists("upload_manager.py"):
    subprocess.run([python_cmd, "upload_manager.py"])

print("\n--- FIM ---")
print("Acesse o site e aperte CTRL + F5 para limpar o cache.")