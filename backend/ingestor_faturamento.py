import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Conexão com Supabase
load_dotenv()
url = os.getenv("SB_URL")
key = os.getenv("SB_KEY")

if not url or not key:
    print("❌ Erro: Configure o arquivo .env com SB_URL e SB_KEY")
    exit()

supabase: Client = create_client(url, key)

# 2. Ler o arquivo CSV enviado
arquivo = 'R_PREV_REC_GLO_ESP_321.csv'
print(f"📂 Processando arquivo: {arquivo}...")

# Lendo sem cabeçalho pois o arquivo tem estrutura irregular
df = pd.read_csv(arquivo, header=None, encoding='latin-1', sep=',')

dados_para_enviar = []
especialidade_atual = None
competencia_atual = None

# 3. Varrendo o arquivo linha por linha (Lógica "Mineradora")
for i, linha in df.iterrows():
    # A. Captura a Especialidade (Geralmente na coluna 1 e nome na 7/8)
    if str(linha[1]).strip() == "Especialidade:":
        part1 = str(linha[7]) if pd.notna(linha[7]) else ""
        part2 = str(linha[8]) if pd.notna(linha[8]) else ""
        especialidade_atual = f"{part1} {part2}".strip()
        
        # A competência costuma estar 4 linhas abaixo do cabeçalho da especialidade
        try:
            val_comp = df.iloc[i+4, 1]
            if pd.notna(val_comp) and '/' in str(val_comp):
                competencia_atual = str(val_comp)
        except:
            pass

    # B. Captura o TOTAL quando aparece a linha "TOTAL DA ESPECIALIDADE"
    # O valor real está na linha DEBAIXO (i+1)
    if str(linha[5]).strip() == "TOTAL DA ESPECIALIDADE":
        try:
            prox_linha = df.iloc[i+1]
            
            # Pega o último valor válido da linha (que é o Valor Total)
            valor_bruto = prox_linha.dropna().iloc[-1]
            # Pega a quantidade (geralmente coluna 12, ou procuramos pelo valor numérico)
            qtd_bruta = prox_linha[12] 
            
            # Limpeza de dinheiro (R$ 1.234,56 -> 1234.56)
            valor_float = float(str(valor_bruto).replace('.', '').replace(',', '.'))
            qtd_int = int(qtd_bruta)

            item = {
                "competencia": competencia_atual,
                "especialidade": especialidade_atual,
                "qtd_contas": qtd_int,
                "valor_total": valor_float
            }
            dados_para_enviar.append(item)
            print(f"   ✅ Detectado: {especialidade_atual} | R$ {valor_float:,.2f}")
            
        except Exception as e:
            print(f"   ⚠️ Erro ao ler totais de {especialidade_atual}: {e}")

# 4. Enviar para a Nuvem
if dados_para_enviar:
    try:
        data = supabase.table("tb_faturamento_mensal").insert(dados_para_enviar).execute()
        print(f"\n🚀 Sucesso! {len(dados_para_enviar)} registros financeiros atualizados no Painel.")
    except Exception as e:
        print(f"❌ Erro no Supabase: {e}")
else:
    print("Nenhum dado encontrado. Verifique se o layout do CSV mudou.")