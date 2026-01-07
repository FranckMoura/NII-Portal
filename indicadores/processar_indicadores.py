import pdfplumber
import re
import json
import os
import glob
import sys

print("--- 📊 EXTRATOR DE INDICADORES HOSPITALARES (PDF) ---")

# Garante que estamos trabalhando na pasta onde o SCRIPT está (pasta indicadores)
caminho_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(caminho_script)

# Encontra todos os PDFs na pasta atual (indicadores)
arquivos_pdf = glob.glob("R_EST_HOSPITALAR*.pdf")

if not arquivos_pdf:
    print(f"❌ Nenhum PDF encontrado em: {caminho_script}")
    print("Certifique-se que os arquivos R_EST_HOSPITALAR*.pdf estão junto com este script.")
    sys.exit()

dados_consolidados = []

def converter_numero(texto):
    """Converte string '1.234,56' para float 1234.56"""
    if not texto: return 0.0
    texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except:
        return 0.0

for arquivo in arquivos_pdf:
    print(f"📄 Processando: {arquivo}...")
    
    soma_internacoes = 0
    soma_obitos = 0
    soma_altas = 0
    lista_ocupacao = [] 
    lista_media_perm = []
    
    periodo_txt = "Desconhecido"

    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto: continue
            
            linhas = texto.split('\n')
            
            # Tenta extrair a data do período
            if periodo_txt == "Desconhecido":
                match_data = re.search(r'Período de (\d{2}/\d{2}/\d{4})', texto)
                if match_data:
                    periodo_txt = match_data.group(1) 
                    partes = periodo_txt.split('/')
                    if len(partes) == 3:
                        periodo_txt = f"{partes[1]}/{partes[2]}" # MM/AAAA

            for linha in linhas:
                if "Unidade" in linha or "Entradas" in linha or "Página" in linha:
                    continue
                
                partes = linha.split()
                
                # Verifica se a linha termina com números
                if len(partes) > 8 and partes[-1].replace(',','').replace('.','').isdigit():
                    try:
                        val_media_perm = converter_numero(partes[-4]) 
                        val_ocupacao = converter_numero(partes[-5])   
                        
                        numeros = []
                        for p in partes:
                            if re.match(r'^\d+([.,]\d+)?$', p):
                                numeros.append(p)
                        
                        if len(numeros) >= 10:
                            intern = converter_numero(numeros[1]) 
                            altas = converter_numero(numeros[3])  
                            obitos = converter_numero(numeros[5]) 
                            
                            soma_internacoes += intern
                            soma_altas += altas
                            soma_obitos += obitos
                            
                            if val_ocupacao > 0: lista_ocupacao.append(val_ocupacao)
                            if val_media_perm > 0: lista_media_perm.append(val_media_perm)
                            
                    except Exception as e:
                        pass 

    media_ocupacao_geral = sum(lista_ocupacao) / len(lista_ocupacao) if lista_ocupacao else 0
    media_permanencia_geral = sum(lista_media_perm) / len(lista_media_perm) if lista_media_perm else 0
    
    dados_mes = {
        "periodo": periodo_txt,
        "internacoes": int(soma_internacoes),
        "altas": int(soma_altas),
        "obitos": int(soma_obitos),
        "taxa_ocupacao": round(media_ocupacao_geral, 2),
        "media_permanencia": round(media_permanencia_geral, 2)
    }
    
    dados_consolidados.append(dados_mes)

dados_consolidados.sort(key=lambda x: x['periodo'].split('/')[1] + x['periodo'].split('/')[0])

# --- CORREÇÃO DE CAMINHO AQUI ---
# Caminho Atual: .../NII-Portal-1/indicadores
# Queremos ir para: .../NII-Portal-1/arquivos

# Sobe um nível (sai de 'indicadores' e vai para 'NII-Portal-1')
pasta_raiz = os.path.dirname(caminho_script)

# Entra na pasta 'arquivos'
pasta_destino = os.path.join(pasta_raiz, "arquivos")

# Garante que a pasta destino existe
if not os.path.exists(pasta_destino):
    print(f"📂 Criando pasta '{pasta_destino}'...")
    os.makedirs(pasta_destino)

# Define o nome do arquivo final
caminho_final = os.path.join(pasta_destino, "dados_estatistica.json")

with open(caminho_final, "w", encoding="utf-8") as f:
    json.dump(dados_consolidados, f, indent=4)

print(f"\n✅ Sucesso! Arquivo gerado em:")
print(f"   {caminho_final}")