Param(
    [string]$Host = $Env:PGHOST,
    [int]$Port = $Env:PGPORT,
    [string]$Database = $Env:PGDATABASE,
    [string]$User = $Env:PGUSER,
    [string]$Password = $Env:PGPASSWORD
)

if (-not $Host -or $Host -eq "") { $Host = "localhost" }
if (-not $Port) { $Port = 5432 }
if (-not $Database -or $Database -eq "") { $Database = "usdt_trading" }
if (-not $User -or $User -eq "") { $User = "postgres" }

Write-Host "Applying sample seed data to database '$Database' on $Host:$Port ..."

$env:PGPASSWORD = $Password
$psqlArgs = @("-h", $Host, "-p", $Port, "-U", $User, "-d", $Database, "-f", "tests/data/seed/sample_data.sql")

& psql @psqlArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "psql returned exit code $LASTEXITCODE. Seed failed."
    Exit $LASTEXITCODE
}

Write-Host "Sample data seed completed successfully."
