import json

def processar_conversas(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    # Iterando pelas conversas
    for conversa in dados:
        print(f"--- Conversa: {conversa.get('conversation_id')} ---")
        for mensagem in conversa.get('messages', []):
            autor = mensagem.get('author')
            conteudo = mensagem.get('content')
            print(f"**{autor}**: {conteudo}\n")

# Substitua pelo caminho do seu arquivo extraído do Takeout
# processar_conversas('conversations.json')