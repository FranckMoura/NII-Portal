import pdfplumber
import pandas as pd
import glob
import os
import re

print("--- 👶 RELATÓRIO DE NATALIDADE (LAYOUT ORGANIZADO) ---")

# --- CONFIGURAÇÃO ---
PASTA_ORIGEM = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SAIDA = os.path.join(PASTA_ORIGEM, "Relatorio_Natalidade_Consolidado.xlsx")

arquivos = glob.glob(os.path.join(PASTA_ORIGEM, "*.pdf"))
dados_extraidos = []

print(f">> Lendo {len(arquivos)} arquivos...")

REGEX_VMATO = re.compile(r'^(.*?)\s+([01]{5})$')

# --- 1. EXTRAÇÃO (Mesma lógica que já funcionou) ---
for arquivo in arquivos:
    nome_arquivo = os.path.basename(arquivo)
    
    if "Relatorio" in nome_arquivo or "Consolidado" in nome_arquivo or "R_MOT" in nome_arquivo:
        continue

    periodo = "Desconhecido"
    match_nome = re.search(r'(\d{2})(\d{4})', nome_arquivo)
    if match_nome:
        periodo = f"{match_nome.group(1)}/{match_nome.group(2)}"

    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto: continue
            
            # Se não achou data no nome, tenta no texto
            if periodo == "Desconhecido":
                match_data = re.search(r'Competência:\s*(\d{2}/\d{4})', texto)
                if match_data: periodo = match_data.group(1)

            linhas = texto.split('\n')
            for linha in linhas:
                linha = linha.strip()
                match = REGEX_VMATO.search(linha)
                
                if match:
                    conteudo_anterior = match.group(1).strip()
                    codigo = match.group(2)
                    
                    # Limpa nome do procedimento
                    proc_limpo = conteudo_anterior
                    match_aih = re.search(r'\d{10,}\s+(.*)', conteudo_anterior)
                    if match_aih: proc_limpo = match_aih.group(1).strip()
                    else:
                        parts = conteudo_anterior.split()
                        if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) > 5:
                            proc_limpo = " ".join(parts[1:])

                    try:
                        dados_extraidos.append({
                            "Competência": periodo,
                            "Procedimento": proc_limpo,
                            "Nascidos Vivos": int(codigo[0]),
                            "Nascidos Mortos": int(codigo[1]),
                            "Óbitos Neo": int(codigo[4])
                        })
                    except: pass

# --- 2. ORGANIZAÇÃO DO EXCEL (A Mágica acontece aqui) ---
if dados_extraidos:
    df = pd.DataFrame(dados_extraidos)
    
    # Cria coluna de data para ordenar os meses corretamente
    df['DataSort'] = pd.to_datetime(df['Competência'], format='%m/%Y', errors='coerce')
    
    # Lista para guardar os blocos do Excel
    lista_final = []
    
    # Pega os meses únicos ordenados
    meses_ordenados = df.sort_values('DataSort')['Competência'].unique()
    
    for mes in meses_ordenados:
        # 1. Filtra dados do mês
        df_mes = df[df['Competência'] == mes]
        
        # 2. Agrupa e Soma por procedimento
        tabela_mes = df_mes.groupby(['Competência', 'Procedimento'])[[
            'Nascidos Vivos', 'Nascidos Mortos', 'Óbitos Neo'
        ]].sum().reset_index()
        
        # 3. Calcula o TOTAL DO MÊS
        total_vivos = tabela_mes['Nascidos Vivos'].sum()
        total_mortos = tabela_mes['Nascidos Mortos'].sum()
        total_obitos = tabela_mes['Óbitos Neo'].sum()
        
        # 4. Cria a linha de Total
        linha_total = pd.DataFrame([{
            'Competência': '', # Deixa vazio para destacar
            'Procedimento': f'>>> TOTAL {mes} <<<',
            'Nascidos Vivos': total_vivos,
            'Nascidos Mortos': total_mortos,
            'Óbitos Neo': total_obitos
        }])
        
        # 5. Cria uma linha em branco (Espaçamento)
        linha_espaco = pd.DataFrame([{
            'Competência': '', 'Procedimento': '', 
            'Nascidos Vivos': None, 'Nascidos Mortos': None, 'Óbitos Neo': None
        }])
        
        # Adiciona tudo na lista final
        lista_final.append(tabela_mes)
        lista_final.append(linha_total)
        lista_final.append(linha_espaco) # Espaço entre meses

    # Junta tudo num único DataFrame
    df_consolidado = pd.concat(lista_final, ignore_index=True)
    
    # Salva
    try:
        df_consolidado.to_excel(ARQUIVO_SAIDA, index=False)
        print("\n" + "="*60)
        print(f"✅ EXCEL ORGANIZADO COM SUCESSO!")
        print(f"📂 Arquivo: {ARQUIVO_SAIDA}")
        print("="*60)
        print("\nExemplo do layout gerado:")
        print(df_consolidado.head(15).to_string(index=False))
        
    except Exception as e:
        print(f"❌ Erro ao salvar (feche o Excel se estiver aberto): {e}")

else:
    print("❌ Nenhum dado encontrado.")