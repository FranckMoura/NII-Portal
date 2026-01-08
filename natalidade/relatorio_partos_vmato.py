import pdfplumber
import pandas as pd
import glob
import os
import re

print("--- 👶 RELATÓRIO DE PARTOS (VMATO) - VERSÃO INTELIGENTE ---")

# --- CONFIGURAÇÃO ---
PASTA_ORIGEM = r"C:\Users\DELL\OneDrive\HBSH\natalidade\2025"
ARQUIVO_SAIDA = os.path.join(PASTA_ORIGEM, "Relatorio_Natalidade_Final.xlsx")

if not os.path.exists(PASTA_ORIGEM):
    print(f"❌ Pasta não encontrada: {PASTA_ORIGEM}")
    exit()

arquivos = glob.glob(os.path.join(PASTA_ORIGEM, "*.pdf"))
print(f">> Analisando {len(arquivos)} arquivos na pasta...")

dados_extraidos = []
arquivos_processados = 0

# Regex para capturar linhas que terminam com 5 dígitos binários (0 ou 1)
# Exemplo: "PARTO NORMAL 10100"
REGEX_VMATO = re.compile(r'^(.*?)\s+([01]{5})$')

for arquivo in arquivos:
    nome_arquivo = os.path.basename(arquivo)
    
    # Pula o relatório completo gerado anteriormente para não duplicar
    if "Relatorio" in nome_arquivo or "Consolidado" in nome_arquivo:
        continue

    with pdfplumber.open(arquivo) as pdf:
        # Verifica se é o relatório certo lendo a primeira página
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"
        
        # Procura pelo padrão VMATO no texto
        if not re.search(r'[01]{5}', texto_completo):
            print(f"⚠️  Ignorado (Layout incorreto): {nome_arquivo}")
            continue

        print(f"✅ Processando (Layout Parto): {nome_arquivo}...")
        arquivos_processados += 1

        # Tenta achar a data
        periodo = "Desconhecido"
        # Tenta pelo nome (022025.pdf)
        match_nome = re.search(r'(\d{2})(\d{4})', nome_arquivo)
        if match_nome:
            periodo = f"{match_nome.group(1)}/{match_nome.group(2)}"
        else:
            # Tenta pelo texto
            match_data = re.search(r'Competência:\s*(\d{2}/\d{4})', texto_completo)
            if match_data: periodo = match_data.group(1)

        linhas = texto_completo.split('\n')
        for linha in linhas:
            linha = linha.strip()
            match = REGEX_VMATO.search(linha)
            
            if match:
                proc_nome = match.group(1).strip()
                codigo = match.group(2) # Ex: 10100
                
                # Limpa nome do procedimento (remove códigos numéricos iniciais se houver)
                match_clean = re.search(r'\d+\s+(.*)', proc_nome)
                if match_clean: proc_nome = match_clean.group(1)

                try:
                    # Decodifica V M A T O
                    vivos = int(codigo[0])
                    mortos = int(codigo[1])
                    obitos = int(codigo[4])

                    dados_extraidos.append({
                        "Competência": periodo,
                        "Procedimento": proc_nome,
                        "Nascidos Vivos": vivos,
                        "Nascidos Mortos": mortos,
                        "Óbitos Pós-Parto": obitos,
                        "Total": 1
                    })
                except: pass

# --- EXPORTAÇÃO ---
if dados_extraidos:
    df = pd.DataFrame(dados_extraidos)
    
    # Agrupa somando os contadores
    df_resumo = df.groupby(['Competência', 'Procedimento'])[[
        'Nascidos Vivos', 'Nascidos Mortos', 'Óbitos Pós-Parto'
    ]].sum().reset_index()
    
    # Ordena cronologicamente
    df_resumo['DataSort'] = pd.to_datetime(df_resumo['Competência'], format='%m/%Y', errors='coerce')
    df_resumo = df_resumo.sort_values(['DataSort', 'Procedimento']).drop(columns=['DataSort'])
    
    df_resumo.to_excel(ARQUIVO_SAIDA, index=False)
    
    print("\n" + "="*60)
    print(f"🎉 SUCESSO! {arquivos_processados} arquivos de parto processados.")
    print(f"📂 Relatório salvo em: {ARQUIVO_SAIDA}")
    print("="*60)
    print(df_resumo.to_string(index=False))
else:
    print("\n❌ NENHUM arquivo de parto foi encontrado na pasta.")
    print(f"   Certifique-se que os arquivos '022025.pdf' (sem R_MOT_ALT) estão em:")
    print(f"   {PASTA_ORIGEM}")