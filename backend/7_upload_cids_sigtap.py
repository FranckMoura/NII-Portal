import os
from supabase import create_client, Client

print("--- 🚜 ROBÔ DE UPLOAD: CIDs e Relacionamentos SIGTAP ---")

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try: supabase: Client = create_client(SB_URL, SB_KEY)
except: print("❌ Erro Conexão Supabase"); exit()

# Caminho atualizado para a pasta "sigtap"
PASTA_SIGTAP = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\sigtap"
ARQUIVO_CID = os.path.join(PASTA_SIGTAP, "tb_cid.txt")
ARQUIVO_RL = os.path.join(PASTA_SIGTAP, "rl_procedimento_cid.txt")

def subir_tb_cid():
    if not os.path.exists(ARQUIVO_CID):
        print(f"⚠️ Arquivo não encontrado: {ARQUIVO_CID}. Pulando.")
        return
    
    print(">> Processando tb_cid (Catálogo de Doenças)...")
    payload = []
    try:
        with open(ARQUIVO_CID, 'r', encoding='iso-8859-1') as f:
            for line in f:
                if len(line) < 5: continue
                co_cid = line[0:4].strip()
                no_cid = line[4:104].strip()
                
                payload.append({"co_cid": co_cid, "no_cid": no_cid})
        
        print(f"   Limpando tabela antiga...")
        try: supabase.table('tb_cid').delete().neq("co_cid", "0").execute()
        except: pass
        
        print(f"   Enviando {len(payload)} registros...")
        for i in range(0, len(payload), 2000):
            supabase.table('tb_cid').insert(payload[i:i+2000]).execute()
        print("✅ tb_cid atualizada com sucesso!\n")
    except Exception as e:
        print(f"❌ Erro na tb_cid: {e}")

def subir_rl_procedimento_cid():
    if not os.path.exists(ARQUIVO_RL):
        print(f"⚠️ Arquivo não encontrado: {ARQUIVO_RL}. Pulando.")
        return
    
    print(">> Processando rl_procedimento_cid (Relação Procedimento x Doença)...")
    payload = []
    try:
        with open(ARQUIVO_RL, 'r', encoding='iso-8859-1') as f:
            for line in f:
                if len(line) < 14: continue
                co_proc = line[0:10].strip()
                co_cid = line[10:14].strip()
                st_princ = line[14:15].strip() if len(line) > 14 else ""
                
                payload.append({"co_procedimento": co_proc, "co_cid": co_cid, "st_principal": st_princ})
        
        print(f"   Limpando tabela antiga...")
        try: supabase.table('rl_procedimento_cid').delete().neq("co_procedimento", "0").execute()
        except: pass
        
        print(f"   Enviando {len(payload)} registros (Isso pode demorar um pouco)...")
        for i in range(0, len(payload), 5000):
            supabase.table('rl_procedimento_cid').insert(payload[i:i+5000]).execute()
            print(f"     Lote {i} / {len(payload)} enviado.")
        print("✅ rl_procedimento_cid atualizada com sucesso!\n")
    except Exception as e:
        print(f"❌ Erro na rl_procedimento_cid: {e}")

subir_tb_cid()
subir_rl_procedimento_cid()
print("🎉 Carga concluída!")