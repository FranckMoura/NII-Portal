@echo off
echo ===================================================
echo INICIANDO ROTINA AUTOMATICA DO FATURAMENTO HBSH
echo ===================================================
echo.

cd /d "%~dp0"

echo 1. RODANDO EXTRACAO E PROCESSAMENTO DO SISREG...
python atualizar_tudo.py

echo.
echo 2. RODANDO O ROBO AUDITOR DO INDICASUS...
python robo_indicasus_auto.py

echo.
echo ===================================================
echo ROTINA FINALIZADA COM SUCESSO!
echo ===================================================
timeout /t 10