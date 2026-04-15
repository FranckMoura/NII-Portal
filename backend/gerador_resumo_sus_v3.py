import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

print("--- 📊 GERADOR DE RESUMO ESTATÍSTICO SUS (V3: LAYOUT FINAL CEBAS) ---")

load_dotenv()
SB_URL = os.getenv("SB_URL") or "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = os.getenv("SB_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar: {e}"); exit()

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
COD_CUIABA = "510340"

def classificar_idade(idade):
    if idade is None: return "IDADE DESCONHECIDA"
    if idade <= 1: return "ATÉ 1 ANO"
    if idade <= 5: return "DE 1 A 5 ANOS"
    if idade <= 12: return "DE 6 A 12 ANOS"
    if idade <= 20: return "DE 13 A 20 ANOS"
    if idade <= 40: return "DE 21 A 40 ANOS"
    if idade <= 60: return "DE 41 A 60 ANOS"
    return "MAIS DE 60 ANOS"

def gerar_relatorios(ano):
    print(f"⏳ Baixando dados de {ano}...")
    todos_dados = []
    from_row = 0
    while True:
        resp = supabase.table("sih_sus_hsh").select("*").eq("ano_cmpt", str(ano)).range(from_row, from_row + 999).execute()
        if not resp.data: break
        todos_dados.extend(resp.data)
        from_row += 1000
        if len(resp.data) < 1000: break
    
    resumo_espec = {m: {'CIRURGICOS':0, 'OBSTETRICOS':0, 'CLINICOS':0, 'PEDIATRICOS':0} for m in MESES}
    resumo_munic = {m: {'PROPRIO MUNICIPIO':0, 'OUTROS MUNICIPIOS':0, 'OUTROS ESTADOS':0} for m in MESES}
    resumo_estat = {m: {'FEMININOS':0, 'MASCULINO':0, 'ATÉ 1 ANO':0, 'DE 1 A 5 ANOS':0, 'DE 6 A 12 ANOS':0, 'DE 13 A 20 ANOS':0, 'DE 21 A 40 ANOS':0, 'DE 41 A 60 ANOS':0, 'MAIS DE 60 ANOS':0, 'ÓBITOS':0} for m in MESES}
    
    partos_map = {
        '0310010039': 'PARTO NORMAL', '0310010047': 'ALTO RISCO NORMAL',
        '0411010026': 'ALTO RISCO CESARIA', '0411010034': 'PARTO CESARIANO',
        '0411010042': 'PARTO CESARIANO COM LAQUEADURA'
    }
    resumo_natal = {m: {p: {'Nascimentos':0, 'Mortos':0} for p in partos_map.values()} for m in MESES}

    for row in todos_dados:
        try:
            m = MESES[int(row.get('mes_cmpt', 0)) - 1]
            espec = str(row.get('espec') or '').zfill(2)
            
            # MAPEAMENTO CORRIGIDO PARA O SEU BANCO
            if espec == '03': resumo_espec[m]['CIRURGICOS'] += 1
            elif espec == '01': resumo_espec[m]['OBSTETRICOS'] += 1
            elif espec == '02': resumo_espec[m]['CLINICOS'] += 1
            elif espec == '07': resumo_espec[m]['PEDIATRICOS'] += 1

            mun = row.get('munic_res')
            if mun == COD_CUIABA: resumo_munic[m]['PROPRIO MUNICIPIO'] += 1
            elif str(mun).startswith('51'): resumo_munic[m]['OUTROS MUNICIPIOS'] += 1
            else: resumo_munic[m]['OUTROS ESTADOS'] += 1

            if row.get('sexo') == '1': resumo_estat[m]['MASCULINO'] += 1
            elif row.get('sexo') == '3': resumo_estat[m]['FEMININOS'] += 1
            
            idade_cat = classificar_idade(row.get('idade'))
            if idade_cat in resumo_estat[m]: resumo_estat[m][idade_cat] += 1
            if row.get('morte') == 1: resumo_estat[m]['ÓBITOS'] += 1

            proc = row.get('proc_rea')
            if proc in partos_map:
                tipo = partos_map[proc]
                # Lógica VMATO para Óbitos (1=Vivo, 0=Morto)
                for c in ['vmato1', 'vmato2', 'vmato3']:
                    v = str(row.get(c) or '')
                    if v == '1': resumo_natal[m][tipo]['Nascimentos'] += 1
                    elif v == '0': resumo_natal[m][tipo]['Mortos'] += 1
                # Se não houver VMATO (campos nulos), conta 1 nascimento por AIH por segurança
                if not any(str(row.get(c)) in ['0','1'] for c in ['vmato1','vmato2','vmato3']):
                    resumo_natal[m][tipo]['Nascimentos'] += 1
        except: continue

    # Montagem do Excel
    df_espec = pd.DataFrame.from_dict(resumo_espec, orient='index')
    df_espec['TOTAL'] = df_espec.sum(axis=1)
    df_espec.loc['TOTAL GERAL'] = df_espec.sum()

    df_munic = pd.DataFrame.from_dict(resumo_munic, orient='index')
    df_munic['TOTAL'] = df_munic.sum(axis=1)
    df_munic.loc['TOTAL GERAL'] = df_munic.sum()

    df_estat = pd.DataFrame.from_dict(resumo_estat, orient='index')
    df_estat.loc['TOTAL GERAL'] = df_estat.sum()

    linhas_natal = []
    for m in MESES:
        l_qtd = {'MÊS/TIPO': f"{m} (Quantidade)"}; l_nas = {'MÊS/TIPO': f"{m} (Nascimentos)"}; l_mor = {'MÊS/TIPO': f"{m} (Mortos)"}
        for p in partos_map.values():
            n, mor = resumo_natal[m][p]['Nascimentos'], resumo_natal[m][p]['Mortos']
            l_qtd[p], l_nas[p], l_mor[p] = (n+mor), n, mor
        l_qtd['TOTAL'] = sum(l_qtd[p] for p in partos_map.values())
        l_nas['TOTAL'] = sum(l_nas[p] for p in partos_map.values())
        l_mor['TOTAL'] = sum(l_mor[p] for p in partos_map.values())
        linhas_natal.extend([l_qtd, l_nas, l_mor])

    nome_arq = f'Resumo_Auditado_HSH_{ano}.xlsx'
    try:
        with pd.ExcelWriter(nome_arq) as writer:
            df_espec.to_excel(writer, sheet_name='Especialidades')
            df_munic.to_excel(writer, sheet_name='Municípios')
            df_estat.to_excel(writer, sheet_name='Estatística')
            pd.DataFrame(linhas_natal).to_excel(writer, sheet_name='Natalidade', index=False)
        print(f"✅ Arquivo gerado com sucesso: {nome_arq}")
    except PermissionError: print(f"❌ Erro: Feche o arquivo {nome_arq} antes de rodar.")

if __name__ == "__main__":
    gerar_relatorios(input("Ano (ex 2024): "))