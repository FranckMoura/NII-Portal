import graphviz

# 1. Criação do objeto do fluxograma
fluxo = graphviz.Digraph('Novo_Fluxo_Faturamento', format='png')
fluxo.attr(rankdir='TB', size='10,10', fontname='Helvetica')
fluxo.attr('node', shape='box', style='filled, rounded', fontname='Helvetica', fontcolor='white')

# 2. Definição dos Nós (Etapas e Responsáveis)
fluxo.node('ARQUIVO', '1. ARQUIVO\nMontagem do Prontuário\ne Anexação de Documentos', fillcolor='#7f8c8d')
fluxo.node('ALEXANDRE', '2. TRIAGEM (Alexandre)\nConsulta Sisreg (AIH),\nImpressão de Exames/AIH', fillcolor='#f39c12')
fluxo.node('DIGITACAO', '3. FATURAMENTO (Cristina e Carlos)\nLançamento no sistema SoulMV', fillcolor='#2980b9')

# Nós das bifurcações
fluxo.node('BIANCA', '4A. AUDITORIA (Bianca)\nConferência minuciosa de\nlançamentos e dados', fillcolor='#27ae60')
fluxo.node('FRANCK_PEND', '4B. GESTÃO DE PENDÊNCIAS (Franck)\nTriagem de NF, Descrição\nCirúrgica, Autorizações', fillcolor='#e74c3c')
fluxo.node('NIR', 'APOIO NIR\nAutorizações (Planejamento Familiar),\nFaturamento Laqueadura e APACs', fillcolor='#8e44ad')

# Nó final
fluxo.node('FRANCK_FINAL', '5. FECHAMENTO (Franck)\nValidação, Consistência, Exportação (SISAIH01),\nRelatórios e Repasses Médicos', fillcolor='#2c3e50')

# 3. Criando as Conexões (Caminho do Prontuário)
fluxo.edge('ARQUIVO', 'ALEXANDRE')
fluxo.edge('ALEXANDRE', 'DIGITACAO')

# Bifurcação a partir da Digitação
fluxo.edge('DIGITACAO', 'BIANCA', label=' Sem pendências', fontcolor='#27ae60', color='#27ae60')
fluxo.edge('DIGITACAO', 'FRANCK_PEND', label=' Com pendências\n(NF, Descrição, etc.)', fontcolor='#c0392b', color='#c0392b')

# Fluxo das Pendências
fluxo.edge('FRANCK_PEND', 'NIR', label=' Eletivas / Planej. Familiar', color='#8e44ad', fontcolor='#8e44ad')
fluxo.edge('FRANCK_PEND', 'FRANCK_FINAL', label=' Outras pendências\nresolvidas', color='#7f8c8d')

# Fluxo de finalização para o Franck
fluxo.edge('BIANCA', 'FRANCK_FINAL', label=' Contas Auditadas', color='#2ecc71')
fluxo.edge('NIR', 'FRANCK_FINAL', label=' Contas Faturadas\ne Autorizadas', color='#8e44ad')

# 4. Salvar a imagem (O display do IPython foi removido)
fluxo.render('novo_fluxograma_faturamento', view=False)
print("Fluxograma gerado com sucesso e salvo como 'novo_fluxograma_faturamento.png'")