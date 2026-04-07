import os
from supabase import create_client, Client

print("--- 🏥 INICIANDO IMPORTAÇÃO DE DICIONÁRIOS DATASUS ---")

# =========================================================
# CONFIGURAÇÕES DO SUPABASE
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

supabase: Client = create_client(SB_URL, SB_KEY)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def importar_dicionario(nome_arquivo, nome_tabela, tamanho_codigo, tamanho_nome):
    caminho_arquivo = os.path.join(BASE_DIR, nome_arquivo)
    
    if not os.path.exists(caminho_arquivo):
        print(f"\n❌ Arquivo não encontrado: {nome_arquivo}")
        print("   Por favor, coloque o arquivo na mesma pasta deste script.")
        return

    print(f"\n📂 Lendo e fatiando o arquivo {nome_arquivo}...")
    
    # O DATASUS usa a codificação ISO-8859-1 (Latin1). Isso corrige os acentos (ç, ã, é).
    try:
        with open(caminho_arquivo, 'r', encoding='iso-8859-1') as file:
            linhas = file.readlines()
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo: {e}")
        return

    dados_para_inserir = []
    
    for linha in linhas:
        if not linha.strip():
            continue
            
        # A Mágica do Fatiamento por Largura Fixa
        codigo = linha[0:tamanho_codigo].strip()
        nome = linha[tamanho_codigo:tamanho_codigo+tamanho_nome].strip()
        
        # Ignora linhas de cabeçalho mal formatadas, se houver
        if codigo and nome and len(codigo) >= 2:
            dados_para_inserir.append({
                "cod": codigo,
                "nome": nome
            })

    total = len(dados_para_inserir)
    print(f"✅ Encontrados {total} registos válidos.")
    print(f"☁️ Iniciando envio seguro para a tabela '{nome_tabela}'...")

    # Envio em lotes (chunks) de 1000 para não estourar o limite de payload do servidor
    tamanho_lote = 1000
    for i in range(0, total, tamanho_lote):
        lote = dados_para_inserir[i:i + tamanho_lote]
        try:
            # O "upsert" é vital: Se o código já existir, ele atualiza o nome. Se não, ele cria.
            supabase.table(nome_tabela).upsert(lote).execute()
            print(f"   ⬆️ Lote processado: {min(i + tamanho_lote, total)} de {total}...")
        except Exception as e:
            print(f"   ❌ Erro de conexão no lote: {e}")
            
    print(f"🚀 Tabela '{nome_tabela}' sincronizada e atualizada com sucesso no Supabase!")

if __name__ == "__main__":
    
    # 1. Dicionário de Procedimentos (SIGTAP)
    # A tabela tb_procedimento.txt reserva 10 posições para o código e 250 para o nome
    importar_dicionario("tb_procedimento.txt", "dic_sigtap", 10, 250)
    
    # 2. Dicionário de Especialidades e Ocupações (CBO)
    # A tabela tb_ocupacao.txt reserva 6 posições para o CBO e 150 para a descrição
    importar_dicionario("tb_ocupacao.txt", "dic_cbo", 6, 150)
    
    print("\n✅ TUDO PRONTO! Pode abrir o seu Painel HTML e testar.")