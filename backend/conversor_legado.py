from dbfread import DBF
import pandas as pd
import os

print("--- 🕰️ CONVERSOR DE LEGADO: DBF -> CSV ---")

# Colocamos o "r" antes das aspas para o Python ler as barras invertidas (\) do Windows corretamente
arquivos_dbf = [
    r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\fonte_dados\dual\tb_dual.dbf",
    r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\fonte_dados\oni\int_oni.dbf"
]

for arquivo in arquivos_dbf:
    if not os.path.exists(arquivo):
        print(f"⚠️ Arquivo {arquivo} não encontrado!")
        continue
        
    print(f"🔄 Lendo o arquivo {arquivo}...")
    try:
        # Lê o DBF (Acentuação padrão de sistemas DOS/Windows antigos)
        tabela_dbf = DBF(arquivo, load=True, encoding='latin1')
        df = pd.DataFrame(iter(tabela_dbf))
        
        # Cria o nome do novo ficheiro substituindo a extensão
        nome_csv = arquivo.lower().replace('.dbf', '.csv')
        
        # Salva em CSV com separador ';' e UTF-8 para ficar perfeito no Supabase e no Excel
        df.to_csv(nome_csv, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"✅ Sucesso! Convertido para: {nome_csv} ({len(df)} linhas)")
    except Exception as e:
        print(f"❌ Erro ao converter {arquivo}: {e}")

print("\n🎉 Conversão concluída! Pode subir os CSVs para o Supabase.")