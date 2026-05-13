import os
from supabase import create_client, Client

print("--- 🚀 UPLOAD DE PRODUÇÃO SUS (BLINDAGEM MÁXIMA E ANTI-DUPLICATAS) ---")

SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}"); exit()

arquivo_csv = "producao.csv"

def limpar_valor(valor):
    """ Remove R$, limpa espaços e converte pontuação para matemática pura """
    v = str(valor).upper().replace('R$', '').replace(' ', '').replace('"', '').strip()
    if not v: return 0.0
    if ',' in v and '.' in v:
        v = v.replace('.', '').replace(',', '.')
    elif ',' in v:
        v = v.replace(',', '.')
    try:
        return float(v)
    except:
        return 0.0

if not os.path.exists(arquivo_csv):
    print(f"❌ ERRO: O arquivo '{arquivo_csv}' não foi encontrado!")
    exit()

# MUDANÇA AQUI: Usando dicionário para esmagar duplicatas automaticamente
dados_processados = {}

try:
    with open(arquivo_csv, 'r', encoding='utf-8', errors='replace') as f:
        linhas = f.readlines()
        
    sep = ';' if ';' in linhas[0] else ','
    
    for i, linha in enumerate(linhas[1:], start=2):
        if not linha.strip(): continue
        
        partes = linha.strip().split(sep)
        if len(partes) < 6: continue
        
        val_ano_fin = limpar_valor(partes[-1])
        val_ano_fis = int(limpar_valor(partes[-2]))
        val_mes_fin = limpar_valor(partes[-3])
        val_mes_fis = int(limpar_valor(partes[-4]))
        val_medio = limpar_valor(partes[-5])
        
        cod_bruto = str(partes[0]).replace('"', '').strip()
        
        if len(cod_bruto) < 10: 
            codigo = str(partes[1]).replace('"', '').strip().zfill(10)
            inicio_desc = 2
        else:
            codigo = cod_bruto.zfill(10)
            inicio_desc = 1
            
        if codigo == "0000000000" or codigo == "0": continue
        
        forma_org = codigo[:6]
        desc = sep.join(partes[inicio_desc : len(partes) - 5]).replace('"', '').strip()

        # O PULO DO GATO: Se o código já existir, ele só atualiza, evitando o erro 21000
        dados_processados[codigo] = {
            "codigo": codigo,
            "descricao": desc,
            "forma_organizacao": forma_org,
            "valor_medio": val_medio,
            "fisico_mes": val_mes_fis,
            "financeiro_mes": val_mes_fin,
            "fisico_ano": val_ano_fis,
            "financeiro_ano": val_ano_fin
        }

    # Transforma o dicionário (único) em uma lista para enviar ao Supabase
    lista_final = list(dados_processados.values())

    print(f"📂 Arquivo lido. De {len(linhas)-1} linhas, filtrei {len(lista_final)} procedimentos ÚNICOS.")
    print(f"⏳ Subindo os dados para o Supabase em lotes...")
    
    for i in range(0, len(lista_final), 100):
        supabase.table("tb_producao_sus").upsert(lista_final[i:i+100]).execute()
        
    print("✅ UPLOAD CONCLUÍDO COM SUCESSO! Banco limpo, atualizado e sem duplicatas.")

except Exception as e:
    print(f"❌ Erro Crítico: {e}")