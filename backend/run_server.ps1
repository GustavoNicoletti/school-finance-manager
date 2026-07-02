Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv-local\Scripts\python.exe"
$stdout = Join-Path $PSScriptRoot "server.log"
$stderr = Join-Path $PSScriptRoot "server.err.log"
$pidFile = Join-Path $PSScriptRoot "server.pid"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment not found at $python"
}

$listener = netstat -ano | Select-String "127.0.0.1:8000\s+.*LISTENING\s+(\d+)" | Select-Object -First 1
if ($listener) {
    $existingPid = $listener.Matches[0].Groups[1].Value
    Set-Content -LiteralPath $pidFile -Value $existingPid
    Write-Host "API ja esta rodando na porta 8000. PID $existingPid"
    exit 0
}

$process = Start-Process `
    -FilePath $python `
    -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' `
    -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

Start-Sleep -Seconds 2

$listener = netstat -ano | Select-String "127.0.0.1:8000\s+.*LISTENING\s+(\d+)" | Select-Object -First 1
if ($listener) {
    $serverPid = $listener.Matches[0].Groups[1].Value
    Set-Content -LiteralPath $pidFile -Value $serverPid
    Write-Host "API iniciada com sucesso. PID $serverPid"
    exit 0
}

if ($process -and -not $process.HasExited) {
    Set-Content -LiteralPath $pidFile -Value $process.Id
    Write-Host "Processo iniciado, mas a porta 8000 ainda nao respondeu. PID $($process.Id)"
    exit 0
}

Write-Host "A API nao iniciou corretamente. Consulte server.err.log para detalhes."
exit 1
