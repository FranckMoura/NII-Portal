import pandas as pd
import json
import re
import warnings

warnings.filterwarnings("ignore")

print("--- IMPORTAÇÃO TIPO 'SCANNER' (VARREDURA LINHA A LINHA) ---")

arquivo_excel = 'censo_utineonatal.xlsx'
abas_para_ler = {'UTIN': 'UTIN', 'UCINCO': 'UCINCO', 'UCINCA': 'UCINCA'}

def validar_data(val):
    # Retorna a data formatada YYYY-MM-DD se for válida, ou None se não for
    try:
        # Se já for data do Excel (datetime)
        if isinstance(val, pd.Timestamp) or isinstance(val, datetime):
            dt = val
        else:
            # Se for texto
            texto = str(val).strip().replace('.', '/')
            if not re.search(r'\d', texto): return None # Sem números
            dt = pd.to_datetime(texto, dayfirst=True, errors='coerce')
        
        if pd.isna(dt): return None
        
        # Filtro de ano (apenas dados recentes)
        if dt.year > 2026: dt = dt.replace(year=2025)
        if dt.year < 2020: dt = dt.replace(year=2025)
        
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def validar_nome(val):
    if pd.isna(val): return None
    txt = str(val).upper().strip()
    lixo = ["DATA", "NOME", "PACIENTE", "TOTAL", "USUÁRIO", "ADMISSÃO", "OBS", "HOSPITAL"]
    if len(txt) < 3: return None
    if any(x in txt for x in lixo): return None
    return txt

from datetime import datetime
pacientes_finais = []

try:
    xls = pd.ExcelFile(arquivo_excel)
    
    for nome_aba, setor_destino in abas_para_ler.items():
        aba_real = next((a for a in xls.sheet_names if nome_aba in a.upper()), None)
        if not aba_real: continue
            
        print(f"-> Varrendo aba '{aba_real}'...")
        df = pd.read_excel(xls, sheet_name=aba_real, header=None)
        
        count_aba = 0
        
        # VARREDURA LINHA POR LINHA
        for idx, row in df.iterrows():
            # Pega valores das primeiras 5 colunas com segurança
            # Col A=0, B=1, C=2, D=3, E=4
            cols = [row[i] if i < len(row) else '' for i in range(6)]
            
            nome_encontrado = None
            adm_encontrada = None
            saida_encontrada = ''
            motivo_encontrado = ''
            
            # --- TENTATIVA 1: Nome na A (0), Data na B (1) ---
            if validar_nome(cols[0]) and validar_data(cols[1]):
                nome_encontrado = validar_nome(cols[0])
                adm_encontrada = validar_data(cols[1])
                saida_encontrada = validar_data(cols[2]) or ''
                motivo_encontrado = str(cols[3]).upper().strip()

            # --- TENTATIVA 2: Nome na B (1), Data na C (2) ---
            elif validar_nome(cols[1]) and validar_data(cols[2]):
                nome_encontrado = validar_nome(cols[1])
                adm_encontrada = validar_data(cols[2])
                saida_encontrada = validar_data(cols[3]) or ''
                motivo_encontrado = str(cols[4]).upper().strip()

            # --- TENTATIVA 3: Nome na C (2), Data na D (3) ---
            elif validar_nome(cols[2]) and validar_data(cols[3]):
                nome_encontrado = validar_nome(cols[2])
                adm_encontrada = validar_data(cols[3])
                saida_encontrada = validar_data(cols[4]) or ''
                motivo_encontrado = str(cols[5]).upper().strip()

            # SE ACHOU ALGUÉM
            if nome_encontrado and adm_encontrada:
                if motivo_encontrado == 'NAN': motivo_encontrado = ''
                
                pacientes_finais.append({
                    'nome': nome_encontrado,
                    'setor': setor_destino,
                    'admissao': adm_encontrada,
                    'saida': saida_encontrada,
                    'motivo': motivo_encontrado
                })
                count_aba += 1

        print(f"   Recuperados: {count_aba}")

    # SALVAR
    if pacientes_finais:
        with open('CENSO_VARREDURA.json', 'w', encoding='utf-8') as f:
            json.dump(pacientes_finais, f, ensure_ascii=False, indent=4)
        print("="*40)
        print(f"SUCESSO! {len(pacientes_finais)} registros encontrados.")
        print("Arquivo: CENSO_VARREDURA.json")
    else:
        print("ERRO: Ainda zero. O Excel deve estar muito diferente do esperado.")

except Exception as e:
    print(f"Erro: {e}")