<#
.SYNOPSIS
Configuration rollback script for Stage 22 (M22)

.DESCRIPTION
Rollback system configuration to a previous version using the config API.
Requires admin credentials and rollback token from the target version.

.PARAMETER TargetVersion
The version number to rollback to (required)

.PARAMETER RollbackToken
The rollback token for the target version (required)

.PARAMETER AdminUsername
Admin username performing the rollback (default: current Windows user)

.PARAMETER Reason
Reason for rollback (required for audit)

.PARAMETER ApiBase
Base URL of the configuration API (default: http://localhost:8000)

.EXAMPLE
.\config_rollback.ps1 -TargetVersion 3 -RollbackToken "abc123..." -Reason "Reverting due to performance issue"

.NOTES
This script logs all rollback attempts to logs/config_rollback.log
#>

param(
    [Parameter(Mandatory=$true)]
    [int]$TargetVersion,

    [Parameter(Mandatory=$true)]
    [string]$RollbackToken,

    [Parameter(Mandatory=$false)]
    [string]$AdminUsername = $env:USERNAME,

    [Parameter(Mandatory=$true)]
    [string]$Reason,

    [Parameter(Mandatory=$false)]
    [string]$ApiBase = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

# Set up logging
$LogDir = Join-Path $PSScriptRoot "..\logs"
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$LogFile = Join-Path $LogDir "config_rollback.log"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

Write-Log "=== Configuration Rollback Started ==="
Write-Log "Target Version: $TargetVersion"
Write-Log "Admin User: $AdminUsername"
Write-Log "Reason: $Reason"

# Step 1: Get current configuration
Write-Log "Step 1: Fetching current configuration..."
try {
    $CurrentConfigUrl = "$ApiBase/config/current"
    $CurrentConfig = Invoke-RestMethod -Uri $CurrentConfigUrl -Method Get -ContentType "application/json"
    Write-Log "Current version: $($CurrentConfig.version)"

    if ($CurrentConfig.version -eq $TargetVersion) {
        Write-Log "WARNING: Current version ($($CurrentConfig.version)) is the same as target version ($TargetVersion)"
        Write-Log "No rollback needed. Exiting."
        exit 0
    }
} catch {
    Write-Log "ERROR: Failed to fetch current configuration: $_"
    exit 1
}

# Step 2: Get configuration history to verify target version exists
Write-Log "Step 2: Verifying target version exists..."
try {
    $HistoryUrl = "$ApiBase/config/history"
    $History = Invoke-RestMethod -Uri $HistoryUrl -Method Get -ContentType "application/json"

    $TargetExists = $false
    foreach ($entry in $History.history) {
        if ($entry.version -eq $TargetVersion) {
            $TargetExists = $true
            Write-Log "Target version found: v$TargetVersion (created by $($entry.created_by) at $($entry.created_at))"
            break
        }
    }

    if (!$TargetExists) {
        Write-Log "ERROR: Target version $TargetVersion not found in history"
        exit 1
    }
} catch {
    Write-Log "ERROR: Failed to fetch configuration history: $_"
    exit 1
}

# Step 3: Perform rollback
Write-Log "Step 3: Performing rollback to version $TargetVersion..."
try {
    $RollbackUrl = "$ApiBase/config/rollback"
    $RollbackBody = @{
        target_version = $TargetVersion
        rollback_token = $RollbackToken
        rollback_by = $AdminUsername
        rollback_reason = $Reason
    } | ConvertTo-Json

    $RollbackResponse = Invoke-RestMethod -Uri $RollbackUrl -Method Post -Body $RollbackBody -ContentType "application/json"

    Write-Log "SUCCESS: $($RollbackResponse.message)"
    Write-Log "Rolled back from version $($RollbackResponse.rolled_back_from) to version $($RollbackResponse.rolled_back_to)"
    Write-Log "New version: $($RollbackResponse.new_version)"
} catch {
    $StatusCode = $_.Exception.Response.StatusCode.value__
    $ErrorMessage = $_.ErrorDetails.Message
    Write-Log "ERROR: Rollback failed (HTTP $StatusCode): $ErrorMessage"
    exit 1
}

# Step 4: Verify rollback
Write-Log "Step 4: Verifying rollback..."
try {
    Start-Sleep -Seconds 1
    $VerifyConfig = Invoke-RestMethod -Uri $CurrentConfigUrl -Method Get -ContentType "application/json"
    Write-Log "Current version after rollback: $($VerifyConfig.version)"

    if ($VerifyConfig.version -ne $RollbackResponse.new_version) {
        Write-Log "WARNING: Version mismatch after rollback. Expected $($RollbackResponse.new_version), got $($VerifyConfig.version)"
    } else {
        Write-Log "Verification successful: Configuration is now at version $($VerifyConfig.version)"
    }
} catch {
    Write-Log "WARNING: Could not verify rollback: $_"
}

Write-Log "=== Configuration Rollback Completed Successfully ==="
Write-Host "`nRollback completed. See logs at: $LogFile"

exit 0
