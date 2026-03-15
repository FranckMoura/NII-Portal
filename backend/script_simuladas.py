import pdfplumber
import pandas as pd
import re
import os
from supabase import create_client, Client

print("--- 🚀 SCRIPT V26: EXTRAÇÃO E UPLOAD PARA SUPABASE ---")

# --- CONFIGURAÇÕES SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

arquivo_pdf = "SIMULADAS 0226.pdf" 
COMPETENCIA = "02/2026" # Pode alterar isto para os próximos PDFs

def enviar_em_lotes(tabela, dados, tamanho_lote=1000):
    total = len(dados)
    for i in range(0, total, tamanho_lote):
        lote = dados[i:i + tamanho_lote]
        supabase.table(tabela).insert(lote).execute()
        print(f"   ☁️ Enviados {min(i + tamanho_lote, total)}/{total} para {tabela}...")

def extrair_e_subir_pdf():
    if not os.path.exists(arquivo_pdf):
        print(f"❌ Arquivo '{arquivo_pdf}' não encontrado!")
        return

    procedimentos = []
    valores = []

    print(f"Lendo o arquivo {arquivo_pdf}...")
    try:
        with pdfplumber.open(arquivo_pdf) as pdf:
            total_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                if (i + 1) % 100 == 0: print(f"  ⏳ Lendo página {i + 1} de {total_paginas}...")
                
                texto = pagina.extract_text()
                if not texto: continue
                texto_flat = re.sub(r'\s+', ' ', texto)

                # CABEÇALHO
                m_nome = re.search(r'Paciente\s*:\s*(.*?)(?:\s+Data Nasc|\s+Sexo|$)', texto_flat, re.IGNORECASE)
                nome = m_nome.group(1).replace('Prontuário', '').strip() if m_nome else "DESCONHECIDO"
                nome = re.sub(r'[:\-\.]*\s*\d+$', '', nome).strip()

                m_aih = re.search(r'Num AIH\s*:\s*([\d\-]+)', texto_flat, re.IGNORECASE)
                aih = m_aih.group(1).strip() if m_aih else "SEM_AIH"

                # PROCEDIMENTOS
                m_bloco_proc = re.search(r'PROCEDIMENTOS\s+REALIZADOS(.*?)VALORES\s+DA\s+PR[EÉ]VIA', texto_flat, re.IGNORECASE)
                if m_bloco_proc:
                    bloco = re.sub(r'Linha\s+Procedimento.*?Descri[cç][aã]o', '', m_bloco_proc.group(1), flags=re.IGNORECASE)
                    for m in re.finditer(r'\b(\d{1,3})\s+(\d{10})\b\s*(.*?)(?=\s+\b\d{1,3}\s+\d{10}\b|$)', bloco):
                        resto = m.group(3).strip()
                        m_qt = re.search(r'\b(\d{1,4})\s+(\d{2}/\d{4})\s+(.*)$', resto)
                        if m_qt:
                            antes = resto[:m_qt.start()].strip()
                            depois = m_qt.group(3).strip()
                            docs = [t for t in antes.split() if re.match(r'^\d+$', t)]
                            desc_words = [w for w in depois.split() if not re.match(r'^\d{4,}$', w)]
                            
                            procedimentos.append({
                                "competencia_arquivo": COMPETENCIA, "paciente": nome, "aih": aih, "pagina": i+1,
                                "linha": m.group(1), "codigo": m.group(2), "documento_cnes": " / ".join(docs) if docs else "-",
                                "qtde": m_qt.group(1), "cmpt": m_qt.group(2), "descricao": " ".join(desc_words)
                            })
                        else:
                            procedimentos.append({
                                "competencia_arquivo": COMPETENCIA, "paciente": nome, "aih": aih, "pagina": i+1,
                                "linha": m.group(1), "codigo": m.group(2), "documento_cnes": "-",
                                "qtde": "-", "cmpt": "-", "descricao": resto
                            })

                # VALORES FINANCEIROS
                m_bloco_val = re.search(r'VALORES\s+DA\s+PR[EÉ]VIA(.*?)(?:SERVI[CÇ]O/CLASSIFICA|CNAER:|$)', texto_flat, re.IGNORECASE)
                if m_bloco_val:
                    b_val = re.sub(r'Serviço Hospitalar.*?Terceiro', '', m_bloco_val.group(1), flags=re.IGNORECASE)
                    for m in re.finditer(r'(\d{2}\.\d{2}\.\d{2}\-[^\d].*?)(?=\s+\d{2}\.\d{2}\.\d{2}\-|\s+Total Geral:|$)', b_val, re.IGNORECASE):
                        item = m.group(1).strip()
                        m_sep = re.search(r'(.*?)\s+([\d\.\s,]+)$', item)
                        if m_sep:
                            vals = re.findall(r'[\d\.]*,\d{2}', m_sep.group(2))
                            valores.append({
                                "competencia_arquivo": COMPETENCIA, "paciente": nome, "aih": aih, "pagina": i+1,
                                "grupo_consolidado": m_sep.group(1).strip(), "valor_rs": vals[-1] if vals else "0,00"
                            })
                            
                    m_tot = re.search(r'Total Geral:\s*([\d\.\s,]+)', b_val, re.IGNORECASE)
                    if m_tot:
                        vals = re.findall(r'[\d\.]*,\d{2}', m_tot.group(1))
                        if vals:
                            valores.append({
                                "competencia_arquivo": COMPETENCIA, "paciente": nome, "aih": aih, "pagina": i+1,
                                "grupo_consolidado": "TOTAL GERAL", "valor_rs": vals[-1]
                            })

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
        return

    print(f"\n✅ Leitura do PDF concluída. Iniciando limpeza no Supabase para a competência {COMPETENCIA}...")
    
    # Apaga os dados antigos da mesma competência para evitar duplicação se rodar 2 vezes
    supabase.table("simuladas_procedimentos").delete().eq("competencia_arquivo", COMPETENCIA).execute()
    supabase.table("simuladas_valores").delete().eq("competencia_arquivo", COMPETENCIA).execute()

    print(f"🚀 Subindo {len(procedimentos)} procedimentos para a Nuvem...")
    enviar_em_lotes("simuladas_procedimentos", procedimentos)
    
    print(f"🚀 Subindo {len(valores)} valores financeiros para a Nuvem...")
    enviar_em_lotes("simuladas_valores", valores)

    print("\n🎉 SUCESSO ABSOLUTO! Dados armazenados no banco de dados com segurança.")

if __name__ == "__main__":
    extrair_e_subir_pdf()