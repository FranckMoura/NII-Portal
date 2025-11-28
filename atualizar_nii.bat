@echo off
cd /d "C:\Users\DELL\OneDrive\NII-Portal-1"

echo ---------------------------------------------------------- >> log_execucao.txt
echo INICIO: %date% - %time% >> log_execucao.txt

echo [1/4] Extraindo... >> log_execucao.txt
python extracao_sisreg_v4.py >> log_execucao.txt 2>&1

echo [2/4] Banco de Dados... >> log_execucao.txt
python banco_dados_sisreg.py >> log_execucao.txt 2>&1

echo [3/4] Gerando HTML... >> log_execucao.txt
python gerar_dashboard.py >> log_execucao.txt 2>&1

echo [4/4] Publicando GitHub... >> log_execucao.txt
git add . >> log_execucao.txt 2>&1
git commit -m "Rotina 10min" >> log_execucao.txt 2>&1
git push >> log_execucao.txt 2>&1

echo FIM: %date% - %time% >> log_execucao.txt
echo ---------------------------------------------------------- >> log_execucao.txt