import pandas as pd
import os

# --- CONFIGURAÇÃO ---
NOME_ARQUIVO_EXCEL = "RELATÓRIO VINCULO  MÉDICO  2025.xlsx"
PASTA_SAIDA = "csv_vinculos_formatados"

# Cria uma pasta para salvar os arquivos organizados
if not os.path.exists(PASTA_SAIDA):
    os.makedirs(PASTA_SAIDA)

print(f"--- PROCESSANDO ARQUIVO: {NOME_ARQUIVO_EXCEL} ---")

try:
    # Carrega o arquivo Excel (todas as abas)
    xls = pd.ExcelFile(NOME_ARQUIVO_EXCEL)
    
    # Itera sobre cada aba (cada mês)
    for nome_aba in xls.sheet_names:
        print(f"\n📂 Processando aba: {nome_aba}...")
        
        try:
            # Lê a aba. header=1 significa que o cabeçalho está na linha 2 (índice 1)
            # pois a linha 1 geralmente é o título "VÍNCULO ATUALIZADO..."
            df = pd.read_excel(xls, sheet_name=nome_aba, header=1)
            
            # Limpa nomes das colunas (remove espaços e joga para maiúsculo)
            df.columns = df.columns.str.strip().str.upper()
            
            # Verifica se as colunas essenciais existem
            if 'MEDICO' in df.columns and 'QTDE' in df.columns:
                
                # 1. Seleciona apenas as colunas desejadas
                df_final = df[['MEDICO', 'QTDE']].copy()
                
                # 2. Renomeia para o padrão do seu CSV exemplo
                df_final.columns = ['prestador', 'vinculo']
                
                # 3. Limpeza de dados
                # Remove linhas onde o nome do médico está vazio
                df_final = df_final.dropna(subset=['prestador'])
                
                # Garante que o nome do médico seja string e maiúsculo
                df_final['prestador'] = df_final['prestador'].astype(str).str.strip().str.upper()
                
                # 4. Salva em CSV
                # Gera um nome de arquivo limpo (ex: JANEIRO_2025.csv)
                nome_csv = nome_aba.strip().replace(" ", "_").upper() + ".csv"
                caminho_csv = os.path.join(PASTA_SAIDA, nome_csv)
                
                # sep=';' define o ponto e vírgula como separador
                # index=False não salva o número da linha
                # float_format='%.2f' garante casas decimais se necessário (opcional)
                df_final.to_csv(caminho_csv, sep=';', index=False, encoding='utf-8-sig')
                
                print(f"   ✅ Salvo: {nome_csv}")
                print(f"      ({len(df_final)} registros encontrados)")
                
            else:
                print(f"   ⚠️ Pulei a aba '{nome_aba}': Colunas MEDICO e QTDE não encontradas.")
                print(f"      Colunas encontradas: {list(df.columns)}")

        except Exception as e:
            print(f"   ❌ Erro ao processar aba {nome_aba}: {e}")

    print(f"\n🏁 Processo concluído! Verifique a pasta '{PASTA_SAIDA}'.")

except FileNotFoundError:
    print(f"❌ Erro: O arquivo '{NOME_ARQUIVO_EXCEL}' não foi encontrado na pasta.")
except Exception as e:
    print(f"❌ Erro Crítico: {e}")