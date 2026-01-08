import pdfplumber
import glob
import os
import re
import json
import sys

print("--- 🏥 EXTRATOR DE INDICADORES POR SETOR (DETALHADO) ---")

# Define diretório de trabalho
caminho_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(caminho_script)

arquivos_pdf = glob.glob("R_EST_HOSPITALAR*.pdf")

if not arquivos_pdf:
    print("❌ Nenhum PDF encontrado!")
    sys.exit()

dados_consolidados = []

def limpar_numero(txt):
    """Converte '1.234,56' para float 1234.56"""
    if not txt: return 0.0
    # Remove pontos de milhar e troca vírgula decimal por ponto
    txt_limpo = txt.replace('.', '').replace(',', '.')
    try:
        return float(txt_limpo)
    except:
        return 0.0

for arquivo in arquivos_pdf:
    print(f"📄 Processando: {arquivo}...")
    
    periodo_txt = "Desconhecido"
    dados_mes = {
        "periodo": "",
        "totais": {},
        "unidades": []
    }

    with pdfplumber.open(arquivo) as pdf:
        # --- 1. IDENTIFICAR DATA ---
        page1_text = pdf.pages[0].extract_text()
        match_data = re.search(r'Período de \d{2}/(\d{2})/(\d{4})', page1_text)
        if match_data:
            periodo_txt = f"{match_data.group(1)}/{match_data.group(2)}" # MM/AAAA
        else:
            # Tenta pegar do nome do arquivo
            try:
                nums = re.findall(r'\d+', arquivo)[0]
                periodo_txt = f"{nums[:2]}/{'20'+nums[2:] if len(nums)==4 else nums[2:]}"
            except: pass
        
        dados_mes["periodo"] = periodo_txt

        # --- 2. EXTRAIR DADOS POR SETOR ---
        for page in pdf.pages:
            linhas = page.extract_text().split('\n')
            
            for linha in linhas:
                # Ignora cabeçalhos e rodapés inúteis
                if "Unidade" in linha or "Entradas" in linha or "Página" in linha or "SoulMV" in linha:
                    continue
                
                # Se for a linha de TOTAL do PDF, ignoramos por enquanto (vamos calcular nós mesmos ou pegar separado)
                if linha.strip().startswith("Total:"):
                    continue

                partes = linha.split()
                
                # Uma linha de dados válida geralmente termina com um número (Pac/Dia)
                # e tem vários campos numéricos.
                if len(partes) > 5 and partes[-1].replace(',','').replace('.','').isdigit():
                    
                    try:
                        # Tenta identificar onde começam os números
                        # O nome da unidade pode ter espaços (Ex: "2º ANDAR - I POSTO")
                        # A estratégia é pegar tudo que NÃO é número no início
                        
                        nome_unidade_parts = []
                        numeros = []
                        
                        for p in partes:
                            # Se for numero (int ou float brasileiro)
                            if re.match(r'^\d+([.,]\d+)?$', p):
                                numeros.append(limpar_numero(p))
                            else:
                                # Se já começamos a pegar números, qualquer texto depois é lixo ou erro
                                if not numeros:
                                    nome_unidade_parts.append(p)
                        
                        nome_unidade = " ".join(nome_unidade_parts)
                        
                        # Filtros de exclusão (opcionais)
                        if "LEITO EXTRA" in nome_unidade: continue

                        # Mapeamento baseado nas colunas do SoulMV (verificado no seu PDF):
                        # As colunas numéricas extraídas geralmente seguem a ordem:
                        # [0] SaldoAnt, [1] Intern, [2] TransfDe, [3] Altas, [4] TransfPara, [5] Obitos...
                        # [-5] %Ocup, [-4] MediaPerm, [-3] TaxaMov, [-2] TaxaMort, [-1] PacDia
                        
                        if len(numeros) >= 8:
                            unidade_data = {
                                "nome": nome_unidade,
                                "internacoes": int(numeros[1]),
                                "altas": int(numeros[3]),
                                "obitos": int(numeros[5]),
                                "media_permanencia": numeros[-4],
                                "taxa_ocupacao": numeros[-5],
                                "pac_dia": int(numeros[-1])
                            }
                            dados_mes["unidades"].append(unidade_data)
                            
                    except Exception as e:
                        # print(f"Erro linha: {linha} -> {e}")
                        pass

    # --- 3. CALCULAR TOTAL INSTITUCIONAL (Soma das unidades extraídas) ---
    soma_intern = sum(u["internacoes"] for u in dados_mes["unidades"])
    soma_altas = sum(u["altas"] for u in dados_mes["unidades"])
    soma_obitos = sum(u["obitos"] for u in dados_mes["unidades"])
    soma_pac_dia = sum(u["pac_dia"] for u in dados_mes["unidades"])
    
    # Médias ponderadas ou simples para o total
    # Para ocupação e permanência, o ideal é recalcular com base nos totais, 
    # mas como faltam dados de leitos exatos por setor no PDF simples, faremos média simples das unidades ativas
    # OU pegamos se o PDF tiver a linha "Total:" (mas excluímos ela acima).
    # Vamos usar média das taxas das unidades para simplificar ou soma se fizer sentido.
    
    # Média de ocupação institucional (aproximada pela média das unidades ou recalculo se tivermos leitos totais)
    # Vamos usar a média simples das ocupações das unidades > 0 para não zerar com unidades vazias
    lista_ocup = [u["taxa_ocupacao"] for u in dados_mes["unidades"] if u["taxa_ocupacao"] > 0]
    media_ocup = sum(lista_ocup)/len(lista_ocup) if lista_ocup else 0
    
    lista_perm = [u["media_permanencia"] for u in dados_mes["unidades"] if u["media_permanencia"] > 0]
    media_perm = sum(lista_perm)/len(lista_perm) if lista_perm else 0

    dados_mes["totais"] = {
        "nome": "INSTITUCIONAL (TOTAL)",
        "internacoes": soma_intern,
        "altas": soma_altas,
        "obitos": soma_obitos,
        "pac_dia": soma_pac_dia,
        "taxa_ocupacao": round(media_ocup, 2),
        "media_permanencia": round(media_perm, 2)
    }
    
    dados_consolidados.append(dados_mes)

# Ordenação Cronológica (Assumindo MM/AAAA)
def get_sort_key(x):
    parts = x["periodo"].split('/')
    if len(parts) == 2: return f"{parts[1]}{parts[0]}" # AAAAMM
    return "000000"

dados_consolidados.sort(key=get_sort_key)

# Salvar JSON
pasta_raiz = os.path.dirname(caminho_script)
pasta_destino = os.path.join(pasta_raiz, "arquivos")
if not os.path.exists(pasta_destino): os.makedirs(pasta_destino)

caminho_final = os.path.join(pasta_destino, "dados_setorizados.json")

with open(caminho_final, "w", encoding="utf-8") as f:
    json.dump(dados_consolidados, f, indent=4, ensure_ascii=False)

print(f"\n✅ DADOS SETORIZADOS GERADOS!")
print(f"📂 Arquivo: {caminho_final}")