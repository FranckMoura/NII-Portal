import pdfplumber
import pandas as pd
import re
import os
import sys

print("--- 📄 EXTRATOR DE ÍNDICE DE PACIENTES (V2.0 - MULTIPAGE) ---")

# --- 1. CONFIGURAÇÃO INTELIGENTE ---
arquivos_na_pasta = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]

if not arquivos_na_pasta:
    print("❌ ERRO: Nenhum arquivo PDF encontrado nesta pasta!")
    input("Pressione Enter para sair...")
    sys.exit()

nome_arquivo_pdf = arquivos_na_pasta[0]
pasta_destino = 'arquivos'
nome_arquivo_saida = os.path.join(pasta_destino, 'indice_pacientes.html')

if not os.path.exists(pasta_destino): os.makedirs(pasta_destino)

print(f"📄 Lendo: {nome_arquivo_pdf}")

# --- 2. LÓGICA DE EXTRAÇÃO AVANÇADA ---
dados_extraidos = []

# Variáveis de "Memória" para páginas de continuação
ultimo_paciente_valido = {
    'nome': None,
    'aih': None,
    'prontuario': None
}

print("   Processando páginas...")

with pdfplumber.open(nome_arquivo_pdf) as pdf:
    total_paginas = len(pdf.pages)
    
    for i, pagina in enumerate(pdf.pages):
        num_pag = i + 1
        # Feedback de progresso a cada 50 páginas
        if num_pag % 50 == 0: print(f"   -> Lendo página {num_pag}/{total_paginas}...")
        
        texto = pagina.extract_text(x_tolerance=2)
        if not texto: continue

        # Tentativa de captura via Regex
        match_nome = re.search(r'Paciente\s*:\s*(.*?)\s*Prontuário', texto)
        match_aih = re.search(r'Num AIH\s*:\s*([\d-]+)', texto)
        match_pront = re.search(r'Prontuário\s*:\s*(\d+)', texto)

        nome_encontrado = match_nome.group(1).strip() if match_nome else None
        aih_encontrada = match_aih.group(1).strip() if match_aih else None
        pront_encontrado = match_pront.group(1).strip() if match_pront else None

        # --- LÓGICA DE DECISÃO ---
        
        # CASO 1: Página Capa (Tem Nome e AIH) -> É um novo paciente ou nova conta
        if nome_encontrado and aih_encontrada:
            registro = {
                'NOME': nome_encontrado,
                'AIH': aih_encontrada,
                'PRONTUARIO': pront_encontrado if pront_encontrado else "N/A",
                'PAGINA': num_pag
            }
            # Atualiza a memória
            ultimo_paciente_valido = {
                'nome': nome_encontrado,
                'aih': aih_encontrada,
                'prontuario': pront_encontrado
            }
            dados_extraidos.append(registro)

        # CASO 2: Página de Continuação (Sem Nome, mas tem AIH)
        elif not nome_encontrado and aih_encontrada:
            # Verifica se a AIH bate com a do último paciente lido
            if ultimo_paciente_valido['aih'] == aih_encontrada:
                # É continuação! Usamos os dados da memória
                registro = {
                    'NOME': ultimo_paciente_valido['nome'], # Pega o nome memorizado
                    'AIH': aih_encontrada,
                    'PRONTUARIO': ultimo_paciente_valido['prontuario'],
                    'PAGINA': num_pag
                }
                dados_extraidos.append(registro)
            else:
                # É uma AIH órfã (estranho, mas registramos como desconhecido para não perder a página)
                dados_extraidos.append({
                    'NOME': "--- (Continuação Desconhecida)",
                    'AIH': aih_encontrada,
                    'PRONTUARIO': "-",
                    'PAGINA': num_pag
                })

print(f"✅ Leitura concluída! {len(dados_extraidos)} páginas mapeadas.")

