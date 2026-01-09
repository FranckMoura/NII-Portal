import pandas as pd
import json
import os
import csv
import re
import sys

print("--- 🏥 PROCESSADOR DE TABELA UNIFICADA (SIGTAP + OPME) ---")

# --- CORREÇÃO DE CAMINHOS ---
# Pega a pasta onde o script está rodando (pasta 'sigtap')
pasta_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(pasta_script)

# Arquivos de entrada (estão na mesma pasta do script/sigtap)
ARQUIVO_PROCEDIMENTOS = 'R_SUB_GRU_PROC_P321.csv'
ARQUIVO_COMPATIBILIDADE = 'R_COMPATIBILIDADE_PROTESE.csv'

# Arquivo de saída (tem que voltar um nível e entrar em 'arquivos')
# os.path.dirname(pasta_script) pega a pasta "mãe" (NII-Portal-1)
pasta_raiz = os.path.dirname(pasta_script)
pasta_destino = os.path.join(pasta_raiz, 'arquivos')

# Garante que a pasta destino existe
if not os.path.exists(pasta_destino):
    print(f"📂 Criando pasta {pasta_destino}...")
    os.makedirs(pasta_destino)

ARQUIVO_SAIDA = os.path.join(pasta_destino, 'tabela_unificada.json')

print(f"📂 Lendo de: {pasta_script}")
print(f"📂 Salvando em: {pasta_destino}")

def limpar_valor(v):
    """Converte '1.234,56' para float 1234.56"""
    if pd.isna(v) or v == '': return 0.0
    if isinstance(v, (int, float)): return float(v)
    try:
        return float(str(v).replace('.', '').replace(',', '.'))
    except: return 0.0

# --- ETAPA 1: Ler Compatibilidades (OPME) ---
print("1. Processando compatibilidades de Próteses...")
opme_dict = {}
current_proc = None

try:
    with open(ARQUIVO_COMPATIBILIDADE, 'r', encoding='latin1') as f:
        leitor = csv.reader(f)
        for linha in leitor:
            cols = [c.strip() for c in linha]
            
            # Identifica Procedimento
            code_candidate = cols[1] if len(cols) > 1 else ""
            if len(code_candidate) == 10 and code_candidate.isdigit():
                current_proc = code_candidate
                if current_proc not in opme_dict:
                    opme_dict[current_proc] = []
                continue
                
            # Identifica Prótese
            if current_proc:
                prot_code = ""
                prot_desc = ""
                prot_val = 0.0
                
                for i in range(2, len(cols)-2):
                    if len(cols[i]) == 10 and cols[i].isdigit() and cols[i].startswith('07'):
                        prot_code = cols[i]
                        for j in range(i+1, len(cols)):
                            if len(cols[j]) > 5 and not cols[j][0].isdigit():
                                prot_desc = cols[j]
                                break
                        for k in range(j, len(cols)):
                            if re.match(r'^\d{1,3}(\.\d{3})*,\d{2}$', cols[k]):
                                prot_val = limpar_valor(cols[k])
                                break
                        break
                
                if prot_code:
                    opme_dict[current_proc].append({
                        "codigo": prot_code,
                        "nome": prot_desc,
                        "valor": prot_val
                    })
except FileNotFoundError:
    print(f"❌ Erro: Arquivo {ARQUIVO_COMPATIBILIDADE} não encontrado na pasta sigtap.")
    sys.exit()

print(f"   -> Encontradas compatibilidades para {len(opme_dict)} procedimentos.")

# --- ETAPA 2: Ler Tabela de Procedimentos ---
print("2. Lendo Tabela Mestra de Procedimentos...")

try:
    try:
        df = pd.read_csv(ARQUIVO_PROCEDIMENTOS, encoding='latin1', header=1, dtype=str)
    except:
        df = pd.read_csv(ARQUIVO_PROCEDIMENTOS, encoding='latin1', header=0, dtype=str)
except FileNotFoundError:
    print(f"❌ Erro: Arquivo {ARQUIVO_PROCEDIMENTOS} não encontrado na pasta sigtap.")
    sys.exit()

dados_finais = []

for index, row in df.iterrows():
    cod_proc = None
    desc_proc = None
    val_amb = 0.0
    val_hosp = 0.0
    val_sp = 0.0
    
    vals = row.values
    for i, v in enumerate(vals):
        v_str = str(v).strip()
        if not cod_proc and len(v_str) == 10 and v_str.isdigit():
            cod_proc = v_str
            if i+2 < len(vals): desc_proc = str(vals[i+6]).strip() if pd.notna(vals[i+6]) else "" 
            
            try:
                money_cols = [x for x in vals[i:] if isinstance(x, str) and ',' in x]
                if len(money_cols) >= 3:
                    val_hosp = limpar_valor(money_cols[1]) 
                    val_sp = limpar_valor(money_cols[2])   
            except: pass
            break
    
    if cod_proc:
        compativeis = opme_dict.get(cod_proc, [])
        total = val_hosp + val_sp
        
        dados_finais.append({
            "codigo": cod_proc,
            "procedimento": desc_proc,
            "valor_sh": val_hosp,
            "valor_sp": val_sp,
            "valor_total": total,
            "compatibilidades": compativeis,
            "qtd_opme": len(compativeis)
        })

# Salva JSON na pasta correta (Raiz/arquivos)
with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
    json.dump(dados_finais, f, indent=4, ensure_ascii=False)

print(f"\n✅ SUCESSO! JSON gerado em: {ARQUIVO_SAIDA}")
print(f"   Total de Procedimentos: {len(dados_finais)}")