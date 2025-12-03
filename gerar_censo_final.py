import pandas as pd
import json
import glob
import re
from datetime import datetime

print("--- INICIANDO GERAÇÃO DO CENSO (COM FILTRO DE ENFERMEIRAS) ---")

# --- FUNÇÕES ---
def formatar_data_hsh(data):
    if pd.isna(data) or str(data).strip() == '' or str(data).strip() == '-': return ''
    texto = str(data).strip().replace('.', '/')
    
    # Tenta limpar texto que venha junto com a data
    match = re.search(r'\d{2}/\d{2}/\d{2,4}', texto)
    if match: texto = match.group()

    try:
        dt = pd.to_datetime(texto, dayfirst=True)
        # Corrige anos (ex: 2028 -> 2025)
        if dt.year > 2025: dt = dt.replace(year=2025) 
        if dt.year < 2020: dt = dt.replace(year=2025)
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def normalizar(txt):
    if pd.isna(txt): return ""
    return str(txt).upper().strip()

# --- EXECUÇÃO ---
pacientes_db = {}
arquivos = glob.glob("*.xlsx")

# Palavras que indicam que a linha NÃO É um paciente
BLACKLIST = [
    "ENFERMEIRA", "ENF.", "ROTINA", "COORDENADORA", "COORD.", 
    "RESPONSÁVEL", "RESPONSAVEL", "USUÁRIO", "PACIENTE", 
    "TOTAL", "DIAS", "OCUPAÇÃO", "VAGAS", "OBS:", "LEITOS"
]

if not arquivos:
    print("ERRO: Nenhum arquivo Excel encontrado.")
else:
    arquivo_alvo = arquivos[0]
    print(f"Lendo arquivo: {arquivo_alvo}")
    
    xls = pd.ExcelFile(arquivo_alvo)
    
    for aba in xls.sheet_names:
        print(f" -> Processando: {aba}")
        
        # Lê a aba inteira sem cabeçalho
        df = pd.read_excel(xls, sheet_name=aba, header=None)
        
        setor_atual = 'UTIN' # Padrão inicial
        
        for index, row in df.iterrows():
            linha_texto = " ".join([str(x).upper() for x in row.values])
            
            # 1. DETECTOR DE SETOR
            if 'UCINCO' in linha_texto or 'MÉDIO RISCO' in linha_texto:
                setor_atual = 'UCINCO'
                continue
            elif 'UCINCA' in linha_texto or 'CANGURU' in linha_texto:
                setor_atual = 'UCINCA'
                continue
            elif 'UTI NEONATAL' in linha_texto and "HOSPITAL" not in linha_texto:
                setor_atual = 'UTIN'

            # 2. DETECTOR DE PACIENTE
            try:
                # Índices baseados no seu arquivo (B=1, C=2, D=3, E=4)
                nome = normalizar(row[1]) 
                
                # --- FILTROS DE LIXO (AQUI ESTÁ A CORREÇÃO) ---
                if not nome or len(nome) < 4: continue
                
                # Verifica se o nome contém palavras proibidas (Enfermeira, etc)
                eh_lixo = False
                for palavra in BLACKLIST:
                    if palavra in nome:
                        eh_lixo = True
                        break
                if eh_lixo: continue

                # --- VALIDAÇÃO POR DATA (CRUCIAL) ---
                # Se não tiver uma data válida na coluna C, NÃO É PACIENTE.
                # Enfermeiras geralmente não têm data de admissão na mesma linha.
                adm = formatar_data_hsh(row[2])
                if not adm: continue 

                # Captura restante
                saida = formatar_data_hsh(row[3]) 
                motivo = normalizar(row[4])
                if motivo == 'NAN': motivo = ''

                chave = (nome, adm)

                # Salva
                if chave not in pacientes_db:
                    pacientes_db[chave] = {
                        'nome': nome,
                        'setor': setor_atual,
                        'admissao': adm,
                        'saida': saida,
                        'motivo': motivo
                    }
                else:
                    if saida: pacientes_db[chave]['saida'] = saida
                    if motivo: pacientes_db[chave]['motivo'] = motivo
                    if setor_atual != 'UTIN':
                        pacientes_db[chave]['setor'] = setor_atual

            except Exception:
                continue

    # --- SALVAR ---
    lista_final = list(pacientes_db.values())
    lista_final.sort(key=lambda x: x['admissao'])

    if lista_final:
        nome_arquivo = 'BACKUP_FINAL_LIMPO.json'
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(lista_final, f, ensure_ascii=False, indent=4)
        print("="*40)
        print("SUCESSO! Enfermeiras e lixo removidos.")
        print(f"Total de pacientes reais: {len(lista_final)}")
        print(f"Arquivo gerado: {nome_arquivo}")
    else:
        print("ERRO: Nenhum paciente encontrado.")