# --- 3. GERAÇÃO DO HTML (PADRÃO PORTAL) ---
if dados_extraidos:
    # Cria DataFrame para facilitar ordenação se necessário
    df = pd.DataFrame(dados_extraidos)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Índice de Pacientes</title>
        
        <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

        <style>
            :root {{ --primary: #0056b3; --success: #28a745; --dark: #343a40; }}
            body {{ font-family: 'Roboto', sans-serif; background: #f4f6f9; padding: 20px; padding-bottom: 80px; }}
            
            .header {{ 
                background: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center;
            }}
            .header h1 {{ margin: 0; font-size: 20px; color: var(--primary); }}
            .header small {{ color: #666; font-size: 14px; }}

            .table-container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            
            /* Tabela Compacta */
            table.dataTable tbody td {{ padding: 6px 10px; font-size: 13px; vertical-align: middle; }}
            table.dataTable thead th {{ background-color: var(--primary); color: white; padding: 8px 10px; font-size: 14px; }}
            
            .btn-add {{ 
                background: var(--success); color: white; border: none; padding: 4px 10px; 
                border-radius: 4px; cursor: pointer; font-size: 12px; transition: 0.2s;
            }}
            .btn-add:hover {{ background: #218838; }}
            .btn-added {{ background: #6c757d; cursor: not-allowed; }}

            /* Barra Flutuante de Coleta */
            .collection-bar {{
                position: fixed; bottom: 0; left: 0; width: 100%;
                background: var(--dark); color: white; padding: 15px 20px;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.2); z-index: 1000;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .pages-display {{ font-family: monospace; color: #ffc107; font-size: 14px; max-width: 70%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
            .btn-copy {{
                background: #007bff; color: white; border: none; padding: 8px 15px;
                border-radius: 4px; font-weight: bold; cursor: pointer;
            }}
            .btn-copy:hover {{ background: #0056b3; }}
            .btn-clear {{ background: transparent; border: 1px solid #6c757d; color: #ccc; margin-left: 10px; padding: 8px; border-radius: 4px; cursor:pointer; }}
        </style>
    </head>
    <body>

        <div class="header">
            <div>
                <h1><i class="fas fa-file-medical"></i> Índice de Pacientes (Simuladas)</h1>
                <small>Arquivo: {nome_arquivo_pdf}</small>
            </div>
            <div>
                <a href="../index.html" style="text-decoration:none; color: #666; font-size:14px;">
                    <i class="fas fa-arrow-left"></i> Voltar ao Portal
                </a>
            </div>
        </div>

        <div class="table-container">
            <table id="tabelaPacientes" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Página</th>
                        <th>Paciente</th>
                        <th>AIH</th>
                        <th>Prontuário</th>
                        <th style="width:80px; text-align:center;">Ação</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Preenche as linhas da tabela
    for _, row in df.iterrows():
        html_content += f"""
                    <tr>
                        <td><span style="font-weight:bold; color:#0056b3;">{row['PAGINA']}</span></td>
                        <td>{row['NOME']}</td>
                        <td>{row['AIH']}</td>
                        <td>{row['PRONTUARIO']}</td>
                        <td style="text-align:center;">
                            <button class="btn-add" onclick="addPage({row['PAGINA']}, this)">
                                <i class="fas fa-plus"></i> Incluir
                            </button>
                        </td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>
        </div>

        <div class="collection-bar">
            <div>
                <strong>Páginas Selecionadas:</strong>
                <span id="pageList" class="pages-display">Nenhuma página selecionada</span>
            </div>
            <div>
                <button class="btn-clear" onclick="clearPages()" title="Limpar Seleção"><i class="fas fa-trash"></i></button>
                <button class="btn-copy" onclick="copyAllPages()" id="btnCopy">
                    <i class="fas fa-copy"></i> COPIAR LISTA
                </button>
            </div>
        </div>

        <script>
            $(document).ready(function() {
                $('#tabelaPacientes').DataTable({
                    language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" },
                    pageLength: 15,
                    order: [[0, 'asc']] // Ordena pela página
                });
            });

            var collectedPages = [];
            var pageListElement = document.getElementById('pageList');

            function addPage(pageNumber, btn) {
                if (!collectedPages.includes(pageNumber)) {
                    collectedPages.push(pageNumber);
                    collectedPages.sort(function(a, b){return a - b}); // Ordena numérico
                    updateDisplay();
                    
                    // Feedback visual no botão
                    btn.classList.add('btn-added');
                    btn.innerHTML = '<i class="fas fa-check"></i>';
                }
            }

            function updateDisplay() {
                if(collectedPages.length === 0) {
                    pageListElement.textContent = "Nenhuma página selecionada";
                } else {
                    pageListElement.textContent = collectedPages.join(', ');
                }
            }

            function clearPages() {
                collectedPages = [];
                updateDisplay();
                // Reseta botões visuais (opcional, requer recarregar ou lógica complexa de DOM, simplificado aqui)
                $('.btn-added').removeClass('btn-added').html('<i class="fas fa-plus"></i> Incluir');
            }

            function copyAllPages() {
                if (collectedPages.length > 0) {
                    var textToCopy = collectedPages.join(',');
                    navigator.clipboard.writeText(textToCopy).then(function() {
                        var btn = document.getElementById('btnCopy');
                        var originalText = btn.innerHTML;
                        btn.innerHTML = '<i class="fas fa-check-double"></i> COPIADO!';
                        btn.style.background = '#28a745';
                        
                        setTimeout(function() { 
                            btn.innerHTML = originalText; 
                            btn.style.background = '#007bff';
                        }, 2000);
                    }, function(err) {
                        alert('Erro ao copiar: ' + err);
                    });
                } else {
                    alert('Selecione pelo menos uma página.');
                }
            }
        </script>
    </body>
    </html>
    """

    with open(nome_arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n🎉 SUCESSO! Arquivo gerado: {nome_arquivo_saida}")
    print("   Abra este arquivo no navegador para ver o novo layout.")

else:
    print("\n⚠️ NENHUM DADO EXTRAÍDO. O PDF pode ser imagem (escaneado) ou formato não reconhecido.")