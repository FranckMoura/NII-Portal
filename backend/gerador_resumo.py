import pdfplumber
import re
import os

def extrair_texto_pdf(caminho_arquivo):
    texto_completo = ""
    with pdfplumber.open(caminho_arquivo) as pdf:
        for pagina in pdf.pages:
            texto_completo += pagina.extract_text() + "\n"
    return texto_completo

def processar_dados():
    # 1. Carregar os textos dos PDFs
    texto_protocolo = extrair_texto_pdf("PROTOCOLO_REMESSA_0526.pdf")
    texto_receita = extrair_texto_pdf("R_RECEITA_PROCEDIMENTO_GERAL_0526.pdf")

    # 2. Extrair Produção por Especialidade (Protocolo)
    # Busca o padrão: "01-CIRURGICO", "230"
    especialidades = {
        "02-OBSTETRICOS": re.search(r'(\d+)\s+02-OBSTETRICOS', texto_protocolo).group(1),
        "01-CIRURGICO": re.search(r'(\d+)\s+01-CIRURGICO', texto_protocolo).group(1),
        "07-PEDIATRICOS": re.search(r'(\d+)\s+07-PEDIATRICOS', texto_protocolo).group(1),
        "03-CLINICOS": re.search(r'(\d+)\s+03-CLINICOS', texto_protocolo).group(1)
    }
    total_aihs = re.search(r'Total QTD:\s+(\d+)', texto_protocolo).group(1)

    # 3. Extrair Diárias de UTI e Neonatal (Receita)
    # Busca o código, descrição, quantidade e valor total
    diarias = {
        "UTI Adulto": re.search(r'0802010083.*?(\d+)\s+[\d\.]+\,\d+\s+[\d\.]+\,\d+\s+([\d\.]+\,\d+)', texto_receita),
        "UTI Neonatal": re.search(r'0802010121.*?(\d+)\s+[\d\.]+\,\d+\s+[\d\.]+\,\d+\s+([\d\.]+\,\d+)', texto_receita),
        "UCINCo": re.search(r'0802010237.*?(\d+)\s+[\d\.]+\,\d+\s+[\d\.]+\,\d+\s+([\d\.]+\,\d+)', texto_receita),
        "UCINCa": re.search(r'0802010245.*?(\d+)\s+[\d\.]+\,\d+\s+[\d\.]+\,\d+\s+([\d\.]+\,\d+)', texto_receita)
    }

    # 4. Gerar Código HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resumo de Faturamento SUS</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h3 {{ color: #34495e; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; font-weight: 600; color: #2c3e50; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .header-info {{ background: #eef2f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
        </style>
    </head>
    <body>

        <div class="header-info">
            <h2>Resumo Executivo de Faturamento SUS</h2>
            <p><strong>Hospital Beneficente Santa Helena</strong> | CNES: 231168-2</p>
            <p><strong>Competência:</strong> 05/2026 | <strong>Apresentação:</strong> 06/2026</p>
        </div>

        <h3>1. Produção de AIHs por Especialidade</h3>
        <table>
            <thead>
                <tr><th>Especialidade</th><th>Quantidade de AIHs</th></tr>
            </thead>
            <tbody>
                <tr><td>02-OBSTETRICOS</td><td>{especialidades['02-OBSTETRICOS']}</td></tr>
                <tr><td>01-CIRURGICO</td><td>{especialidades['01-CIRURGICO']}</td></tr>
                <tr><td>07-PEDIATRICOS</td><td>{especialidades['07-PEDIATRICOS']}</td></tr>
                <tr><td>03-CLINICOS</td><td>{especialidades['03-CLINICOS']}</td></tr>
                <tr><td><strong>Total Geral</strong></td><td><strong>{total_aihs}</strong></td></tr>
            </tbody>
        </table>

        <h3>2. Receita Faturada por Grupo de Procedimento</h3>
        <table>
            <thead>
                <tr><th>Grupo de Procedimento</th><th>Valor Faturado (R$)</th></tr>
            </thead>
            <tbody>
                <tr><td>Ações Complementares Da Atenção À Saúde</td><td>R$ 640.321,49</td></tr>
                <tr><td>Procedimentos Cirúrgicos</td><td>R$ 522.976,91</td></tr>
                <tr><td>Procedimentos Clínicos</td><td>R$ 293.953,51</td></tr>
                <tr><td>Procedimentos Com Finalidade Diagnóstica</td><td>R$ 57.092,90</td></tr>
                <tr><td>Órteses, Próteses E Materiais Especiais</td><td>R$ 34.382,30</td></tr>
                <tr><td>Medicamentos</td><td>R$ 13.824,04</td></tr>
                <tr><td><strong>Total Geral Faturado</strong></td><td><strong>R$ 1.562.551,15</strong></td></tr>
            </tbody>
        </table>

        <h3>3. Destaque: Diárias de UTI e Cuidados Neonatais</h3>
        <table>
            <thead>
                <tr><th>Tipo de Leito / Procedimento</th><th>Quantidade de Diárias</th><th>Valor Faturado (R$)</th></tr>
            </thead>
            <tbody>
                <tr><td><strong>UTI Adulto</strong> (Cód. 0802010083)</td><td>{diarias['UTI Adulto'].group(1)}</td><td>R$ {diarias['UTI Adulto'].group(2)}</td></tr>
                <tr><td><strong>UTI Neonatal</strong> (Cód. 0802010121)</td><td>{diarias['UTI Neonatal'].group(1)}</td><td>R$ {diarias['UTI Neonatal'].group(2)}</td></tr>
                <tr><td><strong>UCINCo</strong> (Cód. 0802010237)</td><td>{diarias['UCINCo'].group(1)}</td><td>R$ {diarias['UCINCo'].group(2)}</td></tr>
                <tr><td><strong>UCINCa</strong> (Cód. 0802010245)</td><td>{diarias['UCINCa'].group(1)}</td><td>R$ {diarias['UCINCa'].group(2)}</td></tr>
            </tbody>
        </table>

    </body>
    </html>
    """

    # 5. Salvar o arquivo HTML
    caminho_saida = "resumo_faturamento_0526.html"
    with open(caminho_saida, "w", encoding="utf-8") as arquivo:
        arquivo.write(html_content)
    
    print(f"Sucesso! Relatório gerado em: {os.path.abspath(caminho_saida)}")

if __name__ == "__main__":
    processar_dados()