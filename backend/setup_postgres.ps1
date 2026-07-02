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

function Parse-DatabaseUrl([string]$databaseUrl) {
    if ($databaseUrl -match "^postgresql\+psycopg://(?<user>[^:]+):(?<password>[^@]+)@(?<host>[^:/]+):(?<port>\d+)/(?<database>[^?]+)") {
        return @{
            User = $Matches["user"]
            Password = $Matches["password"]
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

$databaseInfo = if ($envValues["DATABASE_URL"]) { Parse-DatabaseUrl $envValues["DATABASE_URL"] } else { $null }

$databaseName = if ($databaseInfo) { $databaseInfo.Database } else { "gestao_escolar" }
$postgresUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } elseif ($databaseInfo) { $databaseInfo.User } else { "postgres" }
$hostName = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } elseif ($databaseInfo) { $databaseInfo.Host } else { "127.0.0.1" }
$port = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } elseif ($databaseInfo) { $databaseInfo.Port } else { "5432" }

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

$psql = Find-Psql

if (-not $psql) {
    throw "psql nao foi encontrado. Instale PostgreSQL localmente e abra um novo PowerShell."
}

$password = if ($env:PGPASSWORD) { $env:PGPASSWORD } elseif ($databaseInfo) { $databaseInfo.Password } else { $null }
if ($password) {
    $env:PGPASSWORD = $password
}

$exists = & $psql -h $hostName -p $port -U $postgresUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$databaseName'"

if ($exists -eq "1") {
    Write-Host "Banco $databaseName ja existe."
} else {
    & $psql -h $hostName -p $port -U $postgresUser -d postgres -c "CREATE DATABASE $databaseName WITH ENCODING 'UTF8' TEMPLATE template0"
    Write-Host "Banco $databaseName criado."
}

Write-Host "Agora execute:"
Write-Host "  .\.venv-local\Scripts\python.exe -m alembic upgrade head"
Write-Host "  .\.venv-local\Scripts\python.exe -m app.seed"
