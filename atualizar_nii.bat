@echo off
:: Garante que o terminal use UTF-8 para acentos
chcp 65001 >nul
cd /d "C:\Users\DELL\OneDrive\NII-Portal-1"

echo ==========================================
echo      NII - SISTEMA DE AUTOMACAO GERAL
echo ==========================================
echo.

:: --- 1. ROTINA SISREG (Painel de Regulação) ---
echo [1/4] Atualizando SISREG (Painel de Regulacao)...
python extracao_sisreg_v4.py
python banco_dados_sisreg.py
python gerar_dashboard.py

echo.
:: --- 2. ROTINA SIMULADAS (Índice de Pacientes) ---
echo [2/4] Gerando Indice de Simuladas (PDF)...
python script_simuladas.py

echo.
:: --- 3. ROTINA CNES (Elasticnes) ---
echo [3/4] Organizando arquivos do Elasticnes...
:: Este script pega os CSVs que voce baixou e arruma na pasta correta
python organizar_elastic.py

echo.
:: --- 4. ATUALIZAÇÃO DO SITE ---
echo [4/4] Enviando atualizacoes para o Portal...
python upload_manager.py

echo.
echo ==========================================
echo      CONCLUIDO! SITE 100%% ATUALIZADO.
echo ==========================================
pause