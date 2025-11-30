import pandas as pd
from dbfread import DBF
import os

# --- CONFIGURAÇÕES ---
PASTA = "arquivos"
MEU_CNES = '2311682' # Hospital Santa Helena

# Mapa de Colunas (Nome Feio no DBF -> Nome Bonito no Site)
# Obs: Os nomes no DBF podem variar levemente, o script tenta adivinhar.
COLUNAS_DESEJADAS = {
    'PF': { # Profissionais
        'NOMEPROF': 'NOME',
        'NOME_PROF': 'NOME', # Variação
        'CODCNS': 'CNS',
        'CNS_PROF': 'CNS', # Variação
        'CBO': 'CBO',
        'CBOUNICO': 'CBO',
        'DS_CBO': 'DESCRIÇÃO CBO',
        'VINCULACAO': 'VÍNCULO',
        'CONTRATO': 'VÍNCULO',
        'CH_HOSP': 'CARGA HORÁRIA',
        'CHS_HOSP': 'CARGA HORÁRIA'
    },
    'LT': { # Leitos
        'CODLEITO': 'CÓDIGO',
        'DS_LEITO': 'DESCRIÇÃO',
        'TP_LEITO': 'TIPO',
        'QT_EXIST': 'EXISTENTE',
        'QT_SUS': 'SUS'
    },
    'EQ': { # Equipamentos
        'CODEQUIP': 'CÓDIGO',
        'DS_EQUIP': 'DESCRIÇÃO',
        'QT_EXIST': 'EXISTENTE',
        'QT_USO': 'EM USO',
        'QT_SUS': 'SUS'
    }
}

print(f"🔄 --- CONVERSOR E FILTRO CNES ({MEU_CNES}) ---")

if not os.path.exists(PASTA):
    print("❌ Pasta 'arquivos' não encontrada.")
    exit()

arquivos_dbf = [f for f in os.listdir(PASTA) if f.lower().endswith('.dbf')]

if not arquivos_dbf:
    print("⚠️ Nenhum arquivo .dbf encontrado.")
else:
    for arquivo in arquivos_dbf:
        caminho_dbf = os.path.join(PASTA, arquivo)
        nome_csv = arquivo.lower().replace('.dbf', '.csv')
        caminho_csv = os.path.join(PASTA, nome_csv)
        
        # Identifica o tipo de arquivo (PF, LT, EQ) pelas primeiras letras
        tipo = arquivo[:2].upper()
        mapa = COLUNAS_DESEJADAS.get(tipo, {})
        
        print(f"   🔨 Processando {arquivo}...", end="")
        try:
            # 1. Lê o DBF inteiro (isso pode demorar uns segundos)
            dbf = DBF(caminho_dbf, encoding='iso-8859-1', load=True)
            df = pd.DataFrame(iter(dbf))
            
            # 2. Identifica a coluna do CNES para filtrar
            # Pode vir como 'CNES', 'CO_UNIDADE', 'COD_UNIDADE', etc.
            col_cnes = next((c for c in df.columns if c in ['CNES', 'CO_UNIDADE', 'COD_UNIDADE']), None)
            
            if col_cnes:
                # Garante que é string para comparar
                df[col_cnes] = df[col_cnes].astype(str)
                
                # 3. FILTRA APENAS SANTA HELENA
                df_filtrado = df[df[col_cnes] == MEU_CNES].copy()
                
                if not df_filtrado.empty:
                    # 4. SELECIONA E RENOMEIA AS COLUNAS ÚTEIS
                    colunas_finais = {}
                    for col_dbf in df.columns:
                        if col_dbf in mapa:
                            colunas_finais[col_dbf] = mapa[col_dbf]
                    
                    if colunas_finais:
                        df_final = df_filtrado[list(colunas_finais.keys())].rename(columns=colunas_finais)
                    else:
                        # Se não achou colunas mapeadas, salva tudo filtrado
                        df_final = df_filtrado
                        print(" (Colunas não mapeadas, salvando tudo)", end="")

                    # Salva o CSV limpo e leve
                    df_final.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
                    print(f" ✅ Filtrado! ({len(df_final)} registros)")
                else:
                    print(" ⚠️ Nenhum registro do Santa Helena encontrado neste arquivo.")
            else:
                print(" ❌ Coluna CNES não identificada no arquivo.")
            
            # Remove o DBF gigante para economizar espaço
            os.remove(caminho_dbf)
            
        except Exception as e:
            print(f"\n      ❌ Erro: {e}")

print("\n🚀 Processo concluído! Os CSVs agora contém apenas dados do HBSH.")