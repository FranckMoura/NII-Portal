import os
import pdfplumber
import re
import json
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR SIMULADAS V23: DESAMASSADOR DE TABELAS ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ENTRADA = os.path.join(BASE_DIR, "entradas_pdf")
if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)

try: supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e: print(f"❌ Erro de conexão: {e}"); exit()

def desamassar_linha_procedimento(linha_texto):
    m_data = re.search(r'(\d{2}/\d{4})', linha_texto)
    if not m_data: return None
    
    cmpt = m_data.group(1)
    desc = linha_texto[m_data.end():].strip()
    
    resto_antes = linha_texto[:m_data.start()].strip()
    partes = resto_antes.split()
    
    if partes:
        ultimo_bloco = partes[-1]
        m_qtd = re.search(r'(\d+)$', ultimo_bloco)
        if m_qtd:
            qtd = m_qtd.group(1)
            partes[-1] = ultimo_bloco[:m_qtd.start()]
            if not partes[-1]: partes.pop()
        else: qtd = "1"
    else: qtd = "1"
    
    bloco_esq = "".join(partes) 
    
    if len(bloco_esq) >= 10:
        codigo = bloco_esq[:10]
        docs_str = bloco_esq[10:]
    else:
        codigo = bloco_esq; docs_str = ""
        
    docs_sep = []
    if docs_str:
        if len(docs_str) == 21 and docs_str.startswith('7'): 
            docs_sep.extend([docs_str[:15], docs_str[15:]])
        elif len(docs_str) > 15 and docs_str.startswith('7'):
            docs_sep.append(docs_str[:15])
            resto = docs_str[15:]
            if len(resto) == 13: docs_sep.extend([resto[:7], resto[7:]]) 
            elif len(resto) > 0: docs_sep.append(resto)
        elif len(docs_str) == 14: 
             docs_sep.extend([docs_str[:7], docs_str[7:]])
        else:
            docs_sep.append(docs_str)
            
    return {"codigo": codigo, "qtde": qtd, "cmpt": cmpt, "descricao": desc, "documento_cnes": " / ".join(docs_sep) if docs_sep else "-"}

def forcar_upload_correto(caminho_local, nome_remoto, content_type):
    print(f"☁️ Subindo: {nome_remoto}...")
    try:
        try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
        except: pass
        with open(caminho_local, 'rb') as f:
            supabase.storage.from_(NOME_BUCKET).upload(path=nome_remoto, file=f, file_options={"content-type": content_type, "upsert": "true", "cache-control": "3600"})
        return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
    except Exception as e: print(f"❌ Erro upload: {e}"); return None

