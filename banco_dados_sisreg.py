import pandas as pd
import sqlite3
import os
import glob
import shutil
import unicodedata
import re
from datetime import datetime

# --- CONFIGURAÇÕES ---
# Pastas do projeto
PASTA_EXPORT = r"C:\Users\DELL\OneDrive\NII-Portal-1\SISREG_Export"
PASTA_PROCESSADOS = os.path.join(PASTA_EXPORT, "Processados")
NOME_BANCO = "dados_sisreg.db"

# Garante que a pasta de processados existe
os.makedirs(PASTA_PROCESSADOS, exist_ok=True)

def limpar_nome_coluna(col):
    """
    Transforma nomes feios do SISREG em nomes bonitos para SQL
    Ex: 'N. da solicitação' -> 'n_da_solicitacao'
    """
    # Remove acentos (ex: ç -> c, ã -> a)
    col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('ascii')
    col = col.lower()
    # Troca qualquer símbolo que não seja letra ou número por underline
    col = re.sub(r'[^a-z0-9]+', '_', col)
    return col.strip('_')

def atualizar_banco():
    print("--- INICIANDO ATUALIZAÇÃO DO BANCO DE DADOS (NII) ---")
    
    # 1. Conectar ao Banco (Cria se não existir)
    conn = sqlite3.connect(NOME_BANCO)
    cursor = conn.cursor()
    
    # 2. Buscar arquivos CSV na pasta
    padrao_busca = os.path.join(PASTA_EXPORT, "*.csv")
    arquivos = glob.glob(padrao_busca)
    
    if not arquivos:
        print(f"Nenhum arquivo novo encontrado em: {PASTA_EXPORT}")
        print("Tudo atualizado!")
        conn.close()
        return

    print(f"Encontrados {len(arquivos)} arquivos novos para processar.")

    for arquivo in arquivos:
        try:
            print(f"Processando: {os.path.basename(arquivo)}...")
            
            # Lê o CSV (Encoding utf-8 é o padrão detectado no seu arquivo)
            df = pd.read_csv(arquivo, sep=';', encoding='utf-8')
            
            # Limpa os nomes das colunas
            df.columns = [limpar_nome_coluna(c) for c in df.columns]
            
            # Adiciona uma coluna para saber de qual arquivo veio esse dado
            df['arquivo_origem'] = os.path.basename(arquivo)
            df['data_importacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # --- ESTRATÉGIA DE UPSERT (ATUALIZAÇÃO INTELIGENTE) ---
            # 1. Salva os dados em uma tabela temporária
            df.to_sql('temp_importacao', conn, if_exists='replace', index=False)
            
            # 2. Cria a tabela definitiva se ela ainda não existir
            # Usamos a estrutura da tabela temporária como molde
            colunas = list(df.columns)
            colunas_sql = ", ".join([f"{c} TEXT" for c in colunas]) # Define tudo como TEXTO por segurança inicial ou tipa se preferir
            
            # A chave mágica aqui é PRIMARY KEY (n_da_solicitacao)
            # Isso impede duplicidade
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS solicitacoes (
                {colunas_sql},
                PRIMARY KEY (n_da_solicitacao)
            )
            """
            # Tenta criar (se já existe, ignora, mas garante que o PK seja respeitado na criação inicial)
            # Nota: SQLite não deixa adicionar PK depois de criado facilmente.
            # Se a tabela já existe sem PK, esse script assume que ela foi criada por ele mesmo antes.
            try:
                # Tenta criar tabela vazia baseada no DataFrame se não existir
                # Mas precisamos garantir a Primary Key. 
                # Se a tabela não existe, criamos ela manualmente com a PK.
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='solicitacoes'")
                tabela_existe = cursor.fetchone()
                
                if not tabela_existe:
                    # Gera comando CREATE TABLE dinâmico com tipos inferidos
                    cols_def = []
                    for col in df.columns:
                        tipo = 'TEXT'
                        if 'valor' in col: tipo = 'REAL'
                        if 'qtd' in col: tipo = 'INTEGER'
                        if col == 'n_da_solicitacao': tipo = 'INTEGER PRIMARY KEY'
                        elif col == 'n_da_solicitacao' and 'PRIMARY KEY' not in cols_def: pass # Já tratado
                        else: cols_def.append(f"{col} {tipo}")
                    
                    # Força n_da_solicitacao ser a chave se não foi pego acima
                    # Simplificação: Usar Create Table As Select é arriscado para PK.
                    # Vamos usar um comando fixo robusto:
                    cursor.execute(create_table_sql)
            except Exception as e:
                print(f"Aviso na verificação da tabela: {e}")

            # 3. Executa o MERGE (Inserir ou Atualizar)
            # Pega nomes das colunas para montar a query
            cols_names = ", ".join(colunas)
            
            sql_merge = f"""
            INSERT OR REPLACE INTO solicitacoes ({cols_names})
            SELECT {cols_names} FROM temp_importacao
            """
            cursor.execute(sql_merge)
            conn.commit()
            
            # Remove tabela temporária
            cursor.execute("DROP TABLE temp_importacao")
            
            print(f"   -> Dados integrados ao banco com sucesso!")

            # 4. Move arquivo para pasta de processados
            destino = os.path.join(PASTA_PROCESSADOS, os.path.basename(arquivo))
            shutil.move(arquivo, destino)
            print(f"   -> Arquivo movido para 'Processados'.")

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {e}")

    # Resumo Final
    cursor.execute("SELECT COUNT(*) FROM solicitacoes")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(valor_total_da_aih) FROM solicitacoes")
    faturamento = cursor.fetchone()[0]
    if faturamento is None: faturamento = 0.0

    print("\n--- RESUMO DO BANCO DE DADOS ---")
    print(f"Total de Solicitações Únicas: {total}")
    print(f"Faturamento Total Acumulado: R$ {faturamento:,.2f}")
    
    conn.close()
    print("Conexão fechada.")

if __name__ == "__main__":
    atualizar_banco()