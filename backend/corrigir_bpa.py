def corrigir_duplicidades_bpa(caminho_entrada, caminho_saida):
    with open(caminho_entrada, 'r', encoding='latin-1') as f:
        linhas = f.readlines()
        
    header = ""
    linhas_bpa_c = []
    linhas_bpa_i = []
    
    # Separação das linhas
    for linha in linhas:
        if linha.startswith('01'):
            header = linha
        elif linha.startswith('02'):
            linhas_bpa_c.append(linha)
        elif linha.startswith('03'):
            linhas_bpa_i.append(linha)
            
    linhas_saida = []
    folha_atual = 1
    
    # Processando BPA-C (Consolidado)
    seq_c = 1
    for linha in linhas_bpa_c:
        if seq_c > 20: 
            folha_atual += 1
            seq_c = 1
            
        nova_linha = linha[:21] + f"{folha_atual:03d}{seq_c:02d}" + linha[26:]
        linhas_saida.append(nova_linha)
        seq_c += 1

    # Garante que o BPA-I inicie em uma folha totalmente nova
    if seq_c > 1:
        folha_atual += 1
        
    # Agrupando BPA-I por Profissional + CBO + Procedimento
    grupos_bpa_i = {}
    for linha in linhas_bpa_i:
        cns_prof = linha[15:30]
        cbo = linha[30:36]
        proc = linha[49:59]
        chave = (cns_prof, cbo, proc)
        
        if chave not in grupos_bpa_i:
            grupos_bpa_i[chave] = []
        grupos_bpa_i[chave].append(linha)
        
    # Processando BPA-I com QUEBRA DE PÁGINA OBRIGATÓRIA
    primeiro_grupo = True
    for chave, lista_linhas in grupos_bpa_i.items():
        
        # Avança a página caso não seja o primeiro grupo sendo processado
        if not primeiro_grupo:
            folha_atual += 1
        primeiro_grupo = False
        
        seq_i = 1
        for linha in lista_linhas:
            # Se um mesmo profissional estourar 99 linhas no mesmo procedimento, avança a página
            if seq_i > 99: 
                folha_atual += 1
                seq_i = 1
                
            nova_linha = linha[:44] + f"{folha_atual:03d}{seq_i:02d}" + linha[49:]
            linhas_saida.append(nova_linha)
            seq_i += 1

    # Atualizando o Cabeçalho (Header) com o total correto de folhas e linhas geradas
    total_linhas_prod = len(linhas_saida)
    
    if header:
        header_corrigido = header[:13] + f"{total_linhas_prod:06d}{folha_atual:06d}" + header[25:]
    else:
        header_corrigido = ""

    # Salvando o novo arquivo
    with open(caminho_saida, 'w', encoding='latin-1') as f:
        if header_corrigido:
            f.write(header_corrigido)
        f.writelines(linhas_saida)

    print(f"✅ Arquivo corrigido com sucesso!")
    print(f"📂 Salvo como: {caminho_saida}")
    print(f"📊 Resumo: {total_linhas_prod} linhas distribuídas em {folha_atual} folhas (Páginas Exclusivas).")

# Execução
corrigir_duplicidades_bpa('PAHSH--- (1).MAI', 'PAHSH_CORRIGIDO_V2.MAI')