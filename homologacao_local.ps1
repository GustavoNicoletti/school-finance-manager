param(
    [ValidateSet("start", "status", "smoke", "stop")]
    [string]$Action = "start",
    [switch]$SkipBackendTests,
    [switch]$SkipFrontendTests
)

$ErrorActionPreference = "Stop"

$rootDir = $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

$backendPidFile = Join-Path $backendDir "server.pid"
$backendLogFile = Join-Path $backendDir "server.log"
$backendErrFile = Join-Path $backendDir "server.err.log"

$frontendPidFile = Join-Path $frontendDir "dev.pid"
$frontendPortFile = Join-Path $frontendDir "dev.port"
$frontendLogFile = Join-Path $frontendDir "vite.log"
$frontendErrFile = Join-Path $frontendDir "vite.err.log"

function Write-Step {
    param([string]$Message)
    Write-Host "[homologacao] $Message"
}

function Get-ListenerPid {
    param([int]$Port)

    $listener = netstat -ano | Select-String "127\.0\.0\.1:$Port\s+.*LISTENING\s+(\d+)" | Select-Object -First 1
    if ($listener) {
        return [int]$listener.Matches[0].Groups[1].Value
    }

    return $null
}

function Test-HttpOk {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 750
    }

    return $false
}

function Resolve-PythonPath {
    $preferred = Join-Path $backendDir ".venv-local\Scripts\python.exe"
    if (Test-Path -LiteralPath $preferred) {
        return $preferred
    }

    $fallback = Join-Path $backendDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    throw "Nenhum Python do backend foi encontrado. Rode backend\\setup_local.ps1 primeiro."
}

function Resolve-NpmPath {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npm) {
        return $npm.Source
    }

    $fallback = "C:\Program Files\nodejs\npm.cmd"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    throw "npm.cmd nao foi encontrado. Instale o Node.js e reabra o terminal."
}

function Get-FrontendPort {
    if (Test-Path -LiteralPath $frontendPortFile) {
        $savedPort = Get-Content -LiteralPath $frontendPortFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($savedPort -as [int]) {
            return [int]$savedPort
        }
    }

    return $null
}

function Find-FreeFrontendPort {
    foreach ($candidate in 5173..5180) {
        if (-not (Get-ListenerPid -Port $candidate)) {
            return $candidate
        }
    }

    throw "Nenhuma porta livre entre 5173 e 5180 para o frontend."
}

