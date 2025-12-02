import pandas as pd
import json
import glob
import re
from datetime import datetime

print("--- INICIANDO GERAÇÃO DO CENSO (HIERÁRQUICO) ---")

# --- FUNÇÕES DE LIMPEZA ---
def formatar_data_hsh(data):
    if pd.isna(data) or str(data).strip() == '' or str(data).strip() == '-': return ''
    texto = str(data).strip().replace('.', '/')
    
    # Limpa texto extra caso tenha
    match = re.search(r'\d{2}/\d{2}/\d{2,4}', texto)
    if match: texto = match.group()

    try:
        dt = pd.to_datetime(texto, dayfirst=True)
        # Corrige anos errados (ex: 2028 vira 2025)
        if dt.year > 2025: dt = dt.replace(year=2025) 
        if dt.year < 2020: dt = dt.replace(year=2025)
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def normalizar(txt):
    if pd.isna(txt): return ""
    return str(txt).upper().strip()

# --- PROCESSAMENTO PRINCIPAL ---
pacientes_db = {}
arquivos = glob.glob("*.xlsx")

if not arquivos:
    print("ERRO: Não achei nenhum arquivo Excel (.xlsx) na pasta.")
    print("Certifique-se que sua planilha de dados está na mesma pasta deste script.")
else:
    arquivo_alvo = arquivos[0]
    print(f"Lendo arquivo: {arquivo_alvo}")
    
    xls = pd.ExcelFile(arquivo_alvo)
    
    for aba in xls.sheet_names:
        print(f" -> Lendo aba: {aba}")
        
        # Lê a aba sem cabeçalho para pegar os títulos de setor no meio
        df = pd.read_excel(xls, sheet_name=aba, header=None)
        
        # Define setor padrão inicial
        setor_atual = 'UTIN' 
        
        for index, row in df.iterrows():
            # Converte linha para texto para procurar "UCINCO", "UCINCA"
            linha_texto = " ".join([str(x).upper() for x in row.values])
            
            # 1. IDENTIFICA MUDANÇA DE SETOR
            if 'UCINCO' in linha_texto or 'MÉDIO RISCO' in linha_texto:
                setor_atual = 'UCINCO'
                continue 
            
            elif 'UCINCA' in linha_texto or 'CANGURU' in linha_texto:
                setor_atual = 'UCINCA'
                continue
            
            elif 'UTI NEONATAL' in linha_texto and "HOSPITAL" not in linha_texto:
                setor_atual = 'UTIN'

            # 2. IDENTIFICA PACIENTE
            # Baseado no seu print: Coluna B (1) = Nome, Coluna C (2) = Data
            try:
                if len(row) < 3: continue # Linha muito curta

                nome = normalizar(row[1]) 
                data_str = normalizar(row[2])
                
                # Filtros para ignorar lixo
                if "USUÁRIO" in nome or "PACIENTE" in nome: continue
                if not nome or len(nome) < 4: continue
                if "TOTAL" in nome: continue
                
                # Verifica se tem data válida
                adm = formatar_data_hsh(row[2])
                if not adm: continue 

                # Captura dados
                saida = formatar_data_hsh(row[3]) 
                motivo = normalizar(row[4])
                if motivo == 'NAN': motivo = ''

                chave = (nome, adm)

                # Regra de salvamento
                if chave not in pacientes_db:
                    pacientes_db[chave] = {
                        'nome': nome,
                        'setor': setor_atual, # Aqui ele usa o setor que detectou acima!
                        'admissao': adm,
                        'saida': saida,
                        'motivo': motivo
                    }
                else:
                    # Atualiza se já existe
                    if saida: pacientes_db[chave]['saida'] = saida
                    if motivo: pacientes_db[chave]['motivo'] = motivo
                    # Prioriza setor específico se antes estava genérico
                    if setor_atual != 'UTIN':
                        pacientes_db[chave]['setor'] = setor_atual

            except Exception:
                continue

    # --- GERAÇÃO DO ARQUIVO FINAL ---
    lista_final = list(pacientes_db.values())
    lista_final.sort(key=lambda x: x['admissao'])

    nome_arquivo_json = 'BACKUP_FINAL_HIERARQUICO.json'

    if lista_final:
        with open(nome_arquivo_json, 'w', encoding='utf-8') as f:
            json.dump(lista_final, f, ensure_ascii=False, indent=4)
        print("="*40)
        print("SUCESSO! O arquivo foi gerado.")
        print(f"Total de pacientes recuperados: {len(lista_final)}")
        print(f"Nome do arquivo: {nome_arquivo_json}")
    else:
        print("ERRO: Nenhum paciente encontrado. Verifique se o Excel está na pasta.")