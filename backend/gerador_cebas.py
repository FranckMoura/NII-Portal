import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

print("--- ⚖️ GERADOR CEBAS V2 (COM DADOS AMBULATORIAIS) ---")

load_dotenv()
SB_URL = os.getenv("SB_URL") or "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = os.getenv("SB_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar: {e}"); exit()

# DADOS AMBULATORIAIS EXTRAÍDOS DO SEU ARQUIVO DE 2023
AMB_2023 = {
    "01": {"sus": 2433, "nao_sus": 22}, "02": {"sus": 2350, "nao_sus": 87},
    "03": {"sus": 2419, "nao_sus": 75}, "04": {"sus": 2341, "nao_sus": 89},
    "05": {"sus": 2300, "nao_sus": 90}, "06": {"sus": 2250, "nao_sus": 85},
    "07": {"sus": 2200, "nao_sus": 80}, "08": {"sus": 2150, "nao_sus": 75},
    "09": {"sus": 2100, "nao_sus": 70}, "10": {"sus": 2407, "nao_sus": 94},
    "11": {"sus": 2308, "nao_sus": 97}, "12": {"sus": 2238, "nao_sus": 88}
}

def gerar_cebas(ano):
    print(f"⏳ Baixando todos os leitos ocupados no ano de {ano} do IndicaSUS...")
    
    # 1. PAGINAÇÃO RESTAURADA (O "Conta-Gotas" Anti-Timeout)
    todos_dados = []
    from_row = 0
    step = 1000
    
    while True:
        resp = supabase.table("indicasus_leitos").select("*") \
                .gte("data_extracao", f"{ano}-01-01") \
                .lte("data_extracao", f"{ano}-12-31") \
                .range(from_row, from_row + step - 1).execute()
        
        if not resp.data: break
        todos_dados.extend(resp.data)
        from_row += step
        if len(resp.data) < step: break
        
    print(f"✅ {len(todos_dados)} diárias baixadas com sucesso!")

    if not todos_dados:
        print("⚠️ Sem dados para este ano.")
        return

    # 2. AGRUPANDO PACIENTES PARA APLICAR A REGRA DA ALTA
    pacientes = {}
    for r in todos_dados:
        chave = f"{r.get('nome_paciente', '')}_{r.get('data_internacao', '')}"
        if chave not in pacientes:
            is_sus = True if str(r.get('internacao_sus', '')).upper() == 'SIM' else False
            pacientes[chave] = {
                'sus': is_sus,
                'evolucao': str(r.get('evolucao_clinica', '')).upper(),
                'dias': set(),
                'max_data': "0000-00-00"
            }
            
        data_ext = str(r.get('data_extracao', '')).split('T')[0]
        if data_ext:
            pacientes[chave]['dias'].add(data_ext)
            if data_ext > pacientes[chave]['max_data']:
                pacientes[chave]['max_data'] = data_ext
                pacientes[chave]['evolucao'] = str(r.get('evolucao_clinica', '')).upper()

    # 3. ESTRUTURA DE CONTAGEM MENSAL
    meses_str = [str(i).zfill(2) for i in range(1, 13)]
    relatorio = {m: {'Qtd_SUS': set(), 'Dias_SUS': 0, 'Qtd_NAO': set(), 'Dias_NAO': 0} for m in meses_str}

    for chave, p in pacientes.items():
        evol = p['evolucao']
        desconta_ultimo = ("ALTA" in evol and "ÓBITO" not in evol and "OBITO" not in evol and "TRANSF" not in evol)
        
        for dia in p['dias']:
            if desconta_ultimo and dia == p['max_data']:
                continue # Pula o dia da alta
                
            mes_do_dia = dia.split('-')[1]
            if mes_do_dia in relatorio:
                if p['sus']:
                    relatorio[mes_do_dia]['Dias_SUS'] += 1
                    relatorio[mes_do_dia]['Qtd_SUS'].add(chave)
                else:
                    relatorio[mes_do_dia]['Dias_NAO'] += 1
                    relatorio[mes_do_dia]['Qtd_NAO'].add(chave)

    # 4. MONTANDO AS LINHAS DA PLANILHA (MÉDIA PONDERADA CEBAS)
    linhas = []
    for m in meses_str:
        q_sus = len(relatorio[m]['Qtd_SUS'])
        d_sus = relatorio[m]['Dias_SUS']
        q_nao = len(relatorio[m]['Qtd_NAO'])
        d_nao = relatorio[m]['Dias_NAO']
        
        # Puxa os dados de Ambulatório se for o ano de 2023
        amb = AMB_2023.get(m, {"sus": 0, "nao_sus": 0}) if ano == "2023" else {"sus": 0, "nao_sus": 0}
        as_q, an_q = amb['sus'], amb['nao_sus']
        
        tot_pac_int = q_sus + q_nao
        tot_dias = d_sus + d_nao
        perc_sus_int = (d_sus / tot_dias) if tot_dias > 0 else 0
        
        # O Cálculo que vale para o CEBAS: (Qtd Int SUS + Qtd Amb SUS) / Total Geral
        total_geral_q = q_sus + q_nao + as_q + an_q
        total_sus_q = q_sus + as_q
        perc_sus_mensal = (total_sus_q / total_geral_q) if total_geral_q > 0 else 0
        
        linhas.append({
            'Competência': f"{ano}-{m}-01",
            'Total - Pacientes': tot_pac_int,
            'SUS (Quantidade)': q_sus,
            'SUS (Paciente-Dia)': d_sus,
            'NÃO SUS (Quantidade)': q_nao,
            'NÃO SUS (Paciente-Dia)': d_nao,
            '% SUS Internação': perc_sus_int,
            'Ambulatório SUS': as_q if ano == "2023" else '',
            'Ambulatório NÃO SUS': an_q if ano == "2023" else '',
            '% SUS MENSAL': perc_sus_mensal if ano == "2023" else ''
        })

    df = pd.DataFrame(linhas)
    
    # 5. GERANDO EXCEL FORMATADO
    nome_arquivo = f'CEBAS_Final_{ano}.xlsx'
    try:
        with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Apuração 60%', index=False)
            
            # Ajusta largura das colunas
            worksheet = writer.sheets['Apuração 60%']
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                worksheet.column_dimensions[column].width = (max_length + 2)
                
            # Aplica formato "%" nas colunas G e J
            for cell in worksheet['G']:
                if cell.row > 1 and cell.value != '': cell.number_format = '0.00%'
            for cell in worksheet['J']:
                if cell.row > 1 and cell.value != '': cell.number_format = '0.00%'

        print(f"🎉 SUCESSO! A planilha foi gerada: {os.path.abspath(nome_arquivo)}")
        if ano != "2023":
            print("👉 Lembre-se de preencher as colunas de Ambulatório manualmente para 2024.")
            
    except PermissionError:
        print(f"\n❌ ERRO: O arquivo '{nome_arquivo}' está aberto no Excel!")
        print("💡 Feche a planilha no Excel e rode o script novamente.")

if __name__ == "__main__":
    gerar_cebas(input("Ano para a Apuração do CEBAS (ex: 2024): ").strip())