import pandas as pd
import json
import glob
import re
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Mapeamento exato baseado no seu Raio-X
col_map = {
    'nome': ['USUÁRIO', 'USUARIO', 'NOME DO PACIENTE'],
    'admissao': ['DATA/ADMISSÃO', 'DATA/ADMISSAO', 'DATA ADMISSÃO'],
    'saida': ['DATA/SAÍDA', 'DATA/SAIDA', 'DATA SAÍDA'],
    'motivo': ['MOTIVO DA SAÍDA', 'MOTIVO DA SAIDA', 'MOTIVO'],
    'setor': ['SETOR'] # Se não achar, vamos definir padrão UTIN
}

def normalizar_texto(txt):
    if pd.isna(txt) or str(txt).strip() == '': return ''
    return str(txt).upper().strip()

def formatar_data_hsh(data):
    # Função especial para datas com PONTO (04.12.24)
    if pd.isna(data) or str(data).strip() == '' or str(data).strip() == '-': return ''
    
    texto_data = str(data).strip()
    
    # Se já vier como datetime do Excel (ex: 2024-12-01 00:00:00)
    if isinstance(data, datetime):
        return data.strftime('%Y-%m-%d')

    try:
        # Substitui pontos por barras (04.12.24 -> 04/12/24)
        texto_data = texto_data.replace('.', '/')
        
        # Converte para objeto data (o pandas lida bem com anos de 2 digitos)
        dt = pd.to_datetime(texto_data, dayfirst=True)
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def encontrar_cabecalho_e_dados(df):
    # Procura linha com 'USUÁRIO'
    for idx, row in df.iterrows():
        linha_texto = [str(x).upper() for x in row.values]
        if any('USUÁRIO' in x for x in linha_texto) or any('USUARIO' in x for x in linha_texto):
            # Achou o cabeçalho!
            df.columns = row.values # Define essa linha como nome das colunas
            df = df.iloc[idx+1:].reset_index(drop=True) # Pega tudo que vem depois
            return df
    return None

def buscar_coluna(df, chaves):
    if df is None: return None
    cols_existentes = [str(c).upper().strip() for c in df.columns]
    for chave in chaves:
        for col in cols_existentes:
            if chave == col: # Comparação exata ou parcial segura
                return df.columns[cols_existentes.index(col)]
    return None

# --- EXECUÇÃO ---
pacientes_db = {}
arquivos = glob.glob("*.xlsx")

if not arquivos:
    print("ERRO: Nenhum arquivo .xlsx encontrado.")
else:
    arquivo_alvo = arquivos[0]
    print(f"Processando: {arquivo_alvo}")
    
    try:
        xls = pd.ExcelFile(arquivo_alvo)
        print(f"Abas encontradas: {len(xls.sheet_names)}")

        total_registros = 0

        for aba in xls.sheet_names:
            # Lê a aba bruta
            df_raw = pd.read_excel(xls, sheet_name=aba, header=None)
            
            # Ajusta cabeçalho
            df = encontrar_cabecalho_e_dados(df_raw)
            
            if df is None:
                # print(f"  [i] Aba '{aba}' ignorada (não é de censo).")
                continue

            # Busca colunas
            col_nome = buscar_coluna(df, col_map['nome'])
            col_adm = buscar_coluna(df, col_map['admissao'])
            col_saida = buscar_coluna(df, col_map['saida'])
            col_motivo = buscar_coluna(df, col_map['motivo'])
            
            if not col_nome or not col_adm:
                print(f"  [!] Aba '{aba}' tem formato diferente. Pulando.")
                continue

            # Processa linhas
            for index, row in df.iterrows():
                nome = normalizar_texto(row[col_nome])
                
                # Ignora lixo
                if not nome or "TOTAL" in nome or "HOSPITAL" in nome or "USUÁRIO" in nome: 
                    continue
                
                adm = formatar_data_hsh(row[col_adm])
                if not adm: continue

                saida = formatar_data_hsh(row[col_saida]) if col_saida else ''
                motivo = normalizar_texto(row[col_motivo]) if col_motivo else ''
                
                # Tratamento especial para o motivo
                if motivo == 'NAN': motivo = ''

                # --- Lógica de Unificação (O Pulo do Gato) ---
                chave = (nome, adm)
                
                if chave not in pacientes_db:
                    pacientes_db[chave] = {
                        'nome': nome,
                        'setor': 'UTIN', # Padrão baseado no título do arquivo
                        'admissao': adm,
                        'saida': saida,
                        'motivo': motivo
                    }
                    total_registros += 1
                else:
                    # Se já existe, enriquece os dados
                    if saida and not pacientes_db[chave]['saida']:
                        pacientes_db[chave]['saida'] = saida
                        pacientes_db[chave]['motivo'] = motivo

            print(f"  [OK] Aba '{aba}' processada.")

        # Salva JSON
        lista_final = list(pacientes_db.values())
        lista_final.sort(key=lambda x: x['admissao'])

        if len(lista_final) > 0:
            with open('BACKUP_COMPLETO_HISTORICO.json', 'w', encoding='utf-8') as f:
                json.dump(lista_final, f, ensure_ascii=False, indent=4)
            print("=" * 40)
            print(f"SUCESSO! {len(lista_final)} pacientes únicos recuperados.")
            print("Agora importe o arquivo 'BACKUP_COMPLETO_HISTORICO.json' no Portal.")
        else:
            print("ERRO: Nenhum paciente foi extraído. Verifique o padrão das colunas.")

    except Exception as e:
        print(f"Erro fatal: {e}")