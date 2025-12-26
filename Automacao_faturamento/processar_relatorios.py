import pandas as pd
import numpy as np
import csv
import os

# --- GPS: Garante que acha o arquivo na pasta correta ---
pasta_atual = os.path.dirname(os.path.abspath(__file__))
arquivo_entrada = os.path.join(pasta_atual, 'R_PROC_LANCAMENTOS.csv')
arquivo_saida = os.path.join(pasta_atual, 'Relatorio_Auditoria_Inteligente.xlsx')

# --- CONFIGURAÇÕES ---
def formatar_codigo(valor):
    if pd.isna(valor) or valor == '': return ''
    texto = str(valor).replace('.0', '').strip()
    return texto.zfill(10)

def limpar_valor(valor):
    if pd.isna(valor) or valor == '': return 0.0
    clean_val = str(valor).replace('R$', '').replace('.', '').replace(',', '.')
    try: return float(clean_val)
    except: return 0.0

def definir_prestador(linha_dados):
    # Memória de Prestadores
    proc = str(linha_dados.get('Desc_Procedimento', '')).upper()
    prestador_orig = str(linha_dados.get('Prestador_Original', '')).strip()
    
    if 'TOMOGRAFIA' in proc: return 'DIAG X'
    elif 'ULTRASSONOGRAFIA' in proc or 'ECOGRAFIA' in proc: return 'SANTA HELENA IMAGEM'
    elif 'RAIO X' in proc or 'RADIOGRAFIA' in proc: return 'RAIO X HOSPITAL'
    elif prestador_orig == '' or prestador_orig == 'nan': return 'HOSPITAL (PADRÃO)'
    
    return prestador_orig

# --- EXECUÇÃO ---
print(f"Iniciando processamento (Modo Rastreador de AIH)...")

try:
    with open(arquivo_entrada, 'r', encoding='latin1') as f:
        linhas = f.readlines()

    dados_finais = []
    grupo_atual = "INDEFINIDO"
    procurando_nome_grupo = False
    
    for i, linha in enumerate(linhas):
        reader = csv.reader([linha], delimiter=',')
        cols = list(reader)[0]
        if not cols: continue
        
        texto_col0 = str(cols[0])
        
        # --- 1. LÓGICA DO GRUPO (Corrigida) ---
        # Se achou a etiqueta "Grupo Procedimento:", prepara para pegar o nome
        if 'Grupo Procedimento:' in linha:
            # Tenta pegar na mesma linha (depois dos dois pontos)
            partes = linha.split('Grupo Procedimento:')
            if len(partes) > 1 and len(partes[1].strip()) > 3:
                grupo_atual = partes[1].replace(',', '').strip()
                procurando_nome_grupo = False
            else:
                # Se não tem nada escrito, marca para pegar na PRÓXIMA linha
                procurando_nome_grupo = True
            continue
            
        # Se estava procurando o nome do grupo e achou uma linha com texto (que não é cabeçalho)
        if procurando_nome_grupo:
            # Pega a primeira coluna que tiver texto
            textos = [c for c in cols if len(c.strip()) > 3]
            if textos and 'Atendimento' not in textos[0]:
                grupo_atual = textos[0]
                procurando_nome_grupo = False
            # Se for linha de cabeçalho "Atendimento", ignora e mantem o grupo anterior ou indefinido

        # --- 2. LÓGICA DA AIH (Dinâmica) ---
        # Varre as colunas procurando algo que pareça uma AIH (começa com 512 ou 42 e tem tamanho > 10)
        idx_aih = -1
        for idx, val in enumerate(cols):
            val_str = str(val).strip()
            if (val_str.startswith('512') or val_str.startswith('42')) and len(val_str) >= 12:
                idx_aih = idx
                break
        
        # Se achou uma AIH, usa a posição dela para achar o resto!
        if idx_aih != -1:
            # MAPA RELATIVO (Baseado na posição da AIH)
            # Paciente: Geralmente 2 colunas depois da AIH
            # Código Procedimento: Geralmente 9 colunas depois da AIH
            
            try:
                # Captura dados básicos com segurança de índice
                paciente = cols[idx_aih + 2] if len(cols) > idx_aih + 2 else ''
                
                # Para achar o procedimento, pulamos as datas. É geralmente +9 posições
                # Mas vamos garantir procurando o código numérico adiante
                idx_proc = idx_aih + 9
                cod_proc = ''
                desc_proc = ''
                
                # Scanner local para achar o procedimento (pode variar 1 ou 2 colunas)
                for offset in range(8, 12): # Procura entre +8 e +12 posições
                    if len(cols) > idx_aih + offset:
                        candidato = cols[idx_aih + offset].strip()
                        # Se parece código de procedimento (numerico e longo)
                        if len(candidato) >= 8 and candidato.replace('.0','').isdigit():
                            idx_proc = idx_aih + offset
                            cod_proc = candidato
                            # Descrição é logo depois do código
                            desc_proc = cols[idx_proc + 1] if len(cols) > idx_proc + 1 else ''
                            break
                
                # Valores e Quantidade (Geralmente no final da linha)
                # Vamos pegar de trás para frente para ser mais seguro
                valor = 0.0
                qtd = 0
                colunas_com_valor = [c for c in cols if any(char.isdigit() for char in c)]
                if colunas_com_valor:
                    # O último numérico costuma ser o Valor Total
                    valor = limpar_valor(colunas_com_valor[-1])
                    # O penúltimo costuma ser Quantidade (se for pequeno) ou Valor Unitário
                    # Vamos simplificar pegando a coluna Qtd fixa se possível ou deduzindo
                    # No seu CSV, Qtd parece ser index_proc + 4 ou 5
                
                # Prestador (Geralmente antes da AIH, se existir)
                prestador_orig = ''
                # Se AIH ta na 6, prestador ta na 2. Se AIH ta na 5, prestador ta na... vazio?
                if idx_aih >= 4:
                    candidato_prest = cols[idx_aih - 4]
                    if len(candidato_prest) > 3: prestador_orig = candidato_prest

                item = {
                    'Grupo': grupo_atual,
                    'Prestador_Original': prestador_orig,
                    'AIH': cols[idx_aih],
                    'Paciente': paciente,
                    'Cod_Procedimento': formatar_codigo(cod_proc),
                    'Desc_Procedimento': desc_proc,
                    'Valor': valor
                }
                
                # Aplica regras
                item['Prestador_Final'] = definir_prestador(item)
                
                dados_finais.append(item)

            except Exception as e:
                # Se der erro numa linha específica, pula ela mas avisa
                print(f"Aviso: Erro na linha {i}: {e}")

    # --- 3. EXPORTAÇÃO ---
    if dados_finais:
        df = pd.DataFrame(dados_finais)
        # Reordenar colunas
        cols_order = ['Grupo', 'Prestador_Final', 'AIH', 'Paciente', 'Cod_Procedimento', 'Desc_Procedimento', 'Valor', 'Prestador_Original']
        # Filtra só as que existem
        cols_existentes = [c for c in cols_order if c in df.columns]
        
        df[cols_existentes].to_excel(arquivo_saida, index=False)
        print(f"✅ SUCESSO! {len(df)} linhas recuperadas (incluindo as que faltavam).")
        print(f"Arquivo salvo em: {arquivo_saida}")
    else:
        print("❌ Erro: Nenhuma linha encontrada. O arquivo de entrada está vazio ou ilegível.")

except FileNotFoundError:
    print(f"❌ Erro: Arquivo não encontrado.\nCertifique-se que '{arquivo_entrada}' está na pasta.")