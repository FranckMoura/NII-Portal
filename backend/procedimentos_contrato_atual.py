import pandas as pd

# 1. Lendo o arquivo CSV que acabamos de criar
# (No VS Code certifique-se de que o arquivo está na mesma pasta. No Colab, faça o upload).
df = pd.read_csv('producao_faturamento.csv', sep=';', encoding='utf-8')

# 2. Função para limpar os valores monetários e converter para float (decimal)
def limpar_moeda(valor):
    if pd.isna(valor) or valor == '' or valor == 'R$ 0,00':
        return 0.0
    # Remove 'R$', espaços, troca ponto de milhar e vírgula decimal
    valor = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
    return float(valor)

# 3. Aplicando a limpeza nas colunas financeiras
colunas_financeiras = ['Valor_Medio', 'Financeiro_Mes', 'Financeiro_Ano']
for col in colunas_financeiras:
    df[col] = df[col].apply(limpar_moeda)

# 4. Exibindo as primeiras linhas limpas
print("Dados processados com sucesso:")
display(df.head()) # Use print(df.head()) se estiver no VS Code

# 5. Exportando para um Excel limpo e pronto para relatórios
df.to_excel('faturamento_limpo.xlsx', index=False)