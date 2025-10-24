param(
    [string]$LogPath = "artefacts\zerotodev_execution.log",
    [string]$PythonExe = "python",
    [string]$PostgresBin = "C:\\Program Files\\PostgreSQL\\16\\bin",
    [string]$DatabaseName = "usdt_trading"
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path (Split-Path $LogPath))) {
    New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null
}

$startTime = Get-Date
Start-Transcript -Path $LogPath -Append | Out-Null

Write-Host "[INFO] Zero-to-Dev setup started at $startTime"
Write-Host "[INFO] Running on PowerShell $($PSVersionTable.PSVersion)" -ForegroundColor Cyan
if ($PSVersionTable.PSVersion.Major -lt 5) {
    throw "PowerShell 5.1 or newer is required."
}

function Invoke-Step {
    param(
        [string]$Name,
        [ScriptBlock]$Action
    )
    Write-Host "[STEP] $Name" -ForegroundColor Yellow
    try {
        & $Action
        Write-Host "[OK] $Name" -ForegroundColor Green
    }
    catch {
        Write-Host "[FAIL] $Name : $_" -ForegroundColor Red
        Stop-Transcript | Out-Null
        throw
    }
}

Invoke-Step "Check Python" {
    & $PythonExe --version
}

$psqlPath = Join-Path $PostgresBin 'psql.exe'
Invoke-Step "Check PostgreSQL CLI" {
    if (!(Test-Path $psqlPath)) {
        throw "psql.exe not found at $psqlPath"
    }
    & $psqlPath --version
}

$rabbitService = Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'RabbitMQ*' }
if ($null -eq $rabbitService) {
    Write-Host "[WARN] RabbitMQ service not detected. Install RabbitMQ Windows Service before running producers." -ForegroundColor DarkYellow
}

$venvPath = Join-Path $PSScriptRoot '..\..\.venv'
Invoke-Step "Create/Update Python virtual environment" {
    if (!(Test-Path $venvPath)) {
        & $PythonExe -m venv $venvPath
    }
    $venvPython = Join-Path $venvPath 'Scripts\python.exe'
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot '..\..\requirements.txt')
    Set-Item -Path env:PYTHONPATH -Value (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

Invoke-Step "Ensure config/test.env present" {
    $testEnv = Resolve-Path (Join-Path $PSScriptRoot '..\..\config\test.env')
    Get-Content $testEnv | ForEach-Object {
        if ($_ -match '^([^#=]+)=([^#]+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ([string]::IsNullOrWhiteSpace($value)) {
                Write-Host "[WARN] Environment variable $name has no value" -ForegroundColor DarkYellow
            }
        }
    }
}

$env:PGPASSWORD = 'Postgres#2025!'
$env:PGUSER = 'postgres'
$env:PGHOST = 'localhost'
$env:PGPORT = '5432'
$env:PGDATABASE = $DatabaseName

Invoke-Step "Ensure database exists" {
    $checkDb = "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName';"
    $exists = & $psqlPath -U $env:PGUSER -h $env:PGHOST -p $env:PGPORT -t -c $checkDb postgres
    if (-not ($exists.Trim())) {
        Write-Host "[INFO] Creating database $DatabaseName"
        & $psqlPath -U $env:PGUSER -h $env:PGHOST -p $env:PGPORT -c "CREATE DATABASE $DatabaseName;" postgres
    }
}

Invoke-Step "Apply database migrations" {
    & $psqlPath -U $env:PGUSER -h $env:PGHOST -p $env:PGPORT -d $DatabaseName -f (Join-Path $PSScriptRoot '..\..\db\migrations\001_initial_schema.sql')
}

$venvPython = Join-Path $venvPath 'Scripts\python.exe'

Invoke-Step "Run migration verification test" {
    & $venvPython (Join-Path $PSScriptRoot '..\..\tests\test_migration.py')
}

Invoke-Step "Run performance benchmark" {
    & $venvPython (Join-Path $PSScriptRoot '..\..\tests\test_performance.py')
}

Invoke-Step "Rollback and re-apply migration to ensure clean state" {
    & $psqlPath -U $env:PGUSER -h $env:PGHOST -p $env:PGPORT -d $DatabaseName -f (Join-Path $PSScriptRoot '..\..\db\migrations\rollback\001_initial_schema_rollback.sql')
    & $psqlPath -U $env:PGUSER -h $env:PGHOST -p $env:PGPORT -d $DatabaseName -f (Join-Path $PSScriptRoot '..\..\db\migrations\001_initial_schema.sql')
}

Invoke-Step "Run smoke tests (pytest placeholder)" {
    Write-Host "[INFO] Additional smoke tests can be executed here (e.g., pytest)." -ForegroundColor Cyan
}

$endTime = Get-Date
Write-Host "[INFO] Zero-to-Dev setup finished at $endTime" -ForegroundColor Cyan
$duration = ($endTime - $startTime)
Write-Host "[INFO] Duration: $($duration.TotalMinutes.ToString('N2')) minutes" -ForegroundColor Cyan

Stop-Transcript | Out-Null
