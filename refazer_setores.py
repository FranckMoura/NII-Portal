import pandas as pd
import json
import glob
import re
from datetime import datetime

# --- CONFIGURAÇÃO ---
print("--- INICIANDO REPROCESSAMENTO INTELIGENTE ---")

def normalizar_texto(txt):
    if pd.isna(txt): return ''
    return str(txt).upper().strip()

def identificar_setor_inteligente(row):
    # Converte a linha inteira para texto para procurar palavras-chave
    linha_texto = " ".join([str(x).upper() for x in row.values])
    
    if 'UCINCA' in linha_texto or 'CANGURU' in linha_texto:
        return 'UCINCA'
    if 'UCINCO' in linha_texto or 'INTERMEDIARIA' in linha_texto or 'MÉDIO RISCO' in linha_texto:
        return 'UCINCO'
    
    # Se tiver coluna específica de setor, usa ela
    for col in row.index:
        if 'SETOR' in str(col).upper() or 'UNIDADE' in str(col).upper():
            valor = str(row[col]).upper()
            if 'UCINCA' in valor: return 'UCINCA'
            if 'UCINCO' in valor: return 'UCINCO'
    
    # Padrão se não achar nada
    return 'UTIN'

def formatar_data_hsh(data):
    if pd.isna(data) or str(data).strip() == '' or str(data).strip() == '-': return ''
    texto = str(data).strip().replace('.', '/')
    
    try:
        # Tenta pegar datas misturadas com texto (ex: "01/05/2025 alta")
        padrao_data = re.search(r'\d{2}/\d{2}/\d{2,4}', texto)
        if padrao_data:
            texto = padrao_data.group()
            
        dt = pd.to_datetime(texto, dayfirst=True)
        
        # CORREÇÃO DE ANOS ABSURDOS
        if dt.year > 2025: dt = dt.replace(year=2025)
        if dt.year < 2020: dt = dt.replace(year=2025)
        
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def encontrar_inicio_dados(df):
    # Procura a linha que tem "NOME" ou "USUÁRIO"
    for idx, row in df.iterrows():
        txt = " ".join([str(x).upper() for x in row.values])
        if 'USUÁRIO' in txt or 'PACIENTE' in txt or 'NOME' in txt:
            df.columns = row.values
            return df.iloc[idx+1:].reset_index(drop=True)
    return None

# --- EXECUÇÃO ---
pacientes_db = {}
arquivos = glob.glob("*.xlsx")

if not arquivos:
    print("ERRO: Coloque as planilhas Excel na mesma pasta deste script.")
else:
    arquivo_alvo = arquivos[0]
    print(f"Lendo: {arquivo_alvo}")
    
    xls = pd.ExcelFile(arquivo_alvo)
    total_lidos = 0
    
    for aba in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=aba, header=None)
        df = encontrar_inicio_dados(df_raw)
        
        if df is None: continue

        # Mapear colunas dinamicamente
        col_nome = next((c for c in df.columns if 'USUÁRIO' in str(c).upper() or 'NOME' in str(c).upper()), None)
        col_adm = next((c for c in df.columns if 'ADMISSÃO' in str(c).upper() or 'DATA' in str(c).upper()), None)
        col_saida = next((c for c in df.columns if 'SAÍDA' in str(c).upper() or 'ALTA' in str(c).upper()), None)
        col_motivo = next((c for c in df.columns if 'MOTIVO' in str(c).upper()), None)

        if not col_nome: continue

        for index, row in df.iterrows():
            nome = normalizar_texto(row[col_nome])
            if not nome or len(nome) < 3 or "TOTAL" in nome: continue
            
            adm = formatar_data_hsh(row[col_adm]) if col_adm else ''
            if not adm: continue # Sem admissão não entra
            
            saida = formatar_data_hsh(row[col_saida]) if col_saida else ''
            motivo = normalizar_texto(row[col_motivo]) if col_motivo else ''
            
            # AQUI ESTÁ A MÁGICA: Tenta descobrir o setor
            setor = identificar_setor_inteligente(row)

            chave = (nome, adm)
            
            # Salva ou Atualiza
            if chave not in pacientes_db:
                pacientes_db[chave] = {
                    'nome': nome, 'setor': setor, 'admissao': adm, 'saida': saida, 'motivo': motivo
                }
                total_lidos += 1
            else:
                if saida: pacientes_db[chave]['saida'] = saida
                if motivo: pacientes_db[chave]['motivo'] = motivo
                # Se achou setor específico agora, atualiza
                if setor != 'UTIN': pacientes_db[chave]['setor'] = setor

    # Salva JSON Final
    lista_final = list(pacientes_db.values())
    lista_final.sort(key=lambda x: x['admissao'])
    
    with open('BACKUP_FINAL_SETORES.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)
        
    print("="*40)
    print(f"SUCESSO! {len(lista_final)} pacientes processados.")
    print("Arquivo 'BACKUP_FINAL_SETORES.json' criado.")
    print("IMPORTANTE: Se ainda estiver tudo como UTIN, significa que sua planilha não tem NENHUMA indicação de setor.")
    print("Nesse caso, você precisará adicionar uma coluna 'SETOR' no Excel e escrever UCINCO/UCINCA manualmente.")