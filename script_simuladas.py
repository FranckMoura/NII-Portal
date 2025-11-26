import pdfplumber
import pandas as pd
import re
import os

# --- CONFIGURAÇÃO INTELIGENTE ---
# Em vez de um nome fixo, vamos procurar qualquer PDF na pasta
arquivos_na_pasta = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]

if not arquivos_na_pasta:
    print("❌ ERRO: Nenhum arquivo PDF foi encontrado nesta pasta!")
    print("Por favor, cole o arquivo das simuladas aqui dentro.")
    exit()

# Pega o primeiro PDF que encontrar (assume que só tem o das simuladas ou é o primeiro)
nome_arquivo_pdf = arquivos_na_pasta[0]

# Define onde o resultado será salvo
pasta_destino = 'arquivos'
nome_arquivo_saida = os.path.join(pasta_destino, 'indice_pacientes.html')

# Garante que a pasta 'arquivos' existe
if not os.path.exists(pasta_destino):
    os.makedirs(pasta_destino)

print(f"📄 Arquivo detectado: {nome_arquivo_pdf}")
print(f"Iniciando a leitura...")

# --- LÓGICA DE EXTRAÇÃO (MANTIDA) ---
# Lista para armazenar os dados de cada paciente
dados_extraidos = []

# Variáveis para rastrear informações parciais
partial_name = None
partial_aih = None
partial_prontuario = None
partial_page = None
last_aih = None 

with pdfplumber.open(nome_arquivo_pdf) as pdf:
    for i, pagina in enumerate(pdf.pages):
        texto_pagina = pagina.extract_text(x_tolerance=2)
        if not texto_pagina: continue

        nome_paciente_match = re.search(r'Paciente\s*:\s*(.*?)\s*Prontuário', texto_pagina)
        num_aih_match = re.search(r'Num AIH\s*:\s*([\d-]+)', texto_pagina)
        num_prontuario_match = re.search(r'Prontuário\s*:\s*(\d+)', texto_pagina)

        current_name = nome_paciente_match.group(1).strip() if nome_paciente_match else None
        current_aih = num_aih_match.group(1).strip() if num_aih_match else None
        current_prontuario = num_prontuario_match.group(1).strip() if num_prontuario_match else None

        if current_name or current_aih or current_prontuario:
            if (partial_name or partial_aih or partial_prontuario) and \
                ((current_aih and partial_aih and current_aih == partial_aih) or \
                (current_aih and not partial_aih and current_aih == last_aih) or \
                (not current_aih and partial_aih)):
                registro = {
                    'NOME DO PACIENTE': current_name if current_name else partial_name if partial_name else 'N/A',
                    'Nº DA AIH': current_aih if current_aih else partial_aih if partial_aih else last_aih if last_aih else 'N/A',
                    'PRONTUÁRIO': current_prontuario if current_prontuario else partial_prontuario if partial_prontuario else 'N/A',
                    'PÁGINA': partial_page if partial_page else i + 1 
                }
                # Checagem de duplicidade
                is_duplicate = False
                if current_name and current_aih and current_prontuario:
                        for rec in dados_extraidos:
                            if rec['NOME DO PACIENTE'] == current_name and rec['Nº DA AIH'] == current_aih and rec['PRONTUÁRIO'] == current_prontuario:
                                is_duplicate = True
                                break
                if not is_duplicate:
                    if not dados_extraidos or dados_extraidos[-1] != registro:
                        dados_extraidos.append(registro)

                partial_name = None
                partial_aih = None
                partial_prontuario = None
                partial_page = None

            elif current_name and current_aih and current_prontuario:
                registro = {
                    'NOME DO PACIENTE': current_name,
                    'Nº DA AIH': current_aih,
                    'PRONTUÁRIO': current_prontuario,
                    'PÁGINA': i + 1
                }
                if not dados_extraidos or dados_extraidos[-1] != registro:
                    dados_extraidos.append(registro)
                last_aih = current_aih 

            elif current_name or current_aih or current_prontuario:
                if partial_page is None: partial_page = i + 1
                if current_name: partial_name = current_name
                if current_aih:
                    partial_aih = current_aih
                    last_aih = current_aih
                if current_prontuario: partial_prontuario = current_prontuario
        
        elif partial_name or partial_aih or partial_prontuario:
            pass

# Verifica sobras finais
if partial_name or partial_aih or partial_prontuario:
    registro = {
        'NOME DO PACIENTE': partial_name if partial_name else 'N/A',
        'Nº DA AIH': partial_aih if partial_aih else last_aih if last_aih else 'N/A', 
        'PRONTUÁRIO': partial_prontuario if partial_prontuario else 'N/A',
        'PÁGINA': partial_page if partial_page else 'N/A'
    }
    if not dados_extraidos or dados_extraidos[-1] != registro:
        dados_extraidos.append(registro)

print("\nExtração finalizada.")

