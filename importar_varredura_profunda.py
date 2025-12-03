import pandas as pd
import json
import re
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

print("--- IMPORTAÇÃO VARREDURA PROFUNDA (ELÁSTICA) ---")

arquivo_excel = 'censo_utineonatal.xlsx'
abas_para_ler = {'UTIN': 'UTIN', 'UCINCO': 'UCINCO', 'UCINCA': 'UCINCA'}

def validar_data(val):
    # Tenta validar se é data (aceita datetime ou texto xx/xx/xx)
    try:
        if pd.isna(val) or str(val).strip() == '': return None
        
        # Se já for timestamp do pandas/excel
        if isinstance(val, (pd.Timestamp, datetime)):
            dt = val
        else:
            texto = str(val).strip().replace('.', '/')
            # Tem que ter números e barras/pontos
            if not re.search(r'\d+[./]\d+', texto): return None
            dt = pd.to_datetime(texto, dayfirst=True, errors='coerce')
        
        if pd.isna(dt): return None
        
        # Filtro de ano lógico
        if dt.year > 2026: dt = dt.replace(year=2025)
        if dt.year < 2020: dt = dt.replace(year=2025)
        
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def validar_nome(val):
    if pd.isna(val): return None
    txt = str(val).upper().strip()
    # Lista negra de palavras que parecem nome mas são cabeçalho
    lixo = ["DATA", "NOME", "PACIENTE", "TOTAL", "USUÁRIO", "ADMISSÃO", "OBS", "HOSPITAL", "DIAS", "MOTIVO"]
    
    if len(txt) < 3: return None
    if any(x == txt for x in lixo): return None # Bloqueio exato
    if any(x in txt for x in ["TOTAL DE", "MÉDIA"]): return None # Bloqueio parcial
    
    return txt

pacientes_finais = []

try:
    xls = pd.ExcelFile(arquivo_excel)
    
    for nome_aba, setor_destino in abas_para_ler.items():
        aba_real = next((a for a in xls.sheet_names if nome_aba in a.upper()), None)
        if not aba_real: continue
            
        print(f"-> Varrendo aba '{aba_real}' ({setor_destino})...")
        # Lê todas as colunas e linhas
        df = pd.read_excel(xls, sheet_name=aba_real, header=None)
        
        count_aba = 0
        
        # VARREDURA LINHA A LINHA
        for idx, row in df.iterrows():
            # Pega as primeiras 10 colunas da linha
            cols = [row[i] if i < len(row) else '' for i in range(10)]
            
            nome_encontrado = None
            adm_encontrada = None
            col_idx_adm = -1
            
            # 1. ACHA O NOME (nas primeiras 4 colunas)
            for i in range(4):
                potencial_nome = validar_nome(cols[i])
                if potencial_nome:
                    nome_encontrado = potencial_nome
                    # Agora procura a DATA nas colunas À DIREITA do nome
                    for j in range(i + 1, 8):
                        potencial_data = validar_data(cols[j])
                        if potencial_data:
                            adm_encontrada = potencial_data
                            col_idx_adm = j
                            break
                    break # Se achou nome, para de procurar nome nesta linha
            
            # SE ACHOU PAR (NOME + DATA)
            if nome_encontrado and adm_encontrada:
                # Tenta achar Saída (coluna logo após a Admissão)
                saida_encontrada = ''
                if col_idx_adm + 1 < len(cols):
                    saida_encontrada = validar_data(cols[col_idx_adm + 1]) or ''
                
                # Tenta achar Motivo (coluna após a Saída)
                motivo_encontrado = ''
                if col_idx_adm + 2 < len(cols):
                    motivo_encontrado = str(cols[col_idx_adm + 2]).upper().strip()
                    if motivo_encontrado == 'NAN': motivo_encontrado = ''

                pacientes_finais.append({
                    'nome': nome_encontrado,
                    'setor': setor_destino,
                    'admissao': adm_encontrada,
                    'saida': saida_encontrada,
                    'motivo': motivo_encontrado
                })
                count_aba += 1
                # print(f"   [OK] {nome_encontrado} | {adm_encontrada}")

        print(f"   Recuperados: {count_aba}")

    # SALVAR
    if pacientes_finais:
        with open('CENSO_ELASTICO.json', 'w', encoding='utf-8') as f:
            json.dump(pacientes_finais, f, ensure_ascii=False, indent=4)
        print("="*40)
        print(f"SUCESSO! {len(pacientes_finais)} registros encontrados.")
        print("Arquivo: CENSO_ELASTICO.json")
    else:
        print("ERRO: Zero registros encontrados.")

except Exception as e:
    print(f"Erro: {e}")