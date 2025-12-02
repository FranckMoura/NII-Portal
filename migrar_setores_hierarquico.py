import pandas as pd
import json
import glob
import re
from datetime import datetime

print("--- INICIANDO MIGRAÇÃO COM LEITURA DE CABEÇALHOS (HIERÁRQUICO) ---")

# Função para limpar e padronizar datas (04.12.24 -> 2024-12-04)
def formatar_data_hsh(data):
    if pd.isna(data) or str(data).strip() == '' or str(data).strip() == '-': return ''
    texto = str(data).strip().replace('.', '/')
    
    # Remove textos extras se houver (ex: " alta")
    match = re.search(r'\d{2}/\d{2}/\d{2,4}', texto)
    if match: texto = match.group()

    try:
        dt = pd.to_datetime(texto, dayfirst=True)
        # Trava de segurança para anos errados
        if dt.year > 2025: dt = dt.replace(year=2025) 
        if dt.year < 2020: dt = dt.replace(year=2025)
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def normalizar(txt):
    if pd.isna(txt): return ""
    return str(txt).upper().strip()

pacientes_db = {}
arquivos = glob.glob("*.xlsx")

if not arquivos:
    print("ERRO: Nenhum arquivo Excel encontrado.")
else:
    arquivo_alvo = arquivos[0]
    print(f"Lendo arquivo mestre: {arquivo_alvo}")
    
    xls = pd.ExcelFile(arquivo_alvo)
    
    for aba in xls.sheet_names:
        print(f" -> Processando aba: {aba}")
        
        # Lê a aba inteira, SEM cabeçalho definido (header=None)
        # Isso nos permite ler as linhas de título que estão soltas no meio
        df = pd.read_excel(xls, sheet_name=aba, header=None)
        
        # Define o setor inicial padrão como UTIN
        setor_atual = 'UTIN' 
        
        # Vamos varrer linha por linha
        for index, row in df.iterrows():
            # Transforma a linha inteira em texto para procurar palavras-chave
            linha_texto = " ".join([str(x).upper() for x in row.values])
            
            # --- 1. DETECTOR DE TÍTULO DE SETOR ---
            # Se encontrar essas palavras, muda a "chave" do setor atual
            if 'UCINCO' in linha_texto or 'MÉDIO RISCO' in linha_texto or 'MEDIO RISCO' in linha_texto:
                setor_atual = 'UCINCO'
                # print(f"    [!] Mudou setor para UCINCO na linha {index}")
                continue # Pula para próxima linha
            
            elif 'UCINCA' in linha_texto or 'CANGURU' in linha_texto:
                setor_atual = 'UCINCA'
                # print(f"    [!] Mudou setor para UCINCA na linha {index}")
                continue
            
            elif 'UTI NEONATAL' in linha_texto or 'INTENSIVA' in linha_texto:
                # Cuidado para não resetar se for só o cabeçalho do hospital
                # Mas geralmente se aparecer UTIN explicitamente no meio, é mudança
                if "HOSPITAL" not in linha_texto: 
                    setor_atual = 'UTIN'

            # --- 2. DETECTOR DE PACIENTE ---
            # Baseado no seu print, a coluna B (índice 1) tem o NOME
            # E a coluna C (índice 2) tem a DATA ADMISSÃO
            try:
                nome_potencial = normalizar(row[1]) # Coluna B
                data_potencial = normalizar(row[2]) # Coluna C
                
                # Validações para saber se é paciente mesmo:
                # 1. Não pode ser cabeçalho ("USUÁRIO")
                # 2. Tem que ter nome
                # 3. Tem que ter data válida ou parecer data
                if "USUÁRIO" in nome_potencial or "PACIENTE" in nome_potencial: continue
                if not nome_potencial or len(nome_potencial) < 4: continue
                if "TOTAL" in nome_potencial: continue
                
                # Tenta formatar a data para ver se é válida
                adm = formatar_data_hsh(row[2])
                if not adm: continue # Se não tem data, não é paciente

                # Se passou por tudo isso, É UM PACIENTE!
                saida = formatar_data_hsh(row[3]) # Coluna D (Saída)
                motivo = normalizar(row[4]) # Coluna E (Motivo)
                if motivo == 'NAN': motivo = ''

                chave = (nome_potencial, adm)

                # Salva no banco de dados
                if chave not in pacientes_db:
                    pacientes_db[chave] = {
                        'nome': nome_potencial,
                        'setor': setor_atual, # Usa o setor que detectamos no passo 1
                        'admissao': adm,
                        'saida': saida,
                        'motivo': motivo
                    }
                else:
                    # Atualiza dados se já existir
                    if saida: pacientes_db[chave]['saida'] = saida
                    if motivo: pacientes_db[chave]['motivo'] = motivo
                    # Se o setor atual for diferente de UTIN, atualiza (prioridade para UCINCO/A)
                    if setor_atual != 'UTIN':
                        pacientes_db[chave]['setor'] = setor_atual

            except Exception as e:
                # Erro de leitura na linha, ignora
                continue

    # --- SALVAR ---
    lista_final = list(pacientes_db.values())
    lista_final.sort(key=lambda x: x['admissao'])

    if lista_final:
        with open('BACKUP_FINAL_HIERARQUICO.json', 'w', encoding='utf-8') as f:
            json.dump(lista_final, f, ensure_ascii=False, indent=4)
        print("="*40)
        print(f"SUCESSO! {len(lista_final)} pacientes processados.")
        print("Setores identificados dinamicamente.")
        print("Use o arquivo 'BACKUP_FINAL_HIERARQUICO.json'.")
    else:
        print("Nenhum paciente encontrado. Verifique os índices das colunas.")