if dados_extraidos:
    df = pd.DataFrame(dados_extraidos)
    df_index = df[['NOME DO PACIENTE', 'Nº DA AIH', 'PRONTUÁRIO', 'PÁGINA']].copy()
    df_index = df_index.sort_values(by='NOME DO PACIENTE').reset_index(drop=True)
    print("\nGerando HTML...")

    # --- Geração do HTML ---
    with open(nome_arquivo_saida, 'w', encoding='utf-8') as f:
        f.write("<!DOCTYPE html>\n")
        f.write("<html lang='pt-br'>\n<head>\n<title>Índice de Pacientes</title>\n")
        f.write("<meta charset='UTF-8'>\n")
        f.write("<style>\n")
        f.write("body { font-family: 'Segoe UI', sans-serif; margin: 20px; background-color: #f4f7f6; color: #333; }\n")
        f.write("h1, h2 { color: #2c3e50; }\n")
        f.write("table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); background-color: #fff; }\n")
        f.write("th, td { padding: 12px 15px; border: 1px solid #ddd; text-align: left; }\n")
        f.write("thead th { background-color: #0056b3; color: white; font-size: 16px; }\n")
        f.write("tbody tr:nth-child(even) { background-color: #f9f9f9; }\n")
        f.write("tbody tr:hover { background-color: #e9f5ff; }\n")
        f.write("button { background-color: #28a745; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }\n")
        f.write("button:hover { background-color: #218838; }\n")
        f.write("#collectedPages { margin-top: 20px; border: 1px solid #ccc; padding: 15px; border-radius: 5px; background-color: #fff; }\n")
        f.write("#pageList { font-weight: bold; color: #d9534f; }\n")
        f.write("#copyButton { background-color: #007bff; margin-top: 10px; }\n")
        f.write("</style>\n")
        f.write("</head>\n<body>\n")
        f.write(f"<h1>Índice de Pacientes - Arquivo: {nome_arquivo_pdf}</h1>\n\n") # Mostra o nome do arquivo lido
        f.write("<div id='collectedPages'>\n")
        f.write("<h2>Páginas Coletadas:</h2>\n")
        f.write("<p id='pageList'></p>\n")
        f.write("<button id='copyButton' onclick='copyAllPages()'>Copiar Todas as Páginas</button>\n")
        f.write("</div>\n\n")

        f.write("<table>\n<thead>\n<tr>\n")
        f.write("<th>NOME DO PACIENTE</th><th>Nº DA AIH</th><th>PRONTUÁRIO</th><th>PÁGINA</th><th>AÇÃO</th>\n")
        f.write("</tr>\n</thead>\n<tbody>\n")
        
        for index, row in df_index.iterrows():
            f.write("<tr>\n")
            f.write(f"<td>{row['NOME DO PACIENTE']}</td>\n")
            f.write(f"<td>{row['Nº DA AIH']}</td>\n")
            f.write(f"<td>{row['PRONTUÁRIO']}</td>\n")
            f.write(f"<td>{row['PÁGINA']}</td>\n")
            f.write(f"<td><button onclick='addPage({row['PÁGINA']})'>Adicionar</button></td>\n")
            f.write("</tr>\n")
        f.write("</tbody>\n</table>\n\n")

        f.write("<script>\n")
        f.write("var collectedPages = [];\n")
        f.write("var pageListElement = document.getElementById('pageList');\n")
        f.write("function addPage(pageNumber) {\n")
        f.write("  if (!collectedPages.includes(pageNumber)) {\n")
        f.write("    collectedPages.push(pageNumber);\n")
        f.write("    collectedPages.sort(function(a, b){return a - b});\n")
        f.write("    updatePageList();\n")
        f.write("  }\n")
        f.write("}\n")
        f.write("function updatePageList() {\n")
        f.write("  pageListElement.textContent = collectedPages.join(', ');\n")
        f.write("}\n")
        f.write("function copyAllPages() {\n")
        f.write("  if (collectedPages.length > 0) {\n")
        f.write("    var textToCopy = collectedPages.join(',');\n")
        f.write("    navigator.clipboard.writeText(textToCopy).then(function() {\n")
        f.write("      var button = document.getElementById('copyButton');\n")
        f.write("      button.textContent = 'Copiado!';\n")
        f.write("      setTimeout(function() { button.textContent = 'Copiar Todas as Páginas'; }, 2000);\n")
        f.write("    }, function(err) {\n")
        f.write("      alert('Erro ao copiar: ' + err);\n")
        f.write("    });\n")
        f.write("  } else {\n")
        f.write("    alert('Nenhuma página coletada.');\n")
        f.write("  }\n")
        f.write("}\n")
        f.write("</script>\n")
        f.write("</body>\n</html>")

    print(f"\n🎉 Sucesso! O arquivo '{nome_arquivo_saida}' foi criado.")
    print("Agora, ao rodar o 'upload_manager.py', este arquivo aparecerá no Portal.")
else:
    print("\nNenhum dado foi extraído. Verifique o PDF.")