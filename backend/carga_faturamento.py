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
            buffer_paciente = ""
            
            def processar_buffer():
                nonlocal buffer_paciente
                if not buffer_paciente or clinica_atual == "INDEFINIDA" or clinica_atual == "IGNORAR":
                    buffer_paciente = ""
                    return
                
                # Regex blindado buscando a estrutura garantida: AIH ... Datas ... Codigo ... Resto
                match_linha = re.search(r'^(\d{13})(.*?)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{10})\s+(.+)$', buffer_paciente)
                
                if match_linha:
                    aih = match_linha.group(1)
                    meio_sujo = match_linha.group(2)
                    dt_int_str = match_linha.group(3)
                    dt_alta_str = match_linha.group(4)
                    cod_proc = match_linha.group(5)
                    resto_proc = match_linha.group(6)
                    
                    # 1. Extração Inteligente do Nome
                    nome = "NOME NÃO IDENTIFICADO"
                    match_nome = re.search(r'[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s\.\']+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]', meio_sujo)
                    if match_nome:
                        nome = match_nome.group(0)
                    else:
                        match_nome_fallback = re.search(r'[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]+', meio_sujo)
                        if match_nome_fallback: nome = match_nome_fallback.group(0)

                    # 2. Limpeza da Descrição do Procedimento
                    desc_proc = re.sub(r'\s+\d{2}\s+(ALTA|PERMANENCIA|ENCERRAMENTO|TRANSFERENCIA|OBITO).*', '', resto_proc).strip()
                    
                    try:
                        dt_int = datetime.strptime(dt_int_str, "%d/%m/%Y")
                        dt_alta = datetime.strptime(dt_alta_str, "%d/%m/%Y")
                        
                        permanencia = (dt_alta - dt_int).days
                        if permanencia == 0: permanencia = 1
                        
                        dados_extraidos.append({
                            "nr_conta": aih,
                            "nr_aih": aih,
                            "paciente": limpar_texto(nome),
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
                
                buffer_paciente = ""

            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                
                for line in lines:
                    line_upper = line.strip().upper()

                    # Bloqueios de segurança para não ler contas canceladas/rejeitadas
                    if "REJEITAD" in line_upper or "CANCELAD" in line_upper or "GLOSAD" in line_upper:
                        processar_buffer()
                        clinica_atual = "IGNORAR"
                        continue

                    # Ignorar cabeçalhos inúteis
                    if "NR_GUIA" in line_upper or "SISTEMA DE INFORMAÇÕES" in line_upper:
                        continue

                    # 1. DETECÇÃO DE CLÍNICA
                    if "01 CIRURGICO" in line_upper or "01 CLINICA CIRURGICA" in line_upper:
                        processar_buffer()
                        clinica_atual = "Clínica Cirúrgica"
                        continue
                    if "02 OBSTETRICO" in line_upper or "02 OBSTETRICOS" in line_upper: 
                        processar_buffer()
                        clinica_atual = "Obstetrícia"
                        continue
                    if "03 CLINICO" in line_upper or "03 CLINICA MEDICA" in line_upper:
                        processar_buffer()
                        clinica_atual = "Clínica Médica"
                        continue
                    if "07 PEDIATRIA" in line_upper:
                        processar_buffer()
                        clinica_atual = "Pediatria"
                        continue
                    if "TOTAL DA ESPECIALIDADE" in line_upper or "TOTAL GERAL" in line_upper:
                        processar_buffer()
                        continue
                    
                    # 2. BUFFER DE PACIENTE (Somente 13 dígitos cravados seguidos de espaço)
                    if re.match(r'^\d{13}\s', line_upper):
                        processar_buffer()
                        buffer_paciente = line_upper
                    elif buffer_paciente:
                        buffer_paciente += " " + line_upper
                        
            processar_buffer()
            
    except Exception as e:
        print(f"⚠️ Erro ao abrir {nome_arq}: {e}")

    # --- DEDUPLICAÇÃO PYTHON (Corta o mal pela raiz) ---
    # Garante que se o PDF imprimir a mesma AIH duas vezes, nós só contamos uma.
    dados_unicos = {d["nr_conta"]: d for d in dados_extraidos}
    resultado_limpo = list(dados_unicos.values())
    
    # Se eliminámos duplicatas, avisamos no terminal
    duplicadas = len(dados_extraidos) - len(resultado_limpo)
    if duplicadas > 0:
        print(f"   🧹 Foram encontradas e removidas {duplicadas} AIHs duplicadas no PDF.")

    return resultado_limpo

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
        
    print(f"\n🔄 Total extraído com sucesso: {len(todos_registros)}")
    
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