import os
import pdfplumber
import re
import json
import time
from supabase import create_client, Client
from datetime import datetime

print("--- 🚀 PROCESSADOR SIMULADAS V31: PROCESSAMENTO EM LOTE E FATIAMENTO INTELIGENTE ---")

# --- 1. CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
NOME_BUCKET = "arquivos-faturamento"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ENTRADA = os.path.join(BASE_DIR, "entradas_pdf")
if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)

try: supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e: print(f"❌ Erro de conexão: {e}"); exit()

# --- FUNÇÕES ---
def extrair_competencia_do_nome(nome_arquivo):
    match = re.search(r'(\d{2})(\d{2})\.pdf', nome_arquivo.lower())
    if match:
        mes = match.group(1)
        ano = "20" + match.group(2)
        return f"{mes}/{ano}"
    return input(f"⚠️ Não foi possível detectar o mês no arquivo '{nome_arquivo}'. Digite a competência (Ex: 01/2026): ")

def desamassar_linha_procedimento(linha_texto):
    m_data = re.search(r'(\d{2}/\d{4})', linha_texto)
    if not m_data: return None
    cmpt = m_data.group(1)
    desc = linha_texto[m_data.end():].strip()
    resto_antes = linha_texto[:m_data.start()].strip()
    
    partes = resto_antes.split()
    qtd = "1"
    if partes:
        m_qtd = re.search(r'(\d+)$', partes[-1])
        if m_qtd:
            qtd = m_qtd.group(1)
            partes[-1] = partes[-1][:m_qtd.start()]
            if not partes[-1]: partes.pop()

    bloco_esq = "".join(partes)
    bloco_esq = re.sub(r'\(\d+\)', '', bloco_esq)
    
    codigo = bloco_esq[:10] if len(bloco_esq) >= 10 else bloco_esq
    lixo_e_docs = bloco_esq[10:] if len(bloco_esq) >= 10 else ""

    doc, cbo, cnes = "-", "-", "-"
    d_len = len(lixo_e_docs)
    
    if d_len == 28:   doc, cbo, cnes = lixo_e_docs[:15], lixo_e_docs[15:21], lixo_e_docs[21:]
    elif d_len == 22: doc, cnes = lixo_e_docs[:15], lixo_e_docs[15:]
    elif d_len == 21: doc, cnes = lixo_e_docs[:14], lixo_e_docs[14:]
    elif d_len == 14: cnes = lixo_e_docs[7:]
    elif d_len == 7:  cnes = lixo_e_docs
    elif d_len == 15: doc = lixo_e_docs
    elif d_len == 14: doc = lixo_e_docs
    else: doc = lixo_e_docs if lixo_e_docs else "-"

    return {"codigo": codigo, "qtde": qtd, "cmpt": cmpt, "descricao": desc, "doc_cnes": f"{doc} / {cbo} / {cnes}"}

def forcar_upload_correto(caminho_local, nome_remoto, content_type):
    print(f"☁️  Subindo para a nuvem: {nome_remoto}...")
    for tentativa in range(3):
        try:
            try: supabase.storage.from_(NOME_BUCKET).remove([nome_remoto])
            except: pass
            with open(caminho_local, 'rb') as f:
                supabase.storage.from_(NOME_BUCKET).upload(path=nome_remoto, file=f, file_options={"content-type": content_type, "upsert": "true", "cache-control": "3600"})
            return supabase.storage.from_(NOME_BUCKET).get_public_url(nome_remoto)
        except Exception as e:
            print(f"   ⚠️ Falha no upload (T{tentativa+1}/3). Aguardando... Erro: {e}")
            time.sleep(3)
    return None

def inserir_com_tentativas(tabela, dados, tamanho_lote=100):
    if not dados: return
    total = len(dados)
    for i in range(0, total, tamanho_lote):
        lote = dados[i:i+tamanho_lote]
        sucesso = False
        for tentativa in range(1, 4):
            try:
                supabase.table(tabela).insert(lote).execute()
                sucesso = True
                break
            except Exception as e:
                print(f"\n   ⚠️ Falha no lote {i} da tabela {tabela} (Tentativa {tentativa}/3). Reconectando...")
                time.sleep(3)
        if not sucesso:
            raise Exception(f"Falha de conexão definitiva ao inserir na tabela {tabela}.")

