import pdfplumber
import re
import os
import glob
from datetime import datetime, timezone
from supabase import create_client, Client

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def extrair_competencia_arquivo(nome_arquivo):
    # Tenta extrair MMAA do nome (ex: ..._0325.pdf -> 2025-03)
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo.lower())
    if match:
        mes, ano = match.groups()
        return f"20{ano}-{mes}" # Formato YYYY-MM
    return None

def extrair_dados_pdf(caminho_arquivo):
    nome_arq = os.path.basename(caminho_arquivo)
    comp_arquivo = extrair_competencia_arquivo(nome_arq)
    
    print(f"\n📄 Processando: {nome_arq} (Competência: {comp_arquivo})")
    dados_extraidos = []
    
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            clinica_atual = "INDEFINIDA" 
            
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                
                for line in lines:
                    line_upper = line.strip().upper()

                    # --- 1. DETECÇÃO DE CABEÇALHOS ---
                    if "01 CIRURGICO" in line_upper:
                        clinica_atual = "Clínica Cirúrgica"
                        continue
                    if "02 OBSTETRICO" in line_upper: 
                        clinica_atual = "Obstetrícia"
                        continue
                    if "03 CLINICO" in line_upper or "03 CLINICA MEDICA" in line_upper:
                        clinica_atual = "Clínica Médica"
                        continue
                    if "07 PEDIATRIA" in line_upper:
                        clinica_atual = "Pediatria"
                        continue
                    
                    # --- 2. EXTRAÇÃO DE PACIENTE ---
                    if re.match(r'^\d{13}', line_upper):
                        if clinica_atual == "INDEFINIDA": continue

                        parts = line_upper.split()
                        datas = re.findall(r'\d{2}/\d{2}/\d{4}', line_upper)
                        
                        if len(datas) >= 2:
                            dt_int_str = datas[0]
                            dt_alta_str = datas[1]
                            
                            try:
                                aih = parts[0]
                                nome_procedimento = line_upper
                                
                                dt_int = datetime.strptime(dt_int_str, "%d/%m/%Y")
                                dt_alta = datetime.strptime(dt_alta_str, "%d/%m/%Y")
                                
                                permanencia = (dt_alta - dt_int).days
                                if permanencia == 0: permanencia = 1
                                
                                dados_extraidos.append({
                                    "nr_conta": aih,
                                    "nr_aih": aih,
                                    "paciente": "Paciente SoulMV",
                                    "dt_internacao": dt_int.strftime('%Y-%m-%d'),
                                    "dt_alta": dt_alta.strftime('%Y-%m-%d'),
                                    "procedimento": nome_procedimento,
                                    "clinica": clinica_atual,
                                    "status_conta": "Fechada",
                                    "permanencia": permanencia,
                                    "competencia": comp_arquivo, # <--- CAMPO NOVO IMPORTANTE
                                    "updated_at": datetime.now(timezone.utc).isoformat()
                                })
                            except: pass
    except Exception as e:
        print(f"⚠️ Erro ao abrir {nome_arq}: {e}")

    return dados_extraidos

def processar_carga():
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    pasta_pdfs = os.path.join(pasta_script, "pacientes")
    
    if not os.path.exists(pasta_pdfs):
        print(f"❌ A pasta '{pasta_pdfs}' não existe.")
        return

    arquivos = glob.glob(os.path.join(pasta_pdfs, "R_PACIENTE_ESPEC_SUS_*.pdf"))
    
    if not arquivos:
        print("❌ Nenhum PDF encontrado.")
        return
    
    print(f"✅ Encontrados {len(arquivos)} PDFs.")
    
    todos_registros = []
    for arq in arquivos:
        registros = extrair_dados_pdf(arq)
        todos_registros.extend(registros)
        
    print(f"\n🔄 Total extraído: {len(todos_registros)}")
    
    if len(todos_registros) > 0:
        print("\n☁️ Enviando para Supabase...")
        
        # Opcional: Limpar tabela para garantir integridade
        # supabase.table("faturamento_analitico").delete().gt("id", 0).execute()

        batch_size = 100
        erros = 0
        for i in range(0, len(todos_registros), batch_size):
            batch = todos_registros[i:i + batch_size]
            try:
                supabase.table("faturamento_analitico").upsert(batch, on_conflict="nr_conta").execute()
                print(f"   -> Lote {i} enviado.")
            except Exception as e:
                erros += 1
                print(f"❌ Erro lote {i}: {e}")
                
        if erros == 0:
            print("✅ Carga Completa!")
        else:
            print(f"⚠️ Carga com {erros} erros.")
    else:
        print("⚠️ Nada extraído.")

if __name__ == "__main__":
    processar_carga()