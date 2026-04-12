import pandas as pd
import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Conexão com Supabase
load_dotenv()
url = os.getenv("SB_URL")
key = os.getenv("SB_KEY")

if not url or not key:
    url = "https://voweywtzoldwfhgkniup.supabase.co"
    key = "COLE_SUA_CHAVE_AQUI" # Cole sua chave longa aqui se o .env falhar

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def processar_e_subir():
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    
    arquivos_excel = glob.glob(os.path.join(pasta_script, "*fila*zero*.xlsx"))
    
    if not arquivos_excel:
        print(f"❌ Nenhum arquivo Excel do 'fila zero' encontrado na pasta:\n   {pasta_script}")
        return

    dados_finais = []

    for arq in arquivos_excel:
        nome_arq = os.path.basename(arq)
        print(f"📖 Abrindo arquivo Excel: {nome_arq}...")
        
        try:
            xls = pd.read_excel(arq, sheet_name=None)
            
            for nome_aba, df in xls.items():
                aba_upper = nome_aba.upper()
                complexidade = "Indefinida"
                
                if "ALTA" in aba_upper:
                    complexidade = "Alta"
                elif "MEDIA" in aba_upper or "MÉDIA" in aba_upper:
                    complexidade = "Média"
                
                if complexidade != "Indefinida":
                    print(f"   📊 Lendo a aba '{nome_aba}' -> Classificada como {complexidade} Complexidade.")
                    
                    df.columns = df.columns.str.strip().str.upper()
                    
                    for _, row in df.iterrows():
                        if pd.isna(row.get('CODIGO_SIGTAP')):
                            continue
                            
                        try:
                            sigtap = str(int(row['CODIGO_SIGTAP'])).zfill(10)
                            descricao = str(row['DESCRICAO_PROCEDIMENTO']).strip()
                            valor = float(str(row['VALOR_UNITARIO']).replace(',', '.'))
                            
                            dados_finais.append({
                                "codigo_sigtap": sigtap,
                                "descricao": descricao,
                                "valor_unitario": valor,
                                "complexidade": complexidade
                            })
                        except Exception:
                            pass 
        except Exception as e:
            print(f"   ⚠️ Erro ao ler o arquivo {nome_arq}: {e}")

    if dados_finais:
        print(f"\n🚀 Preparando para enviar {len(dados_finais)} procedimentos para o Supabase...")
        
        # --- ESTRATÉGIA DELETE & INSERT ---
        try:
            print("   🗑️ Limpando a tabela antiga no Supabase...")
            # O Supabase exige um filtro para deletar. "neq id -1" é sempre verdade, então apaga tudo.
            supabase.table("fila_zero_procedimentos").delete().neq("id", -1).execute()
        except Exception as e:
            print(f"   ⚠️ Aviso ao limpar tabela: {e}")
        
        erros = 0
        for i in range(0, len(dados_finais), 500):
            lote = dados_finais[i:i+500]
            try:
                # Agora usamos o INSERT normal, pois a tabela está vazia
                supabase.table("fila_zero_procedimentos").insert(lote).execute()
                print(f"   ✅ Lote {i} a {i+len(lote)} enviado.")
            except Exception as e:
                erros += 1
                print(f"   ❌ Erro no lote {i}: {e}")
        
        if erros == 0:
            print("\n🎉 Carga do Fila Zero concluída com sucesso! Já pode abrir o portal.")
        else:
            print(f"\n⚠️ Carga finalizada, mas ocorreram {erros} erros de envio.")
    else:
        print("❌ Nenhum dado válido encontrado nas abas ALTA ou MEDIA do Excel.")

if __name__ == "__main__":
    processar_e_subir()