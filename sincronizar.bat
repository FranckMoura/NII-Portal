@echo off
echo =========================================
echo  🚀 ENVIANDO ATUALIZACOES PARA O GITHUB
echo =========================================
echo.

git add .
git commit -m "Atualizacao do Sistema NII Portal"
git push

echo.
echo ✅ Tudo sincronizado com sucesso!
pause