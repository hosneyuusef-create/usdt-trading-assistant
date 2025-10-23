Param(
    [string]$Host = $Env:PGHOST,
    [int]$Port = $Env:PGPORT,
    [string]$Database = $Env:PGDATABASE,
    [string]$User = $Env:PGUSER,
    [string]$Password = $Env:PGPASSWORD
)

Write-Host "Preparing integration test environment..."
Push-Location $PSScriptRoot\..\..

if (!(Test-Path artefacts\test_reports)) {
    New-Item -Path artefacts\test_reports -ItemType Directory | Out-Null
}

# Seed database if script exists
if (Test-Path tests\data\seed\seed.ps1) {
    Write-Host "Running database seed..."
    $seedArgs = @()
    if ($Host) { $seedArgs += "-Host"; $seedArgs += $Host }
    if ($Port) { $seedArgs += "-Port"; $seedArgs += $Port }
    if ($Database) { $seedArgs += "-Database"; $seedArgs += $Database }
    if ($User) { $seedArgs += "-User"; $seedArgs += $User }
    if ($Password) { $seedArgs += "-Password"; $seedArgs += $Password }
    powershell.exe -ExecutionPolicy Bypass -File tests\data\seed\seed.ps1 @seedArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Database seed failed."
        Pop-Location
        Exit 1
    }
}

Write-Host "Running integration tests..."
pytest tests/integration --junitxml=artefacts/test_reports/integration_test_report.xml
$exitCode = $LASTEXITCODE

Pop-Location
Exit $exitCode
