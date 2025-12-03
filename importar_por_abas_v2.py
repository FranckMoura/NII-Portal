import pandas as pd
import json
import re
from datetime import datetime

print("--- IMPORTAÇÃO POR ABAS (VERSÃO CORRIGIDA 'USUÁRIO') ---")

arquivo_excel = 'censo_utineonatal.xlsx'

# Mapeamento: Nome da Aba -> Nome do Setor no Sistema
abas_para_ler = {
    'UTIN': 'UTIN',
    'UCINCO': 'UCINCO',
    'UCINCA': 'UCINCA'
}

def limpar_data(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).strip() == '-': return ''
    texto = str(val).strip().replace('.', '/')
    
    match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', texto)
    if match: texto = match.group()

    try:
        dt = pd.to_datetime(texto, dayfirst=True)
        if dt.year > 2025: dt = dt.replace(year=2025)
        if dt.year < 2020: dt = dt.replace(year=2025)
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def limpar_nome(val):
    if pd.isna(val): return ''
    txt = str(val).upper().strip()
    if "PACIENTE" in txt or "NOME" in txt or "TOTAL" in txt or "USUÁRIO" in txt: return ''
    if len(txt) < 3: return ''
    return txt

pacientes_finais = []

try:
    xls = pd.ExcelFile(arquivo_excel)
    print(f"Arquivo carregado: {arquivo_excel}")
    
    for nome_aba, setor_destino in abas_para_ler.items():
        # Busca aba ignorando maiúsculas/minúsculas
        aba_real = next((a for a in xls.sheet_names if nome_aba in a.upper()), None)
        
        if not aba_real:
            print(f"AVISO: Aba '{nome_aba}' não encontrada.")
            continue
            
        print(f" -> Processando aba '{aba_real}' -> Setor: {setor_destino}")
        
        df = pd.read_excel(xls, sheet_name=aba_real, header=None)
        
        # --- BUSCA DO CABEÇALHO ---
        inicio_dados = 0
        col_nome = -1
        col_adm = -1
        col_saida = -1
        col_motivo = -1

        # Palavras-chave permitidas para identificar a coluna de nome
        chaves_nome = ["USUÁRIO", "USUARIO", "NOME", "PACIENTE", "RN", "RECÉM"]

        for idx, row in df.iterrows():
            linha = [str(x).upper() for x in row.values]
            
            # Verifica se alguma palavra-chave está nesta linha
            if any(key in x for key in chaves_nome for x in linha):
                inicio_dados = idx + 1
                print(f"    [OK] Cabeçalho encontrado na linha {idx+1}")
                
                # Mapeia colunas dinamicamente
                for i, col_val in enumerate(linha):
                    if any(k in col_val for k in chaves_nome): col_nome = i
                    elif "ADMISSÃO" in col_val or "DATA" in col_val or "ENTRADA" in col_val: col_adm = i
                    elif "SAÍDA" in col_val or "ALTA" in col_val: col_saida = i
                    elif "MOTIVO" in col_val or "OBS" in col_val or "DESTINO" in col_val: col_motivo = i
                break
        
        # Se não achou cabeçalho, tenta usar índices fixos (B=1, C=2...)
        if col_nome == -1: 
            print("    [!] Cabeçalho não detectado. Tentando colunas padrão (B, C, D, E)...")
            col_nome, col_adm, col_saida, col_motivo = 1, 2, 3, 4

        count_setor = 0
        
        # Processa as linhas de dados
        for idx, row in df.iloc[inicio_dados:].iterrows():
            try:
                nome = limpar_nome(row[col_nome])
                if not nome: continue

                adm = limpar_data(row[col_adm])
                if not adm: continue

                saida = limpar_data(row[col_saida]) if col_saida != -1 else ''
                motivo = str(row[col_motivo]).upper().strip() if col_motivo != -1 else ''
                if motivo == 'NAN': motivo = ''

                pacientes_finais.append({
                    'nome': nome,
                    'setor': setor_destino, # Força o setor correto
                    'admissao': adm,
                    'saida': saida,
                    'motivo': motivo
                })
                count_setor += 1
            except Exception:
                continue
        
        print(f"    -> Recuperados {count_setor} pacientes nesta aba.")

    # Salva JSON
    if pacientes_finais:
        with open('CENSO_NOVEMBRO_LIMPO.json', 'w', encoding='utf-8') as f:
            json.dump(pacientes_finais, f, ensure_ascii=False, indent=4)
        print("="*40)
        print(f"SUCESSO TOTAL! {len(pacientes_finais)} registros gerados.")
        print("Arquivo pronto: CENSO_NOVEMBRO_LIMPO.json")
    else:
        print("ERRO: Ainda não encontrei pacientes. Verifique se as colunas estão preenchidas.")

except Exception as e:
    print(f"Erro: {e}")