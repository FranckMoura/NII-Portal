import json
import os
from urllib.parse import urlparse

# Nome do seu arquivo de gravação
ARQUIVO_ENTRADA = "gravacao_soulmv.json"

def analisar_har():
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"❌ Erro: Não encontrei o arquivo '{ARQUIVO_ENTRADA}' na pasta.")
        return

    print(">> Lendo o arquivo...")
    
    try:
        with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8', errors='ignore') as f:
            dados = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler JSON: {e}")
        return

    print("\n--- 🕵️ RESUMO DA INTERAÇÃO SOULMV ---")
    
    # CORREÇÃO DO ERRO: Verifica se é Lista Direta ou Formato HAR Padrão
    entradas = []
    if isinstance(dados, list):
        print("ℹ️ Formato detectado: Lista Direta")
        entradas = dados
    elif isinstance(dados, dict):
        print("ℹ️ Formato detectado: HAR Padrão")
        entradas = dados.get('log', {}).get('entries', [])
    else:
        print("❌ Formato desconhecido.")
        return
    
    passo = 1
    
    for entrada in entradas:
        req = entrada.get('request', {})
        if not req: continue # Pula se não tiver dados de requisição

        url = req.get('url', '')
        metodo = req.get('method', '')
        
        # FILTROS: Ignora lixo visual e analítico
        ignorar = ['.css', '.js', '.png', '.jpg', '.gif', '.svg', '.woff', 'google', 'facebook', 'analytics', 'clarity']
        if any(x in url for x in ignorar):
            continue
            
        # Filtra por tipo de recurso (se disponível)
        tipo = entrada.get('_resourceType', '').lower()
        if tipo in ['image', 'font', 'stylesheet', 'script']:
            continue

        # Extrai o caminho (ex: /mv-soul-services/rest/auth)
        try:
            parsed = urlparse(url)
            caminho = parsed.path
        except:
            caminho = url[:50]
        
        # Pega o Payload (Dados enviados no POST)
        dados_post = ""
        if metodo == 'POST' and 'postData' in req:
            texto = req['postData'].get('text', '')
            if texto:
                # Limpa um pouco se for JSON muito grande
                if len(texto) > 300:
                    dados_post = f"   📦 DADOS: {texto[:300]}... (cortado)"
                else:
                    dados_post = f"   📦 DADOS: {texto}"

        print(f"\n[{passo}] {metodo}: {caminho}")
        if dados_post:
            print(dados_post)
            
        passo += 1

    print("\n" + "="*50)
    print("✅ AGORA SIM! COPIE O TEXTO ACIMA E COLE NO CHAT")

if __name__ == "__main__":
    analisar_har()