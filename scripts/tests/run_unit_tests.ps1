Param()

Write-Host "Running unit tests..."
Push-Location $PSScriptRoot\..\..

if (!(Test-Path artefacts\test_reports)) {
    New-Item -Path artefacts\test_reports -ItemType Directory | Out-Null
}

pytest tests/unit --junitxml=artefacts/test_reports/unit_test_report.xml --cov=src --cov-report=xml:artefacts/test_reports/coverage.xml
$exitCode = $LASTEXITCODE

Pop-Location
Exit $exitCode
