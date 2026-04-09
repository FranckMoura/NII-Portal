import os
import glob
import json
import pandas as pd
from dbfread import DBF
import datasus_dbc
from supabase import create_client, Client
import time

print("--- 🚀 SCRIPT: SINCRONIZAÇÃO AMBULATORIAL SUPABASE (Poliglota Histórico) ---")

# =========================================================
# CONFIGURAÇÕES DO SUPABASE
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

supabase: Client = create_client(SB_URL, SB_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ORIGEM = os.path.join(BASE_DIR, "bases_pamt_brutas") 
ARQUIVO_CACHE = os.path.join(BASE_DIR, "cache_sia_processados.json")

CNES_HSH = "2311682"

def carregar_checkpoint():
    if os.path.exists(ARQUIVO_CACHE):
        with open(ARQUIVO_CACHE, "r") as f:
            return set(json.load(f))
    return set()

def salvar_checkpoint(arquivos_processados):
    with open(ARQUIVO_CACHE, "w") as f:
        json.dump(list(arquivos_processados), f)

def subir_dados_ambulatoriais():
    arquivos_brutos = glob.glob(os.path.join(PASTA_ORIGEM, "*.dbc")) + glob.glob(os.path.join(PASTA_ORIGEM, "*.DBC"))
    arquivos_dbc = list(set(arquivos_brutos))
    arquivos_dbc.sort()
    
    print(f"📂 Encontrados {len(arquivos_dbc)} arquivos DBC na pasta {PASTA_ORIGEM}.")
    if len(arquivos_dbc) == 0:
        return

    arquivos_ja_processados = carregar_checkpoint()
    if len(arquivos_ja_processados) > 0:
        print(f"🧠 Checkpoint ativado: {len(arquivos_ja_processados)} ficheiros ignorados.")

    for arquivo in arquivos_dbc:
        nome_arquivo = os.path.basename(arquivo)
        
        if nome_arquivo in arquivos_ja_processados:
            print(f"⏭️ [PULADO] {nome_arquivo} já processado.")
            continue

        arquivo_dbf = arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf")
        if os.path.getsize(arquivo) == 0: 
            continue

        print(f"\n⚙️ Lendo e filtrando: {nome_arquivo}...")
        
        try:
            datasus_dbc.decompress(arquivo, arquivo_dbf)
            dbf = DBF(arquivo_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)
            
            # 3. FILTRO CRÍTICO (Poliglota: Lê colunas Novas e Antigas)
            mascara_filtro = pd.Series(False, index=df.index)
            if 'PA_CNES' in df.columns: 
                mascara_filtro |= (df['PA_CNES'].astype(str).str.strip() == CNES_HSH)
            if 'CNES' in df.columns:
                mascara_filtro |= (df['CNES'].astype(str).str.strip() == CNES_HSH)
            if 'PA_CODUNI' in df.columns:
                mascara_filtro |= (df['PA_CODUNI'].astype(str).str.strip() == CNES_HSH)
                
            df_hsh = df[mascara_filtro].copy()
            
            if df_hsh.empty:
                print(f"  ⚠️ Nenhuma produção do HSH neste mês. Salvando no checkpoint.")
                arquivos_ja_processados.add(nome_arquivo)
                salvar_checkpoint(arquivos_ja_processados)
                continue

            # 4. PREPARAR O PAYLOAD (Poliglota)
            df_hsh = df_hsh.fillna("")
            payload = []
            
            for _, row in df_hsh.iterrows():
                linha_json = row.to_json()
                linha_dict = json.loads(linha_json)
                
                # Extraindo o Ano/Mês (A coluna mudou de PA_DATPR -> PA_CMPT)
                competencia_str = str(linha_dict.get("PA_CMPT", linha_dict.get("PA_DATPR", linha_dict.get("PA_DATREF", "")))).strip()
                if len(competencia_str) >= 6:
                    ano = competencia_str[:4]
                    mes = competencia_str[4:6]
                else:
                    ano = str(linha_dict.get("ANO_CMPT", ""))[:4]
                    mes = str(linha_dict.get("MES_CMPT", ""))[-2:]

                # Extraindo o resto adaptando-se aos nomes antigos
                proc = str(linha_dict.get("PA_PROC_ID", linha_dict.get("PA_CODPRO", ""))).strip()
                cbo = str(linha_dict.get("PA_CBO_PROF", linha_dict.get("PA_CODESP", ""))).strip()
                qtd = float(linha_dict.get("PA_QTD_PRO", linha_dict.get("PA_QTDAPR", linha_dict.get("PA_QTD_APR", linha_dict.get("PA_QTDPRO", 0.0)))))
                val = float(linha_dict.get("PA_VAL_PRO", linha_dict.get("PA_VALAPR", linha_dict.get("PA_VAL_APR", linha_dict.get("PA_VALPRO", 0.0)))))
                idade = float(linha_dict.get("PA_IDADE", 0.0))
                cid = str(linha_dict.get("PA_CIDPRI", linha_dict.get("PA_CIDCAS", ""))).strip()
                
                payload.append({
                    "ano_cmpt": ano,
                    "mes_cmpt": mes,
                    "pa_proc_id": proc,
                    "pa_cbo_prof": cbo,
                    "pa_qtd_pro": qtd,
                    "pa_val_pro": val,
                    "pa_idade": idade,
                    "pa_cidpri": cid,
                    "dados_completos": linha_dict
                })

            # 5. UPLOAD PARA A NUVEM
            tamanho_lote = 500
            total = len(payload)
            print(f"  ☁️ A enviar {total} registos para a nuvem em lotes...")
            
            sucesso_total_lotes = True
            for i in range(0, total, tamanho_lote):
                lote = payload[i : i + tamanho_lote]
                try:
                    supabase.table("sia_sus_hsh").insert(lote).execute()
                except Exception as err:
                    print(f"  ❌ Erro ao enviar lote: {err}")
                    sucesso_total_lotes = False
                    time.sleep(2)
                    break 

            # 6. GRAVAR CHECKPOINT
            if sucesso_total_lotes:
                arquivos_ja_processados.add(nome_arquivo)
                salvar_checkpoint(arquivos_ja_processados)
                print(f"  ✅ Upload concluído! {nome_arquivo} marcado no Checkpoint.")
                
            del df
            del df_hsh
            del payload

        except Exception as e:
            print(f"  ❌ Erro ao processar {nome_arquivo}: {e}")
            if os.path.exists(arquivo_dbf): os.remove(arquivo_dbf)

    print("\n🎉 TABELA DE AMBULATÓRIO (SIA) 100% SINCRONIZADA!")

if __name__ == "__main__":
    subir_dados_ambulatoriais()