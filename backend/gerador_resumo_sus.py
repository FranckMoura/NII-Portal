import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

print("--- 📊 GERADOR DE RESUMO ESTATÍSTICO SUS ---")

# --- CONFIGURAÇÕES ---
load_dotenv()
SB_URL = os.getenv("SB_URL") or "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = os.getenv("SB_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

# Dicionários de Apoio
MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
COD_CUIABA = "510340" # Código IBGE de Cuiabá

def obter_dados_ano(ano):
    print(f"⏳ Baixando todas as AIHs faturadas no ano de {ano}...")
    todos_dados = []
    from_row = 0
    step = 1000
    while True:
        resp = supabase.table("sih_sus_hsh").select("*").eq("ano_cmpt", str(ano)).range(from_row, from_row + step - 1).execute()
        if not resp.data: break
        todos_dados.extend(resp.data)
        from_row += step
        if len(resp.data) < step: break
    print(f"✅ {len(todos_dados)} AIHs encontradas para o ano {ano}.")
    return todos_dados

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
    dados = obter_dados_ano(ano)
    if not dados: return
    
    # --- ESTRUTURAS ZERADAS ---
    resumo_espec = {m: {'CIRURGICOS':0, 'OBSTETRICOS':0, 'CLINICOS':0, 'PEDIATRICOS':0} for m in MESES}
    resumo_munic = {m: {'PROPRIO MUNICIPIO':0, 'OUTROS MUNICIPIOS':0, 'OUTROS ESTADOS':0} for m in MESES}
    resumo_estat = {m: {'FEMININOS':0, 'MASCULINO':0, 'ATÉ 1 ANO':0, 'DE 1 A 5 ANOS':0, 'DE 6 A 12 ANOS':0, 'DE 13 A 20 ANOS':0, 'DE 21 A 40 ANOS':0, 'DE 41 A 60 ANOS':0, 'MAIS DE 60 ANOS':0, 'ÓBITOS':0} for m in MESES}
    
    partos_map = {
        '0310010039': 'PARTO NORMAL',
        '0310010047': 'ALTO RISCO NORMAL',
        '0411010026': 'ALTO RISCO CESARIA',
        '0411010034': 'PARTO CESARIANO',
        '0411010042': 'PARTO CESARIANO COM LAQUEADURA'
    }
    resumo_natal = {m: {p: {'Quantidade':0, 'Nascimentos':0, 'Mortos':0} for p in partos_map.values()} for m in MESES}

    # --- PROCESSAMENTO DOS DADOS ---
    for row in dados:
        try:
            mes_idx = int(row.get('mes_cmpt', 0)) - 1
            if mes_idx < 0 or mes_idx > 11: continue
            mes_nome = MESES[mes_idx]
            
            # 1. Especialidade (Corrigida e Mapeada Oficialmente)
            espec_raw = row.get('espec')
            if espec_raw:
                espec = str(espec_raw).strip().zfill(2)
                if espec == '01': resumo_espec[mes_nome]['CIRURGICOS'] += 1
                elif espec == '02': resumo_espec[mes_nome]['OBSTETRICOS'] += 1
                elif espec == '03': resumo_espec[mes_nome]['CLINICOS'] += 1
                elif espec == '07': resumo_espec[mes_nome]['PEDIATRICOS'] += 1
            
            # 2. Município
            munic = row.get('munic_res')
            if munic == COD_CUIABA: resumo_munic[mes_nome]['PROPRIO MUNICIPIO'] += 1
            elif str(munic).startswith('51'): resumo_munic[mes_nome]['OUTROS MUNICIPIOS'] += 1
            else: resumo_munic[mes_nome]['OUTROS ESTADOS'] += 1
                
            # 3. Estatística (Sexo, Idade, Óbito Materno)
            sexo = row.get('sexo')
            if sexo == '1': resumo_estat[mes_nome]['MASCULINO'] += 1
            elif sexo == '3': resumo_estat[mes_nome]['FEMININOS'] += 1
            
            idade_cat = classificar_idade(row.get('idade'))
            if idade_cat in resumo_estat[mes_nome]: resumo_estat[mes_nome][idade_cat] += 1
                
            if row.get('morte') == 1: resumo_estat[mes_nome]['ÓBITOS'] += 1
                
            # 4. Natalidade (Baseada na AIH, pois não há VMATO)
            proc = row.get('proc_rea')
            if proc in partos_map:
                tipo_parto = partos_map[proc]
                resumo_natal[mes_nome][tipo_parto]['Quantidade'] += 1
                resumo_natal[mes_nome][tipo_parto]['Nascimentos'] += 1
                # Como não temos os dados do RN, não conseguimos contabilizar óbitos neonatais aqui

        except Exception as e:
            pass

    print("📈 Montando tabelas e calculando totais...")
    
    # Montando DataFrames
    df_espec = pd.DataFrame.from_dict(resumo_espec, orient='index')
    df_espec['TOTAL'] = df_espec.sum(axis=1)
    df_espec.loc['TOTAL GERAL'] = df_espec.sum()

    df_munic = pd.DataFrame.from_dict(resumo_munic, orient='index')
    df_munic['TOTAL'] = df_munic.sum(axis=1)
    df_munic.loc['TOTAL GERAL'] = df_munic.sum()
    
    df_estat = pd.DataFrame.from_dict(resumo_estat, orient='index')
    df_estat.loc['TOTAL GERAL'] = df_estat.sum()

    linhas_natalidade = []
    for m in MESES:
        linha_qtd = {'MÊS': m, 'TIPO': 'Quantidade'}
        linha_nas = {'MÊS': m, 'TIPO': 'Nascimentos'}
        linha_mor = {'MÊS': m, 'TIPO': 'Mortos'}
        
        tot_q, tot_n, tot_m = 0, 0, 0
        
        for p in partos_map.values():
            q = resumo_natal[m][p]['Quantidade']
            n = resumo_natal[m][p]['Nascimentos']
            mor = resumo_natal[m][p]['Mortos']
            
            linha_qtd[p] = q; linha_nas[p] = n; linha_mor[p] = mor
            tot_q += q; tot_n += n; tot_m += mor
            
        linha_qtd['TOTAL'] = tot_q; linha_nas['TOTAL'] = tot_n; linha_mor['TOTAL'] = tot_m
        
        linhas_natalidade.extend([linha_qtd, linha_nas, linha_mor])
        
    df_natal = pd.DataFrame(linhas_natalidade)

    # --- EXPORTANDO PARA EXCEL ---
    nome_arquivo = f'Resumo_Atendimentos_SUS_HSH_{ano}.xlsx'
    print(f"💾 Salvando arquivo {nome_arquivo}...")
    
    with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
        df_espec.to_excel(writer, sheet_name='Especialidades')
        df_munic.to_excel(writer, sheet_name='Municípios')
        # A ABA ESTATÍSTICA VOLTOU:
        df_estat.to_excel(writer, sheet_name='Estatística')
        df_natal.to_excel(writer, sheet_name='Natalidade', index=False)

    print(f"🎉 SUCESSO! A sua planilha está pronta na pasta: {os.path.abspath(nome_arquivo)}")

if __name__ == "__main__":
    ano_desejado = input("Digite o ANO que deseja gerar o relatório (ex: 2024): ").strip()
    if ano_desejado.isdigit():
        gerar_relatorios(ano_desejado)
    else:
        print("Ano inválido.")