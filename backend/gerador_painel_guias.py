import os
import pandas as pd
import glob
import json

print("--- 🚀 GERADOR DE PAINEL DE GUIAS (TURBINADO 56K+ com Filtros) ---")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_FRONTEND = os.path.join(os.path.dirname(BASE_DIR), "frontend")
if not os.path.exists(PASTA_FRONTEND): PASTA_FRONTEND = BASE_DIR

ARQUIVO_HTML = os.path.join(PASTA_FRONTEND, "Painel_Guias.html")
PASTA_CSV = os.path.join(BASE_DIR, "solus_unimed")

def encontrar_arquivo_csv():
    if not os.path.exists(PASTA_CSV): os.makedirs(PASTA_CSV)
    padrao_busca = os.path.join(PASTA_CSV, "*.csv")
    arquivos_encontrados = glob.glob(padrao_busca)
    if arquivos_encontrados: return max(arquivos_encontrados, key=os.path.getmtime)
    return None

def processar_guias():
    arquivo_csv = encontrar_arquivo_csv()
    
    if not arquivo_csv:
        print(f"❌ Nenhum arquivo CSV encontrado na pasta: {PASTA_CSV}")
        return

    nome_base = os.path.basename(arquivo_csv)
    print(f"📄 Lendo arquivo encontrado: {nome_base}...")
    
    try:
        df = pd.read_csv(arquivo_csv, sep=';', encoding='latin1', dtype=str)
    except Exception as e:
        print(f"❌ Erro ao tentar abrir o arquivo: {e}")
        return

    df = df.fillna("-")
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    dados_json = df.to_json(orient="records")

    print(f"✅ Arquivo compactado! Gerando painel HTML com {len(df)} registros...")

    html_code = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Guias - NII</title>
    
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>

    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        body {{ font-family: 'Roboto', sans-serif; background: #f3f4f6; color: #1e293b; padding: 0; margin: 0; min-height: 100vh; padding-bottom: 50px; }}
        .header-bg {{ background: linear-gradient(135deg, #000428 0%, #004e92 100%) !important; color: white !important; padding: 25px 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); margin-bottom: 25px; }}
        .header-mini-logo {{ height: 40px; margin-right: 15px; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.3)); }}
        .container {{ max-width: 1500px; margin: 0 auto; padding: 0 15px; }}
        .btn-back {{ background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; display: flex; align-items: center; gap: 8px; text-decoration: none; }}
        .btn-back:hover {{ background: rgba(255,255,255,0.3); color: white; }}
        
        .table-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb; overflow-x: auto; }}
        table.dataTable {{ width: 100% !important; border-collapse: collapse !important; }}
        table.dataTable thead th {{ background-color: #004e92 !important; color: white !important; font-weight: 700 !important; text-transform: uppercase; padding: 10px 8px !important; font-size: 0.75rem; white-space: nowrap; border: none; }}
        table.dataTable tbody td {{ padding: 8px 10px !important; border-bottom: 1px solid #f1f5f9; color: #334155; font-size: 0.75rem; vertical-align: middle; }}
        .dt-button {{ background: #10b981 !important; color: white !important; border: none !important; border-radius: 6px !important; padding: 6px 12px !important; font-weight: 600 !important; font-size: 0.75rem !important; }}
        .dt-button:hover {{ background: #059669 !important; }}
        
        .badge-tipo {{ padding: 3px 6px; border-radius: 4px; font-weight: 800; font-size: 0.7rem; letter-spacing: 0.5px; text-transform: uppercase; }}
        .tipo-proc {{ background: #dbeafe; color: #1e40af; }}
        .tipo-taxa {{ background: #fef08a; color: #854d0e; }}
        .tipo-opme {{ background: #fce7f3; color: #9d174d; }}
        
        .btn-detalhes {{ background-color: #f3f4f6; border: 1px solid #d1d5db; color: #4b5563; padding: 5px 12px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: 0.2s; white-space: nowrap; }}
        .btn-detalhes:hover {{ background-color: #e5e7eb; color: #111827; }}

        #modalDetalhes {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; backdrop-filter: blur(4px); }}
        .modal-content {{ background: white; width: 90%; max-width: 800px; border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); overflow: hidden; animation: slideUp 0.3s ease-out; max-height: 90vh; display: flex; flex-direction: column; }}
        @keyframes slideUp {{ from {{ transform: translateY(20px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
        .modal-header {{ background: #004e92; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }}
        .modal-header h2 {{ margin: 0; font-size: 1.2rem; font-weight: bold; }}
        .btn-close {{ background: transparent; border: none; color: white; font-size: 1.5rem; cursor: pointer; transition: 0.2s; }}
        .btn-close:hover {{ color: #fca5a5; }}
        .modal-body {{ padding: 20px; overflow-y: auto; background: #f8fafc; }}
        
        .detalhe-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .detalhe-item {{ background: white; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; }}
        .detalhe-label {{ font-size: 0.65rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 4px; }}
        .detalhe-valor {{ font-size: 0.85rem; font-weight: 600; color: #0f172a; word-break: break-word; }}
        
        .filtro-container {{ background: white; padding: 15px 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #e5e7eb; display: flex; flex-wrap: wrap; gap: 20px; align-items: center; }}
        .filtro-box {{ display: flex; flex-direction: column; gap: 5px; }}
        .filtro-box label {{ font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; }}
        .filtro-box select, .filtro-box input {{ padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; outline: none; font-weight: 600; color: #1e293b; font-size: 0.85rem; }}
        
        /* Caixas de pesquisa nas colunas */
        .search-input {{ width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.7rem; font-weight: normal; color: #334155; outline: none; }}
        .search-input:focus {{ border-color: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }}
    </style>
</head>
<body>

    <div class='header-bg'>
        <div class='max-w-7xl mx-auto flex justify-between items-center px-4'>
            <div class="flex items-center gap-4">
                <div class="bg-white/20 p-3 rounded-lg"><i class="fa-solid fa-file-medical-alt text-3xl"></i></div>
                <div>
                    <h1 class='text-3xl font-bold'>Painel de Guias</h1>
                    <p class='text-gray-300'>Visualização Simplificada de Atendimentos</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <img src="logo.png" alt="Logo HSH" class="header-mini-logo" onerror="this.style.display='none'">
                <a href="modulo_operacional.html" class="btn-back"><i class="fas fa-arrow-left"></i> Voltar</a>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="filtro-container">
            <div class="filtro-box">
                <label><i class="fas fa-filter"></i> Mostrar Tipo:</label>
                <select id="filtroTipo">
                    <option value="PROCEDIMENTO" selected>Apenas Procedimentos (Principal)</option>
                    <option value="TAXA">Apenas Taxas</option>
                    <option value="OPME">Apenas OPME</option>
                    <option value="">Mostrar Tudo (Completo)</option>
                </select>
            </div>
            
            <div class="filtro-box">
                <label><i class="far fa-calendar-alt"></i> Período de Emissão:</label>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <input type="date" id="dataIni">
                    <span class="text-gray-500 font-bold">até</span>
                    <input type="date" id="dataFim">
                    <button onclick="limparDatas()" class="text-xs text-blue-500 hover:text-blue-700 font-bold ml-2 underline cursor-pointer bg-transparent border-none">Limpar Datas</button>
                </div>
            </div>
        </div>
        
        <div class="table-card">
            <table id="tabelaGuias" class="display compact w-full">
                <thead>
                    <tr>
                        <th style="width: 150px;">Beneficiário</th>
                        <th style="width: 70px;">Carteirinha</th>
                        <th style="width: 60px;">Guia</th>
                        <th style="width: 60px;">Tipo</th>
                        <th>Procedimento / Item</th>
                        <th style="width: 60px;">Código</th>
                        <th style="width: 100px;">Especialidade</th>
                        <th style="width: 100px;">Prestador</th>
                        <th style="width: 70px;">Emissão</th>
                        <th style="width: 80px; text-align:center;">Ações</th>
                    </tr>
                    <tr class="table-search no-print">
                        </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <div id="modalDetalhes">
        <div class="modal-content">
            <div class="modal-header">
                <h2><i class="fas fa-file-invoice-dollar mr-2"></i> Detalhes Completos da Linha</h2>
                <button class="btn-close" onclick="fecharModal()"><i class="fas fa-times"></i></button>
            </div>
            <div class="modal-body">
                <div class="detalhe-grid" id="modalConteudo"></div>
            </div>
        </div>
    </div>

    <script>
        var datasetLocal = {dados_json}; 
        var tabela;
        
        // FUNÇÃO DE FILTRO DE DATAS CUSTOMIZADO (Lê o formato DD/MM/YY HH:MM:SS)
        $.fn.dataTable.ext.search.push(
            function( settings, data, dataIndex ) {{
                var minStr = $('#dataIni').val(); 
                var maxStr = $('#dataFim').val();
                
                if (!minStr && !maxStr) return true; // Se não tiver data, mostra tudo

                var emissaoFull = data[8] || ""; // Coluna Emissão
                if (!emissaoFull || emissaoFull === "-") return false;

                // Extrai DD/MM/YY e converte para Date
                var partes = emissaoFull.split(' ')[0].split('/');
                if(partes.length !== 3) return true;
                
                var dia = parseInt(partes[0], 10);
                var mes = parseInt(partes[1], 10) - 1;
                var anoStr = partes[2];
                var ano = anoStr.length === 2 ? parseInt("20" + anoStr, 10) : parseInt(anoStr, 10);

                var dataLinha = new Date(ano, mes, dia);
                
                var minDate = minStr ? new Date(minStr.split('-')[0], minStr.split('-')[1] - 1, minStr.split('-')[2]) : null;
                var maxDate = maxStr ? new Date(maxStr.split('-')[0], maxStr.split('-')[1] - 1, maxStr.split('-')[2]) : null;

                if (
                    ( minDate === null && dataLinha <= maxDate ) ||
                    ( minDate <= dataLinha && maxDate === null ) ||
                    ( minDate <= dataLinha && dataLinha <= maxDate )
                ) {{
                    return true;
                }}
                return false;
            }}
        );

        $(document).ready(function() {{
            
            // CONSTRÓI AS CAIXINHAS DE PESQUISA NAS COLUNAS
            $('#tabelaGuias thead tr:eq(0) th').each( function (i) {{
                if(i === 9) {{ // Coluna de Ações
                    $('.table-search').append('<th></th>');
                }} else {{
                    $('.table-search').append('<th><input type="text" placeholder="Buscar..." class="search-input" /></th>');
                }}
            }});

            tabela = $('#tabelaGuias').DataTable({{
                data: datasetLocal, 
                deferRender: true,  
                orderCellsTop: true, // Avisa a tabela que a linha de pesquisa existe
                language: {{ url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pt-BR.json" }},
                dom: 'Bfrtip',
                pageLength: 50,
                order: [[0, 'asc']],
                buttons: [
                    {{ extend: 'excelHtml5', text: '<i class="fas fa-file-excel"></i> Exportar para Excel', className: 'dt-button' }}
                ],
                columns: [
                    {{ data: 'BENEFICIARIO', render: function(d) {{ return d ? `<span class="font-bold text-gray-800 uppercase" title="${{d}}">${{d.length > 25 ? d.substring(0,25)+'...' : d}}</span>` : '-'; }} }},
                    {{ data: 'CARTEIRINHA', render: function(d) {{ return d ? `<span class="text-gray-500 font-medium">${{d}}</span>` : '-'; }} }},
                    {{ data: 'GUIA', render: function(d) {{ return d ? `<span class="font-bold text-blue-700">${{d}}</span>` : '-'; }} }},
                    {{ data: 'TIPO', render: function(d) {{ 
                        if(!d) return '-';
                        var t = d.toUpperCase();
                        var c = "bg-gray-200 text-gray-700";
                        if(t.includes('PROCEDIMENTO')) c = "tipo-proc";
                        if(t.includes('TAXA')) c = "tipo-taxa";
                        if(t.includes('OPME')) c = "tipo-opme";
                        return `<span class="badge-tipo ${{c}}">${{t}}</span>`;
                    }} }},
                    {{ data: 'PROCEDIMENTO', render: function(d) {{ return d ? `<span title="${{d}}">${{d.length > 45 ? d.substring(0,45)+'...' : d}}</span>` : '-'; }} }},
                    {{ data: 'CODIGO', render: function(d) {{ return d ? `<span class="text-gray-600 font-bold">${{d}}</span>` : '-'; }} }},
                    {{ data: 'ESPECIALIDADE', render: function(d) {{ return d ? `<span class="text-gray-500 text-xs uppercase">${{d}}</span>` : '-'; }} }},
                    {{ data: 'PRESTADOR', render: function(d) {{ return d ? `<span class="text-gray-500 text-xs uppercase" title="${{d}}">${{d.length > 20 ? d.substring(0,20)+'...' : d}}</span>` : '-'; }} }},
                    {{ data: 'EMISSAO' }},
                    {{ data: null, render: function(data, type, row) {{
                        var rowData = encodeURIComponent(JSON.stringify(row));
                        return `<button class="btn-detalhes" onclick="abrirModal('${{rowData}}')"><i class="fas fa-eye"></i> Detalhes</button>`;
                    }}, className: "text-center" }}
                ],
                initComplete: function () {{
                    // ATIVA AS CAIXINHAS DE PESQUISA
                    this.api().columns().every( function () {{
                        var that = this;
                        $('input', $('.table-search th').eq(this.index())).on('keyup change clear', function () {{
                            if (that.search() !== this.value) {{
                                that.search(this.value).draw();
                            }}
                        }});
                    }});
                }}
            }});

            // ATIVA O FILTRO "TIPO"
            $('#filtroTipo').on('change', function() {{
                var val = $(this).val();
                tabela.column(3).search(val ? '^' + val + '$' : '', true, false).draw();
            }});

            // ATIVA O FILTRO DE DATAS
            $('#dataIni, #dataFim').on('change', function() {{
                tabela.draw();
            }});

            // Dispara o filtro "PROCEDIMENTO" logo ao carregar a página
            $('#filtroTipo').trigger('change');
        }});

        function limparDatas() {{
            $('#dataIni').val('');
            $('#dataFim').val('');
            tabela.draw();
        }}

        function abrirModal(dadosJsonStr) {{
            const dados = JSON.parse(decodeURIComponent(dadosJsonStr));
            const container = $('#modalConteudo');
            container.empty();

            const ignorar = ["Unnamed: 23"];

            for (const [chave, valor] of Object.entries(dados)) {{
                if (ignorar.includes(chave)) continue;
                
                let valFormatado = valor;
                if (!valFormatado || valFormatado === "-") valFormatado = "<span class='text-gray-400 italic'>Não informado</span>";

                container.append(`
                    <div class="detalhe-item">
                        <div class="detalhe-label">${{chave}}</div>
                        <div class="detalhe-valor">${{valFormatado}}</div>
                    </div>
                `);
            }}
            $('#modalDetalhes').css('display', 'flex');
        }}

        function fecharModal() {{ $('#modalDetalhes').css('display', 'none'); }}
        $(window).on('click', function(event) {{ if ($(event.target).is('#modalDetalhes')) {{ fecharModal(); }} }});
    </script>
</body>
</html>
"""

    with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html_code)
    
    print(f"🎉 Painel HTML criado com sucesso e incrivelmente leve!")
    os.startfile(ARQUIVO_HTML)

if __name__ == "__main__":
    processar_guias()