function Start-Backend {
    $existingPid = Get-ListenerPid -Port 8000
    if ($existingPid) {
        if (Wait-HttpOk -Url "http://127.0.0.1:8000/health" -TimeoutSeconds 5) {
            Set-Content -LiteralPath $backendPidFile -Value $existingPid
            Write-Step "Backend ja esta online em http://127.0.0.1:8000 (PID $existingPid)."
            return
        }

        throw "A porta 8000 esta ocupada por outro processo (PID $existingPid)."
    }

    $python = Resolve-PythonPath
    Write-Step "Iniciando backend com $python"

    $process = Start-Process `
        -FilePath $python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $backendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $backendLogFile `
        -RedirectStandardError $backendErrFile `
        -PassThru

    if (-not (Wait-HttpOk -Url "http://127.0.0.1:8000/health" -TimeoutSeconds 30)) {
        throw "O backend nao respondeu em http://127.0.0.1:8000/health. Veja backend\\server.err.log."
    }

    Set-Content -LiteralPath $backendPidFile -Value $process.Id
    Write-Step "Backend online em http://127.0.0.1:8000"
}

function Start-Frontend {
    $savedPort = Get-FrontendPort
    if ($savedPort -and (Test-HttpOk -Url "http://127.0.0.1:$savedPort/login")) {
        $savedPid = Get-ListenerPid -Port $savedPort
        if ($savedPid) {
            Set-Content -LiteralPath $frontendPidFile -Value $savedPid
        }
        Write-Step "Frontend ja esta online em http://127.0.0.1:$savedPort/login"
        return $savedPort
    }

    $port = Find-FreeFrontendPort
    $npm = Resolve-NpmPath
    Write-Step "Iniciando frontend na porta $port"

    $command = "`"$npm`" run dev -- --host 127.0.0.1 --port $port"
    $process = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList "/c", $command `
        -WorkingDirectory $frontendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $frontendLogFile `
        -RedirectStandardError $frontendErrFile `
        -PassThru

    if (-not (Wait-HttpOk -Url "http://127.0.0.1:$port/login" -TimeoutSeconds 45)) {
        throw "O frontend nao respondeu em http://127.0.0.1:$port/login. Veja frontend\\vite.err.log."
    }

    Set-Content -LiteralPath $frontendPidFile -Value $process.Id
    Set-Content -LiteralPath $frontendPortFile -Value $port
    Write-Step "Frontend online em http://127.0.0.1:$port/login"
    return $port
}

function Stop-Backend {
    $pids = @()

    if (Test-Path -LiteralPath $backendPidFile) {
        $pids += Get-Content -LiteralPath $backendPidFile -ErrorAction SilentlyContinue
    }

    $listenerPid = Get-ListenerPid -Port 8000
    if ($listenerPid) {
        $pids += $listenerPid
    }

    $pids = $pids | Where-Object { $_ } | Sort-Object -Unique

    foreach ($pid in $pids) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $pid -Force
            Write-Step "Backend parado (PID $pid)."
        }
    }

    if (Test-Path -LiteralPath $backendPidFile) {
        Remove-Item -LiteralPath $backendPidFile -Force
    }
}

function Stop-Frontend {
    $pids = @()
    $knownPort = Get-FrontendPort

    if (Test-Path -LiteralPath $frontendPidFile) {
        $pids += Get-Content -LiteralPath $frontendPidFile -ErrorAction SilentlyContinue
    }

    if ($knownPort) {
        $listenerPid = Get-ListenerPid -Port $knownPort
        if ($listenerPid) {
            $pids += $listenerPid
        }
    }

    $pids = $pids | Where-Object { $_ } | Sort-Object -Unique

    foreach ($pid in $pids) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $pid -Force
            Write-Step "Frontend parado (PID $pid)."
        }
    }

    foreach ($file in @($frontendPidFile, $frontendPortFile)) {
        if (Test-Path -LiteralPath $file) {
            Remove-Item -LiteralPath $file -Force
        }
    }
}

function Show-Status {
    $frontendPort = Get-FrontendPort
    $apiOnline = Test-HttpOk -Url "http://127.0.0.1:8000/health"
    $dbOnline = Test-HttpOk -Url "http://127.0.0.1:8000/health/db"
    $frontendOnline = $false

    if ($frontendPort) {
        $frontendOnline = Test-HttpOk -Url "http://127.0.0.1:$frontendPort/login"
    }

    Write-Host ""
    Write-Host "Status local"
    Write-Host "-----------"
    Write-Host ("Backend:  {0}" -f ($(if ($apiOnline) { "online" } else { "offline" })))
    Write-Host ("Banco:    {0}" -f ($(if ($dbOnline) { "online" } else { "offline" })))
    Write-Host ("Frontend: {0}" -f ($(if ($frontendOnline) { "online" } else { "offline" })))

    if ($apiOnline) {
        Write-Host "API:      http://127.0.0.1:8000"
        if (Test-HttpOk -Url "http://127.0.0.1:8000/api/docs") {
            Write-Host "Docs:     http://127.0.0.1:8000/api/docs"
        }
    }

    if ($frontendOnline) {
        Write-Host "App:      http://127.0.0.1:$frontendPort/login"
    }

    Write-Host ""
}

function Run-Smoke {
    $python = Resolve-PythonPath
    $npm = Resolve-NpmPath

    Start-Backend
    $frontendPort = Start-Frontend
    Show-Status

    if (-not $SkipBackendTests) {
        if ($env:TEST_DATABASE_URL) {
            Write-Step "Rodando smoke do backend"
            Push-Location $backendDir
            try {
                & $python -m pytest tests/test_smoke_critical_flows.py -q
                if ($LASTEXITCODE -ne 0) {
                    throw "O smoke do backend falhou."
                }
            }
            finally {
                Pop-Location
            }
        }
        else {
            Write-Step "Smoke do backend ignorado: defina TEST_DATABASE_URL para rodar os testes."
        }
    }

    if (-not $SkipFrontendTests) {
        Write-Step "Rodando smoke E2E do frontend"
        $env:E2E_API_URL = "http://127.0.0.1:8000/api"
        Push-Location $frontendDir
        try {
            & $npm run test:smoke:e2e
            if ($LASTEXITCODE -ne 0) {
                throw "O smoke do frontend falhou."
            }
        }
        finally {
            Pop-Location
        }
    }

    Write-Step "Homologacao local concluida. Frontend ativo em http://127.0.0.1:$frontendPort/login"
}

switch ($Action) {
    "start" {
        Start-Backend
        $null = Start-Frontend
        Show-Status
    }
    "status" {
        Show-Status
    }
    "smoke" {
        Run-Smoke
    }
    "stop" {
        Stop-Frontend
        Stop-Backend
        Show-Status
    }
}
