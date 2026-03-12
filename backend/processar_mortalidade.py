import pandas as pd
from supabase import create_client, Client
import os
import glob
import sys
import re

print("--- ✝️ PROCESSADOR DE MORTALIDADE (SUPABASE CLOUD) ---")

# --- SUAS CREDENCIAIS DO SUPABASE ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "sb_publishable_o4-ci54177LQmQFsIl1-7g_sN5vp55n"

try:
    # Conecta no banco de dados na nuvem
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro na configuração do Supabase: {e}")
    sys.exit()

# 1. Navegação
pasta_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(pasta_script)

# 2. Busca Excel
arquivos = glob.glob("*.xlsx")
# Ignora arquivos temporários (~$)
arquivos = [f for f in arquivos if not os.path.basename(f).startswith('~$')]

if not arquivos:
    print("❌ Nenhum arquivo .xlsx encontrado na pasta backend.")
    sys.exit()

dados_consolidados = []

def formatar_data(str_data):
    try:
        if isinstance(str_data, pd.Timestamp) or hasattr(str_data, 'strftime'):
            d, m, y = str_data.day, str_data.month, str_data.year
            return f"{y}-{m:02d}-{d:02d}", f"{d:02d}/{m:02d}/{y}", f"{m:02d}/{y}"
        
        str_data = str(str_data).strip()
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', str_data)
        if match:
            d, m, y = match.groups()
            return f"{y}-{m}-{d}", f"{d}/{m}/{y}", f"{m}/{y}"
    except: pass
    return None, None, None

for arquivo in arquivos:
    print(f"📄 Lendo: {arquivo}...")
    try:
        df = pd.read_excel(arquivo, header=None, dtype=str)
        
        for index, row in df.iterrows():
            colunas_uteis = [str(x).strip() for x in row.values if pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan']
            if len(colunas_uteis) < 8: continue

            datas = [c for c in colunas_uteis if re.match(r'\d{2}/\d{2}/\d{4}', c) or '00:00:00' in c]
            if not datas: continue

            dt_obito_raw = datas[-1]
            iso_date, fmt_date, mes_ref = formatar_data(dt_obito_raw)
            if not iso_date: continue

            # Extração dos dados
            nome = colunas_uteis[2] if len(colunas_uteis) > 2 else "Desconhecido"
            
            idade = 0
            for item in colunas_uteis[3:6]:
                if item.isdigit() and int(item) < 130:
                    idade = int(item)
                    break
            
            unidade = "Geral"
            possiveis_unidades = [u for u in colunas_uteis if "UTI" in u or "ANDAR" in u or "NEONATAL" in u]
            if possiveis_unidades: unidade = possiveis_unidades[0]
            elif len(colunas_uteis) > 6: unidade = colunas_uteis[6]

            medico = colunas_uteis[5] if len(colunas_uteis) > 5 and colunas_uteis[5] != unidade else "-"
            
            cid, cid_desc = "-", "-"
            for item in reversed(colunas_uteis):
                match_cid = re.search(r'([A-Z]\d{2,4})', item)
                if match_cid and len(item) < 100:
                    cid_desc = item
                    cid = match_cid.group(1)
                    break
            
            if "Paciente" in nome: continue

            dados_consolidados.append({
                "data_iso": iso_date,
                "data_fmt": fmt_date,
                "mes_ref": mes_ref,
                "paciente": nome,
                "idade": idade,
                "unidade": unidade,
                "medico": medico,
                "cid": cid,
                "cid_desc": cid_desc
            })

    except Exception as e:
        print(f"   ⚠️ Erro ao ler {arquivo}: {e}")

if dados_consolidados:
    print(f"☁️ Enviando {len(dados_consolidados)} registros para o Supabase...")
    
    try:
        # Tenta apagar dados antigos para evitar duplicidade
        try:
            supabase.table('mortalidade').delete().neq("id", 0).execute()
        except:
            print("   ⚠️ Aviso: Permissão de delete restrita. Tentando apenas inserir...")

        # Insere em lotes de 100
        batch_size = 100
        for i in range(0, len(dados_consolidados), batch_size):
            batch = dados_consolidados[i:i + batch_size]
            supabase.table('mortalidade').insert(batch).execute()
            print(f"   -> Lote {i} a {i+len(batch)} enviado.")

        print("\n✅ SUCESSO! Dados enviados para a nuvem.")
    except Exception as e:
        print(f"\n❌ ERRO NO ENVIO: {e}")
else:
    print("Nenhum dado encontrado para enviar.")