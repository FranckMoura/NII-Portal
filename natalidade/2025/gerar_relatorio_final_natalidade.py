import pdfplumber
import pandas as pd
import glob
import os
import re

print("--- 👶 GERADOR DE INDICADORES DE NATALIDADE (RESUMO) ---")

# --- CONFIGURAÇÃO ---
PASTA_ORIGEM = os.path.dirname(os.path.abspath(__file__)) # Usa a pasta onde o script está
ARQUIVO_SAIDA = os.path.join(PASTA_ORIGEM, "Relatorio_Natalidade_Consolidado.xlsx")

# Busca PDFs na pasta
arquivos = glob.glob(os.path.join(PASTA_ORIGEM, "*.pdf"))
dados_extraidos = []

print(f">> Lendo {len(arquivos)} arquivos na pasta...")

# Regex para capturar linhas que terminam com o código VMATO (5 dígitos 0 ou 1)
# Exemplo de linha: "5125... O800 PARTO NORMAL 10100"
REGEX_VMATO = re.compile(r'^(.*?)\s+([01]{5})$')

for arquivo in arquivos:
    nome_arquivo = os.path.basename(arquivo)
    
    # Ignora arquivos que não sejam os de dados mensais
    if "Relatorio" in nome_arquivo or "Consolidado" in nome_arquivo or "R_MOT" in nome_arquivo:
        continue

    # Tenta descobrir o mês pelo nome do arquivo (ex: 112025.pdf -> 11/2025)
    periodo = "Desconhecido"
    match_nome = re.search(r'(\d{2})(\d{4})', nome_arquivo)
    if match_nome:
        periodo = f"{match_nome.group(1)}/{match_nome.group(2)}"

    count_linhas = 0
    
    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto: continue
            
            linhas = texto.split('\n')
            for linha in linhas:
                linha = linha.strip()
                
                # Procura o padrão "Texto + 10100" no final da linha
                match = REGEX_VMATO.search(linha)
                
                if match:
                    conteudo_anterior = match.group(1).strip()
                    codigo_vmato = match.group(2) # Ex: 10100
                    
                    # Limpeza do Nome do Procedimento
                    # Remove números longos (AIH/CNS) que aparecem antes do procedimento
                    # Ex: "5125105871820 O800 PARTO NORMAL" -> "O800 PARTO NORMAL"
                    # A lógica: pega tudo depois do último número grande
                    proc_limpo = conteudo_anterior
                    
                    # Procura um padrão de AIH (13 dígitos) ou similar para cortar
                    match_aih = re.search(r'\d{10,}\s+(.*)', conteudo_anterior)
                    if match_aih:
                        proc_limpo = match_aih.group(1).strip()
                    else:
                        # Fallback: se tiver qualquer número seguido de espaço, tenta limpar
                        parts = conteudo_anterior.split()
                        # Se a primeira parte for número longo, remove
                        if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) > 5:
                            proc_limpo = " ".join(parts[1:])

                    # --- DECODIFICAÇÃO (V M A T O) ---
                    # Posição 0: Vivos
                    # Posição 1: Mortos (Natimortos)
                    # Posição 4: Óbitos (Pós-parto)
                    try:
                        vivos = int(codigo_vmato[0])
                        mortos = int(codigo_vmato[1])
                        obitos_pos = int(codigo_vmato[4])
                        
                        dados_extraidos.append({
                            "Competência": periodo,
                            "Procedimento": proc_limpo,
                            "Nascidos Vivos": vivos,
                            "Nascidos Mortos": mortos,
                            "Óbitos Neo": obitos_pos,
                            "Total": 1 # Contador de partos
                        })
                        count_linhas += 1
                    except: pass
    
    print(f"   -> {nome_arquivo}: {count_linhas} registros processados.")

# --- GERAÇÃO DO EXCEL ---
if dados_extraidos:
    df = pd.DataFrame(dados_extraidos)
    
    # Agrupamento (Soma os valores por Mês e Procedimento)
    df_resumo = df.groupby(['Competência', 'Procedimento'])[[
        'Nascidos Vivos', 
        'Nascidos Mortos', 
        'Óbitos Neo'
    ]].sum().reset_index()
    
    # Ordenação Cronológica
    df_resumo['DataSort'] = pd.to_datetime(df_resumo['Competência'], format='%m/%Y', errors='coerce')
    df_resumo = df_resumo.sort_values(['DataSort', 'Procedimento']).drop(columns=['DataSort'])
    
    # Totais Gerais (Linha de Soma)
    # (Opcional: O Excel facilita isso, mas o arquivo já vai pronto para uso)
    
    try:
        df_resumo.to_excel(ARQUIVO_SAIDA, index=False)
        print("\n" + "="*60)
        print(f"✅ SUCESSO! Relatório consolidado gerado.")
        print(f"📂 Arquivo: {ARQUIVO_SAIDA}")
        print("="*60)
        
        # Mostra uma prévia rápida no terminal
        print("\n--- PRÉVIA DOS DADOS ---")
        print(df_resumo.head(10).to_string(index=False))
        print("...")
        
    except Exception as e:
        print(f"❌ Erro ao salvar Excel: {e}")
        print("💡 Dica: Feche o arquivo Excel se ele estiver aberto!")
else:
    print("❌ Nenhum dado encontrado. Verifique se os arquivos PDF estão na pasta correta.")