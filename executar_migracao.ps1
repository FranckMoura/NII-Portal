Write-Host "--- INICIANDO MIGRAÇÃO NII PORTAL ---" -ForegroundColor Cyan

# Define o caminho do Python e do Script
$pythonPath = "C:\Users\DELL\AppData\Local\Programs\Python\Python312\python.exe"
$scriptPath = "C:\Users\DELL\OneDrive\NII-Portal-1\migracao_postgres.py"

# Verifica se o script existe
if (Test-Path $scriptPath) {
    Write-Host "Executando script Python..." -ForegroundColor Yellow
    & $pythonPath $scriptPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Sucesso! Banco de dados e JSON atualizados." -ForegroundColor Green
    } else {
        Write-Host "Erro na execução do Python." -ForegroundColor Red
    }
} else {
    Write-Host "Arquivo não encontrado: $scriptPath" -ForegroundColor Red
}

Write-Host "Pressione qualquer tecla para sair..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")