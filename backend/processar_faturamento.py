import pandas as pd
from supabase import create_client, Client
import os
import glob
import sys
import re

print("--- 💰 PROCESSADOR DE FATURAMENTO V10 (MASTER KEY) ---")

# --- CREDENCIAIS ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"

# ⚠️ CHAVE MESTRA (SERVICE ROLE) - Acesso Total
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro na configuração do Supabase: {e}")
    sys.exit()

os.chdir(os.path.dirname(os.path.abspath(__file__)))
arquivos = glob.glob("*.csv") + glob.glob("*.txt")
arquivos = [f for f in arquivos if "processar" not in f and not f.startswith("~")]

if not arquivos:
    print("❌ Nenhum arquivo encontrado.")
    sys.exit()

# --- PASSO 1: LIMPEZA ---
print("\n🧹 LIMPANDO BANCO DE DADOS...")
try:
    supabase.table('faturamento').delete().gt('id', 0).execute()
    print("✅ Tabela limpa.")
except Exception as e:
    print(f"⚠️ Erro ao limpar: {e}")

# --- PASSO 2: PROCESSAMENTO ---
print("\n⚙️  PROCESSANDO ARQUIVOS...")

registros_unicos = {} 

def str_to_float(valor):
    s = str(valor).strip().replace('"', '').replace("'", '')
    if pd.isna(valor) or s in ['-', '', '0,00']: return 0.0
    val_str = s.replace('.', '').replace(',', '.')
    try: return float(val_str)
    except: return 0.0

def converter_int(valor):
    s = str(valor).strip().replace('"', '').replace("'", '')
    if pd.isna(valor) or s in ['-', '']: return 0
    try: return int(float(s.replace('.', '').replace(',', '.')))
    except: return 0

def extrair_competencia(linhas):
    for linha in linhas[:30]:
        match = re.search(r'([A-Z][a-z]{2}/\d{4})', linha)
        if match: return match.group(1)
    return "Desconhecida"

meses_map = {'Jan':'01', 'Fev':'02', 'Mar':'03', 'Abr':'04', 'Mai':'05', 'Jun':'06', 'Jul':'07', 'Ago':'08', 'Set':'09', 'Out':'10', 'Nov':'11', 'Dez':'12'}

def ler_arquivo_seguro(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return f.readlines()
    except:
        with open(caminho, 'r', encoding='latin-1') as f: return f.readlines()

for arquivo in arquivos:
    try:
        linhas = ler_arquivo_seguro(arquivo)
        comp_txt = extrair_competencia(linhas)

        for linha in linhas:
            linha = linha.strip()
            if not linha: continue

            match_codigo = re.match(r'^"?(\d{7,})', linha)
            if not match_codigo: continue 

            try:
                valores_brutos = []
                if ';' in linha:
                    partes = [p.replace('"', '').strip() for p in linha.split(';')]
                    if len(partes) < 4: continue
                    proc_full = partes[0]
                    m_proc = re.match(r'^(\d+)\s+(.+)$', proc_full)
                    if m_proc:
                        proc_cod, proc_nome = m_proc.group(1), m_proc.group(2)
                    else:
                        proc_cod, proc_nome = match_codigo.group(1), proc_full
                    valores_brutos = partes[1:]
                else:
                    m_split = re.match(r'^(\d+)\s+(.+?)\s+(\d+.*)$', linha)
                    if not m_split: continue
                    proc_cod, proc_nome = m_split.group(1), m_split.group(2).strip()
                    valores_brutos = re.split(r'\s+', m_split.group(3))

                numeros = [str_to_float(v) for v in valores_brutos]
                inteiros = [converter_int(v) for v in valores_brutos]
                if not numeros: continue

                aih = inteiros[0] if len(inteiros) > 0 else 0
                internacoes = inteiros[1] if len(inteiros) > 1 else 0
                dias = inteiros[-4] if len(inteiros) >= 4 else 0
                obitos = inteiros[-2] if len(inteiros) >= 2 else 0

                valores_validos = [n for n in numeros if n < 5000000]
                if not valores_validos: continue
                valor_total = max(valores_validos)

                valor_hosp = numeros[3] if len(numeros) > 3 else 0.0
                valor_prof = numeros[6] if len(numeros) > 6 else 0.0

                media = round(dias / aih, 1) if aih > 0 else 0.0

                item = {
                    "competencia_fmt": comp_txt,
                    "procedimento": f"{proc_cod} {proc_nome}",
                    "aih_aprovadas": aih,
                    "internacoes": internacoes,
                    "valor_total": valor_total, 
                    "valor_serv_hosp": valor_hosp,
                    "valor_serv_prof": valor_prof,
                    "obitos": obitos,
                    "dias_permanencia": dias,
                    "media_permanencia": media
                }

                if '/' in comp_txt and comp_txt != "Desconhecida":
                    try:
                        m, a = comp_txt.split('/')
                        if m.strip().title() in meses_map:
                            item["competencia_iso"] = f"{a.strip()}-{meses_map[m.strip().title()]}-01"
                    except: pass

                chave = (comp_txt, proc_cod)
                if chave in registros_unicos:
                    reg = registros_unicos[chave]
                    reg['aih_aprovadas'] += aih
                    reg['valor_total'] += valor_total
                    reg['internacoes'] += internacoes
                    reg['dias_permanencia'] += dias
                    if reg['aih_aprovadas'] > 0:
                        reg['media_permanencia'] = round(reg['dias_permanencia']/reg['aih_aprovadas'], 1)
                else:
                    registros_unicos[chave] = item

            except Exception as ex: continue

    except Exception as e:
        print(f"❌ Erro arquivo {arquivo}: {e}")

dados_finais = list(registros_unicos.values())
total_val_nov = sum(d['valor_total'] for d in dados_finais if 'Nov/2025' in d['competencia_fmt'])
print(f"\n🔎 AUDITORIA (NOV/2025): R$ {total_val_nov:,.2f}")

if dados_finais:
    print(f"\n☁️  ENVIANDO {len(dados_finais)} REGISTROS...")
    batch_size = 200
    total = len(dados_finais)
    for i in range(0, total, batch_size):
        batch = dados_finais[i:i + batch_size]
        try:
            supabase.table('faturamento').insert(batch).execute()
            sys.stdout.write(f"\r   Progresso: {int((i/total)*100)}%")
            sys.stdout.flush()
        except: pass
    print(f"\n\n🎉 SUCESSO! Faturamento atualizado com Chave Mestra.")
else:
    print("Nenhum dado extraído.")