$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$python = ".venv-local\Scripts\python.exe"

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

if (-not (Test-Path -LiteralPath $python)) {
    python -m venv .venv-local
}

& $python -m pip install -r requirements.txt
try {
    & $python -m alembic upgrade head
    & $python -m app.seed
} catch {
    Write-Host ""
    Write-Host "Nao foi possivel concluir a configuracao do banco."
    Write-Host "Execute .\check_setup.ps1 para revisar PostgreSQL, porta 5432 e variaveis do .env."
    throw
}

Write-Host "Backend configurado. Execute .\run_server.bat para iniciar a API."
