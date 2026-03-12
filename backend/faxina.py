from supabase import create_client, Client

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

print("🧹 Iniciando a faxina no Banco de Dados (Removendo os 35 mil registros antigos)...")

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
    
    # Usando uma data real bem antiga para não irritar o PostgreSQL
    resultado = supabase.table("indicasus_leitos").delete().neq("data_extracao", "1900-01-01").execute()
    
    print("✅ Banco de Dados limpo com sucesso! A sujeira do V19 foi removida.")
    print("👉 Agora, rode o seu 'robo_indicasus_v20.py' mais uma vez para tirar a 1ª foto limpa.")
except Exception as e:
    print(f"❌ Erro ao limpar o banco: {e}")