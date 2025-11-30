import requests
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURAÇÕES ---
CNES_ID = "5103402311682" # Cuiabá + Santa Helena
NOME_HOSPITAL = "Hospital Beneficente Santa Helena"
BASE_URL = "https://cnes.datasus.gov.br/services/estabelecimentos"
PASTA_DESTINO = "arquivos"

# Cabeçalhos para "enganar" o site e parecer um navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://cnes.datasus.gov.br/'
}

# Garante que a pasta existe
if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

print(f"🏥 --- EXTRATOR CNES NII ---")
print(f"Alvo: {NOME_HOSPITAL}")

def salvar_csv(dataframe, nome_arquivo):
    caminho = os.path.join(PASTA_DESTINO, nome_arquivo)
    dataframe.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
    print(f"   -> Salvo em: {caminho}")

# 1. DADOS GERAIS E HABILITAÇÕES
print("\n[1/4] Baixando Habilitações...")
try:
    response = requests.get(f"{BASE_URL}/{CNES_ID}", headers=HEADERS).json()
    habilitacoes = []
    if 'habilitacoes' in response:
        for hab in response['habilitacoes']:
            habilitacoes.append({
                'CODIGO': hab['codHabilitacao'],
                'DESCRICAO': hab['dsHabilitacao'],
                'INICIO': hab['dtCompetenciaInicial'],
                'FIM': hab['dtCompetenciaFinal'] or "ATIVO"
            })
    
    if habilitacoes:
        salvar_csv(pd.DataFrame(habilitacoes), 'CNES_Habilitacoes.csv')
    else:
        print("   ⚠️ Nenhuma habilitação encontrada.")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. PROFISSIONAIS
print("\n[2/4] Baixando Profissionais (Corpo Clínico)...")
try:
    response = requests.get(f"{BASE_URL}/{CNES_ID}/profissionais", headers=HEADERS).json()
    profissionais = []
    for p in response:
        profissionais.append({
            'NOME': p.get('nome', 'N/A'),
            'CNS': p.get('cns', 'N/A'),
            'CBO': p.get('cbo', 'N/A'),
            'DESC_CBO': p.get('dsCbo', 'N/A'),
            'VINCULO': p.get('dsVinculo', 'N/A'),
            'CH_HOSP': p.get('chHosp', 0),
            'CH_AMB': p.get('chAmb', 0)
        })
        
    if profissionais:
        salvar_csv(pd.DataFrame(profissionais), 'CNES_Profissionais.csv')
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 3. LEITOS
print("\n[3/4] Baixando Quadro de Leitos...")
try:
    response = requests.get(f"{BASE_URL}/{CNES_ID}/leitos", headers=HEADERS).json()
    leitos = []
    for l in response:
        leitos.append({
            'CODIGO': l['codLeito'],
            'DESCRICAO': l['dsLeito'],
            'TIPO': l.get('dsTipoLeito', 'N/A'),
            'EXISTENTE': l['qtExistente'],
            'CONTRATADO': l['qtContratada'],
            'SUS': l['qtSus']
        })

    if leitos:
        salvar_csv(pd.DataFrame(leitos), 'CNES_Leitos.csv')
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 4. EQUIPAMENTOS
print("\n[4/4] Baixando Equipamentos...")
try:
    response = requests.get(f"{BASE_URL}/{CNES_ID}/equipamentos", headers=HEADERS).json()
    equipamentos = []
    for e in response:
        equipamentos.append({
            'DESCRICAO': e['dsEquipamento'],
            'TIPO': e['dsTipoEquipamento'],
            'EXISTENTE': e['qtExistente'],
            'EM_USO': e['qtUso'],
            'SUS': e['qtSus']
        })

    if equipamentos:
        salvar_csv(pd.DataFrame(equipamentos), 'CNES_Equipamentos.csv')
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n✅ Extração concluída! Rode o 'upload_manager.py' para atualizar o site.")