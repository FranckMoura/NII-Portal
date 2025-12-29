import json
import os

CAMINHO_JSON = r"C:\Users\DELL\OneDrive\NII-Portal-1\arquivos\dados_financeiro.json"

print("--- LIMPEZA DO PORTAL FINANCEIRO ---")
print(f"Alvo: {CAMINHO_JSON}")

if os.path.exists(CAMINHO_JSON):
    resposta = input("Tem certeza que deseja APAGAR todo o histórico de relatórios do portal? (S/N): ")
    
    if resposta.upper() == 'S':
        try:
            # Cria uma lista vazia e salva
            with open(CAMINHO_JSON, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)
            print("✅ Limpeza concluída! O painel financeiro está vazio.")
            print("   -> Agora execute o 'executar_fechamento.py' para repopular com os dados corretos.")
        except Exception as e:
            print(f"❌ Erro: {e}")
    else:
        print("Operação cancelada.")
else:
    print("Arquivo JSON não encontrado.")