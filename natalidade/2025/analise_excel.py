import pdfplumber
import pandas as pd
import glob
import os
import re

print("--- 👶 EXTRATOR DE DADOS DE NATALIDADE (MOTIVOS DE ALTA) ---")

# --- CONFIGURAÇÃO ---
PASTA_ORIGEM = r"C:\Users\DELL\OneDrive\HBSH\natalidade\2025"
ARQUIVO_SAIDA = os.path.join(PASTA_ORIGEM, "Consolidado_Natalidade_2025.xlsx")

# Verifica se a pasta existe
if not os.path.exists(PASTA_ORIGEM):
    print(f"❌ Erro: A pasta informada não existe: {PASTA_ORIGEM}")
    exit()

arquivos = glob.glob(os.path.join(PASTA_ORIGEM, "*.pdf"))
dados_consolidados = []

print(f">> Encontrados {len(arquivos)} arquivos PDF.")

for arquivo in arquivos:
    nome_arquivo = os.path.basename(arquivo)
    print(f"📄 Lendo: {nome_arquivo}...")
    
    with pdfplumber.open(arquivo) as pdf:
        # Geralmente relatório de 1 página, mas vamos iterar por segurança
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto: continue

            # 1. Extrair a Competência (Mês/Ano)
            # Padrão: "Competência: MM/AAAA"
            periodo = "Desconhecido"
            match_data = re.search(r'Competência:\s*(\d{2}/\d{4})', texto)
            if match_data:
                periodo = match_data.group(1)
            
            # 2. Processar Linha a Linha
            linhas = texto.split('\n')
            especialidade_atual = "GERAL"
            
            for linha in linhas:
                linha = linha.strip()
                
                # Detectar Especialidade (ex: OBSTETRICOS, CIRURGICO)
                if "ESPECIALIDADE:" in linha:
                    especialidade_atual = linha.split(":")[1].strip()
                    continue
                
                # Detectar Linhas de Dados
                # Padrão esperado: "CODIGO DESCRICAO ... QUANTIDADE"
                # Ex: "61 ALTA DA MÃE/PUÉPURA E DO RN 375"
                # Regex: Começa com digitos, tem texto no meio, termina com digitos
                match_linha = re.search(r'^(\d{2}\s+.*?)\s+(\d+)$', linha)
                
                if match_linha:
                    descricao = match_linha.group(1).strip()
                    quantidade = int(match_linha.group(2))
                    
                    # Extrair apenas o código e o texto separadamente se quiser
                    codigo = descricao.split(' ')[0]
                    motivo = " ".join(descricao.split(' ')[1:])

                    dados_consolidados.append({
                        "Arquivo": nome_arquivo,
                        "Competência": periodo,
                        "Especialidade": especialidade_atual,
                        "Cód": codigo,
                        "Motivo Alta": motivo,
                        "Quantidade": quantidade
                    })

# --- SALVAR ---
if dados_consolidados:
    df = pd.DataFrame(dados_consolidados)
    
    # Ordenar por Competência (truque para ordenar MM/AAAA corretamente)
    df['SortDate'] = pd.to_datetime(df['Competência'], format='%m/%Y', errors='coerce')
    df = df.sort_values('SortDate').drop(columns=['SortDate'])
    
    df.to_excel(ARQUIVO_SAIDA, index=False)
    print(f"\n✅ Sucesso! Dados exportados para:")
    print(f"   {ARQUIVO_SAIDA}")
    
    # Mostra um resumo rápido
    print("\n--- RESUMO DO ANO ---")
    print(df.groupby('Motivo Alta')['Quantidade'].sum())
else:
    print("❌ Nenhum dado foi extraído. Verifique o layout dos PDFs.")