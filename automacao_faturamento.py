import pandas as pd
import csv
import os

# --- 1. CONFIGURAÇÕES E CAMINHOS ---
pasta_atual = os.path.dirname(os.path.abspath(__file__))
arquivo_entrada = os.path.join(pasta_atual, 'R_CONF_PROCEDIMENTO_P321.csv')
arquivo_saida = os.path.join(pasta_atual, 'Relatorio_Conferencia_Final.xlsx')

# --- 2. O "CÉREBRO" DO SCRIPT (SUAS REGRAS) ---

# Mapa exato de Códigos -> Prestadores (Copiado da sua lista)
MAPA_PRESTADORES = {
    # LAPAT CUIABA
    '0203020030': 'LAPAT CUIABA',
    '0203010035': 'LAPAT CUIABA',
    
    # SANTA HELENA IMAGEM
    '0205010040': 'SANTA HELENA IMAGEM',
    '0205010059': 'SANTA HELENA IMAGEM',
    '0205020038': 'SANTA HELENA IMAGEM',
    '0205020046': 'SANTA HELENA IMAGEM',
    '0205020054': 'SANTA HELENA IMAGEM',
    '0205020062': 'SANTA HELENA IMAGEM',
    '0205020070': 'SANTA HELENA IMAGEM',
    '0205020089': 'SANTA HELENA IMAGEM',
    '0205020097': 'SANTA HELENA IMAGEM',
    '0205020100': 'SANTA HELENA IMAGEM',
    '0205020143': 'SANTA HELENA IMAGEM',
    '0205020151': 'SANTA HELENA IMAGEM',
    '0205020160': 'SANTA HELENA IMAGEM',
    '0205020178': 'SANTA HELENA IMAGEM',
    '0205020186': 'SANTA HELENA IMAGEM',
    
    # DIAG X DIGITAL
    '0206010010': 'DIAG X DIGITAL',
    '0206010028': 'DIAG X DIGITAL',
    '0206010036': 'DIAG X DIGITAL',
    '0206010052': 'DIAG X DIGITAL',
    '0206010060': 'DIAG X DIGITAL',
    '0206010079': 'DIAG X DIGITAL',
    '0206020023': 'DIAG X DIGITAL',
    '0206020031': 'DIAG X DIGITAL',
    '0206030010': 'DIAG X DIGITAL',
    '0206030037': 'DIAG X DIGITAL',
    
    # GASTROMAT
    '0209010010': 'GASTROMAT',
    '0209010029': 'GASTROMAT',
    '0209010037': 'GASTROMAT',
    
    # CINECOR
    '0211020010': 'CINECOR',
    
    # HEMOSAN
    '0212010026': 'HEMOSAN',
    '0212010034': 'HEMOSAN',
    '0306020068': 'HEMOSAN',
    '0306020076': 'HEMOSAN',
    '0306020106': 'HEMOSAN',
    
    # CLINEMAT
    '0305010131': 'CLINEMAT',
    
    # LABORATORIO SANTA HELENA (Testes Rápidos)
    '0214010058': 'LABORATORIO SANTA HELENA',
    '0214010279': 'LABORATORIO SANTA HELENA',
    '0214010040': 'LABORATORIO SANTA HELENA'
}

def formatar_codigo(valor):
    """Garante que o código tenha 10 dígitos (ex: 203020030 -> 0203020030)"""
    if pd.isna(valor) or valor == '': return ''
    # Remove pontos e espaços
    texto = str(valor).replace('.', '').strip()
    # Adiciona zeros à esquerda até ter 10 dígitos
    return texto.zfill(10)

def definir_prestador_inteligente(cod_procedimento, nome_grupo):
    """
    Aplica a lógica de decisão:
    1. Verifica o código específico na lista.
    2. Se não achar, verifica o nome do Grupo.
    """
    codigo = formatar_codigo(cod_procedimento)
    grupo = str(nome_grupo).upper()
    
    # 1. Busca no Mapa de Códigos (Prioridade Alta)
    if codigo in MAPA_PRESTADORES:
        return MAPA_PRESTADORES[codigo]
    
    # 2. Busca por Grupo (Prioridade Baixa)
    if 'CLINICOS' in grupo or 'CLÍNICOS' in grupo:
        return 'HOSPITAL BENEFICENTE SANTA HELENA'
    if 'CIRURGICOS' in grupo or 'CIRÚRGICOS' in grupo:
        return 'HOSPITAL BENEFICENTE SANTA HELENA'
    if 'COMPLEMENTARES' in grupo:
        return 'HOSPITAL BENEFICENTE SANTA HELENA' # Ações complementares
    if 'MEDICAMENTOS' in grupo:
        return 'HOSPITAL BENEFICENTE SANTA HELENA'
    if 'ORTESES' in grupo or 'OPM' in grupo:
        return 'HOSPITAL BENEFICENTE SANTA HELENA'
        
    # 3. Caso não ache nada (ex: Diárias, Taxas)
    return 'HOSPITAL BENEFICENTE SANTA HELENA' 

