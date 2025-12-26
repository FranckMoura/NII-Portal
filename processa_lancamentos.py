import pandas as pd
import csv

# --- CONFIGURAÇÕES ---
ARQUIVO_ENTRADA = 'R_CONF_PROCEDIMENTO_P321.csv'
ARQUIVO_SAIDA = 'Relatorio_Conferencia_Limpo.xlsx'

# --- FUNÇÕES DE INTELEGÊNCIA ---

def formatar_codigo(valor):
    """Padroniza códigos para 10 dígitos (ex: 80201 -> 0000080201)"""
    if pd.isna(valor) or valor == '': return ''
    texto = str(valor).replace('.0', '').strip()
    return texto.zfill(10)

def definir_prestador_por_regra(nome_procedimento):
    """
    MEMÓRIA: Define o prestador baseado APENAS no nome do exame,
    já que este relatório não traz o nome do médico.
    """
    proc = str(nome_procedimento).upper()
    
    # --- SUAS REGRAS AQUI ---
    if 'TOMOGRAFIA' in proc:
        return 'DIAG X'
    elif 'ULTRASSONOGRAFIA' in proc or 'ECOGRAFIA' in proc:
        return 'SANTA HELENA IMAGEM'
    elif 'RAIO X' in proc or 'RADIOGRAFIA' in proc:
        return 'RAIO X HOSPITAL'
    elif 'RESSONANCIA' in proc:
        return 'CLINICA DE IMAGEM Y'
    elif 'LABORATORIO' in proc or 'HEMOGRAMA' in proc or 'GLICEMIA' in proc:
        return 'LABORATORIO INTERNO'
        
    return 'PRESTADOR PADRAO' # Caso não caia em nenhuma regra

def limpar_valor(valor):
    if pd.isna(valor) or valor == '': return 0.0
    clean_val = str(valor).replace('R$', '').replace('.', '').replace(',', '.')
    try: return float(clean_val)
    except: return 0.0

# --- EXECUÇÃO ---
print(f"Processando {ARQUIVO_ENTRADA}...")

try:
    with open(ARQUIVO_ENTRADA, 'r', encoding='latin1') as f:
        linhas = f.readlines()

    dados_limpos = []
    
    # Variáveis de Estado (para guardar o cabeçalho enquanto desce as linhas)
    grupo_atual = ""
    subgrupo_atual = ""
    cod_procedimento_atual = ""
    nome_procedimento_atual = ""
    
    for i, linha in enumerate(linhas):
        # Lê a linha tratando aspas do CSV
        reader = csv.reader([linha], delimiter=',')
        cols = list(reader)[0]
        if not cols: continue
        
        texto_col0 = str(cols[0])
        texto_col1 = str(cols[1]) if len(cols) > 1 else ""
        
        # 1. CAPTURA OS CABEÇALHOS (Contexto)
        if 'Grupo:' in texto_col1:
            # Ex: Grupo: 02 PROCEDIMENTOS... (está na coluna 7 ou 8 geralmente)
            # Vamos pegar tudo que tiver texto nas colunas da frente
            grupo_atual = " ".join([c for c in cols[2:] if c.strip()])
        
        elif 'Sub-Grupo:' in texto_col0:
            subgrupo_atual = " ".join([c for c in cols[1:] if c.strip()])
            
        elif 'Procedimento:' in texto_col1 or 'Procedimento:' in texto_col0:
            # A linha de procedimento geralmente tem o código numa coluna e o nome na outra
            # Vamos varrer a linha procurando o código (números) e a descrição
            partes = [c for c in cols if c.strip()]
            # Geralmente: ['Procedimento:', '0202010074', 'DETERMINACAO...']
            if len(partes) >= 3:
                cod_procedimento_atual = formatar_codigo(partes[1])
                nome_procedimento_atual = " ".join(partes[2:])
        
        # 2. CAPTURA OS DADOS DOS PACIENTES
        # Critério: Coluna 0 tem código numérico (Paciente) e Coluna 13 tem AIH
        # Ajuste de índices baseado na análise do seu arquivo:
        # Col 0: Paciente ID, Col 4: Nome, Col 13: AIH, Col 27: Qtd
        if len(cols) > 20 and texto_col0.isdigit():
            aih = cols[13] if len(cols) > 13 else ""
            
            # Filtro de segurança: Só pega se tiver cara de AIH
            if aih.startswith('512') or aih.startswith('42'):
                item = {
                    'Grupo': grupo_atual,
                    'SubGrupo': subgrupo_atual,
                    'Cod_Item_Cobrado': cod_procedimento_atual,
                    'Desc_Item_Cobrado': nome_procedimento_atual,
                    'Prestador_Regra': defining_prestador_por_regra(nome_procedimento_atual),
                    
                    'Paciente_ID': cols[0],
                    'Paciente_Nome': cols[4],
                    'AIH': aih,
                    'Proc_Principal_AIH': formatar_codigo(cols[15]), # O código na linha do paciente costuma ser o motivo da internação
                    'Data_Internacao': cols[19],
                    'Data_Alta': cols[21],
                    'Qtd': cols[27]
                }
                dados_limpos.append(item)

    # Gera o Excel
    if dados_limpos:
        df = pd.DataFrame(dados_limpos)
        df.to_excel(ARQUIVO_SAIDA, index=False)
        print(f"Sucesso! {len(df)} registros processados.")
        print(f"Arquivo gerado: {ARQUIVO_SAIDA}")
    else:
        print("Nenhum dado encontrado. Verifique se o layout do arquivo mudou.")

except Exception as e:
    print(f"Erro Crítico: {e}")