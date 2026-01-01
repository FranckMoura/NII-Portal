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
    print("❌ ERRO: Nenhum CSV encontrado em 'SISREG_Export'!")
    print("   Certifique-se que moveu os arquivos para dentro desta pasta.")
    input("   Pressione ENTER para tentar novamente...")
    csvs = glob.glob(os.path.join(pasta_export, "*.csv"))
    if not csvs:
        print("   Ainda vazio. Encerrando.")
        exit()

print(f"   ✅ Arquivos encontrados: {len(csvs)}")

# 2. RODAR O PROCESSAMENTO (MUDANÇA AQUI)
print("\n2. Processando dados (Gerando Banco e JSON)...")
subprocess.run([python_cmd, "processar_dados_sisreg.py"])

# 3. CONFERÊNCIA
if os.path.exists(arquivo_json):
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    print(f"\n   📊 O JSON foi gerado com {len(dados)} registros.")
    print("   ✅ Tudo pronto para o site!")
else:
    print("   ❌ O JSON não foi criado. Verifique o script de processamento.")

# 4. UPLOAD
print("\n3. Enviando para o Portal...")
if os.path.exists("upload_manager_v6.py"):
    subprocess.run([python_cmd, "upload_manager_v6.py"])
elif os.path.exists("upload_manager.py"):
    subprocess.run([python_cmd, "upload_manager.py"])

print("\n--- FIM ---")
print("Acesse o site e aperte CTRL + F5.")