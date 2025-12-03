import pandas as pd
import glob
import re

print("--- INICIANDO AUDITORIA DOS DADOS ---")

# Função simples de limpeza
def limpar(txt):
    if pd.isna(txt): return ""
    return str(txt).upper().strip()

pacientes_audit = []
arquivos = glob.glob("*.xlsx")

if not arquivos:
    print("ERRO: Nenhum Excel encontrado.")
else:
    arquivo_alvo = arquivos[0]
    print(f"Auditando arquivo: {arquivo_alvo}")
    
    xls = pd.ExcelFile(arquivo_alvo)
    
    for aba in xls.sheet_names:
        # Lê a aba bruta
        df = pd.read_excel(xls, sheet_name=aba, header=None)
        
        setor_atual = 'UTIN (PADRÃO)' # Começa assumindo UTIN
        
        for index, row in df.iterrows():
            # Texto da linha toda para achar cabeçalhos
            linha_texto = " ".join([str(x).upper() for x in row.values])
            
            # --- DETECTOR DE SETOR (O que o robô está pensando?) ---
            if 'UCINCO' in linha_texto or 'MÉDIO RISCO' in linha_texto:
                setor_atual = 'UCINCO (DETECTADO)'
            elif 'UCINCA' in linha_texto or 'CANGURU' in linha_texto:
                setor_atual = 'UCINCA (DETECTADO)'
            elif 'UTI NEONATAL' in linha_texto and "HOSPITAL" not in linha_texto:
                setor_atual = 'UTIN (REINICIADO)'

            # Tenta pegar nome e data (Colunas B e C geralmente)
            try:
                # Ajuste esses índices se sua planilha for diferente (0=A, 1=B, 2=C...)
                nome_bruto = limpar(row[1]) 
                data_bruta = limpar(row[2])
                
                # Ignora linhas vazias ou cabeçalhos
                if not nome_bruto or len(nome_bruto) < 4: continue
                if "USUÁRIO" in nome_bruto or "PACIENTE" in nome_bruto: continue
                if "TOTAL" in nome_bruto: continue

                # Salva para o Franck conferir
                pacientes_audit.append({
                    'ABA_ORIGEM': aba,
                    'LINHA_EXCEL': index + 1,
                    'NOME_LIDO': nome_bruto,
                    'DATA_LIDA': data_bruta,
                    'SETOR_DECIDIDO': setor_atual,
                    'TEXTO_DA_LINHA': linha_texto[:50] + "..." # Um pedaço da linha para ver o contexto
                })
                
            except Exception:
                continue

    # Gera o CSV de Auditoria
    df_audit = pd.DataFrame(pacientes_audit)
    df_audit.to_csv('AUDITORIA_ERROS.csv', index=False, sep=';', encoding='utf-8-sig')
    
    print("="*40)
    print(f"AUDITORIA CONCLUÍDA. Foram lidos {len(df_audit)} registros.")
    print("Abra o arquivo 'AUDITORIA_ERROS.csv' no Excel e veja a coluna 'SETOR_DECIDIDO'.")