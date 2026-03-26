import oracledb
import pandas as pd
import json
import os
from datetime import datetime
from supabase import create_client, Client

print("--- 🚀 EXTRATOR ETL: SOUL MV -> NII PORTAL ---")

# --- 1. CREDENCIAIS DO BANCO DO HOSPITAL (ORACLE) ---
# Peça estes dados à TI do hospital (IP, Porta, Service Name, Usuário de Leitura e Senha)
ORACLE_USER = "seu_usuario_de_leitura"
ORACLE_PASS = "sua_senha"
ORACLE_DSN = "IP_DO_SERVIDOR:1521/NOME_DO_SERVICO" 

# --- 2. CREDENCIAIS DO SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 3. DICIONÁRIO DE QUERIES (Últimos 30 dias para não travar o servidor) ---
# Dica: Substitua 'SYSDATE - 30' pelo período que desejar
QUERIES = {
    "PACIENTE": """
        SELECT CD_PACIENTE, NM_PACIENTE, NM_MAE, DT_NASCIMENTO, TP_SEXO, NR_CPF, NR_CNS 
        FROM PACIENTE 
        WHERE DT_CADASTRO >= TRUNC(SYSDATE) - 30
    """,
    "ATENDIME": """
        SELECT CD_ATENDIMENTO, CD_PACIENTE, DT_ATENDIMENTO, HR_ATENDIMENTO, DT_ALTA, 
               CD_CONVENIO, CD_LEITO, CD_PRESTADOR, TP_ATENDIMENTO
        FROM ATENDIME 
        WHERE DT_ATENDIMENTO >= TRUNC(SYSDATE) - 30
    """,
    "AVISO_CIRURGIA": """
        SELECT CD_AVISO_CIRURGIA, CD_PACIENTE, CD_ATENDIMENTO, DT_AVISO_CIRURGIA, 
               DT_REALIZACAO, CD_SITUACAO_AVISO 
        FROM AVISO_CIRURGIA 
        WHERE DT_REALIZACAO >= TRUNC(SYSDATE) - 30
    """,
    "REG_FAT": """
        SELECT CD_REG_FAT, CD_ATENDIMENTO, DT_INICIO, DT_FINAL, CD_CONVENIO, 
               VL_TOTAL_CONTA, SN_FECHADA 
        FROM REG_FAT 
        WHERE DT_INICIO >= TRUNC(SYSDATE) - 30
    """
}

def formatar_dados_para_json(df):
    """ Converte datas do Oracle para o formato ISO que o Supabase aceita """
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Preenche valores nulos com None para o JSON não quebrar
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient='records')

def extrair_e_enviar():
    try:
        print("🔄 Conectando ao Oracle (Soul MV)...")
        # Modo 'Thick' desativado (usa o cliente nativo do Python, muito mais leve)
        conexao = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
        print("✅ Conexão estabelecida com sucesso!")

        for nome_tabela, query in QUERIES.items():
            print(f"\n📥 Extraindo tabela: {nome_tabela}...")
            
            # 1. Lê do Oracle
            df = pd.read_sql(query, con=conexao)
            linhas = len(df)
            print(f"   📊 {linhas} registros encontrados.")
            
            if linhas == 0:
                continue

            # 2. Salva um backup em CSV (USE ESTE CSV PARA CRIAR A TABELA NO SUPABASE NA 1ª VEZ)
            caminho_csv = f"{nome_tabela}_BKP.csv"
            df.to_csv(caminho_csv, index=False, sep=";", encoding="utf-8-sig")
            print(f"   💾 Backup salvo localmente em: {caminho_csv}")

            # 3. Envia para o Supabase em lotes
            dados_limpos = formatar_dados_para_json(df)
            
            print(f"   ☁️ Enviando para a nuvem (Tabela: {nome_tabela.lower()})...")
            tamanho_lote = 500
            for i in range(0, linhas, tamanho_lote):
                lote = dados_limpos[i:i+tamanho_lote]
                try:
                    # ATENÇÃO: A tabela já deve existir no Supabase!
                    supabase.table(nome_tabela.lower()).upsert(lote).execute()
                    print(f"      Enviado lote {i} a {i+len(lote)}...")
                except Exception as erro_supa:
                    print(f"      ⚠️ Erro ao enviar lote: {erro_supa}")
                    
        conexao.close()
        print("\n🎉 MEGA EXTRAÇÃO FINALIZADA!")

    except Exception as e:
        print(f"\n❌ Erro Geral: {e}")

if __name__ == "__main__":
    extrair_e_enviar()