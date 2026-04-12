import os
import glob
import pdfplumber
import re
from supabase import create_client, Client

# 1. Conexão com Supabase
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

# 2. Pasta alvo com os PDFs
PASTA_ALVO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\financeiro_soulmv"

if not os.path.exists(PASTA_ALVO):
    print(f"❌ Erro: A pasta {PASTA_ALVO} não foi encontrada.")
    exit()

# Pega todos os arquivos que começam com R_PREV_REC_GLO_ESP e terminam em .pdf
arquivos = glob.glob(os.path.join(PASTA_ALVO, "R_PREV_REC_GLO_ESP_*.pdf"))

if not arquivos:
    print(f"❌ Nenhum arquivo PDF encontrado na pasta {PASTA_ALVO}.")
    exit()

print(f"✅ Encontrados {len(arquivos)} arquivos PDF para processar.\n")

dados_para_enviar = []

# 3. Lógica "Mineradora" em PDF
for arquivo in arquivos:
    nome_arq = os.path.basename(arquivo)
    print(f"📂 Processando arquivo: {nome_arq}...")
    
    competencia_atual = None
    especialidade_atual = None
    
    try:
        with pdfplumber.open(arquivo) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                
                for i, line in enumerate(lines):
                    
                    # A. Captura a Competência (ex: 02/2026 -> 2026-02)
                    if "Competência:" in line and not competencia_atual:
                        match_comp = re.search(r'(\d{2}/\d{4})', line)
                        if match_comp:
                            mes, ano = match_comp.group(1).split('/')
                            competencia_atual = f"{ano}-{mes}"
                    
                    # B. Captura a Especialidade
                    if "Especialidade:" in line:
                        match_esp = re.search(r'Especialidade:\s*\d+\s+(.+)', line)
                        if match_esp:
                            especialidade_atual = match_esp.group(1).strip()
                    
                    # C. Captura o Total da Especialidade
                    if "TOTAL DA ESPECIALIDADE" in line:
                        try:
                            # Os valores costumam estar na linha logo abaixo
                            if i + 1 < len(lines):
                                prox_linha = lines[i+1].strip()
                                
                                # Extrai o valor financeiro (pega sempre o último valor com ,XX da linha)
                                valores = re.findall(r'[\d\.]+\,\d{2}', prox_linha)
                                if valores:
                                    valor_str = valores[-1]
                                    valor_float = float(valor_str.replace('.', '').replace(',', '.'))
                                else:
                                    valor_float = 0.0
                                    
                                # Extrai a quantidade (pega o primeiro número isolado da linha)
                                match_qtd = re.search(r'\b(\d+)\b', prox_linha)
                                qtd_int = int(match_qtd.group(1)) if match_qtd else 0
                                
                                if valor_float > 0 and competencia_atual and especialidade_atual:
                                    dados_para_enviar.append({
                                        "competencia": competencia_atual,
                                        "especialidade": especialidade_atual,
                                        "qtd_contas": qtd_int,
                                        "valor_total": valor_float
                                    })
                                    print(f"   ✅ Detectado: {competencia_atual} | {especialidade_atual} | Qtd: {qtd_int} | R$ {valor_float:,.2f}")
                        except Exception as e:
                            print(f"   ⚠️ Erro ao ler totais de {especialidade_atual}: {e}")
                            
    except Exception as e:
        print(f"❌ Erro ao ler o PDF {nome_arq}: {e}")

# 4. Enviar para a Nuvem (Supabase)
if dados_para_enviar:
    print(f"\n☁️ Preparando para enviar {len(dados_para_enviar)} registros para o Supabase...")
    try:
        supabase.table("tb_faturamento_mensal").insert(dados_para_enviar).execute()
        print(f"🚀 Sucesso! Banco atualizado com o faturamento mensal das especialidades.")
    except Exception as e:
        print(f"❌ Erro no Supabase: {e}")
else:
    print("\n⚠️ Nenhum dado encontrado. Verifique a estrutura dos PDFs.")