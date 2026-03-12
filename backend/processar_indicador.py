import pdfplumber
import pandas as pd
from supabase import create_client
import os
import re

print("\n--- 🏥 PROCESSADOR DE INDICADORES V3 (LIMPEZA REVERSA) ---")

# --- SUAS CREDENCIAIS REAIS ---
url = "https://voweywtzoldwfhgkniup.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
supabase = create_client(url, key)

def is_pure_number(s):
    """Retorna True se a string for apenas número (ex: '421', '0', '1.200')"""
    s = s.replace('.', '').replace(',', '').strip()
    return s.isdigit()

def processar_estatistica(pdf_path):
    print(f"📂 Lendo: {pdf_path}...")
    
    if not os.path.exists(pdf_path):
        print(f"❌ Erro: Arquivo não encontrado: {pdf_path}")
        return

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            
            # Tenta capturar a data
            competencia = "2026-01-01"
            match_data = re.search(r'Período de (\d{2}/\d{2}/\d{4})', page.extract_text())
            if match_data:
                dia, mes, ano = match_data.group(1).split('/')
                competencia = f"{ano}-{mes}-{dia}"
                print(f"📅 Competência: {competencia}")

            # Configuração de leitura
            settings = { "vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 4 }
            table = page.extract_table(table_settings=settings)

            if not table: return print("❌ Erro: Tabela não detectada.")

            dados_para_envio = []
            chaves_processadas = set()

            for row in table:
                # Remove nulos
                row = [str(x).strip() for x in row if x is not None and str(x).strip() != ""]
                
                # Pula linhas de cabeçalho ou muito curtas
                if len(row) < 5: continue
                first_word = row[0].upper()
                if any(x in first_word for x in ["UNID", "ENTRADA", "SAIDA", "TOTAL", "INDICADOR"]): continue

                try:
                    # 1. PEGA OS INDICADORES (Últimos 5 elementos)
                    # Layout: ... | Pac/Dia | TaxaMort | TaxaMov | MedPerm | %Ocup
                    val_pac_dia = row[-1]
                    val_taxa_mort = row[-2]
                    val_med_perm = row[-4]
                    val_ocup = row[-5]

                    # Valida se pegamos números (segurança)
                    if not is_pure_number(val_pac_dia): continue 

                    # 2. LIMPEZA INTELIGENTE DO NOME
                    # Pega tudo que sobrou à esquerda (row[:-5])
                    # E remove números da direita para a esquerda até achar letra
                    
                    sobras = row[:-5] 
                    while sobras and is_pure_number(sobras[-1]):
                        sobras.pop() # Remove o último item se for número (ex: 609, 89, 53...)

                    # O que restou é o nome limpo
                    nome_unidade = " ".join(sobras).replace("\n", "").strip()
                    nome_unidade = re.sub(r'\s+', ' ', nome_unidade) # Remove espaços extras

                    if not nome_unidade or len(nome_unidade) < 3: continue

                    # Tratamento dos Valores
                    pac_dia = int(val_pac_dia.replace(".", ""))
                    percent_ocup = float(val_ocup.replace(",", "."))
                    med_perm = float(val_med_perm.replace(",", "."))
                    taxa_mort = float(val_taxa_mort.replace(",", "."))

                    # 3. PREPARA DADOS
                    chave_unica = (competencia, nome_unidade)
                    if chave_unica in chaves_processadas: continue
                    chaves_processadas.add(chave_unica)

                    dados_hospitalares = {
                        "competencia": competencia,
                        "unidade_internacao": nome_unidade,
                        "pac_dia": pac_dia,
                        "percent_ocupacao": percent_ocup,
                        "media_permanencia": med_perm,
                        "taxa_mortalidade": taxa_mort
                    }
                    
                    dados_para_envio.append(dados_hospitalares)
                    print(f"   -> Lido: {nome_unidade.ljust(25)} | Ocup: {percent_ocup}%")

                except Exception:
                    pass

            if dados_para_envio:
                print(f"🚀 Enviando {len(dados_para_envio)} registros...")
                supabase.table("estatistica_hospitalar").upsert(dados_para_envio, on_conflict="competencia, unidade_internacao").execute()
                print("✅ DADOS CORRIGIDOS COM SUCESSO!")
            else:
                print("⚠️ Nada para enviar.")

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")

# Execução
caminho_arquivo = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\R_EST_HOSPITALAR_0126.pdf"
processar_estatistica(caminho_arquivo)