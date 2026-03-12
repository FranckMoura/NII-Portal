import sqlite3
from datetime import datetime

# ==========================================
# Passo 1: Configurar o Banco de Dados (SQL)
# ==========================================
def inicializar_banco():
    # Cria uma conexão com o banco (se não existir, ele cria o arquivo)
    conexao = sqlite3.connect('faturamento_agua.db')
    cursor = conexao.cursor()

    # Cria tabela de Participantes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        )
    ''')

    # Cria tabela de Histórico de Pagamentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_pagamento TEXT,
            pessoa_1 TEXT,
            pessoa_2 TEXT,
            valor_total REAL
        )
    ''')
    
    # Verifica se os participantes já foram inseridos, se não, insere a lista inicial
    cursor.execute('SELECT COUNT(*) FROM participantes')
    if cursor.fetchone()[0] == 0:
        lista_participantes = ["Cristina", "Bianca", "Franck", "Thiago", "Lucelia", "Geovana"]
        for pessoa in lista_participantes:
            cursor.execute('INSERT INTO participantes (nome) VALUES (?)', (pessoa,))
            
    conexao.commit()
    return conexao

# ==========================================
# Passo 2: Lógica com Python
# ==========================================
def obter_duplas(conexao):
    cursor = conexao.cursor()
    cursor.execute('SELECT nome FROM participantes ORDER BY id')
    pessoas = [linha[0] for linha in cursor.fetchall()]
    
    # Cria duplas (Agrupa de 2 em 2)
    duplas = [(pessoas[i], pessoas[i+1]) for i in range(0, len(pessoas), 2)]
    return duplas

def verificar_vez_atual(conexao, duplas):
    cursor = conexao.cursor()
    # Pega o total de pagamentos já registrados para saber de quem é a vez
    cursor.execute('SELECT COUNT(*) FROM pagamentos')
    total_pagamentos = cursor.fetchone()[0]
    
    # Usa o resto da divisão (%) para criar um ciclo contínuo (loop)
    indice_atual = total_pagamentos % len(duplas)
    return duplas[indice_atual]

def registrar_pagamento(conexao, dupla):
    cursor = conexao.cursor()
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    valor_total = 39.00
    
    cursor.execute('''
        INSERT INTO pagamentos (data_pagamento, pessoa_1, pessoa_2, valor_total)
        VALUES (?, ?, ?, ?)
    ''', (data_hoje, dupla[0], dupla[1], valor_total))
    
    conexao.commit()
    print(f"\n✅ Pagamento registrado com sucesso para a dupla: {dupla[0]} e {dupla[1]}!")

# ==========================================
# Passo 3: Executando o Sistema
# ==========================================
if __name__ == '__main__':
    print("💧 Sistema de Controle de Água - Faturamento Hospital Santa Helena 💧")
    print("-" * 65)
    
    conn = inicializar_banco()
    duplas_possiveis = obter_duplas(conn)
    
    dupla_da_vez = verificar_vez_atual(conn, duplas_possiveis)
    
    print(f"👉 É a vez de pagar: {dupla_da_vez[0]} e {dupla_da_vez[1]}")
    print(f"💰 Cota individual: R$ 19,50 (Total: R$ 39,00 para 3 galões)")
    print("-" * 65)
    
    # Simulação de interação do usuário no terminal (VS Code / Colab)
    acao = input("Deseja registrar que esta dupla comprou a água desta semana? (s/n): ")
    if acao.lower() == 's':
        registrar_pagamento(conn, dupla_da_vez)
    else:
        print("Pagamento não registrado. A vez continua com a mesma dupla.")
        
    conn.close()