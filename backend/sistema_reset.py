import os
from dotenv import load_dotenv
from supabase import create_client, Client

print("--- ⚠️ SISTEMA DE RESET DE BANCO DE DADOS ⚠️ ---")
print("Isso apagará TODOS os dados das tabelas para permitir uma reimportação limpa.")

confirmacao = input("Digite 'CONFIRMAR' para continuar: ")
if confirmacao != "CONFIRMAR":
    exit("Operação cancelada.")

# --- CONFIGURAÇÃO ---
load_dotenv()
SB_URL = os.getenv("SB_URL")
SB_KEY = os.getenv("SB_KEY")
supabase: Client = create_client(SB_URL, SB_KEY)

tabelas_para_limpar = [
    "financeiro_repasses",
    # Descomente abaixo se quiser limpar o institucional também
    # "institucional_profissionais",
    # "institucional_leitos",
    # "institucional_servicos",
    # "institucional_marcacoes"
]

for tabela in tabelas_para_limpar:
    try:
        # Deleta onde ID > 0 (basicamente tudo)
        supabase.table(tabela).delete().neq("id", 0).execute()
        print(f"🗑️  Tabela '{tabela}' limpa com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao limpar {tabela}: {e}")

print("\n✅ Banco limpo. Agora você pode rodar os Robôs novamente para restaurar os dados.")