# --- 3. PROCESSAMENTO DO ARQUIVO ---
print("Iniciando processamento do Relatório de Conferência (P321)...")

try:
    with open(arquivo_entrada, 'r', encoding='latin1') as f:
        linhas = f.readlines()

    dados_finais = []
    
    # Variáveis de Estado (Memória de contexto enquanto lê o arquivo)
    grupo_atual = "INDEFINIDO"
    cod_proc_atual = ""
    desc_proc_atual = ""
    
    for linha in linhas:
        # Lê a linha csv
        reader = csv.reader([linha], delimiter=',')
        cols = list(reader)[0]
        if not cols: continue
        
        texto_col0 = str(cols[0]).strip()
        texto_col1 = str(cols[1]).strip() if len(cols) > 1 else ""
        
        # A. IDENTIFICA O GRUPO
        if 'Grupo:' in texto_col1:
            # Ex: "Grupo: 02 PROCEDIMENTOS..." -> Pega o texto da coluna 2 em diante
            grupo_raw = " ".join([c for c in cols[2:] if c.strip()])
            if grupo_raw: grupo_atual = grupo_raw
            
        # B. IDENTIFICA O PROCEDIMENTO
        elif 'Procedimento:' in texto_col1 or 'Procedimento:' in texto_col0:
            # Varre a linha para achar o código (numérico)
            partes = [c for c in cols if c.strip()]
            # Geralmente a estrutura é: ['Procedimento:', 'CODE', 'DESCRIÇÃO']
            if len(partes) >= 2:
                # Procura qual parte parece um código
                for parte in partes:
                    parte_limpa = parte.replace('.0','')
                    if parte_limpa.isdigit() and len(parte_limpa) >= 8:
                        cod_proc_atual = formatar_codigo(parte_limpa)
                        # A descrição costuma ser o próximo item ou o resto da linha
                        idx = partes.index(parte)
                        if idx + 1 < len(partes):
                            desc_proc_atual = " ".join(partes[idx+1:])
                        break
        
        # C. IDENTIFICA O PACIENTE (DADOS)
        # Regra: Coluna 0 é numérica (ID Paciente) e existe uma AIH na linha
        if texto_col0.isdigit() and len(cols) > 15:
            # Procura a AIH na linha (começa com 512 ou 42)
            idx_aih = -1
            for i, val in enumerate(cols):
                v = str(val).strip()
                if (v.startswith('512') or v.startswith('42')) and len(v) >= 12:
                    idx_aih = i
                    break
            
            if idx_aih != -1:
                # Monta o registro
                prestador_definido = definir_prestador_inteligente(cod_proc_atual, grupo_atual)
                
                # Tenta capturar Qtd e Datas baseado na posição relativa da AIH
                # No seu arquivo P321: Paciente(0), Nome(4), AIH(13), Qtd(27)
                # Vamos usar posições relativas para segurança
                
                item = {
                    'Grupo': grupo_atual,
                    'Prestador': prestador_definido, # AQUI ESTÁ A MÁGICA
                    'Codigo': cod_proc_atual,
                    'Procedimento': desc_proc_atual,
                    'Paciente_ID': texto_col0,
                    'Paciente_Nome': cols[4] if len(cols) > 4 else '', # Ajuste se necessário
                    'AIH': cols[idx_aih],
                    'Data_Internacao': cols[idx_aih + 6] if len(cols) > idx_aih + 6 else '',
                    'Qtd': cols[idx_aih + 14] if len(cols) > idx_aih + 14 else '1'
                }
                dados_finais.append(item)

    # --- 4. EXPORTAÇÃO ---
    if dados_finais:
        df = pd.DataFrame(dados_finais)
        
        # Organizando colunas
        cols_order = ['Grupo', 'Prestador', 'Codigo', 'Procedimento', 'AIH', 'Paciente_Nome', 'Qtd', 'Data_Internacao']
        cols_exist = [c for c in cols_order if c in df.columns]
        
        df[cols_exist].to_excel(arquivo_saida, index=False)
        print(f"✅ SUCESSO! {len(df)} registros processados.")
        print(f"📁 Arquivo salvo em: {arquivo_saida}")
        print("Verifique a coluna 'Prestador' para ver as regras aplicadas.")
    else:
        print("❌ Nenhum dado encontrado. Verifique se o arquivo R_CONF_PROCEDIMENTO_P321.csv está na pasta.")

except Exception as e:
    print(f"❌ Erro crítico: {e}")