@echo off
echo --- INICIANDO ROTINA DO PORTAL NII (HBSH) ---
date /t
time /t

:: 1. Entra na pasta do projeto
cd /d "C:\Users\DELL\OneDrive\NII-Portal-1"

:: 2. Roda a Extração (Baixa o CSV do SISREG)
echo [1/4] Extraindo dados do SISREG...
python extracao_sisreg_v4.py

:: 3. Roda o Banco de Dados (Lê o CSV e guarda no SQL)
echo [2/4] Atualizando Banco de Dados...
python banco_dados_sisreg.py

:: 4. Roda o Dashboard (Gera o HTML novo)
echo [3/4] Gerando Painel HTML...
python gerar_dashboard_v3.py

:: 5. Envia para o GitHub (Atualiza o site na internet)
echo [4/4] Publicando no Portal NII...
git add .
git commit -m "Atualizacao automatica - Rotina 1h"
git push

echo --- PROCESSO CONCLUIDO COM SUCESSO ---
timeout /t 10