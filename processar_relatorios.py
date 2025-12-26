import pandas as pd
import numpy as np
import csv

# --- 1. CONFIGURAÇÕES E FUNÇÕES ---

def formatar_codigo_procedimento(valor):
    """
    Padroniza o código do procedimento para 10 dígitos com zeros à esquerda.
    Ex: 80201003 -> 0080201003
    Ex: 214010279 -> 0214010279
    """
    if pd.isna(valor) or valor == '': return ''
    
    texto = str(valor)
    # Remove sufixo .0 se vier do Excel/CSV numérico
    if texto.endswith('.0'): 
        texto = texto.replace('.0', '')
    
    texto = texto.strip()
    # Adiciona zeros à esquerda até completar 10 casas
    return texto.zfill(10)

def descobrir_prestador_correto(linha_atual):
    """
    MEMÓRIA DO SCRIPT:
    Define quem é o prestador baseado no nome do procedimento.
    """
    # Pega os valores e joga para maiúsculo para facilitar a comparação
    prestador_original = str(linha_atual.get('Prestador_Original', '')).strip()
    descricao_proc = str(linha_atual.get('Desc_Procedimento', '')).upper()
    grupo_proc = str(linha_atual.get('Grupo_Procedimento', '')).upper()
    
    # --- REGRAS DE NEGÓCIO (EDITE AQUI) ---
    
    if 'TOMOGRAFIA' in descricao_proc or 'TOMOGRAFIA' in grupo_proc:
        return 'DIAG X'
        
    elif 'ULTRASSONOGRAFIA' in descricao_proc or 'ECOGRAFIA' in descricao_proc:
        return 'SANTA HELENA IMAGEM'
        
    elif 'RAIO X' in descricao_proc or 'RADIOGRAFIA' in descricao_proc:
        return 'RAIO X HOSPITAL'
        
    elif 'RESSONANCIA' in descricao_proc:
        return 'CLINICA DE IMAGEM Y'

    # Se não for nenhum desses, mantêm o original
    return prestador_original

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == '': return 0.0
    clean_val = str(valor).replace('R$', '').replace('.', '').replace(',', '.')
    try: return float(clean_val)
    except: return 0.0

# --- 2. EXECUÇÃO ---

print("Iniciando processamento inteligente...")

try:
    # Usamos o módulo CSV padrão para ler linha a linha
    # Isso evita erros quando o relatório do SoulMV vem com colunas quebradas
    with open('R_PROC_LANCAMENTOS.csv', 'r', encoding='latin1') as f:
        linhas = f.readlines()
    
    lista_lancamentos = []
    grupo_atual = "Indefinido"
    
    for linha in linhas:
        # Divide a linha pelas vírgulas
        # O módulo csv.reader é mais esperto que o split() simples
        reader = csv.reader([linha], delimiter=',')
        cols = list(reader)[0]
        
        if not cols: continue # Pula linhas vazias

        texto_col0 = str(cols[0])
        
        # 1. Captura o GRUPO (Memória de contexto)
        if 'Grupo Procedimento:' in texto_col0:
            partes = texto_col0.split(':')
            if len(partes) > 1 and len(partes[1].strip()) > 1:
                grupo_atual = partes[1].strip()
            continue
        
        # 2. Identifica se é uma linha de DADOS (Baseado na AIH e Procedimento)
        # Verifica se tem colunas suficientes para ser uma linha de dados
        if len(cols) > 15:
            # Verifica se tem código de procedimento válido na coluna 15
            cod_proc_raw = cols[15]
            
            # Validação simples: se tem números e tamanho razoável
            if len(cod_proc_raw) > 3:
                # Mapeamento das colunas (Baseado na nossa análise)
                item = {
                    'Grupo_Procedimento': grupo_atual,
                    'Prestador_Original': cols[2] if len(cols) > 2 else '',
                    'Atendimento': cols[4] if len(cols) > 4 else '',
                    'AIH': cols[6] if len(cols) > 6 else '',
                    'Paciente': cols[8] if len(cols) > 8 else '',
                    'Data': cols[10] if len(cols) > 10 else '',
                    
                    # APLICA A CORREÇÃO DOS ZEROS AQUI
                    'Cod_Procedimento': formatar_codigo_procedimento(cols[15]),
                    
                    'Desc_Procedimento': cols[16] if len(cols) > 16 else '',
                    'Qtd': cols[20] if len(cols) > 20 else '0',
                    'Valor': limpar_valor_monetario(cols[21]) if len(cols) > 21 else 0.0
                }
                
                # Só adiciona se tiver AIH válida (filtro de lixo)
                if str(item['AIH']).startswith('512') or str(item['AIH']).startswith('42'):
                    # APLICA A REGRA DE PRESTADOR AQUI
                    item['Prestador_Final'] = descobrir_prestador_correto(item)
                    lista_lancamentos.append(item)

    # 3. Gera o Excel Final
    if lista_lancamentos:
        df_final = pd.DataFrame(lista_lancamentos)
        
        # Reorganiza as colunas para ficar bonito
        colunas_ordem = ['Grupo_Procedimento', 'Prestador_Final', 'AIH', 'Paciente', 
                         'Cod_Procedimento', 'Desc_Procedimento', 'Qtd', 'Valor', 'Prestador_Original']
        
        # Garante que só chama colunas que existem
        cols_existentes = [c for c in colunas_ordem if c in df_final.columns]
        
        df_final[cols_existentes].to_excel('Relatorio_Auditoria_Inteligente.xlsx', index=False)
        print(f"Sucesso! {len(df_final)} linhas processadas.")
        print("Arquivo salvo: Relatorio_Auditoria_Inteligente.xlsx")
    else:
        print("Aviso: Nenhuma linha de dados válida foi encontrada.")

except Exception as e:
    print(f"Ocorreu um erro: {e}")