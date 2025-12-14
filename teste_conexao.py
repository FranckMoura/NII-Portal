import psycopg2
from sqlalchemy import create_engine, text

print("--- TESTE DE CONEXÃO POSTGRESQL ---")

# CONFIGURAÇÕES
USUARIO = "postgres"
SENHA = "admin123"  # <--- COLOQUE A SENHA QUE VOCÊ CRIOU NA INSTALAÇÃO
HOST = "localhost"
PORTA = "5432"

try:
    # 1. Tenta conectar
    print("1. Batendo na porta do Banco de Dados...")
    string_conexao = f"postgresql://{USUARIO}:{SENHA}@{HOST}:{PORTA}/postgres"
    engine = create_engine(string_conexao)
    
    # 2. Tenta rodar um comando simples
    with engine.connect() as conexao:
        resultado = conexao.execute(text("SELECT version();"))
        versao = resultado.fetchone()[0]
        
    print("\n✅ SUCESSO! CONEXÃO ESTABELECIDA.")
    print(f"   Versão do Banco: {versao}")
    print("   O Python e o PostgreSQL já estão conversando!")

except Exception as e:
    print("\n❌ FALHA NA CONEXÃO.")
    print(f"Erro: {e}")
    print("\nDICA: Verifique se a senha está correta.")