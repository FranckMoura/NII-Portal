import os
import pdfplumber
import pandas as pd
import re
import json
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR SIMULADAS V21: ARQUITETURA JSON (INTEGRAÇÃO NATIVA) ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ENTRADA = os.path.join(BASE_DIR, "entradas_pdf")

if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro de conexão: {e}"); exit()

def forcar_upload_correto(caminho_local, nome_remoto, content_type):
    print(f"☁️  Subindo para a nuvem: {nome_remoto}...")
    try:
        try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except: pass
        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(
                path=nome_remoto, file=f,
                file_options={"content-type": content_type, "upsert": "true", "cache-control": "3600"}
            )
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except Exception as e:
        print(f"❌ Erro no upload: {e}"); return None

def processar():
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]
    if not arquivos:
        print(f"❌ Pasta '{PASTA_ENTRADA}' vazia!"); return

    nome_pdf = arquivos[0]
    caminho_pdf = os.path.join(PASTA_ENTRADA, nome_pdf)
    
    data_hoje_str = datetime.now().strftime('%d-%m-%Y')
    data_banco = datetime.now().strftime('%Y-%m-%d')
    
    nome_pdf_remoto = f"PDFs/{data_hoje_str}_{nome_pdf}"
    nome_json_remoto = f"INDICES/Indice_{data_hoje_str}_{nome_pdf.replace('.pdf', '.json')}"

    print(f"📄 Processando: {nome_pdf}")
    link_pdf_final = forcar_upload_correto(caminho_pdf, nome_pdf_remoto, "application/pdf")
    if not link_pdf_final: return

    dados_extraidos = []
    ultimo_paciente_valido = { 'NOME': None, 'AIH': None, 'PRONTUARIO': None, 'ESPEC': None, 'CNS': None, 'PROC': None, 'DT_INT': None, 'DT_SAI': None }
    
    print("🕵️  Lendo PDF (Ativando Limpeza Profunda)...")
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            total_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                num_pag = i + 1
                if num_pag % 50 == 0: print(f"   Pag {num_pag}/{total_paginas}...")
                
                texto = pagina.extract_text() or ""
                texto_sq = re.sub(r'\s+', '', texto).lower()
                
                m_nome = re.search(r'Paciente\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                nome_bruto = m_nome.group(1).replace('Prontuário', '').replace('Data Nasc', '').replace('Sexo', '').strip() if m_nome else None
                nome = re.sub(r'[:\-\.]*\s*\d+$', '', nome_bruto).strip() if nome_bruto else None
                
                m_proc = re.search(r'Procedimento principal\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                proc = m_proc.group(1).replace('Diag. principal', '').strip() if m_proc else "-"
                
                m_aih = re.search(r'aih:([\d\-]+)', texto_sq)
                aih = m_aih.group(1).strip() if m_aih else None
                
                m_pront = re.search(r'prontu.rio:(\d+)', texto_sq)
                pront = m_pront.group(1).strip() if m_pront else "N/A"
                
                m_espec = re.search(r'especialidade:(\d+-[a-z]+)', texto_sq)
                espec = m_espec.group(1).upper().replace('-', ' - ') if m_espec else "-"
                
                m_cns = re.search(r'cns/cpf:([\d\.\-]+)', texto_sq)
                if not m_cns: m_cns = re.search(r'cns:([\d\.\-]+)', texto_sq)
                cns = m_cns.group(1).upper() if m_cns else "-"
                
                m_dt_int = re.search(r'interna..o:?(\d{2}/\d{2}/\d{4})', texto_sq)
                dt_int = m_dt_int.group(1) if m_dt_int else "-"
                
                m_dt_sai = re.search(r'(?:sa.da|alta):?(\d{2}/\d{2}/\d{4})', texto_sq)
                dt_sai = m_dt_sai.group(1) if m_dt_sai else "-"

                todas_datas = re.findall(r'\d{2}/\d{2}/\d{4}', texto_sq)
                if dt_int == "-" and len(todas_datas) >= 3: dt_int = todas_datas[-2]
                if dt_sai == "-" and len(todas_datas) >= 4: dt_sai = todas_datas[-1]

                if nome and aih:
                    registro = { 'NOME': nome, 'AIH': aih, 'PRONTUARIO': pront, 'ESPEC': espec, 'CNS': cns, 'PROC': proc, 'DT_INT': dt_int, 'DT_SAI': dt_sai, 'PAGINA': num_pag }
                    ultimo_paciente_valido = registro.copy()
                    dados_extraidos.append(registro)
                elif not nome and aih:
                    if ultimo_paciente_valido['AIH'] == aih:
                        registro = ultimo_paciente_valido.copy()
                        registro['NOME'] = registro['NOME'] + " (Cont.)"
                        registro['PAGINA'] = num_pag
                        dados_extraidos.append(registro)
    except Exception as e:
        print(f"❌ Erro leitura PDF: {e}"); return

    print(f"✅ Extraído: {len(dados_extraidos)} registros detalhados.")

    if dados_extraidos:
        print("💾 Gravando dados puros em JSON para a Tela do Painel...")
        temp_file = os.path.join(BASE_DIR, "temp_indice.json")
        
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(dados_extraidos, f, ensure_ascii=False)
        
        link_json_final = forcar_upload_correto(temp_file, nome_json_remoto, "application/json; charset=utf-8")
        os.remove(temp_file)

        print("💾 Atualizando links no banco...")
        try:
            supabase.table("controle_simuladas").delete().eq("data_arquivo", data_banco).execute()
            supabase.table("controle_simuladas").insert({
                "data_arquivo": data_banco,
                "nome_original": nome_pdf,
                "link_pdf": link_pdf_final,
                "link_indice": link_json_final # Agora armazena o JSON!
            }).execute()
            print("✅ Banco atualizado!")
        except Exception as e:
            print(f"⚠️ Erro ao salvar no banco: {e}")

        print("\n🎉 FIM! O painel vai puxar a lista de pacientes instantaneamente!")

if __name__ == "__main__":
    processar()