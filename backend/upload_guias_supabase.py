import os
import pandas as pd
import glob
from supabase import create_client, Client
import math

print("--- 🚀 UPLOAD DE GUIAS PARA O SUPABASE (56K+) ---")

# Suas credenciais do Supabase
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_CSV = os.path.join(BASE_DIR, "solus_unimed")

def encontrar_arquivo_csv():
    if not os.path.exists(PASTA_CSV): os.makedirs(PASTA_CSV)
    padrao_busca = os.path.join(PASTA_CSV, "*.csv")
    arquivos_encontrados = glob.glob(padrao_busca)
    if arquivos_encontrados: return max(arquivos_encontrados, key=os.path.getmtime)
    return None

def processar_guias():
    arquivo_csv = encontrar_arquivo_csv()
    
    if not arquivo_csv:
        print(f"❌ Nenhum arquivo CSV encontrado na pasta: {PASTA_CSV}")
        return

    nome_base = os.path.basename(arquivo_csv)
    print(f"📄 Lendo arquivo encontrado: {nome_base}...")
    
    try:
        # Lê o arquivo
        df = pd.read_csv(arquivo_csv, sep=';', encoding='latin1', dtype=str)
    except Exception as e:
        print(f"❌ Erro ao tentar abrir o arquivo: {e}")
        return

    # Limpeza básica
    df = df.fillna("-")
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Vamos converter o DataFrame em uma lista de dicionários para o banco
    registros = []
    
    for index, row in df.iterrows():
        linha_completa = row.to_dict()
        
        # O HTML usa essas chaves maiúsculas do antigo script, 
        # mas o ideal no banco é minúsculo. Mapeamento de Extração:
        reg = {
            "beneficiario": linha_completa.get("BENEFICIARIO", "-"),
            "carteirinha": linha_completa.get("CARTEIRINHA", "-"),
            "guia": linha_completa.get("GUIA", "-"),
            "tipo": linha_completa.get("TIPO", "-"),
            "procedimento": linha_completa.get("PROCEDIMENTO", "-"),
            "codigo": linha_completa.get("CODIGO", "-"),
            "especialidade": linha_completa.get("ESPECIALIDADE", "-"),
            "prestador": linha_completa.get("PRESTADOR", "-"),
            "emissao": linha_completa.get("EMISSAO", "-"),
            "dados_completos": linha_completa # Joga todas as outras 20 colunas como JSONB
        }
        registros.append(reg)

    total = len(registros)
    print(f"✅ Arquivo processado! Iniciando upload de {total} registros para o Supabase...")

    # Limpar tabela antes de enviar carga nova (opcional, mas recomendado para substituir 56k)
    print("🧹 Limpando dados antigos da tabela 'guias_unimed'...")
    # Supabase restringe deletes sem filtro, usamos um filtro abrangente:
    supabase.table('guias_unimed').delete().neq('id', 0).execute() 

    # UPLOAD EM LOTES DE 1000 (Limitação de API da Supabase)
    tamanho_lote = 1000
    lotes = math.ceil(total / tamanho_lote)

    for i in range(lotes):
        inicio = i * tamanho_lote
        fim = inicio + tamanho_lote
        lote_atual = registros[inicio:fim]
        
        # Envia para o Supabase
        resposta = supabase.table('guias_unimed').insert(lote_atual).execute()
        
        print(f"📤 Lote {i+1}/{lotes} enviado ({len(lote_atual)} registros)...")

    print(f"🎉 Upload CONCLUÍDO COM SUCESSO! O Painel de Guias já pode ser acessado na Web.")

if __name__ == "__main__":
    processar_guias()