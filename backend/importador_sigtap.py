import pandas as pd
import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv

# --- CONFIGURAÇÕES ---
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

def formatar_valor_sigtap(valor_str):
    try:
        if pd.isna(valor_str): return 0.0
        texto_limpo = str(valor_str).strip()
        if not texto_limpo: return 0.0
        numero_puro = ''.join(filter(str.isdigit, texto_limpo))
        if not numero_puro: return 0.0
        return float(numero_puro) / 100
    except:
        return 0.0

def extrair_layout_dinamico(caminho_layout):
    """Lê o arquivo de layout oficial do DATASUS e descobre as posições exatas das colunas"""
    map_campos = {
        'CO_PROCEDIMENTO': 'codigo',
        'NO_PROCEDIMENTO': 'nome',
        'TP_COMPLEXIDADE': 'complexidade',
        'TP_SEXO': 'sexo',
        'QT_IDADE_MINIMA': 'idade_min',
        'QT_IDADE_MAXIMA': 'idade_max',
        'VL_SH': 'vl_hosp',
        'VL_SA': 'vl_amb',
        'VL_SP': 'vl_prof',
        'DT_COMPETENCIA': 'competencia'
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
                        # As posições são sempre os últimos dois números da linha
                        numeros = [int(p.strip().replace('"', '')) for p in partes if p.strip().replace('"', '').isdigit()]
                        if len(numeros) >= 2:
                            ini = numeros[-2] - 1 # Ajuste porque o Python começa no índice 0
                            fim = numeros[-1]
                            nome_amigavel = map_campos[campo_original]
                            posicoes[nome_amigavel] = (ini, fim)
                    except Exception:
                        pass
    return posicoes

def processar_sigtap():
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    pasta_sigtap = os.path.join(pasta_script, 'sigtap')
    
    if not os.path.exists(pasta_sigtap):
        print(f"❌ ERRO: A pasta 'sigtap' não existe.")
        return

    # Busca Arquivos
    busca_proc = glob.glob(os.path.join(pasta_sigtap, "*tb_procedimento.txt"))
    busca_layout = glob.glob(os.path.join(pasta_sigtap, "*tb_procedimento_layout.txt"))
    
    if not busca_proc or not busca_layout:
        print(f"❌ ERRO: Faltam os arquivos tb_procedimento.txt ou tb_procedimento_layout.txt.")
        return

    arq_procedimento = busca_proc[0]
    arq_layout = busca_layout[0]
    
    print(f"📂 Arquivo Mestre: {os.path.basename(arq_procedimento)}")
    print(f"🔍 Lendo o Layout Oficial dinamicamente de {os.path.basename(arq_layout)}...")
    
    # 1. Lê o layout
    posicoes = extrair_layout_dinamico(arq_layout)
    
    if not posicoes:
        print("❌ ERRO: Não foi possível ler as colunas do arquivo de layout.")
        return
        
    print(f"✅ Layout interpretado! {len(posicoes)} colunas mapeadas com precisão cirúrgica.")
    
    # 2. Prepara para o Pandas
    colspecs = []
    nomes_cols = []
    for key, (ini, fim) in sorted(posicoes.items(), key=lambda item: item[1][0]):
        colspecs.append((ini, fim))
        nomes_cols.append(key)
        
    print("⏳ Extraindo dados do TXT usando a régua exata do Ministério da Saúde...")
    
    df_proc = pd.read_fwf(arq_procedimento, colspecs=colspecs, names=nomes_cols, encoding='latin-1', dtype=str)
    
    print(f"✅ {len(df_proc)} procedimentos processados. Montando pacotes de envio...")
    
    dados_para_enviar = []
    
    for _, row in df_proc.iterrows():
        try:
            dados_para_enviar.append({
                "codigo": str(row.get('codigo', '')).strip(),
                "nome": str(row.get('nome', '')).strip(),
                "complexidade": str(row.get('complexidade', '')).strip(),
                "sexo": str(row.get('sexo', '')).strip(),
                "idade_minima": int(row['idade_min']) if 'idade_min' in row and pd.notna(row['idade_min']) and str(row['idade_min']).strip().isdigit() else 0,
                "idade_maxima": int(row['idade_max']) if 'idade_max' in row and pd.notna(row['idade_max']) and str(row['idade_max']).strip().isdigit() else 9999,
                "valor_ambulatorial": formatar_valor_sigtap(row.get('vl_amb', '0')),
                "valor_hospitalar": formatar_valor_sigtap(row.get('vl_hosp', '0')),
                "valor_profissional": formatar_valor_sigtap(row.get('vl_prof', '0')),
                "competencia": str(row.get('competencia', '000000')).strip()
            })
        except Exception:
            pass 

    # 4. ENVIO PARA O SUPABASE
    if dados_para_enviar:
        print(f"🚀 Preparando para atualizar {len(dados_para_enviar)} registros no Supabase...")
        erros = 0
        for i in range(0, len(dados_para_enviar), 1000):
            lote = dados_para_enviar[i:i+1000]
            try:
                # O upsert vai corrigir todos os milhões de reais antigos para os valores certos
                supabase.table("sigtap_oficial").upsert(lote, on_conflict="codigo").execute()
                print(f"   ✅ Lote {i} a {i+len(lote)} enviado.")
            except Exception as e:
                erros += 1
                print(f"   ❌ Erro no lote {i}: {e}")
                
        if erros == 0:
            print("\n🎉 Correção do SIGTAP Oficial concluída!")
        else:
            print(f"\n⚠️ Carga finalizada com {erros} erros.")

if __name__ == "__main__":
    processar_sigtap()