import pandas as pd
import json
import glob
import re
from datetime import datetime

print("--- GERAÇÃO DO CENSO (CORREÇÃO DE TRANSFERÊNCIAS) ---")

def formatar_data_hsh(data):
    if pd.isna(data) or str(data).strip() == '' or str(data).strip() == '-': return ''
    texto = str(data).strip().replace('.', '/')
    match = re.search(r'\d{2}/\d{2}/\d{2,4}', texto)
    if match: texto = match.group()
    try:
        dt = pd.to_datetime(texto, dayfirst=True)
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
        df = pd.read_excel(xls, sheet_name=aba, header=None)
        setor_atual = 'UTIN' 
        
        for index, row in df.iterrows():
            linha_texto = " ".join([str(x).upper() for x in row.values])
            
            # 1. Detector de Setor
            if 'UCINCO' in linha_texto or 'MÉDIO RISCO' in linha_texto:
                setor_atual = 'UCINCO'
                continue
            elif 'UCINCA' in linha_texto or 'CANGURU' in linha_texto:
                setor_atual = 'UCINCA'
                continue
            elif 'UTI NEONATAL' in linha_texto and "HOSPITAL" not in linha_texto:
                setor_atual = 'UTIN'

            # 2. Detector de Paciente
            try:
                nome = normalizar(row[1]) 
                
                # Filtros de Lixo
                if not nome or len(nome) < 4: continue
                eh_lixo = False
                for palavra in BLACKLIST:
                    if palavra in nome:
                        eh_lixo = True; break
                if eh_lixo: continue

                # Validação de Data
                adm = formatar_data_hsh(row[2])
                if not adm: continue 

                saida = formatar_data_hsh(row[3]) 
                motivo = normalizar(row[4])
                if motivo == 'NAN': motivo = ''

                # --- A CORREÇÃO ESTÁ AQUI ---
                # Agora a chave inclui o SETOR. 
                # Se o João estava na UTIN e foi pra UCINCO, serão 2 registros diferentes.
                chave = (nome, adm, setor_atual) 

                if chave not in pacientes_db:
                    pacientes_db[chave] = {
                        'nome': nome,
                        'setor': setor_atual,
                        'admissao': adm,
                        'saida': saida,
                        'motivo': motivo
                    }
                else:
                    # Atualiza apenas se for o MESMO registro (mesmo setor)
                    if saida: pacientes_db[chave]['saida'] = saida
                    if motivo: pacientes_db[chave]['motivo'] = motivo

            except Exception:
                continue

    lista_final = list(pacientes_db.values())
    lista_final.sort(key=lambda x: x['admissao'])

    if lista_final:
        nome_arquivo = 'BACKUP_CORRECAO_TRANSF.json'
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(lista_final, f, ensure_ascii=False, indent=4)
        print("="*40)
        print(f"SUCESSO! {len(lista_final)} registros processados.")
        print("Agora as transferências não serão apagadas.")
        print(f"Arquivo gerado: {nome_arquivo}")
    else:
        print("ERRO: Nenhum dado encontrado.")