# --- PROCESSAMENTO PRINCIPAL EM LOTE ---
def processar():
    arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.lower().endswith('.pdf')]
    if not arquivos: 
        print(f"❌ Pasta '{PASTA_ENTRADA}' vazia!")
        return

    print(f"🔎 Encontrados {len(arquivos)} arquivo(s) PDF na pasta.")

    for idx, nome_pdf in enumerate(arquivos):
        print(f"\n{'='*60}")
        print(f"🔄 PROCESSANDO ARQUIVO {idx + 1} DE {len(arquivos)}: {nome_pdf}")
        print(f"{'='*60}")
        
        caminho_pdf = os.path.join(PASTA_ENTRADA, nome_pdf)
        competencia_global = extrair_competencia_do_nome(nome_pdf)
        print(f"📌 Competência detectada: {competencia_global}")

        data_banco = datetime.now().strftime('%Y-%m-%d')
        nome_pdf_remoto = f"PDFs/{competencia_global.replace('/', '_')}_{nome_pdf}"
        nome_json_remoto = f"INDICES/Indice_{competencia_global.replace('/', '_')}_{nome_pdf.replace('.pdf', '.json')}"

        link_pdf_final = forcar_upload_correto(caminho_pdf, nome_pdf_remoto, "application/pdf")
        if not link_pdf_final: 
            print(f"⏭️ Pulando arquivo {nome_pdf} devido a erro no upload.")
            continue

        pacientes_map = {} 
        lista_procedimentos_banco = []
        lista_valores_banco = []
        
        ultimo_paciente_valido = None
        chave_ativa = None
        
        try:
            with pdfplumber.open(caminho_pdf) as pdf:
                total_paginas = len(pdf.pages)
                for i, pagina in enumerate(pdf.pages):
                    num_pag = i + 1
                    if num_pag % 20 == 0: print(f"   Lendo Pag {num_pag}/{total_paginas}...")
                    
                    texto = pagina.extract_text() or ""
                    texto_sq = re.sub(r'\s+', '', texto).lower()
                    texto_flat = re.sub(r'\s+', ' ', texto) 
                    
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

                    is_continuation = (aih and ultimo_paciente_valido and aih == ultimo_paciente_valido['AIH'])

                    if is_continuation:
                        nome_base = ultimo_paciente_valido['NOME'].replace(" (Cont.)", "")
                        nome_cont = f"{nome_base} (Cont.)"
                        chave_ativa = f"{nome_cont}_{aih}_{num_pag}"
                        
                        pacientes_map[chave_ativa] = {
                            'NOME': nome_cont, 'AIH': aih, 'PRONTUARIO': ultimo_paciente_valido['PRONTUARIO'], 
                            'ESPEC': ultimo_paciente_valido['ESPEC'], 'CNS': ultimo_paciente_valido['CNS'], 
                            'PROC': ultimo_paciente_valido['PROC'], 'DT_INT': dt_int if dt_int != "-" else ultimo_paciente_valido['DT_INT'], 
                            'DT_SAI': dt_sai if dt_sai != "-" else ultimo_paciente_valido['DT_SAI'], 
                            'PAGINA': num_pag, 'procedimentos': [], 'valores': [], 'valor_total': "0,00"
                        }
                        ultimo_paciente_valido = pacientes_map[chave_ativa].copy()

                    elif nome and aih:
                        chave_ativa = f"{nome}_{aih}_{num_pag}"
                        pacientes_map[chave_ativa] = { 'NOME': nome, 'AIH': aih, 'PRONTUARIO': pront, 'ESPEC': espec, 'CNS': cns, 'PROC': proc, 'DT_INT': dt_int, 'DT_SAI': dt_sai, 'PAGINA': num_pag, 'procedimentos': [], 'valores': [], 'valor_total': "0,00" }
                        ultimo_paciente_valido = pacientes_map[chave_ativa].copy()
                    else: continue 

                    m_bloco_proc = re.search(r'PROCEDIMENTOS\s+REALIZADOS(.*?)VALORES\s+DA\s+PR[EÉ]VIA', texto_flat, re.IGNORECASE)
                    if m_bloco_proc:
                        bloco = m_bloco_proc.group(1)
                        bloco = re.sub(r'Linha\s+Procedimento.*?Descri[cç][aã]o', '', bloco, flags=re.IGNORECASE)
                        padrao = r'\b(\d{1,3})\s+(\d{10}\b.*?\d{2}/\d{4}.*?)(?=\s+\b\d{1,3}\s+\d{10}\b|$)'
                        for m in re.finditer(padrao, bloco):
                            lnh = m.group(1)
                            dados_proc = desamassar_linha_procedimento(m.group(2).strip())
                            if dados_proc:
                                dados_proc['linha'] = lnh
                                pacientes_map[chave_ativa]['procedimentos'].append(dados_proc)
                                lista_procedimentos_banco.append({
                                    "competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": pacientes_map[chave_ativa]['NOME'],
                                    "linha": lnh, "codigo": dados_proc["codigo"], "qtde": dados_proc["qtde"], "cmpt": dados_proc["cmpt"],
                                    "documento_cnes": dados_proc["doc_cnes"], "descricao": dados_proc["descricao"]
                                })

                    m_bloco_val = re.search(r'VALORES\s+DA\s+PR[EÉ]VIA(.*?)(?:SERVI[CÇ]O/CLASSIFICA|CNAER:|$)', texto_flat, re.IGNORECASE)
                    if m_bloco_val:
                        b_val = m_bloco_val.group(1)
                        b_val = re.sub(r'Serviço Hospitalar.*?Terceiro', '', b_val, flags=re.IGNORECASE)
                        for m in re.finditer(r'(\d{2}\.\d{2}\.\d{2}\-[^\d].*?)(?=\s+\d{2}\.\d{2}\.\d{2}\-|\s+Total Geral:|$)', b_val, re.IGNORECASE):
                            item = m.group(1).strip()
                            m_sep = re.search(r'(.*?)\s+([\d\.\s,]+)$', item)
                            if m_sep:
                                vals = re.findall(r'[\d\.]*,\d{2}', m_sep.group(2))
                                val_ext = vals[-1] if vals else "0,00"
                                desc_ext = m_sep.group(1).strip()
                                pacientes_map[chave_ativa]['valores'].append({"descricao": desc_ext, "valor": val_ext})
                                lista_valores_banco.append({"competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": pacientes_map[chave_ativa]['NOME'], "grupo_consolidado": desc_ext, "valor_rs": val_ext})
                                
                        m_tot = re.search(r'Total Geral:\s*([\d\.\s,]+)', b_val, re.IGNORECASE)
                        if m_tot:
                            vals = re.findall(r'[\d\.]*,\d{2}', m_tot.group(1))
                            if vals: 
                                pacientes_map[chave_ativa]['valor_total'] = vals[-1]
                                lista_valores_banco.append({"competencia_arquivo": competencia_global, "pagina": num_pag, "aih": aih, "paciente": pacientes_map[chave_ativa]['NOME'], "grupo_consolidado": "TOTAL GERAL", "valor_rs": vals[-1]})

        except Exception as e: 
            print(f"❌ Erro Crítico ao processar PDF {nome_pdf}: {e}")
            continue

        print(f"✅ Extrato concluído para {nome_pdf}: {len(pacientes_map)} páginas validadas.")

        print("💾 Gravando arquivo JSON (Dados Puros)...")
        temp_file = os.path.join(BASE_DIR, "temp_indice.json")
        dados_para_json = list(pacientes_map.values())
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(dados_para_json, f, ensure_ascii=False)
            
        link_json_final = forcar_upload_correto(temp_file, nome_json_remoto, "application/json; charset=utf-8")
        os.remove(temp_file)

        print("💾 Atualizando banco de dados no Supabase...")
        try:
            supabase.table("controle_simuladas").delete().eq("competencia_arquivo", competencia_global).execute()
            supabase.table("simuladas_procedimentos").delete().eq("competencia_arquivo", competencia_global).execute()
            supabase.table("simuladas_valores").delete().eq("competencia_arquivo", competencia_global).execute()

            supabase.table("controle_simuladas").insert({
                "data_arquivo": data_banco, 
                "nome_original": nome_pdf,
                "link_pdf": link_pdf_final, 
                "link_indice": link_json_final,
                "competencia_arquivo": competencia_global 
            }).execute()

            print("   Enviando Procedimentos...")
            inserir_com_tentativas("simuladas_procedimentos", lista_procedimentos_banco)
                
            print("   Enviando Valores...")
            inserir_com_tentativas("simuladas_valores", lista_valores_banco)
                
            print(f"✅ Arquivo {nome_pdf} processado e sincronizado com sucesso!")
        except Exception as e: 
            print(f"⚠️ Erro ao salvar no banco para {nome_pdf}: {e}")

    print(f"\n🎉 FIM! TODOS OS {len(arquivos)} ARQUIVOS FORAM PROCESSADOS.")

if __name__ == "__main__":
    processar()