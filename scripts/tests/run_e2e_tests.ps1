Param()

Write-Host "Running E2E tests..."
Push-Location $PSScriptRoot\..\..

if (!(Test-Path artefacts\test_reports)) {
    New-Item -Path artefacts\test_reports -ItemType Directory | Out-Null
}

pytest tests/e2e --junitxml=artefacts/test_reports/e2e_test_report.xml
$exitCode = $LASTEXITCODE

Pop-Location
Exit $exitCode
