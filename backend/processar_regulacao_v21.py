import pandas as pd
import os
import glob
from supabase import create_client, Client
from datetime import datetime

print(f"--- 🏥 PROCESSADOR DE REGULAÇÃO V22 (COM PROCEDIMENTOS SOLICITADOS) ---")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOADS = os.path.join(BASE_DIR, "downloads")

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro Supabase: {e}")
    exit()

def limpar(val):
    if pd.isna(val) or val == "": return None
    return str(val).strip()

def converter_data(data_str):
    if not data_str or pd.isna(data_str): return None
    try: return datetime.strptime(data_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except: return None

def traduzir_carater(valor):
    v = limpar(valor)
    if not v: return None
    if "10" in v or "ELET" in v.upper(): return "ELETIVA"
    if "11" in v or "URG" in v.upper(): return "URGÊNCIA"
    return v

def validar_nome_paciente(nome, num_solicitacao):
    """ Impede que Status ou Lixo entrem como Nome do Paciente """
    n = limpar(nome)
    if not n: return f"PACIENTE {num_solicitacao}"
    
    n_upper = n.upper()
    palavras_proibidas = ["APROVADA", "AUTORIZADO", "PENDENTE", "NEGADO", "CANCELADO", "DEVOLVIDO", "AGUARDANDO", "URGENCIA", "ELETIVA", "SOLICITACAO"]
    
    if n_upper in palavras_proibidas:
        return f"ERRO LEITURA CSV ({num_solicitacao})"
        
    return n

def corrigir_nomes_colunas(df):
    mapa = {
        'N. da solicitaÃ§Ã£o': 'N. da solicitação',
        'Data da solicitaÃ§Ã£o': 'Data da solicitação',
        'Data da autorizaÃ§Ã£o': 'Data da autorização',
        'Data da InternaÃ§Ã£o': 'Data da Internação',
        'CarÃ¡ter internaÃ§Ã£o': 'Caráter internação',
        'Status da solicitaÃ§Ã£o de InternaÃ§Ã£o': 'Status da solicitação de Internação',
        'Nome da clÃ\xadnica': 'Nome da clínica',
        'Nome do procedimento solicitado': 'Nome do procedimento solicitado', # ADICIONADO
        'MÃ©dico Solicitante': 'Médico Solicitante',
        'ClassificaÃ§Ã£o de risco': 'Classificação de risco',
        'Justificativa': 'Justificativa', 
        'N. AIH': 'N. AIH',
        'Nome do paciente': 'Nome do paciente',
        'Valor total da AIH': 'Valor total da AIH',
    }
    
    for col in df.columns:
        if 'cns' in col.lower() or 'cart' in col.lower():
            mapa[col] = 'CNS'
            
    return df.rename(columns=mapa)

def forcar_atualizacao(registro):
    try:
        supabase.table("regulacao").upsert(registro, on_conflict="num_solicitacao").execute()
        return True
    except Exception as e1:
        erro = str(e1)
        if "duplicate key" in erro or "constraint" in erro:
            try:
                # Trator: Apaga do banco qualquer conflito com essa solicitação e recria a linha limpa
                supabase.table("regulacao").delete().eq("num_solicitacao", registro["num_solicitacao"]).execute()
                supabase.table("regulacao").insert(registro).execute()
                return True
            except:
                return False
        return False

def processar():
    arquivos = glob.glob(os.path.join(PASTA_DOWNLOADS, "*.csv"))
    registros = {}

    if not arquivos:
        print("⚠️ Nenhum arquivo CSV encontrado na pasta downloads.")
        return

    for arq in arquivos:
        print(f"Lendo: {os.path.basename(arq)}...", end="\r")
        try:
            df = pd.read_csv(arq, sep=";", encoding="latin1", on_bad_lines='skip', dtype=str)
            df.columns = [c.strip() for c in df.columns]
            df = corrigir_nomes_colunas(df)

            for i, row in df.iterrows():
                aih = limpar(row.get("N. AIH"))
                solicitacao = limpar(row.get("N. da solicitação"))
                if not solicitacao: continue

                # Cria chave primária falsa para quem ainda não tem AIH
                chave_aih = aih if aih else solicitacao
                
                nome_bruto = row.get("Nome do paciente")
                nome_corrigido = validar_nome_paciente(nome_bruto, solicitacao)

                registros[solicitacao] = {
                    "num_aih": chave_aih,
                    "num_solicitacao": solicitacao,
                    "nome_paciente": nome_corrigido,
                    "cns_paciente": limpar(row.get("CNS")), 
                    "status": limpar(row.get("Status da solicitação de Internação")),
                    "data_solicitacao": converter_data(row.get("Data da solicitação")),
                    "data_autorizacao": converter_data(row.get("Data da autorização")),
                    "data_internacao": converter_data(row.get("Data da Internação")),
                    "nome_clinica": limpar(row.get("Nome da clínica")),
                    "carater_internacao": traduzir_carater(row.get("Caráter internação")),
                    "medico_solicitante": limpar(row.get("Médico Solicitante")),
                    "valor_total_aih": limpar(row.get("Valor total da AIH")),
                    "procedimento": limpar(row.get("Nome do procedimento solicitado")), # COLUNA ADICIONADA E MAPEADA
                    "data_atualizacao": datetime.now().isoformat()
                }
        except Exception as e: 
            print(f"\n❌ Erro leitura {arq}: {e}")

    lista = list(registros.values())
    
    if lista:
        print(f"\n📦 Processando {len(lista)} registros (Enviando Procedimentos para Nuvem)...")
        
        sucessos = 0
        TAMANHO_LOTE = 50
        
        for i in range(0, len(lista), TAMANHO_LOTE):
            lote = lista[i:i+TAMANHO_LOTE]
            try:
                supabase.table("regulacao").upsert(lote, on_conflict="num_solicitacao").execute()
                sucessos += len(lote)
                print(f"   ✅ Lote {i} processado.", end="\r")
            except:
                print(f"\n   ⚠️ Lote {i} com conflito/erro. Corrigindo linha a linha...")
                for item in lote:
                    forcar_atualizacao(item)
                    sucessos += 1
        
        print(f"\n✅ Banco de dados higienizado e Populado! Abra o painel HTML.")
    else:
        print("⚠️ Nada para enviar.")

if __name__ == "__main__":
    processar()