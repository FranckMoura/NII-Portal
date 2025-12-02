import pandas as pd
import json
import os
import glob
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Lista de possíveis nomes para as colunas nas suas planilhas (para o script achar sozinho)
col_map = {
    'nome': ['NOME', 'PACIENTE', 'NOME DO PACIENTE', 'NM PACIENTE'],
    'admissao': ['DATA ADMISSÃO', 'DT ADMISSÃO', 'DATA INTERNAÇÃO', 'ADMISSÃO'],
    'saida': ['DATA SAÍDA', 'DT SAÍDA', 'ALTA', 'SAÍDA'],
    'motivo': ['MOTIVO', 'OBSERVAÇÃO', 'MOTIVO SAÍDA', 'DESTINO'],
    'setor': ['SETOR', 'UNIDADE', 'LOCAL']
}

def normalizar_texto(txt):
    if pd.isna(txt) or txt == '': return ''
    return str(txt).upper().strip()

def formatar_data(data):
    # Tenta converter diversos formatos de data para AAAA-MM-DD
    if pd.isna(data) or str(data).strip() == '': return ''
    try:
        return pd.to_datetime(data, dayfirst=True).strftime('%Y-%m-%d')
    except:
        return ''

def encontrar_coluna(df, chaves):
    # Procura qual coluna do Excel corresponde às chaves configuradas
    colunas_df = [c.upper().strip() for c in df.columns]
    for chave in chaves:
        for col in colunas_df:
            if chave in col:
                return df.columns[colunas_df.index(col)]
    return None

# --- PROCESSAMENTO ---
pacientes_db = {} # Dicionário para garantir unicidade: Chave = (NOME, DATA_ADMISSAO)

# Busca todos os arquivos CSV e XLSX na pasta
arquivos = glob.glob("*.csv") + glob.glob("*.xlsx")
print(f"Encontrados {len(arquivos)} arquivos para processar...")

for arquivo in arquivos:
    if "migrar" in arquivo or "json" in arquivo: continue # Pula o próprio script
    
    print(f"Lendo: {arquivo}...")
    try:
        # Tenta ler CSV ou Excel
        if arquivo.endswith('.csv'):
            # Tenta descobrir onde começa o cabeçalho (pula linhas vazias iniciais)
            df = pd.read_csv(arquivo, header=None)
        else:
            df = pd.read_excel(arquivo, header=None)
            
        # Acha a linha de cabeçalho (onde tem 'NOME')
        header_row_idx = -1
        for idx, row in df.iterrows():
            row_str = row.astype(str).str.upper().values
            if any("NOME" in str(x) for x in row_str):
                header_row_idx = idx
                break
        
        if header_row_idx == -1:
            print(f" -> Pulei (não achei cabeçalho): {arquivo}")
            continue

        # Recarrega o arquivo usando o cabeçalho correto
        if arquivo.endswith('.csv'):
            df = pd.read_csv(arquivo, header=header_row_idx)
        else:
            df = pd.read_excel(arquivo, header=header_row_idx)

        # Identifica colunas
        c_nome = encontrar_coluna(df, col_map['nome'])
        c_adm = encontrar_coluna(df, col_map['admissao'])
        c_saida = encontrar_coluna(df, col_map['saida'])
        c_motivo = encontrar_coluna(df, col_map['motivo'])
        c_setor = encontrar_coluna(df, col_map['setor'])

        if not c_nome or not c_adm:
            print(f" -> Colunas obrigatórias não encontradas em {arquivo}")
            continue

        # Itera sobre as linhas do arquivo
        for index, row in df.iterrows():
            nome = normalizar_texto(row[c_nome])
            if not nome or "TOTAL" in nome: continue # Pula linhas de totais/vazias

            adm = formatar_data(row[c_adm])
            if not adm: continue # Sem admissão não tem como cadastrar

            # Dados opcionais
            saida = formatar_data(row[c_saida]) if c_saida else ''
            motivo = normalizar_texto(row[c_motivo]) if c_motivo else ''
            setor = normalizar_texto(row[c_setor]) if c_setor else 'UTIN' # Padrão UTIN se não tiver
            
            # Limpeza fina do motivo
            if "NAN" in motivo: motivo = ""

            # CHAVE ÚNICA: Nome + Admissão identifica o paciente único
            chave = (nome, adm)

            if chave not in pacientes_db:
                # Se não existe, cria
                pacientes_db[chave] = {
                    'nome': nome,
                    'setor': setor,
                    'admissao': adm,
                    'saida': saida,
                    'motivo': motivo
                }
            else:
                # Se JÁ EXISTE (veio de mês anterior), ATUALIZA apenas se tiver dados novos
                # Ex: Em Jan ele não tinha saída, em Fev ele tem. Atualizamos.
                if saida and not pacientes_db[chave]['saida']:
                    pacientes_db[chave]['saida'] = saida
                    pacientes_db[chave]['motivo'] = motivo
                
                # Atualiza motivo se o novo for mais detalhado
                if motivo and not pacientes_db[chave]['motivo']:
                    pacientes_db[chave]['motivo'] = motivo

    except Exception as e:
        print(f"Erro ao ler {arquivo}: {e}")

# Converte dicionário para lista
lista_final = list(pacientes_db.values())

# Ordena por data
lista_final.sort(key=lambda x: x['admissao'])

# Salva o arquivo final
nome_arquivo_final = 'BACKUP_COMPLETO_HISTORICO.json'
with open(nome_arquivo_final, 'w', encoding='utf-8') as f:
    json.dump(lista_final, f, ensure_ascii=False, indent=4)

print("-" * 30)
print(f"CONCLUÍDO! {len(lista_final)} pacientes únicos consolidados.")
print(f"Arquivo gerado: {nome_arquivo_final}")