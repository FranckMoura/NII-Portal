import pandas as pd
import csv
import os

# --- 1. CONFIGURAÇÃO DE CAMINHOS (GPS) ---
pasta_atual = os.path.dirname(os.path.abspath(__file__))
arquivo_entrada = os.path.join(pasta_atual, 'R_PROC_LANCAMENTOS.csv')
arquivo_saida = os.path.join(pasta_atual, 'Relatorio_Auditoria_Inteligente.xlsx')

# --- 2. FUNÇÕES AUXILIARES ---

def formatar_codigo(valor):
    """Padroniza códigos para 10 dígitos."""
    if pd.isna(valor) or valor == '': return ''
    return str(valor).replace('.0', '').strip().zfill(10)

def limpar_valor(valor):
    """Converte '1.200,50' para float 1200.50"""
    if pd.isna(valor) or valor == '': return 0.0
    clean_val = str(valor).replace('R$', '').replace('.', '').replace(',', '.')
    try: return float(clean_val)
    except: return 0.0

def definir_prestador(item):
    """
    Regras de Negócio: Define o prestador final.
    Prioridade: 1. Regra de Procedimento -> 2. Prestador Original (Memória) -> 3. Padrão
    """
    proc = str(item.get('Desc_Procedimento', '')).upper()
    orig = str(item.get('Prestador_Original', '')).strip()
    
    # SUAS REGRAS DE EXCEÇÃO:
    if 'TOMOGRAFIA' in proc: return 'DIAG X'
    elif 'ULTRASSONOGRAFIA' in proc: return 'SANTA HELENA IMAGEM'
    elif 'RAIO X' in proc: return 'RAIO X HOSPITAL'
    
    # Se não cair em regra especial, usa o original que recuperamos da memória
    if len(orig) > 2:
        return orig
    
    # Último caso: se mesmo a memória falhou
    return 'HOSPITAL (PADRÃO)'

# --- 3. PROCESSAMENTO ---
print(f"Iniciando processamento com Memória de Prestador e Paciente...")

try:
    with open(arquivo_entrada, 'r', encoding='latin1') as f:
        linhas = f.readlines()

    dados = []
    
    # --- MEMÓRIAS (Variáveis que guardam o valor anterior) ---
    grupo_atual = "INDEFINIDO"
    ultimo_paciente = "DESCONHECIDO"
    ultimo_prestador = "HOSPITAL BENEFICENTE SANTA HELENA" # Valor inicial padrão
    procurando_grupo = False
    
    for linha in linhas:
        cols = list(csv.reader([linha], delimiter=','))[0]
        if not cols: continue
        texto_linha = str(linha)

        # A. GRUPO
        if 'Grupo Procedimento:' in texto_linha:
            partes = texto_linha.split(':')
            if len(partes) > 1 and len(partes[1].strip()) > 3:
                grupo_atual = partes[1].replace(',','').strip()
                procurando_grupo = False
            else:
                procurando_grupo = True
            continue
        
        if procurando_grupo:
            textos = [c for c in cols if len(c.strip()) > 3 and 'Atendimento' not in c]
            if textos: 
                grupo_atual = textos[0]
                procurando_grupo = False

        # B. RASTREADOR DE AIH
        idx_aih = -1
        for i, val in enumerate(cols):
            v = str(val).strip()
            if (v.startswith('512') or v.startswith('42')) and len(v) >= 12:
                idx_aih = i
                break
        
        if idx_aih != -1:
            try:
                # --- C. PRESTADOR (Memória) ---
                # O prestador costuma estar 4 colunas antes da AIH
                candidato_prestador = ''
                if idx_aih >= 4:
                    candidato_prestador = cols[idx_aih-4].strip()
                
                if len(candidato_prestador) > 3:
                    # Se achou um nome novo, atualiza a memória
                    ultimo_prestador = candidato_prestador
                else:
                    # Se está vazio, mantém o 'ultimo_prestador' anterior
                    pass 

                # --- D. PACIENTE (Memória) ---
                idx_paciente = idx_aih + 2
                nome_paciente = ''
                if len(cols) > idx_paciente:
                    nome_paciente = cols[idx_paciente].strip()
                
                if len(nome_paciente) > 2:
                    ultimo_paciente = nome_paciente
                
                # --- E. PROCEDIMENTO ---
                cod_proc, desc_proc = '', ''
                for off in range(8, 15):
                    if len(cols) > idx_aih + off:
                        cand = cols[idx_aih + off].strip()
                        if len(cand) >= 8 and cand.replace('.0','').isdigit():
                            cod_proc = cand
                            if len(cols) > idx_aih + off + 1:
                                desc_proc = cols[idx_aih + off + 1]
                            break
                
                # --- F. VALOR ---
                vals = [c for c in cols if any(k.isdigit() for k in c) and ',' in c]
                valor_final = limpar_valor(vals[-1]) if vals else 0.0
                
                item = {
                    'Grupo': grupo_atual,
                    'AIH': cols[idx_aih],
                    'Paciente': ultimo_paciente,
                    'Prestador_Original': ultimo_prestador, # Usa a memória
                    'Cod_Procedimento': formatar_codigo(cod_proc),
                    'Desc_Procedimento': desc_proc,
                    'Valor': valor_final
                }
                
                # Aplica regra (Troca o nome se for Tomografia, etc.)
                item['Prestador_Final'] = definir_prestador(item)
                
                dados.append(item)
            except: pass

    # --- 4. SALVAR ---
    if dados:
        df = pd.DataFrame(dados)
        cols_final = ['Grupo', 'Prestador_Final', 'AIH', 'Paciente', 'Cod_Procedimento', 'Desc_Procedimento', 'Valor', 'Prestador_Original']
        cols_exist = [c for c in cols_final if c in df.columns]
        
        df[cols_exist].to_excel(arquivo_saida, index=False)
        print(f"✅ SUCESSO! {len(df)} linhas processadas.")
        print(f"   Prestadores vazios foram preenchidos com o anterior.")
        print(f"📁 Arquivo salvo em: {arquivo_saida}")
    else:
        print("❌ ERRO: Nenhuma linha válida encontrada.")

except FileNotFoundError:
    print(f"❌ ERRO: Arquivo 'R_PROC_LANCAMENTOS.csv' não encontrado na pasta.")
except Exception as e:
    print(f"❌ Erro inesperado: {e}")