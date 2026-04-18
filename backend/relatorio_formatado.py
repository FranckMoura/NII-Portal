import pdfplumber
import pandas as pd
import re

# Caminho do relatório que você tira do MV
ARQUIVO_PDF = "R_SANTAHELENAIMAGEM.pdf"
ARQUIVO_SAIDA = "Repasse_SantaHelenaImagem_Limpo.xlsx"

linhas_dados = []

print("🚀 Iniciando a leitura do PDF do SOULMV...")

with pdfplumber.open(ARQUIVO_PDF) as pdf:
    for pagina in pdf.pages:
        texto = pagina.extract_text()
        if not texto: continue
        
        # Lê linha por linha do PDF
        linhas = texto.split('\n')
        
        for linha in linhas:
            # Pula cabeçalhos e linhas vazias
            if "Relatório de Receita" in linha or "Competência" in linha or "Prestador" in linha:
                continue
            
            # Se a linha contiver o código ou o nome da Ecocardiografia, O ROBÔ IGNORA!
            if "020501003" in linha or "ECOCARDIOGRAFIA" in linha:
                print(f"✂️ Ecocardiografia removida: {linha[:40]}...")
                continue
            
            # Se for uma linha válida de exame (ex: tem uma data no formato DD/MM), nós guardamos
            if re.search(r'\d{2}/\d{2}', linha):
                linhas_dados.append([linha.strip()])

# Salva o resultado limpo num Excel
df = pd.DataFrame(linhas_dados, columns=["Dados do Exame (Sem Ecocardiografia)"])
df.to_excel(ARQUIVO_SAIDA, index=False)

print(f"✅ Sucesso! Planilha limpa gerada: {ARQUIVO_SAIDA}")