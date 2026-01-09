import pandas as pd
import json
import os
import glob
import sys
import re

print("--- ✝️ PROCESSADOR DE MORTALIDADE (V3 - EXCEL NATIVO) ---")

# 1. Navegação de Pastas
pasta_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(pasta_script)

pasta_raiz = os.path.dirname(pasta_script)
pasta_destino = os.path.join(pasta_raiz, 'arquivos')
if not os.path.exists(pasta_destino): os.makedirs(pasta_destino)

arquivo_saida = os.path.join(pasta_destino, 'dados_mortalidade.json')

# 2. Busca arquivos Excel (.xlsx)
arquivos = glob.glob("*.xlsx")

# Remove arquivos temporários do Excel (começam com ~$)
arquivos = [f for f in arquivos if not os.path.basename(f).startswith('~$')]

if not arquivos:
    print("❌ Nenhum arquivo .xlsx encontrado na pasta atual!")
    print(f"   Pasta: {pasta_script}")
    sys.exit()

dados_consolidados = []

def formatar_data(str_data):
    """Converte dd/mm/aaaa ou datetime para formatos úteis"""
    try:
        # Se vier formato datetime do Excel
        if isinstance(str_data, pd.Timestamp) or hasattr(str_data, 'strftime'):
            d = str_data.day
            m = str_data.month
            y = str_data.year
            return f"{y}-{m:02d}-{d:02d}", f"{d:02d}/{m:02d}/{y}", f"{m:02d}/{y}"
        
        # Se vier string
        str_data = str(str_data).strip()
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', str_data)
        if match:
            d, m, y = match.groups()
            return f"{y}-{m}-{d}", f"{d}/{m}/{y}", f"{m}/{y}"
    except: pass
    return None, None, None

for arquivo in arquivos:
    print(f"📄 Lendo Excel: {arquivo}...")
    
    try:
        # Lê o Excel sem cabeçalho (header=None) para pegar a estrutura crua
        df = pd.read_excel(arquivo, header=None, dtype=str)
        
        count_linhas = 0
        
        # Itera sobre as linhas do Excel
        for index, row in df.iterrows():
            # Limpeza: Pega apenas células preenchidas da linha
            # Remove NaNs, Nones e strings vazias
            colunas_uteis = []
            for x in row.values:
                val_str = str(x).strip()
                if pd.notna(x) and val_str != '' and val_str.lower() != 'nan':
                    colunas_uteis.append(val_str)
            
            # Validação básica de estrutura de linha de óbito do SoulMV
            # Precisa ter pelo menos: Nome, Idade, Alguma Data, Unidade
            if len(colunas_uteis) < 8: continue

            # Procura datas na linha para identificar se é um registro válido
            datas = []
            for c in colunas_uteis:
                # Verifica formato dd/mm/aaaa ou se parece timestamp string
                if re.match(r'\d{2}/\d{2}/\d{4}', c) or '00:00:00' in c:
                    datas.append(c)
            
            # Se não tem data, não é linha de paciente
            if not datas: continue

            # Lógica de Datas:
            # 1ª Data = Internação
            # 2ª Data = Óbito (Geralmente)
            dt_obito_raw = datas[-1] # Pega a última data encontrada na linha (geralmente é o óbito)
            
            iso_date, fmt_date, mes_ref = formatar_data(dt_obito_raw)
            if not iso_date: continue

            # --- EXTRAÇÃO DE DADOS ---
            # Baseado na sequência visual do relatório SoulMV:
            # [0] Atendimento
            # [1] Prontuário
            # [2] Nome (Texto longo sem números)
            # [3] Idade (Número < 130)
            
            nome = "Desconhecido"
            idade = 0
            unidade = "Geral"
            medico = "-"
            cid = "-"
            cid_desc = "-"

            # Tenta pegar Nome (Geralmente índice 2)
            if len(colunas_uteis) > 2: nome = colunas_uteis[2]

            # Tenta pegar Idade (Geralmente índice 3 ou 4)
            for item in colunas_uteis[3:6]:
                if item.isdigit() and int(item) < 130:
                    idade = int(item)
                    break
            
            # Tenta achar Unidade (Procura palavras chaves ou pega posição relativa)
            # Geralmente está depois do médico.
            # Vamos procurar strings conhecidas ou pegar pelo índice 6
            possiveis_unidades = [u for u in colunas_uteis if "UTI" in u or "ANDAR" in u or "NEONATAL" in u]
            if possiveis_unidades:
                unidade = possiveis_unidades[0]
            elif len(colunas_uteis) > 6:
                unidade = colunas_uteis[6]

            # Médico (Geralmente antes da unidade ou índice 5)
            if len(colunas_uteis) > 5 and colunas_uteis[5] != unidade:
                medico = colunas_uteis[5]

            # CID (Geralmente penúltimo item, antes do "Sim")
            # Procura padrão Letra+Numero (Ex: I509)
            for item in reversed(colunas_uteis):
                match_cid = re.search(r'([A-Z]\d{2,4})', item)
                if match_cid and len(item) < 100: # CID + Descrição
                    cid_desc = item
                    cid = match_cid.group(1)
                    break
            
            # Filtra cabeçalhos que podem ter sido lidos
            if "Paciente" in nome or "Idade" in str(idade): continue

            dados_consolidados.append({
                "data_iso": iso_date,
                "data_fmt": fmt_date,
                "mes_ref": mes_ref,
                "paciente": nome,
                "idade": idade,
                "unidade": unidade,
                "medico": medico,
                "cid": cid,
                "cid_desc": cid_desc
            })
            count_linhas += 1
            
        print(f"   -> {count_linhas} óbitos extraídos.")

    except Exception as e:
        print(f"   ⚠️ Erro ao ler {arquivo}: {e}")

# Ordena do mais recente para o antigo
dados_consolidados.sort(key=lambda x: x['data_iso'] or "", reverse=True)

# Salva JSON
with open(arquivo_saida, 'w', encoding='utf-8') as f:
    json.dump(dados_consolidados, f, indent=4, ensure_ascii=False)

print("\n" + "="*40)
print(f"✅ SUCESSO! JSON gerado: {len(dados_consolidados)} registros.")
print(f"📂 Salvo em: {arquivo_saida}")
print("="*40)