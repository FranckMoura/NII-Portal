import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# 1. Dados extraídos do PDF original 
dados_originais = [
    ["Alceneu Nunes De Almeida", "CITOLOGIA LIQUIDA", 11, 550.00],
    ["Anna Gabrielly Silva Da Costa", "ANATOMO PATOLOGICO", 1, 50.00],
    ["Bruna Beatriz Narciso", "ANATOMO PATOLOGICO", 3, 150.00],
    ["Cristina Inacio Ferreira", "ANATOMO PATOLOGICO", 2, 100.00],
    ["Dione Santos da Rocha gomes", "ANATOMO PATOLOGICO", 3, 150.00],
    ["Edson Do Espirito Santo", "CITOLOGIA LIQUIDA", 1, 50.00],
    ["Elena Epifania Da Silva", "CITOLOGIA LIQUIDA", 2, 100.00],
    ["Erica De Almeida Dias", "ANATOMO PATOLOGICO", 3, 150.00],
    ["Kathielly Goncalves Santos", "ANATOMO PATOLOGICO", 2, 100.00],
    ["Pamella Goncalves Leite De Arrud", "ANATOMO PATOLOGICO", 1, 50.00]
]

# 2. Novos dados fornecidos para acréscimo
novos_dados = [
    ["Adnny Costa Martinho", "PROCEDIMENTO", 3, 150.00],
    ["Ana Julia de arruda Gonçalves", "PROCEDIMENTO", 1, 50.00],
    ["Bruna Letícia bispo", "PROCEDIMENTO", 3, 150.00],
    ["Dicarlyelli Pedryelli Gonçalves", "PROCEDIMENTO", 2, 100.00],
    ["Fernando Luís paschoal", "PROCEDIMENTO", 1, 50.00],
    ["Jessica Talita bispo", "PROCEDIMENTO", 2, 100.00],
    ["Júlia Francisca Martins", "PROCEDIMENTO", 3, 150.00],
    ["Juliana de Souza Ferraz", "PROCEDIMENTO", 2, 100.00],
    ["Kelly Vitória Vaz Santos", "PROCEDIMENTO", 3, 150.00],
    ["LiaMara da silva Benítes", "PROCEDIMENTO", 2, 100.00],
    ["Luana Luzia Ortega", "PROCEDIMENTO", 2, 100.00],
    ["Lucilene de Andrade", "PROCEDIMENTO", 2, 100.00],
    ["maxsuelem almeida Ramos", "PROCEDIMENTO", 2, 100.00],
    ["Mercedes nelly Bueno", "PROCEDIMENTO", 1, 50.00],
    ["Narciso narcilio da silva", "PROCEDIMENTO", 2, 100.00],
    ["Paulo Antunes Maciel", "PROCEDIMENTO", 2, 100.00],
    ["rosilma Lopes Reis", "PROCEDIMENTO", 2, 100.00]
]

# Unir listas e criar DataFrame
df = pd.DataFrame(dados_originais + novos_dados, columns=["Paciente", "Procedimento", "Qtd", "Total"])
total_geral = df["Total"].sum()

# 3. Geração do Novo PDF
def gerar_pdf(dataframe, valor_total):
    c = canvas.Canvas("LAPAT_GRATUITO_1225_ATUALIZADO.pdf", pagesize=A4)
    c.setFont("Helvetica-Bold", 12)
    
    # Cabeçalho baseado no original [cite: 1, 6, 7, 10]
    c.drawString(50, 800, "HOSPITAL BENEFICENTE SANTA HELENA")
    c.setFont("Helvetica", 10)
    c.drawString(50, 785, "RELATÓRIO LAPAT - GRATUIDADE 12/2025")
    c.drawString(50, 770, "Responsável: FRANCK | Portal NII")
    
    # Tabela
    y = 740
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Paciente")
    c.drawString(300, y, "Qtd")
    c.drawString(400, y, "Vlr. Total")
    c.line(50, y-5, 550, y-5)
    
    y -= 20
    c.setFont("Helvetica", 8)
    for index, row in dataframe.iterrows():
        if y < 50: # Nova página se necessário
            c.showPage()
            y = 800
        c.drawString(50, y, str(row['Paciente']))
        c.drawString(300, y, str(row['Qtd']))
        c.drawString(400, y, f"R$ {row['Total']:.2f}")
        y -= 15
        
    # Rodapé com Total Geral
    c.setFont("Helvetica-Bold", 10)
    c.line(50, y, 550, y)
    c.drawString(300, y-20, "TOTAL GERAL:")
    c.drawString(400, y-20, f"R$ {valor_total:.2f}")
    
    c.save()

gerar_pdf(df, total_geral)
print("Relatório atualizado com sucesso!")