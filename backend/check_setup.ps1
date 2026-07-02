$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

function Read-EnvFile([string]$path) {
    $values = @{}

    if (-not (Test-Path -LiteralPath $path)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $path) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $trimmedLine = $line.Trim()
        if ($trimmedLine.StartsWith("#")) {
            continue
        }

        $parts = $trimmedLine -split "=", 2
        if ($parts.Count -eq 2) {
            $values[$parts[0].Trim()] = $parts[1].Trim()
        }
    }

    return $values
}

function Find-Psql {
    $command = Get-Command psql -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $installedVersions = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending

    foreach ($version in $installedVersions) {
        $candidate = Join-Path $version.FullName "bin\psql.exe"
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Parse-DatabaseUrl([string]$databaseUrl) {
    if ($databaseUrl -match "^postgresql\+psycopg://.+@(?<host>[^:/]+):(?<port>\d+)/(?<database>[^?]+)") {
        return @{
            Host = $Matches["host"]
            Port = $Matches["port"]
            Database = $Matches["database"]
        }
    }

    return $null
}

$envValues = Read-EnvFile ".env"
if ($envValues.Count -eq 0) {
    $envValues = Read-EnvFile ".env.example"
}

$databaseUrl = $envValues["DATABASE_URL"]
$adminEmail = $envValues["FIRST_SUPERUSER_EMAIL"]
$databaseInfo = if ($databaseUrl) { Parse-DatabaseUrl $databaseUrl } else { $null }
$psqlPath = Find-Psql
$pythonPath = Join-Path $PSScriptRoot ".venv-local\Scripts\python.exe"

Write-Host ""
Write-Host "Diagnostico local do backend"
Write-Host "---------------------------"
Write-Host "Arquivo .env.............: " -NoNewline
Write-Host ($(if (Test-Path -LiteralPath ".env") { "OK" } else { "NAO encontrado, usando .env.example como referencia" }))
Write-Host "Python .venv-local.......: " -NoNewline
Write-Host ($(if (Test-Path -LiteralPath $pythonPath) { "OK" } else { "NAO encontrado" }))
Write-Host "psql.....................: " -NoNewline
Write-Host ($(if ($psqlPath) { $psqlPath } else { "NAO encontrado" }))

if ($databaseInfo) {
    $tcpResult = Test-NetConnection -ComputerName $databaseInfo.Host -Port ([int]$databaseInfo.Port) -WarningAction SilentlyContinue
    Write-Host "Banco configurado........: $($databaseInfo.Database)"
    Write-Host "Host / porta.............: $($databaseInfo.Host):$($databaseInfo.Port)"
    Write-Host "Porta acessivel..........: " -NoNewline
    Write-Host ($(if ($tcpResult.TcpTestSucceeded) { "SIM" } else { "NAO" }))
} else {
    Write-Host "Banco configurado........: DATABASE_URL nao pode ser interpretada"
}

Write-Host "Admin inicial............: $adminEmail"

if ($adminEmail -and $adminEmail.EndsWith(".local")) {
    Write-Host ""
    Write-Host "Aviso: o e-mail do admin termina com .local e pode ser rejeitado pelo validador."
}

Write-Host ""
Write-Host "Proximos passos sugeridos"
Write-Host "1. Instalar ou iniciar o PostgreSQL local."
Write-Host "2. Executar .\setup_postgres.ps1 para criar o banco gestao_escolar."
Write-Host "3. Executar .\setup_local.ps1 para rodar migrations e seed."
Write-Host "4. Executar .\run_server.bat para iniciar a API."
