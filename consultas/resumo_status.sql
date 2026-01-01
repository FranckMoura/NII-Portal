SELECT situacao, COUNT(*) as quantidade
FROM sisreg_solicitacoes
GROUP BY situacao
ORDER BY quantidade DESC;