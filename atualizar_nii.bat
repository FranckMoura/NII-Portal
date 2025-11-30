@echo off
:: Garante que estamos na pasta certa
cd /d "C:\Users\DELL\OneDrive\NII-Portal-1"

echo ---------------------------------------------------------- >> log_execucao.txt
echo INICIO DA ROTINA NII: %date% - %time% >> log_execucao.txt

:: --- BLOCO 1: ROTINA SISREG (Existente) ---
echo [1/6] Extraindo dados do SISREG... >> log_execucao.txt
python extracao_sisreg_v4.py >> log_execucao.txt 2>&1

echo [2/6] Atualizando Banco de Dados SISREG... >> log_execucao.txt
python banco_dados_sisreg.py >> log_execucao.txt 2>&1

echo [3/6] Gerando HTML do Dashboard... >> log_execucao.txt
python gerar_dashboard.py >> log_execucao.txt 2>&1

:: --- BLOCO 2: NOVAS ROTINAS (Simuladas e CNES) ---
echo [4/6] Gerando Indice de Simuladas (PDF)... >> log_execucao.txt
python script_simuladas.py >> log_execucao.txt 2>&1

echo [5/6] Baixando Dados Oficiais do CNES... >> log_execucao.txt
python extrator_cnes.py >> log_execucao.txt 2>&1

:: --- BLOCO 3: ATUALIZAÇÃO DO PORTAL E GITHUB ---
echo [6/6] Atualizando Site e Enviando para Nuvem... >> log_execucao.txt
:: O upload_manager le a pasta 'arquivos', atualiza o index.html e faz o git push
python upload_manager.py >> log_execucao.txt 2>&1

echo FIM: %date% - %time% >> log_execucao.txt
echo ---------------------------------------------------------- >> log_execucao.txt