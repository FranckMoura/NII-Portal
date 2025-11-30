@echo off
echo ==========================================
echo      NII - SISTEMA DE AUTOMACAO (PRO)
echo ==========================================
echo.

echo [1/4] Gerando Indice de Simuladas...
python script_simuladas.py

echo.
echo [2/4] Baixando Arquivos do CNES (FTP)...
python extrator_cnes_ftp.py

echo.
echo [ATENCAO] Se voce ja usou o TabWin para converter os DBC em DBF,
echo o proximo passo vai gerar os CSVs para o site.
echo.
pause

echo [3/4] Convertendo DBF para CSV...
python conversor_dbf.py

echo.
echo [4/4] Atualizando o Portal NII...
python upload_manager.py

echo.
echo ==========================================
echo      CONCLUIDO!
echo ==========================================
pause