import pdfplumber
import pandas as pd
import re
import os

print("--- 🚀 SCRIPT DEFINITIVO: EXTRAÇÃO DE PDF REAL ---")

# AQUI ESTÁ O SEU ARQUIVO OFICIAL
arquivo_pdf = "SIMULADAS 0226.pdf" 

def extrair_dados_pdf():
    if not os.path.exists(arquivo_pdf):
        print(f"❌ Arquivo '{arquivo_pdf}' não encontrado na pasta!")
        return

    procedimentos = []
    valores = []

    print(f"Lendo o mega arquivo {arquivo_pdf}...")
    try:
        with pdfplumber.open(arquivo_pdf) as pdf:
            total_paginas = len(pdf.pages)
            print(f"📄 Total de páginas encontradas: {total_paginas}")
            
            for i, pagina in enumerate(pdf.pages):
                # Mostra o progresso a cada 50 páginas
                if (i + 1) % 50 == 0 or (i + 1) == total_paginas:
                    print(f"  ⏳ Processando página {i + 1} de {total_paginas}...")
                
                texto = pagina.extract_text()
                if not texto: continue
                
                # A MÁGICA: Achata o texto para ignorar colunas tortas
                texto_flat = re.sub(r'\s+', ' ', texto)

                # --- CABEÇALHO ---
                m_nome = re.search(r'Paciente\s*:\s*(.*?)(?:\s+Data Nasc|\s+Sexo|$)', texto_flat, re.IGNORECASE)
                nome = m_nome.group(1).replace('Prontuário', '').strip() if m_nome else "DESCONHECIDO"
                nome = re.sub(r'[:\-\.]*\s*\d+$', '', nome).strip()

                m_aih = re.search(r'Num AIH\s*:\s*([\d\-]+)', texto_flat, re.IGNORECASE)
                aih = m_aih.group(1).strip() if m_aih else "SEM_AIH"

                # --- PROCEDIMENTOS ---
                m_bloco_proc = re.search(r'PROCEDIMENTOS\s+REALIZADOS(.*?)VALORES\s+DA\s+PR[EÉ]VIA', texto_flat, re.IGNORECASE)
                if m_bloco_proc:
                    bloco = m_bloco_proc.group(1)
                    # Remove o cabeçalho da tabela
                    bloco = re.sub(r'Linha\s+Procedimento.*?Descri[cç][aã]o', '', bloco, flags=re.IGNORECASE)
                    
                    # Procura o padrão: Linha + Código + Resto
                    padrao = r'\b(\d{1,3})\s+(\d{10})\b\s*(.*?)(?=\s+\b\d{1,3}\s+\d{10}\b|$)'
                    for m in re.finditer(padrao, bloco):
                        lnh = m.group(1)
                        cod = m.group(2)
                        resto = m.group(3).strip()

                        # Procura Quantidade e Competência
                        m_qt = re.search(r'\b(\d{1,4})\s+(\d{2}/\d{4})\s+(.*)$', resto)
                        if m_qt:
                            qtde = m_qt.group(1)
                            cmpt = m_qt.group(2)
                            antes = resto[:m_qt.start()].strip()
                            depois = m_qt.group(3).strip()
                            
                            docs = [t for t in antes.split() if re.match(r'^\d+$', t)]
                            desc_words = []
                            for w in depois.split():
                                if re.match(r'^\d{4,}$', w):
                                    if w not in docs: docs.append(w)
                                else:
                                    desc_words.append(w)
                                    
                            procedimentos.append({
                                "Paciente": nome, "AIH": aih, "Página": i+1,
                                "Linha": lnh, "Código": cod, 
                                "Documento/CNES": " / ".join(docs) if docs else "-",
                                "Qtde": qtde, "Cmpt": cmpt, "Descrição": " ".join(desc_words)
                            })
                        else:
                            procedimentos.append({
                                "Paciente": nome, "AIH": aih, "Página": i+1,
                                "Linha": lnh, "Código": cod, 
                                "Documento/CNES": "-", "Qtde": "-", "Cmpt": "-", "Descrição": resto
                            })

                # --- VALORES FINANCEIROS ---
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
                            valores.append({"Paciente": nome, "AIH": aih, "Página": i+1, "Grupo": desc, "Valor": val})
                            
                    m_tot = re.search(r'Total Geral:\s*([\d\.\s,]+)', b_val, re.IGNORECASE)
                    if m_tot:
                        vals = re.findall(r'[\d\.]*,\d{2}', m_tot.group(1))
                        if vals:
                            valores.append({"Paciente": nome, "AIH": aih, "Página": i+1, "Grupo": "TOTAL GERAL", "Valor": vals[-1]})

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
        return

    # --- SALVAR RESULTADOS ---
    df_p = pd.DataFrame(procedimentos)
    df_v = pd.DataFrame(valores)

    print(f"\n✅ EXTRAÇÃO FINALIZADA COM SUCESSO!")
    print(f"📊 {len(df_p)} procedimentos extraídos (UAU!).")
    print(f"💰 {len(df_v)} valores financeiros extraídos.")

    if not df_p.empty: df_p.to_csv("01_procedimentos_extraidos.csv", index=False, sep=";", encoding="utf-8-sig")
    if not df_v.empty: df_v.to_csv("02_valores_financeiros.csv", index=False, sep=";", encoding="utf-8-sig")
    
    print("\n📁 CSVs gerados. Pode abrir o Excel e comemorar!")

if __name__ == "__main__":
    extrair_dados_pdf()