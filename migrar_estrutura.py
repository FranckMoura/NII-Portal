import os
import shutil
import glob

print("--- 🚀 INICIANDO MIGRAÇÃO PARA NII-PORTAL-CLOUD ---")

# 1. Configurar Caminhos
pasta_atual = os.getcwd() # Pasta NII-Portal-1
pasta_pai = os.path.dirname(pasta_atual)
pasta_destino = os.path.join(pasta_pai, "NII-Portal-Cloud")

print(f"📂 Origem: {pasta_atual}")
print(f"📂 Destino: {pasta_destino}")

# 2. Criar Pastas
pastas_criar = [
    "backend",
    "frontend",
    os.path.join("frontend", "css"),
    os.path.join("frontend", "img"),
    os.path.join("frontend", "arquivos"),
    "docs"
]

for p in pastas_criar:
    caminho_completo = os.path.join(pasta_destino, p)
    if not os.path.exists(caminho_completo):
        os.makedirs(caminho_completo)
        print(f"   + Pasta criada: {p}")

# 3. Migrar BACKEND (Mortalidade)
print("\n🐍 Migrando Backend...")
src_script = os.path.join(pasta_atual, "mortalidade", "processar_mortalidade.py")
dst_script = os.path.join(pasta_destino, "backend", "processar_mortalidade.py")

if os.path.exists(src_script):
    shutil.copy2(src_script, dst_script)
    print("   + Script Python copiado.")
else:
    print("   ⚠️ AVISO: Script processar_mortalidade.py não encontrado na origem.")

# Copiar Excel
excels = glob.glob(os.path.join(pasta_atual, "mortalidade", "*.xlsx"))
for excel in excels:
    nome_arquivo = os.path.basename(excel)
    if not nome_arquivo.startswith("~$"): # Ignora temporários
        shutil.copy2(excel, os.path.join(pasta_destino, "backend", nome_arquivo))
        print(f"   + Relatório copiado: {nome_arquivo}")

# 4. Migrar FRONTEND (Site)
print("\n🌐 Migrando Frontend...")
arquivos_html = glob.glob(os.path.join(pasta_atual, "*.html"))
for html in arquivos_html:
    shutil.copy2(html, os.path.join(pasta_destino, "frontend", os.path.basename(html)))
    print(f"   + HTML copiado: {os.path.basename(html)}")

# Copiar Imagens
src_img = os.path.join(pasta_atual, "img")
if os.path.exists(src_img):
    imagens = glob.glob(os.path.join(src_img, "*"))
    for img in imagens:
        shutil.copy2(img, os.path.join(pasta_destino, "frontend", "img", os.path.basename(img)))
    print("   + Imagens copiadas.")

print("\n" + "="*50)
print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
print(f"👉 Agora trabalhe apenas na pasta: {pasta_destino}")
print("="*50)