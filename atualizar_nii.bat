@echo off
:: Garante que o terminal use UTF-8 para acentos
chcp 65001 >nul
cd /d "C:\Users\DELL\OneDrive\NII-Portal-1"

echo ==========================================
echo      NII - SISTEMA DE AUTOMACAO GERAL
echo ==========================================
echo.

:: --- 1. ROTINA SISREG ---
echo [1/4] Atualizando SISREG...
python extracao_sisreg_v4.py
python banco_dados_sisreg.py
python gerar_dashboard.py

echo.
echo ---------------------------------------------------
echo [2/4] ROTINA SIMULADAS (PDF)
echo.
echo Voce tem 10 segundos para teclar 'S' caso queira atualizar.
echo Caso contrario, o sistema pulara esta etapa automaticamente.
echo.

:: /C SN -> Opções S ou N
:: /T 10 -> Espera 10 segundos
:: /D N  -> Se ninguém responder, a resposta padrão é N (Não)
choice /C SN /T 10 /D N /M "Deseja atualizar as SIMULADAS agora?"

:: O 'errorlevel' verifica qual opção foi escolhida (1=S, 2=N)
if errorlevel 2 goto PularSimuladas
if errorlevel 1 goto RodarSimuladas

:RodarSimuladas
echo.
echo    -> OK! Rodando atualizacao das Simuladas...
python script_simuladas.py
goto FimSimuladas

:PularSimuladas
echo.
echo    -> Tempo esgotado ou 'N' pressionado. Pulando Simuladas...

:FimSimuladas
echo ---------------------------------------------------

echo.
:: --- 3. ROTINA CNES ---
echo [3/4] Organizando arquivos do Elasticnes...
python organizar_elastic.py

echo.
:: --- 4. PUBLICACAO ---
echo [4/4] Enviando tudo para o Portal...
python upload_manager.py

echo.
echo ==========================================
echo      CONCLUIDO! SITE ATUALIZADO.
echo ==========================================
:: O pause no final pode ser removido se você quiser que a janela feche sozinha
:: Mas é bom deixar para você conferir se deu erro quando voltar pro PC
timeout /t 30