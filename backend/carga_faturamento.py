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
    match = re.search(r'_(\d{2})(\d{2})\.pdf', nome_arquivo.lower())
    if match:
        mes, ano = match.groups()
        return f"20{ano}-{mes}" 
    return None

def limpar_texto(texto):
    if not texto: return ""
    return re.sub(r'\s+', ' ', texto).strip()

def extrair_dados_pdf(caminho_arquivo):
    nome_arq = os.path.basename(caminho_arquivo)
    comp_arquivo = extrair_competencia_arquivo(nome_arq)
    
    print(f"\n📄 Processando: {nome_arq} (Ref: {comp_arquivo})")
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

                    # 1. DETECÇÃO DE CLÍNICA
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
                    
                    # 2. EXTRAÇÃO DETALHADA DE PACIENTE
                    # Padrão esperado: AIH (13) + ID + NOME + PRONTUARIO/DATA
                    if re.match(r'^\d{13}', line_upper):
                        if clinica_atual == "INDEFINIDA": continue

                        # Regex Poderoso para separar colunas
                        # Grupo 1: AIH (13 digitos)
                        # Grupo 2: Nome do Paciente (Texto entre números)
                        # Grupo 3: Resto da linha (Datas e Procedimento)
                        match_linha = re.search(r'^(\d{13})\s+\d+\s+(.+?)\s+(\d{4,}.*)', line_upper)
                        
                        if match_linha:
                            aih = match_linha.group(1)
                            nome_paciente_sujo = match_linha.group(2)
                            resto_linha = match_linha.group(3)
                            
                            # Busca datas no resto da linha
                            datas = re.findall(r'\d{2}/\d{2}/\d{4}', resto_linha)
                            
                            if len(datas) >= 2:
                                dt_int_str = datas[0]
                                dt_alta_str = datas[1]
                                
                                try:
                                    dt_int = datetime.strptime(dt_int_str, "%d/%m/%Y")
                                    dt_alta = datetime.strptime(dt_alta_str, "%d/%m/%Y")
                                    
                                    permanencia = (dt_alta - dt_int).days
                                    if permanencia == 0: permanencia = 1
                                    
                                    # Extrair Procedimento (Código 10 digitos + Nome)
                                    cod_proc = ""
                                    desc_proc = "Não identificado"
                                    
                                    match_proc = re.search(r'(\d{10})\s+(.+)', resto_linha)
                                    if match_proc:
                                        cod_proc = match_proc.group(1)
                                        desc_proc = match_proc.group(2)
                                        # Remove "12 ALTA MELHORADO" se estiver colado no fim
                                        desc_proc = desc_proc.split(" 12 ALTA")[0].strip()
                                    else:
                                        # Fallback: pega o texto depois das datas
                                        try:
                                            desc_proc = resto_linha.split(dt_alta_str)[1].strip()
                                        except: pass

                                    dados_extraidos.append({
                                        "nr_conta": aih,
                                        "nr_aih": aih,
                                        "paciente": limpar_texto(nome_paciente_sujo), # Nome limpo!
                                        "dt_internacao": dt_int.strftime('%Y-%m-%d'),
                                        "dt_alta": dt_alta.strftime('%Y-%m-%d'),
                                        "procedimento": limpar_texto(f"{cod_proc} {desc_proc}"),
                                        "clinica": clinica_atual,
                                        "status_conta": "Fechada",
                                        "permanencia": permanencia,
                                        "competencia": comp_arquivo,
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
    
    # Exemplo de como ficaram os dados (Debug)
    if len(todos_registros) > 0:
        exemplo = todos_registros[0]
        print(f"\n🔎 Exemplo de registro extraído:")
        print(f"   Paciente: {exemplo['paciente']}")
        print(f"   Procedimento: {exemplo['procedimento']}")
        print(f"   Clinica: {exemplo['clinica']}")

    if len(todos_registros) > 0:
        print("\n☁️ Enviando para Supabase...")
        
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
            print(f"⚠️ Carga concluída com {erros} erros.")
    else:
        print("⚠️ Nada extraído.")

if __name__ == "__main__":
    processar_carga()