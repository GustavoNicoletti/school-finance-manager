$listeners = netstat -ano | Select-String "127.0.0.1:5173\s+.*LISTENING\s+(\d+)"

if (-not $listeners) {
    Write-Host "Nenhum servidor frontend encontrado na porta 5173."
    exit 0
}

foreach ($listener in $listeners) {
    $serverPid = $listener.Matches[0].Groups[1].Value
    $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $serverPid
        Write-Host "Frontend parado: PID $serverPid"
    }
}
