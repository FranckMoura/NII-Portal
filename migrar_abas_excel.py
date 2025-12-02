import pandas as pd
import json
import glob
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Mapeamento de colunas (Flexível para achar variações)
col_map = {
    'nome': ['NOME', 'PACIENTE', 'NM PACIENTE', 'NOME DO PACIENTE'],
    'admissao': ['ADMISSÃO', 'DATA INTERNAÇÃO', 'DT INTERNACAO', 'DATA ADMISSÃO', 'DT ADMISSAO'],
    'saida': ['SAÍDA', 'ALTA', 'DT SAIDA', 'DATA SAÍDA', 'DATA ALTA'],
    'motivo': ['MOTIVO', 'OBSERVAÇÃO', 'DESTINO', 'DESFECHO'],
    'setor': ['SETOR', 'UNIDADE', 'ALA']
}

def normalizar_texto(txt):
    if pd.isna(txt) or str(txt).strip() == '': return ''
    return str(txt).upper().strip()

def formatar_data(data):
    if pd.isna(data) or str(data).strip() == '': return ''
    try:
        # Tenta converter o objeto data direto
        return pd.to_datetime(data, dayfirst=True).strftime('%Y-%m-%d')
    except:
        return ''

def encontrar_cabecalho_e_dados(df):
    # Procura em qual linha está o cabeçalho
    for idx, row in df.iterrows():
        linha_texto = [str(x).upper() for x in row.values]
        # Se encontrar 'NOME' ou 'PACIENTE' nesta linha, é o cabeçalho
        if any(x in linha_texto for x in ['NOME', 'PACIENTE', 'NM PACIENTE']):
            # Define esta linha como cabeçalho e recarrega os dados a partir dela
            df.columns = row.values
            df = df.iloc[idx+1:].reset_index(drop=True)
            return df
    return None

def buscar_coluna(df, chaves):
    cols_existentes = [str(c).upper().strip() for c in df.columns]
    for chave in chaves:
        for col in cols_existentes:
            if chave in col:
                return df.columns[cols_existentes.index(col)]
    return None

# --- EXECUÇÃO ---
pacientes_db = {}
arquivos = glob.glob("*.xlsx")

if not arquivos:
    print("ERRO: Nenhum arquivo .xlsx encontrado na pasta.")
else:
    arquivo_alvo = arquivos[0] # Pega o primeiro Excel que achar
    print(f"Processando arquivo: {arquivo_alvo}")
    
    try:
        # Carrega o arquivo Excel inteiro (todas as abas)
        xls = pd.ExcelFile(arquivo_alvo)
        print(f"Abas encontradas: {xls.sheet_names}")

        for aba in xls.sheet_names:
            print(f" -> Lendo aba: '{aba}'...")
            
            # Lê a aba sem cabeçalho definido para podermos procurar
            df_raw = pd.read_excel(xls, sheet_name=aba, header=None)
            
            # Tenta achar onde começam os dados
            df = encontrar_cabecalho_e_dados(df_raw)
            
            if df is None:
                print(f"    [X] Pulei aba '{aba}': Não achei coluna 'NOME' ou 'PACIENTE'.")
                continue

            # Identifica as colunas nesta aba específica
            col_nome = buscar_coluna(df, col_map['nome'])
            col_adm = buscar_coluna(df, col_map['admissao'])
            col_saida = buscar_coluna(df, col_map['saida'])
            col_motivo = buscar_coluna(df, col_map['motivo'])
            col_setor = buscar_coluna(df, col_map['setor'])

            if not col_nome or not col_adm:
                print(f"    [X] Aba '{aba}' incompleta (Falta Nome ou Data Admissão).")
                continue

            count_aba = 0
            for index, row in df.iterrows():
                nome = normalizar_texto(row[col_nome])
                # Ignora linhas de totais ou vazias
                if not nome or "TOTAL" in nome or "LEITOS" in nome: continue
                
                adm = formatar_data(row[col_adm])
                if not adm: continue # Sem data de admissão não entra

                saida = formatar_data(row[col_saida]) if col_saida else ''
                motivo = normalizar_texto(row[col_motivo]) if col_motivo else ''
                setor = normalizar_texto(row[col_setor]) if col_setor else 'UTIN'

                # Limpeza de texto 'nan'
                if motivo == 'NAN': motivo = ''
                if setor == 'NAN': setor = 'UTIN'

                # Lógica de Unificação (Chave = Nome + Admissão)
                chave = (nome, adm)
                
                if chave not in pacientes_db:
                    pacientes_db[chave] = {
                        'nome': nome, 'setor': setor, 'admissao': adm, 
                        'saida': saida, 'motivo': motivo
                    }
                    count_aba += 1
                else:
                    # Se já existe, atualiza se tiver informação nova (ex: data de saída)
                    if saida and not pacientes_db[chave]['saida']:
                        pacientes_db[chave]['saida'] = saida
                        pacientes_db[chave]['motivo'] = motivo

            print(f"    [OK] Processados {count_aba} novos registros na aba '{aba}'.")

        # Salva o JSON final
        lista_final = list(pacientes_db.values())
        lista_final.sort(key=lambda x: x['admissao'])

        if len(lista_final) > 0:
            with open('BACKUP_COMPLETO_HISTORICO.json', 'w', encoding='utf-8') as f:
                json.dump(lista_final, f, ensure_ascii=False, indent=4)
            print("-" * 40)
            print(f"SUCESSO TOTAL! {len(lista_final)} pacientes únicos consolidados.")
            print("Arquivo 'BACKUP_COMPLETO_HISTORICO.json' criado.")
        else:
            print("ERRO: Nenhum paciente encontrado em nenhuma aba.")

    except Exception as e:
        print(f"Erro fatal: {e}")