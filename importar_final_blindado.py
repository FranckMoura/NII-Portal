import pandas as pd
import json
import re
import warnings

# Silenciar avisos chatos do pandas
warnings.filterwarnings("ignore")

print("--- IMPORTAÇÃO BLINDADA (FORÇANDO COLUNAS) ---")

arquivo_excel = 'censo_utineonatal.xlsx'

# Mapeamento de Abas
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
        # Tenta formatos comuns no Brasil
        dt = pd.to_datetime(texto, dayfirst=True, errors='coerce')
        if pd.isna(dt): return ''
        
        # Correção de anos
        if dt.year > 2025: dt = dt.replace(year=2025)
        if dt.year < 2020: dt = dt.replace(year=2025)
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def limpar_nome(val):
    if pd.isna(val): return ''
    txt = str(val).upper().strip()
    # Lista de palavras para ignorar
    lixo = ["PACIENTE", "NOME", "TOTAL", "USUÁRIO", "DATA", "ADMISSÃO", "SAÍDA", "OBS"]
    if any(x in txt for x in lixo): return ''
    if len(txt) < 3: return ''
    return txt

pacientes_finais = []

try:
    xls = pd.ExcelFile(arquivo_excel)
    
    for nome_aba, setor_destino in abas_para_ler.items():
        # Busca aba (ignora maiúscula/minúscula)
        aba_real = next((a for a in xls.sheet_names if nome_aba in a.upper()), None)
        
        if not aba_real:
            print(f"AVISO: Aba '{nome_aba}' não encontrada.")
            continue
            
        print(f" -> Processando aba '{aba_real}'...")
        
        # Lê a aba
        df = pd.read_excel(xls, sheet_name=aba_real, header=None)
        
        # --- ESTRATÉGIA BLINDADA ---
        # Vamos procurar onde começam os dados, mas vamos FORÇAR as colunas B, C, D, E
        # Coluna B (índice 1) = Nome
        # Coluna C (índice 2) = Admissão
        # Coluna D (índice 3) = Saída
        # Coluna E (índice 4) = Motivo
        
        col_nome = 1
        col_adm = 2
        col_saida = 3
        col_motivo = 4
        
        # Acha a linha de cabeçalho apenas para saber onde começar a ler (pular o topo)
        inicio_dados = 0
        for idx, row in df.iterrows():
            linha = [str(x).upper() for x in row.values]
            if any("USUÁRIO" in x or "NOME" in x or "PACIENTE" in x for x in linha):
                inicio_dados = idx + 1
                break
        
        print(f"    Iniciando leitura na linha {inicio_dados + 1}")
        
        count = 0
        for idx, row in df.iloc[inicio_dados:].iterrows():
            try:
                # Tenta ler nas colunas fixas
                if len(row) < 5: continue # Pula linhas incompletas

                nome = limpar_nome(row[col_nome])
                if not nome: continue

                adm = limpar_data(row[col_adm])
                if not adm: continue # Sem data não entra

                saida = limpar_data(row[col_saida])
                
                motivo = str(row[col_motivo]).upper().strip()
                if motivo == 'NAN': motivo = ''

                pacientes_finais.append({
                    'nome': nome,
                    'setor': setor_destino,
                    'admissao': adm,
                    'saida': saida,
                    'motivo': motivo
                })
                count += 1
            except Exception:
                continue
        
        print(f"    Recuperados: {count} pacientes.")

    # Salvar
    if pacientes_finais:
        with open('CENSO_NOVEMBRO_LIMPO.json', 'w', encoding='utf-8') as f:
            json.dump(pacientes_finais, f, ensure_ascii=False, indent=4)
        print("="*40)
        print(f"SUCESSO! Total de {len(pacientes_finais)} registros.")
        print("Importe o arquivo 'CENSO_NOVEMBRO_LIMPO.json' no portal.")
    else:
        print("ERRO: Zero pacientes encontrados.")

except Exception as e:
    print(f"Erro: {e}")