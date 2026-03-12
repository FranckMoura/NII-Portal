from supabase import create_client, Client
import json

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Pega os 5 últimos registros alterados
    response = supabase.table("regulacao").select("*").order("data_atualizacao", desc=True).limit(5).execute()
    
    dados = response.data
    
    print(f"\n🔍 ENCONTRADOS {len(dados)} REGISTROS RECENTES:\n")
    
    for i, p in enumerate(dados):
        print(f"--- REGISTRO {i+1} ---")
        print(f"🏥 AIH: {p.get('num_aih')}")
        print(f"👤 Paciente (HTML): {p.get('nome_paciente')}")
        print(f"📄 CNS (PDF):       {p.get('cns') or '❌ Não leu'}")
        print(f"👩 Mãe (PDF):       {p.get('nome_mae') or '❌ Não leu'}")
        print(f"💉 Procedimento:    {p.get('procedimento') or '❌ Não leu'}")
        print(f"📅 Nascimento:      {p.get('data_nascimento')}")
        print(f"🔗 Link PDF:        {p.get('arquivo_pdf')}")
        print("-" * 30)

except Exception as e:
    print(f"Erro: {e}")