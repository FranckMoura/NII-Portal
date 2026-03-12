import os
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Carrega as senhas do arquivo .env (Segurança Total)
load_dotenv()

url = os.getenv("SB_URL")
key = os.getenv("SB_KEY")

if not url or not key:
    raise ValueError("❌ Erro: Arquivo .env não encontrado ou variáveis vazias.")

# Conecta ao Supabase
supabase: Client = create_client(url, key)
print(f"✅ Conectado ao Supabase: {url}")

# 2. DADOS (Aqui você substituiria por pd.read_csv('exportacao_mv.csv'))
print("🔍 Iniciando Auditoria nos dados...")
dados_simulados = {
    'AIH': ['1124100012345', '1124100099999'],
    'PACIENTE': ['MARIA DA SILVA (SIMULAÇÃO)', 'TESTE SEM ANESTESIA'],
    'PROCEDIMENTOS_CONTA': [['0411010034', '0411010026'], ['0411010034']] 
}
df = pd.DataFrame(dados_simulados)

# Regras (Exemplo: Cesariana exige Anestesia)
regras = {'0411010034': ['0411010026']} 

erros_para_enviar = []

for index, linha in df.iterrows():
    procs = linha['PROCEDIMENTOS_CONTA']
    for proc in procs:
        if proc in regras:
            for item_obrigatorio in regras[proc]:
                if item_obrigatorio not in procs:
                    erro_msg = f"Omissão: Lançou {proc}, faltou {item_obrigatorio}"
                    print(f"🚨 {erro_msg}")
                    
                    erros_para_enviar.append({
                        "aih": linha['AIH'],
                        "paciente": linha['PACIENTE'],
                        "erro": erro_msg,
                        "data_auditoria": datetime.now().isoformat(),
                        "status": "PENDENTE"
                    })

# 3. Envia para a Nuvem
if erros_para_enviar:
    try:
        data = supabase.table("tb_auditoria_erros").insert(erros_para_enviar).execute()
        print(f"\n🚀 Sucesso! {len(erros_para_enviar)} erros enviados para o Portal NII.")
    except Exception as e:
        print(f"❌ Falha ao enviar: {e}")
else:
    print("✅ Nenhum erro encontrado.")