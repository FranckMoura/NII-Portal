import os
import re
import pdfplumber
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

print("==========================================================")
print(" 🏥 PROCESSADOR SOULMV V2 (Leitura Direta de PDFs)")
print("==========================================================")

# --- CREDENCIAIS SUPABASE (NII / Santa Helena) ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Conectado ao Supabase (NII).")
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

PASTA_PDFS = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\relatorios_soulmv"

if not os.path.exists(PASTA_PDFS):
    os.makedirs(PASTA_PDFS)
    print(f"⚠️ Pasta criada: {PASTA_PDFS}. Coloque os PDFs lá e rode novamente.")
    exit()

def calcular_permanencia(dt_int, dt_alta):
    try:
        d1 = datetime.strptime(dt_int, "%d/%m/%Y")
        d2 = datetime.strptime(dt_alta, "%d/%m/%Y")
        dias = (d2 - d1).days
        return dias if dias > 0 else 1
    except:
        return 1

def mapear_clinica(texto):
    t = texto.upper()
    if 'CIRURG' in t: return 'Clínica Cirúrgica'
    if 'OBSTETR' in t or 'MATERNIDADE' in t: return 'Obstetrícia'
    if 'PEDIATR' in t: return 'Pediatria'
    return 'Clínica Médica'

def extrair_competencia(nome_arquivo):
    # Procura o MMYY no final do nome (ex: 0226.pdf -> 2026-02)
    match = re.search(r'(\d{2})(\d{2})\.pdf', nome_arquivo, re.IGNORECASE)
    if match:
        mes = match.group(1)
        ano = "20" + match.group(2)
        return f"{ano}-{mes}"
    return None

arquivos = os.listdir(PASTA_PDFS)
pdfs_pacientes = [f for f in arquivos if 'PACIENTE' in f.upper() and f.endswith('.pdf')]
pdfs_receita = [f for f in arquivos if 'PREV_REC' in f.upper() and f.endswith('.pdf')]

# =========================================================================
# 1. PROCESSAR PACIENTES (Para calcular as Metas e o TMP)
# =========================================================================
if pdfs_pacientes:
    print(f"\n>> Encontrados {len(pdfs_pacientes)} relatórios de Pacientes.")
    for arquivo in pdfs_pacientes:
        caminho = os.path.join(PASTA_PDFS, arquivo)
        competencia = extrair_competencia(arquivo)
        if not competencia: continue
        
        print(f"📄 Lendo {arquivo} (Competência: {competencia})...")
        pacientes_lidos = []
        clinica_atual = "Clínica Médica"
        
        with pdfplumber.open(caminho) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()
                if not texto: continue
                
                linhas = texto.split('\n')
                for linha in linhas:
                    # Deteta a mudança de Clínica (ex: "01 CIRURGICO")
                    if re.search(r'^\d{2}\s+(CIRURGICO|CLINICO|OBSTETRICOS|PEDIATRICO)', linha):
                        clinica_atual = mapear_clinica(linha)
                        continue
                    
                    # Deteta a linha do paciente (Começa com 13 números e tem 2 datas)
                    match = re.search(r'^(\d{13})\s+(.*?)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.*)', linha)
                    if match:
                        aih = match.group(1)
                        meio = match.group(2) # Tem o ID, Nome e Prontuário misturados
                        dt_int = match.group(3)
                        dt_alt = match.group(4)
                        procedimento = match.group(5).strip()
                        
                        # Limpa os números do nome do paciente
                        nome = " ".join([p for p in meio.split() if not p.isdigit()]).strip()
                        if len(nome) < 3: continue
                        
                        pacientes_lidos.append({
                            "competencia": competencia,
                            "nr_aih": aih,
                            "paciente": nome,
                            "clinica": clinica_atual,
                            "dt_internacao": datetime.strptime(dt_int, "%d/%m/%Y").strftime("%Y-%m-%d"),
                            "dt_alta": datetime.strptime(dt_alt, "%d/%m/%Y").strftime("%Y-%m-%d"),
                            "permanencia": calcular_permanencia(dt_int, dt_alt),
                            "procedimento": procedimento
                        })
        
        if pacientes_lidos:
            # Apaga dados velhos desse mês e insere os novos
            supabase.table('faturamento_analitico').delete().eq('competencia', competencia).execute()
            
            for i in range(0, len(pacientes_lidos), 500):
                lote = pacientes_lidos[i:i+500]
                supabase.table('faturamento_analitico').insert(lote).execute()
            print(f"   ✅ {len(pacientes_lidos)} pacientes guardados no banco!")

# =========================================================================
# 2. PROCESSAR UTI (Relatório de Receita Global)
# =========================================================================
if pdfs_receita:
    print(f"\n>> Encontrados {len(pdfs_receita)} relatórios de Previsão de Receita (UTI).")
    for arquivo in pdfs_receita:
        caminho = os.path.join(PASTA_PDFS, arquivo)
        competencia = extrair_competencia(arquivo)
        if not competencia: continue
        
        print(f"📄 Lendo {arquivo}...")
        utis_encontradas = []
        clinica_atual = "Clínica Médica"
        
        with pdfplumber.open(caminho) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()
                if not texto: continue
                
                linhas = texto.split('\n')
                for linha in linhas:
                    # Pega o nome da especialidade
                    if re.search(r'Especialidade:\s*\d+\s+(.*)', linha):
                        clinica_atual = mapear_clinica(linha)
                    
                    # Procura a linha que diz "UTI Especializada" e os seus valores
                    match = re.search(r'UTI Especializada\s+(\d+)\s+([\d\.,]+)', linha)
                    if match:
                        qtd = int(match.group(1))
                        valor_str = match.group(2).replace('.', '').replace(',', '.')
                        valor = float(valor_str)
                        
                        utis_encontradas.append({
                            "competencia": competencia,
                            "indicador": "Diárias UTI",
                            "clinica": clinica_atual,
                            "quantidade": qtd,
                            "valor": valor
                        })
                        
        if utis_encontradas:
            # Limpa UTIs antigas deste mês para não duplicar
            supabase.table('indicadores_metas').delete().eq('competencia', competencia).eq('indicador', 'Diárias UTI').execute()
            supabase.table('indicadores_metas').insert(utis_encontradas).execute()
            print(f"   ✅ {len(utis_encontradas)} registos de UTI atualizados!")

print("\n🎉 PROCESSAMENTO CONCLUÍDO! O seu painel de Metas & UTI está atualizado!")