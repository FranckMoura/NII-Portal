import pandas as pd
import json
import os

print("--- 🚀 PROCESSADOR DE SÉRIE HISTÓRICA SUS (COM GRUPOS E FILTROS) ---")

# Caminhos exatos dos arquivos: Lê do Backend e Salva no Frontend
ARQUIVO_CSV = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\indicadores_gerais\pSerieHistFinTab_Dados completos_data.csv"
ARQUIVO_SAIDA_JS = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\frontend\dados_financeiros.js"

# Tabela Oficial de Grupos do SUS
MAPA_GRUPOS = {
    '01': '01 - Ações de Promoção e Prevenção',
    '02': '02 - Finalidade Diagnóstica',
    '03': '03 - Procedimentos Clínicos',
    '04': '04 - Procedimentos Cirúrgicos',
    '05': '05 - Transplantes',
    '06': '06 - Medicamentos',
    '07': '07 - Órteses e Próteses (OPM)',
    '08': '08 - Ações Complementares'
}

try:
    print(f"📄 Lendo arquivo CSV...")
    try:
        df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin1', on_bad_lines='skip')

    print("⚙️ Mapeando Grupos do SUS e formatando valores...")
    
    if 'Valor Aprov,' in df.columns:
        df['Valor Aprovado'] = df['Valor Aprov,'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
    else:
        print("❌ Erro: Coluna 'Valor Aprov,' não encontrada.")
        exit()

    df['Quantidade'] = pd.to_numeric(df['Quantidade'], errors='coerce').fillna(0)

    df['Ano'] = df['Competência'].str[6:10]
    df['Mes'] = df['Competência'].str[3:5]

    # Inteligência SIGTAP
    df['Procedimento_Cod'] = df['Procedimento'].astype(str).str.zfill(10)
    df['Grupo_Cod'] = df['Procedimento_Cod'].str[0:2]
    df['Grupo_SUS'] = df['Grupo_Cod'].map(MAPA_GRUPOS).fillna('09 - Outros Procedimentos')
    df['Procedimento_Completo'] = df['Procedimento_Cod'] + ' - ' + df['Procedimento Descrição']

    print("📊 Agrupando dados...")
    df_agg = df.groupby(['Ano', 'Mes', 'Competência', 'Origem', 'Grupo_SUS', 'Procedimento_Completo'], as_index=False).agg({
        'Quantidade': 'sum',
        'Valor Aprovado': 'sum'
    })

    dados_json = df_agg.to_dict(orient='records')
    
    with open(ARQUIVO_SAIDA_JS, 'w', encoding='utf-8') as f:
        f.write(f"const DADOS_FINANCEIROS = {json.dumps(dados_json, ensure_ascii=False)};")

    print(f"✅ SUCESSO! Arquivo 'dados_financeiros.js' salvo na pasta FRONTEND!")

except FileNotFoundError:
    print(f"❌ ERRO: O arquivo CSV não foi encontrado no backend.")
except Exception as e:
    print(f"❌ ERRO INESPERADO: {e}")