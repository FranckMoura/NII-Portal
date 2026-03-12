import json
import os
from supabase import create_client, Client

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
# Usando a chave que você forneceu nos htmls anteriores
SUPABASE_KEY = "sb_publishable_o4-ci54177LQmQFsIl1-7g_sN5vp55n" 

# Caminho do arquivo JSON gerado pelo script anterior
CAMINHO_JSON = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\pacientes\pacientes_processados.json"

def main():
    # 1. Conectar ao Supabase
    print("Conectando ao Supabase...")
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return

    # 2. Ler o arquivo JSON
    if not os.path.exists(CAMINHO_JSON):
        print(f"ERRO: Arquivo não encontrado: {CAMINHO_JSON}")
        print("Rode o script 'leitor_pacientes.py' primeiro.")
        return

    print(f"Lendo dados de: {CAMINHO_JSON}")
    with open(CAMINHO_JSON, 'r', encoding='utf-8') as f:
        dados_locais = json.load(f)

    if not dados_locais:
        print("O arquivo JSON está vazio.")
        return

    print(f"Preparando para enviar {len(dados_locais)} registros...")

    # 3. Enviar para o Supabase (em lotes para não sobrecarregar)
    tabela = "painel_clinico"
    
    # Opcional: Limpar dados antigos desse arquivo para evitar duplicação?
    # supabase.table(tabela).delete().neq("id", 0).execute() 
    
    lote_tamanho = 100
    total_enviados = 0

    for i in range(0, len(dados_locais), lote_tamanho):
        lote = dados_locais[i : i + lote_tamanho]
        
        try:
            data, count = supabase.table(tabela).insert(lote).execute()
            total_enviados += len(lote)
            print(f"Enviado lote {i} a {i+len(lote)}... Sucesso.")
        except Exception as e:
            print(f"Erro ao enviar lote {i}: {e}")

    print(f"\nCONCLUÍDO! Total de {total_enviados} pacientes enviados para o Supabase.")

if __name__ == "__main__":
    main()