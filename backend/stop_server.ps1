$pidFile = Join-Path $PSScriptRoot "server.pid"
$pids = @()

if (Test-Path -LiteralPath $pidFile) {
    $pids += Get-Content -LiteralPath $pidFile
}

$listeners = netstat -ano | Select-String "127.0.0.1:8000\s+.*LISTENING\s+(\d+)"
foreach ($listener in $listeners) {
    $pids += $listener.Matches[0].Groups[1].Value
}

$pids = $pids | Where-Object { $_ } | Sort-Object -Unique

if (-not $pids) {
    Write-Host "Nenhum servidor encontrado na porta 8000."
    exit 0
}

foreach ($serverPid in $pids) {
    $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $serverPid
        Write-Host "Servidor parado: PID $serverPid"
    }
}

if (Test-Path -LiteralPath $pidFile) {
    Remove-Item -LiteralPath $pidFile -Force
}
