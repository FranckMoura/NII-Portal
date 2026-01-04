import json
import os

ARQUIVO = "gravacao_soulmv.json"

if os.path.exists(ARQUIVO):
    try:
        with open(ARQUIVO, 'r', encoding='utf-8', errors='ignore') as f:
            dados = json.load(f)
        
        print(f"Total de itens na lista: {len(dados)}")
        
        if len(dados) > 0:
            primeiro = dados[0]
            print("\n--- ESTRUTURA DO PRIMEIRO ITEM ---")
            print(json.dumps(primeiro, indent=4)[:1000]) # Mostra só o começo
        else:
            print("A lista está vazia!")
            
    except Exception as e:
        print(f"Erro: {e}")
else:
    print("Arquivo não encontrado.")