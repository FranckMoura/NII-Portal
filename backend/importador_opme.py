import pandas as pd
import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SB_URL") or "https://voweywtzoldwfhgkniup.supabase.co"
key = os.getenv("SB_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def extrair_layout_dinamico(caminho_layout):
    """Lê o arquivo de layout oficial para achar a posição exata das colunas"""
    map_campos = {
        'CO_PROCEDIMENTO_PRINCIPAL': 'principal',
        'CO_PROCEDIMENTO_COMPATIVEL': 'compativel',
        'QT_PERMITIDA': 'qtd_max'
    }
    
    posicoes = {}
    with open(caminho_layout, 'r', encoding='latin-1') as f:
        for linha in f:
            if not linha.strip() or 'NM_CAMPO' in linha: continue
            partes = linha.strip().split(',')
            
            if len(partes) >= 5:
                campo_original = partes[0].strip().upper().replace('"', '')
                if campo_original in map_campos:
                    try:
                        numeros = [int(p.strip().replace('"', '')) for p in partes if p.strip().replace('"', '').isdigit()]
                        if len(numeros) >= 2:
                            ini = numeros[-2] - 1
                            fim = numeros[-1]
                            posicoes[map_campos[campo_original]] = (ini, fim)
                    except:
                        pass
    return posicoes

def processar_opme():
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    pasta_sigtap = os.path.join(pasta_script, 'sigtap')
    
    busca_dados = glob.glob(os.path.join(pasta_sigtap, "*rl_procedimento_compativel.txt"))
    busca_layout = glob.glob(os.path.join(pasta_sigtap, "*rl_procedimento_compativel_layout.txt"))
    
    if not busca_dados or not busca_layout:
        print("❌ Arquivos rl_procedimento_compativel não encontrados na pasta sigtap.")
        return

    arq_dados = busca_dados[0]
    arq_layout = busca_layout[0]

    print("🔍 Lendo o mapa de posições (Layout) do DATASUS...")
    posicoes = extrair_layout_dinamico(arq_layout)
    
    if not posicoes:
        print("❌ Erro ao decodificar o arquivo de layout.")
        return
        
    colspecs = []
    nomes_cols = []
    for key, (ini, fim) in sorted(posicoes.items(), key=lambda item: item[1][0]):
        colspecs.append((ini, fim))
        nomes_cols.append(key)

    print("⏳ Cruzando tabela de compatibilidades (Isso pode levar uns segundos)...")
    
    df = pd.read_fwf(arq_dados, colspecs=colspecs, names=nomes_cols, encoding='latin-1', dtype=str)
    
    dados = []
    
    for _, row in df.iterrows():
        principal = str(row.get('principal', '')).strip()
        compativel = str(row.get('compativel', '')).strip()
        qtd = str(row.get('qtd_max', '1')).strip()
        
        # Regra de Ouro: Todo OPME no SIGTAP começa com '07'
        if principal and compativel and compativel.startswith('07'):
            dados.append({
                "codigo_principal": principal,
                "codigo_opme": compativel,
                "quantidade_maxima": int(qtd) if qtd.isdigit() else 1
            })

    if dados:
        print(f"🚀 Preparando para enviar {len(dados)} relações de OPME para o Supabase...")
        
        print("🗑️ Limpando base antiga...")
        supabase.table("sigtap_opme").delete().neq("codigo_principal", "0").execute()
        
        erros = 0
        # Envia em lotes de 2000 para ser rápido
        for i in range(0, len(dados), 2000):
            lote = dados[i:i+2000]
            try:
                supabase.table("sigtap_opme").insert(lote).execute()
                print(f"   ✅ Lote {i} a {i+len(lote)} enviado.")
            except Exception as e:
                erros += 1
                print(f"   ❌ Erro no lote {i}: {e}")
                
        if erros == 0:
            print("🎉 Carga de OPMEs concluída com sucesso! Pode verificar o painel.")
        else:
            print(f"⚠️ Carga finalizada com {erros} erros.")
    else:
        print("⚠️ Nenhuma OPME encontrada. O filtro falhou ou o arquivo está vazio.")

if __name__ == "__main__":
    processar_opme()