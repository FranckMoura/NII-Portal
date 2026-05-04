import pandas as pd
import re
from supabase import create_client, Client

# =====================================================================
# 1. CONFIGURAÇÕES PRINCIPAIS
# =====================================================================
URL = "https://voweywtzoldwfhgkniup.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
supabase: Client = create_client(URL, KEY)

# 👇 Mude o nome do arquivo aqui toda vez que for subir uma nova competência
ARQUIVO_CSV = 'R_INTERNACOESMEDICO_ABRIL.csv' 
# =====================================================================

parsed_data = []
current_doctor = "NÃO IDENTIFICADO"

print(f"Iniciando a extração do arquivo: {ARQUIVO_CSV}...")

# --- 2. LEITURA E LIMPEZA DINÂMICA DO CSV ---
try:
    with open(ARQUIVO_CSV, 'r', encoding='latin1') as f:
        for line in f:
            line = line.strip()
            
            if not line or line.startswith('Atendimento') or line.startswith('Total do M') or line.startswith('Total do conv'):
                continue
                
            parts = line.split(',')
            partes_validas = [p.strip() for p in parts if p.strip() != ""]
            
            if not partes_validas:
                continue

            if "Médico:" in line or "M\xe9dico:" in line: 
                current_doctor = "NÃO IDENTIFICADO"
                for p in partes_validas:
                    if len(p) > 5 and not p.isdigit() and "Médico" not in p:
                        current_doctor = p
                        break
                         
            elif "SUS - INTERNA" in line.upper():
                atendimento = ""
                paciente = ""
                idade = ""
                dt_internacao = ""
                plano = "PLANO UNICO" 
                
                for i, p in enumerate(partes_validas):
                    if p.isdigit() and len(p) >= 5 and atendimento == "":
                        atendimento = p
                        if i + 1 < len(partes_validas):
                            paciente = partes_validas[i+1]
                        break
                
                if not paciente or re.search(r'\d+a\s+\d+m', paciente) or re.search(r'\d{2}/\d{2}/\d{4}', paciente) or "SUS" in paciente.upper():
                    for p in partes_validas:
                        if p != atendimento and not p.isdigit() and not re.search(r'\d+a\s+\d+m', p) and not re.search(r'\d{2}/\d{2}/\d{4}', p) and "SUS" not in p.upper() and "PLANO" not in p.upper() and "FILA" not in p.upper():
                            paciente = p
                            break
                            
                for p in partes_validas:
                    if 'a ' in p and 'm ' in p and 'd' in p:
                        idade = p
                        break
                        
                match = re.search(r'\d{2}/\d{2}/\d{4}', line)
                dt_internacao = match.group(0) if match else ""
                
                linha_upper = line.upper()
                if "FILA ZERO" in linha_upper:
                    plano = "FILA ZERO"
                elif "PLANO UNICO" in linha_upper or "PLANO ÚNICO" in linha_upper:
                    plano = "PLANO UNICO"
                
                parsed_data.append({
                    "medico": current_doctor,
                    "atendimento": atendimento,
                    "paciente": paciente,
                    "idade": idade,
                    "dt_internacao": dt_internacao,
                    "plano": plano
                })
                
except FileNotFoundError:
    print(f"❌ ERRO: O arquivo '{ARQUIVO_CSV}' não foi encontrado na pasta.")
    print("Verifique se o nome está correto ou se você colou ele na mesma pasta do script.")
    exit()
except Exception as e:
    print(f"❌ Erro Crítico ao ler o arquivo: {e}")
    exit()

print(f"Sucesso! {len(parsed_data)} internações lidas e formatadas.")

# --- 3. ENVIO PARA O SUPABASE (COM LÓGICA ANTI-DUPLICAÇÃO) ---
if len(parsed_data) > 0:
    print("Limpando possíveis duplicações deste arquivo na base...")
    
    # Extrai apenas os números de atendimento deste CSV
    atendimentos = [item['atendimento'] for item in parsed_data if item['atendimento']]
    
    # Apaga na base qualquer registro que tenha esses mesmos atendimentos
    if atendimentos:
        batch_size_del = 100
        for i in range(0, len(atendimentos), batch_size_del):
            lote = atendimentos[i : i + batch_size_del]
            supabase.table('internacoes_planos').delete().in_('atendimento', lote).execute()

    print("Enviando dados para a nuvem e adicionando ao histórico...")
    batch_size = 100
    for i in range(0, len(parsed_data), batch_size):
        batch = parsed_data[i : i + batch_size]
        supabase.table('internacoes_planos').insert(batch).execute()
    
    print("✅ Automação concluída! Histórico atualizado sem duplicações.")
else:
    print("Nenhum dado válido de internação foi encontrado no arquivo.")