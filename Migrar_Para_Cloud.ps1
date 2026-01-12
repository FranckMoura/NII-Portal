# ==========================================
# SCRIPT DE MIGRAÇÃO: NII-PORTAL V1 -> CLOUD
# ==========================================

Clear-Host
Write-Host "🚀 INICIANDO MIGRAÇÃO PARA ESTRUTURA PROFISSIONAL..." -ForegroundColor Cyan

# 1. Definição de Caminhos
$Origem = "C:\Users\DELL\OneDrive\NII-Portal-1"
$Destino = "C:\Users\DELL\OneDrive\NII-Portal-Cloud"

# 2. Criar Nova Estrutura de Pastas
Write-Host "`n📁 Criando pastas em: $Destino" -ForegroundColor Yellow

# Cria Raiz
if (-not (Test-Path $Destino)) { New-Item -Path $Destino -ItemType Directory | Out-Null }

# Cria Subpastas
$pastas = @(
    "$Destino\backend", 
    "$Destino\frontend", 
    "$Destino\frontend\css", 
    "$Destino\frontend\img",
    "$Destino\frontend\arquivos",
    "$Destino\docs"
)

foreach ($p in $pastas) {
    if (-not (Test-Path $p)) { 
        New-Item -Path $p -ItemType Directory | Out-Null 
        Write-Host "   + Criada: $p" -ForegroundColor Gray
    }
}

# 3. Migrar BACKEND (Scripts e Dados Brutos)
Write-Host "`n🐍 Migrando Backend (Python + Excel)..." -ForegroundColor Yellow

# Copia o script de mortalidade atualizado
Copy-Item "$Origem\mortalidade\processar_mortalidade.py" "$Destino\backend\" -Force
Write-Host "   + Script Python copiado." -ForegroundColor Green

# Copia os arquivos Excel (Relatórios) para junto do script
Copy-Item "$Origem\mortalidade\*.xlsx" "$Destino\backend\" -Force
Write-Host "   + Arquivos Excel copiados." -ForegroundColor Green

# 4. Migrar FRONTEND (Site)
Write-Host "`n🌐 Migrando Frontend (HTML + Assets)..." -ForegroundColor Yellow

# Lista de HTMLs essenciais
$htmls = @(
    "index.html", 
    "painel_mortalidade.html", 
    "consulta_tabela.html",
    "faturamento.html", 
    "financeiro.html", 
    "painel_regulacao.html", 
    "indicasus.html", 
    "institucional.html", 
    "indicadores.html", 
    "manuais.html"
)

foreach ($arquivo in $htmls) {
    if (Test-Path "$Origem\$arquivo") {
        Copy-Item "$Origem\$arquivo" "$Destino\frontend\" -Force
    }
}
Write-Host "   + Arquivos HTML copiados." -ForegroundColor Green

# Copia Imagens
if (Test-Path "$Origem\img") {
    Copy-Item "$Origem\img\*" "$Destino\frontend\img\" -Recurse -Force
    Write-Host "   + Imagens copiadas." -ForegroundColor Green
}

# Copia arquivos JSON antigos (como backup para os módulos que ainda não migraram)
if (Test-Path "$Origem\arquivos") {
    Copy-Item "$Origem\arquivos\*" "$Destino\frontend\arquivos\" -Recurse -Force
    Write-Host "   + JSONs antigos copiados (Backup)." -ForegroundColor Green
}

# 5. Finalização
Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "✅ MIGRAÇÃO CONCLUÍDA!" -ForegroundColor Cyan
Write-Host "Sua nova pasta de trabalho é: $Destino" -ForegroundColor White
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "👉 Próximo passo: Abra a pasta 'NII-Portal-Cloud' no VS Code." -ForegroundColor Yellow