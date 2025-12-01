@echo off
:: Configura o terminal para aceitar acentos (UTF-8)
chcp 65001 >nul
cd /d "C:\Users\DELL\OneDrive\NII-Portal-1"

echo ==========================================
echo      NII - SISTEMA DE AUTOMACAO GERAL
echo ==========================================
echo.

:: --- 1. ROTINA SISREG (Painel de Regulacao) ---
echo [1/4] Atualizando SISREG...
python extracao_sisreg_v4.py
python banco_dados_sisreg.py
python gerar_dashboard.py

echo.
:: --- 2. ROTINA SIMULADAS ---
echo [2/4] Gerando Indice de Simuladas...
python script_simuladas.py

echo.
:: --- 3. ROTINA CNES (Elasticnes) ---
echo [3/4] Organizando arquivos do Elasticnes...
:: Pega os CSVs que voce baixou manualmente e joga na pasta certa
python organizar_elastic.py

echo.
:: --- 4. PUBLICACAO ---
echo [4/4] Enviando tudo para o Portal...
python upload_manager.py

echo.
echo ==========================================
echo      CONCLUIDO! SITE 100%% ATUALIZADO.
echo ==========================================
pause