def processar():
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]
    if not arquivos: print(f"❌ Pasta '{PASTA_ENTRADA}' vazia!"); return

    nome_pdf = arquivos[0]
    caminho_pdf = os.path.join(PASTA_ENTRADA, nome_pdf)
    competencia_global = "02/2026"
    data_banco = datetime.now().strftime('%Y-%m-%d')
    nome_json_remoto = f"INDICES/Indice_{datetime.now().strftime('%d-%m-%Y')}_{nome_pdf.replace('.pdf', '.json')}"

    print(f"📄 Processando Megarquivo: {nome_pdf}")
    link_pdf = forcar_upload_correto(caminho_pdf, f"PDFs/{datetime.now().strftime('%d-%m-%Y')}_{nome_pdf}", "application/pdf")
    if not link_pdf: return

    dados_indice = []
    lista_procedimentos = []
    lista_valores = []
    
    ultimo_paciente_valido = { 'NOME': None, 'AIH': None, 'PRONTUARIO': None, 'ESPEC': None, 'CNS': None, 'PROC': None, 'DT_INT': None, 'DT_SAI': None }
    
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            total_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                num_pag = i + 1
                if num_pag % 10 == 0: print(f"   Lendo Pag {num_pag}/{total_paginas}...")
                
                texto = pagina.extract_text() or ""
                texto_sq = re.sub(r'\s+', '', texto).lower()
                texto_flat = re.sub(r'\s+', ' ', texto) 
                
                # 1. PEGAR CABEÇALHO (ÍNDICE)
                m_nome = re.search(r'Paciente\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                nome = m_nome.group(1).replace('Prontuário', '').replace('Data Nasc', '').replace('Sexo', '').strip() if m_nome else None
                nome = re.sub(r'[:\-\.]*\s*\d+$', '', nome).strip() if nome else None
                
                m_proc = re.search(r'Procedimento principal\s*:\s*([^\n\r]+)', texto, re.IGNORECASE)
                proc = m_proc.group(1).replace('Diag. principal', '').strip() if m_proc else "-"
                
                m_aih = re.search(r'aih:([\d\-]+)', texto_sq)
                aih = m_aih.group(1).strip() if m_aih else None
                
                pront = (re.search(r'prontu.rio:(\d+)', texto_sq) or re.search(r'', '')).group(1) if re.search(r'prontu.rio:(\d+)', texto_sq) else "N/A"
                espec = (re.search(r'especialidade:(\d+-[a-z]+)', texto_sq) or re.search(r'', '')).group(1).upper().replace('-', ' - ') if re.search(r'especialidade:(\d+-[a-z]+)', texto_sq) else "-"
                
                m_cns = re.search(r'cns/cpf:([\d\.\-]+)', texto_sq) or re.search(r'cns:([\d\.\-]+)', texto_sq)
                cns = m_cns.group(1).upper() if m_cns else "-"
                
                dt_int = (re.search(r'interna..o:?(\d{2}/\d{2}/\d{4})', texto_sq) or re.search(r'', '')).group(1) if re.search(r'interna..o:?(\d{2}/\d{2}/\d{4})', texto_sq) else "-"
                dt_sai = (re.search(r'(?:sa.da|alta):?(\d{2}/\d{2}/\d{4})', texto_sq) or re.search(r'', '')).group(1) if re.search(r'(?:sa.da|alta):?(\d{2}/\d{2}/\d{4})', texto_sq) else "-"

                if nome and aih:
                    reg_indice = { 'NOME': nome, 'AIH': aih, 'PRONTUARIO': pront, 'ESPEC': espec, 'CNS': cns, 'PROC': proc, 'DT_INT': dt_int, 'DT_SAI': dt_sai, 'PAGINA': num_pag }
                    ultimo_paciente_valido = reg_indice.copy()
                    dados_indice.append(reg_indice)
                elif not nome and aih and ultimo_paciente_valido['AIH'] == aih:
                    nome = ultimo_paciente_valido['NOME'] + " (Cont.)"
                    reg_indice = ultimo_paciente_valido.copy()
                    reg_indice['NOME'] = nome; reg_indice['PAGINA'] = num_pag
                    dados_indice.append(reg_indice)
                elif not nome:
                    nome = ultimo_paciente_valido['NOME'] if ultimo_paciente_valido['NOME'] else "DESCONHECIDO"
                    aih = ultimo_paciente_valido['AIH'] if ultimo_paciente_valido['AIH'] else "SEM_AIH"

                # 2. RASPAR TABELA DE PROCEDIMENTOS
                m_bloco_proc = re.search(r'PROCEDIMENTOS\s+REALIZADOS(.*?)VALORES\s+DA\s+PR[EÉ]VIA', texto_flat, re.IGNORECASE)
                if m_bloco_proc:
                    bloco = m_bloco_proc.group(1)
                    bloco = re.sub(r'Linha\s+Procedimento.*?Descri[cç][aã]o', '', bloco, flags=re.IGNORECASE)
                    
                    padrao = r'\b(\d{1,3})\s+(\d{10}\b.*?\d{2}/\d{4}.*?)(?=\s+\b\d{1,3}\s+\d{10}\b|$)'
                    for m in re.finditer(padrao, bloco):
                        lnh = m.group(1)
                        resto = m.group(2).strip()
                        dados_proc = desamassar_linha_procedimento(resto)
                        
                        if dados_proc:
                            lista_procedimentos.append({
                                "competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": nome,
                                "linha": lnh, "codigo": dados_proc["codigo"], "qtde": dados_proc["qtde"], "cmpt": dados_proc["cmpt"],
                                "documento_cnes": dados_proc["documento_cnes"], "descricao": dados_proc["descricao"]
                            })

                # 3. RASPAR TABELA DE VALORES (CORRIGIDO: grupo_consolidado e valor_rs)
                m_bloco_val = re.search(r'VALORES\s+DA\s+PR[EÉ]VIA(.*?)(?:SERVI[CÇ]O/CLASSIFICA|CNAER:|$)', texto_flat, re.IGNORECASE)
                if m_bloco_val:
                    b_val = m_bloco_val.group(1)
                    b_val = re.sub(r'Serviço Hospitalar.*?Terceiro', '', b_val, flags=re.IGNORECASE)
                    
                    for m in re.finditer(r'(\d{2}\.\d{2}\.\d{2}\-[^\d].*?)(?=\s+\d{2}\.\d{2}\.\d{2}\-|\s+Total Geral:|$)', b_val, re.IGNORECASE):
                        item = m.group(1).strip()
                        m_sep = re.search(r'(.*?)\s+([\d\.\s,]+)$', item)
                        if m_sep:
                            desc = m_sep.group(1).strip()
                            vals = re.findall(r'[\d\.]*,\d{2}', m_sep.group(2))
                            val = vals[-1] if vals else "0,00"
                            lista_valores.append({"competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": nome, "grupo_consolidado": desc, "valor_rs": val})
                            
                    m_tot = re.search(r'Total Geral:\s*([\d\.\s,]+)', b_val, re.IGNORECASE)
                    if m_tot:
                        vals = re.findall(r'[\d\.]*,\d{2}', m_tot.group(1))
                        if vals:
                            lista_valores.append({"competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": nome, "grupo_consolidado": "TOTAL GERAL", "valor_rs": vals[-1]})

    except Exception as e: print(f"❌ Erro Crítico: {e}"); return

    print(f"✅ FIM! {len(dados_indice)} pacientes, {len(lista_procedimentos)} procedimentos, {len(lista_valores)} valores.")

    if dados_indice:
        temp_file = os.path.join(BASE_DIR, "temp_indice.json")
        with open(temp_file, "w", encoding="utf-8") as f: json.dump(dados_indice, f, ensure_ascii=False)
        link_json = forcar_upload_correto(temp_file, nome_json_remoto, "application/json; charset=utf-8")
        os.remove(temp_file)

        print("💾 Atualizando Supabase (Apagando Antigos do Mês)...")
        supabase.table("controle_simuladas").delete().eq("data_arquivo", data_banco).execute()
        supabase.table("simuladas_procedimentos").delete().eq("competencia_arquivo", competencia_global).execute()
        supabase.table("simuladas_valores").delete().eq("competencia_arquivo", competencia_global).execute()

        supabase.table("controle_simuladas").insert({
            "data_arquivo": data_banco, "nome_original": nome_pdf,
            "link_pdf": link_pdf, "link_indice": link_json
        }).execute()

        print("💾 Enviando Procedimentos para o Supabase em Lotes...")
        for i in range(0, len(lista_procedimentos), 100):
            supabase.table("simuladas_procedimentos").insert(lista_procedimentos[i:i+100]).execute()
            
        print("💾 Enviando Valores para o Supabase em Lotes...")
        for i in range(0, len(lista_valores), 100):
            supabase.table("simuladas_valores").insert(lista_valores[i:i+100]).execute()

    print("🎉 PRONTO! PODE ABRIR O PAINEL_SIMULADAS.HTML")

if __name__ == "__main__":
    processar()