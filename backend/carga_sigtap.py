import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(os.getenv("SB_URL"), os.getenv("SB_KEY"))

print("📥 Preparando carga da Tabela SIGTAP...")

# Exemplo: Procedimentos de Faturamento Hospitalar (Valores fictícios para teste)
# Na versão final, isso vem do download do FTP que mostrei antes
dados_sigtap = [
    {"codigo": "0411010034", "nome": "PARTO CESARIANO", "valor_sh": 545.73, "valor_sp": 200.00, "complexidade": "AC", "sexo": "F"},
    {"codigo": "0303010037", "nome": "TRATAMENTO COVID-19", "valor_sh": 1500.00, "valor_sp": 0.00, "complexidade": "MC", "sexo": "I"},
    {"codigo": "0415010012", "nome": "TRATAMENTO DE PNEUMONIA", "valor_sh": 250.00, "valor_sp": 100.00, "complexidade": "MC", "sexo": "I"}
]

try:
    # Usamos 'upsert' para atualizar se já existir, ou criar se for novo
    data = supabase.table("tb_procedimentos_sus").upsert(dados_sigtap).execute()
    print("✅ Tabela SIGTAP sincronizada no Supabase!")
except Exception as e:
    print(f"❌ Erro na sincronização: {e}")