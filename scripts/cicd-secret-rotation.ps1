#!/usr/bin/env powershell
# GameForge Secret Rotation CI/CD Integration
# Automated scheduling and pipeline integration for enterprise secret rotation

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [string]$SecretType = "all",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ForceRotation = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath = "./config/secret-rotation-config.yml"
)

# Configuration
$ScriptRoot = $PSScriptRoot
$LogDir = "$ScriptRoot/logs/cicd"
$StateDir = "$ScriptRoot/state"
$BackupDir = "$ScriptRoot/backups"

# Ensure directories exist
@($LogDir, $StateDir, $BackupDir) | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Enhanced logging
function Write-CICDLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "CICD"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] [$Component] $Message"
    
    # Console output with colors
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN" { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        default { Write-Host $logMessage -ForegroundColor White }
    }
    
    # File logging
    $logFile = "$LogDir/cicd-rotation-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage
    
    # Structured logging for monitoring
    $structuredLog = @{
        timestamp = $timestamp
        level = $Level
        component = $Component
        message = $Message
        environment = $Environment
        secretType = $SecretType
        dryRun = $DryRun.IsPresent
    } | ConvertTo-Json -Compress
    
    $structuredLogFile = "$LogDir/structured-$(Get-Date -Format 'yyyy-MM-dd').jsonl"
    Add-Content -Path $structuredLogFile -Value $structuredLog
}

# Load configuration
function Load-RotationConfig {
    param([string]$ConfigPath)
    
    try {
        if (!(Test-Path $ConfigPath)) {
            throw "Configuration file not found: $ConfigPath"
        }
        
        # Use PowerShell-Yaml if available, otherwise parse manually
        if (Get-Module -ListAvailable -Name powershell-yaml) {
            Import-Module powershell-yaml
            $config = Get-Content $ConfigPath -Raw | ConvertFrom-Yaml
        } else {
            # Basic YAML parsing for our specific structure
            $yamlContent = Get-Content $ConfigPath -Raw
            $config = ConvertFrom-Json ($yamlContent -replace "(?m)^(\s*)([^:]+):\s*(.*)$", '$1"$2": "$3"' -replace "^\s*#.*$", "")
        }
        
        Write-CICDLog "Configuration loaded successfully" -Level "SUCCESS"
        return $config
    } catch {
        Write-CICDLog "Failed to load configuration: $_" -Level "ERROR"
        throw
    }
}

# Check if rotation is due
function Test-RotationDue {
    param(
        [string]$SecretType,
        [hashtable]$Config
    )
    
    try {
        $stateFile = "$StateDir/${SecretType}_last_rotation.json"
        
        if (!(Test-Path $stateFile)) {
            Write-CICDLog "No previous rotation state found for $SecretType - rotation due" -Level "INFO"
            return $true
        }
        
        $lastRotation = Get-Content $stateFile | ConvertFrom-Json
        $lastRotationDate = [DateTime]::Parse($lastRotation.timestamp)
        
        # Get rotation frequency from config
        $frequency = $Config.rotation_schedules."${SecretType}_rotation".frequency
        $intervalDays = switch ($SecretType) {
            "root" { 90 }
            "application" { 45 }
            "tls" { 60 }
            "internal" { 1 }
            "database" { 90 }
            default { 30 }
        }
        
        $nextRotationDue = $lastRotationDate.AddDays($intervalDays)
        $isDue = (Get-Date) -gt $nextRotationDue
        
        if ($isDue) {
            Write-CICDLog "Rotation due for $SecretType (last: $lastRotationDate, due: $nextRotationDue)" -Level "INFO"
        } else {
            Write-CICDLog "Rotation not due for $SecretType (last: $lastRotationDate, next: $nextRotationDue)" -Level "INFO"
        }
        
        return $isDue
    } catch {
        Write-CICDLog "Error checking rotation status for ${SecretType}: $_" -Level "ERROR"
        return $true  # Default to rotation needed if we can't determine
    }
}

# Check secrets approaching expiry
function Get-ExpiringSecrets {
    param([hashtable]$Config)
    
    $expiringSecrets = @()
    $warningDays = $Config.alert_thresholds.expiry_warning_days
    $criticalDays = $Config.alert_thresholds.critical_warning_days
    
    try {
        # Check each secret type
        @("root", "application", "tls", "internal", "database") | ForEach-Object {
            $secretType = $_
            $stateFile = "$StateDir/${secretType}_last_rotation.json"
            
            if (Test-Path $stateFile) {
                $lastRotation = Get-Content $stateFile | ConvertFrom-Json
                $lastRotationDate = [DateTime]::Parse($lastRotation.timestamp)
                
                $intervalDays = switch ($secretType) {
                    "root" { 90 }
                    "application" { 45 }
                    "tls" { 60 }
                    "internal" { 1 }
                    "database" { 90 }
                }
                
                $expiryDate = $lastRotationDate.AddDays($intervalDays)
                $daysToExpiry = ($expiryDate - (Get-Date)).Days
                
                if ($daysToExpiry -le $criticalDays) {
                    $expiringSecrets += @{
                        type = $secretType
                        expiryDate = $expiryDate
                        daysToExpiry = $daysToExpiry
                        severity = "critical"
                    }
                } elseif ($daysToExpiry -le $warningDays) {
                    $expiringSecrets += @{
                        type = $secretType
                        expiryDate = $expiryDate
                        daysToExpiry = $daysToExpiry
                        severity = "warning"
                    }
                }
            }
        }
        
        return $expiringSecrets
    } catch {
        Write-CICDLog "Error checking expiring secrets: $_" -Level "ERROR"
        return @()
    }
}

# Send notifications
function Send-Notification {
    param(
        [string]$Message,
        [string]$Severity = "info",
        [hashtable]$Config
    )
    
    try {
        # Slack notification
        if ($Config.notifications.slack.webhook_url) {
            $slackPayload = @{
                text = $Message
                username = "Vault Rotation Bot"
                icon_emoji = ":key:"
                attachments = @(@{
                    color = switch ($Severity) {
                        "critical" { "danger" }
                        "warning" { "warning" }
                        "success" { "good" }
                        default { "#36a64f" }
                    }
                    text = $Message
                    footer = "GameForge Secret Rotation"
                    ts = [int][double]::Parse((Get-Date -UFormat %s))
                })
            } | ConvertTo-Json -Depth 3
            
            Invoke-RestMethod -Uri $Config.notifications.slack.webhook_url -Method Post -Body $slackPayload -ContentType "application/json"
            Write-CICDLog "Slack notification sent successfully" -Level "SUCCESS"
        }
        
        # Email notification (if configured)
        if ($Config.notifications.email.smtp_server) {
            # Email implementation would go here
            Write-CICDLog "Email notification configured but not implemented in this version" -Level "INFO"
        }
        
    } catch {
        Write-CICDLog "Failed to send notification: $_" -Level "ERROR"
    }
}

# Update CI/CD secrets
function Update-CICDSecrets {
    param(
        [string]$SecretType,
        [hashtable]$NewSecrets,
        [hashtable]$Config
    )
    
    try {
        $secretsToUpdate = $Config.cicd_integration.github_actions.secrets_to_update
        
        # GitHub Actions secrets update
        foreach ($secretName in $secretsToUpdate) {
            if ($NewSecrets.ContainsKey($secretName)) {
                Write-CICDLog "Updating GitHub Actions secret: $secretName" -Level "INFO"
                
                if (!$DryRun) {
                    # Use GitHub CLI to update secrets
                    $secretValue = $NewSecrets[$secretName]
                    & gh secret set $secretName --body $secretValue
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-CICDLog "Successfully updated GitHub Actions secret: $secretName" -Level "SUCCESS"
                    } else {
                        Write-CICDLog "Failed to update GitHub Actions secret: $secretName" -Level "ERROR"
                    }
                } else {
                    Write-CICDLog "DRY RUN: Would update GitHub Actions secret: $secretName" -Level "INFO"
                }
            }
        }
        
        # Docker Compose restart
        $servicesToRestart = $Config.cicd_integration.docker_compose.restart_services_after_rotation.$SecretType
        if ($servicesToRestart) {
            foreach ($service in $servicesToRestart) {
                Write-CICDLog "Restarting Docker service: $service" -Level "INFO"
                
                if (!$DryRun) {
                    & docker-compose restart $service
                    if ($LASTEXITCODE -eq 0) {
                        Write-CICDLog "Successfully restarted service: $service" -Level "SUCCESS"
                    } else {
                        Write-CICDLog "Failed to restart service: $service" -Level "ERROR"
                    }
                } else {
                    Write-CICDLog "DRY RUN: Would restart Docker service: $service" -Level "INFO"
                }
            }
        }
        
    } catch {
        Write-CICDLog "Error updating CI/CD secrets: $_" -Level "ERROR"
        throw
    }
}

# Main execution function
function Invoke-CICDRotation {
    try {
        Write-CICDLog "Starting CI/CD secret rotation" -Level "INFO"
        Write-CICDLog "Environment: $Environment, SecretType: $SecretType, DryRun: $($DryRun.IsPresent)" -Level "INFO"
        
        # Load configuration
        $config = Load-RotationConfig -ConfigPath $ConfigPath
        
        # Check for expiring secrets
        $expiringSecrets = Get-ExpiringSecrets -Config $config
        if ($expiringSecrets.Count -gt 0) {
            foreach ($secret in $expiringSecrets) {
                $message = "Secret '$($secret.type)' expires in $($secret.daysToExpiry) days (expires: $($secret.expiryDate))"
                Write-CICDLog $message -Level $secret.severity.ToUpper()
                Send-Notification -Message $message -Severity $secret.severity -Config $config
            }
        }
        
        # Determine which secrets need rotation
        $secretsToRotate = @()
        
        if ($SecretType -eq "all") {
            $secretTypes = @("root", "application", "tls", "internal", "database")
        } else {
            $secretTypes = @($SecretType)
        }
        
        foreach ($type in $secretTypes) {
            if ($ForceRotation -or (Test-RotationDue -SecretType $type -Config $config)) {
                $secretsToRotate += $type
            }
        }
        
        if ($secretsToRotate.Count -eq 0) {
            Write-CICDLog "No secrets require rotation at this time" -Level "INFO"
            return
        }
        
        Write-CICDLog "Secrets scheduled for rotation: $($secretsToRotate -join ', ')" -Level "INFO"
        
        # Execute rotations with staggering
        $staggerConfig = $config.stagger_config
        
        foreach ($type in $secretsToRotate) {
            try {
                Write-CICDLog "Starting rotation for secret type: $type" -Level "INFO"
                
                # Apply stagger delay
                if ($staggerConfig.enable_staggering -and $staggerConfig.stagger_delays.ContainsKey($type)) {
                    $delayHours = $staggerConfig.stagger_delays[$type]
                    if ($delayHours -gt 0) {
                        Write-CICDLog "Applying stagger delay of $delayHours hours for $type" -Level "INFO"
                        if (!$DryRun) {
                            Start-Sleep -Seconds ($delayHours * 3600)
                        }
                    }
                }
                
                # Execute the rotation script
                if (!$DryRun) {
                    $rotationArgs = @(
                        "-SecretType", $type,
                        "-Environment", $Environment
                    )
                    
                    $rotationResult = & "$ScriptRoot/enterprise-secret-rotation.ps1" @rotationArgs
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-CICDLog "Successfully completed rotation for $type" -Level "SUCCESS"
                        
                        # Update CI/CD systems
                        if ($rotationResult -and $rotationResult.new_secrets) {
                            Update-CICDSecrets -SecretType $type -NewSecrets $rotationResult.new_secrets -Config $config
                        }
                        
                        # Send success notification
                        Send-Notification -Message "Successfully rotated $type secrets in $Environment environment" -Severity "success" -Config $config
                        
                    } else {
                        Write-CICDLog "Failed to rotate $type secrets" -Level "ERROR"
                        Send-Notification -Message "FAILED to rotate $type secrets in $Environment environment" -Severity "critical" -Config $config
                    }
                } else {
                    Write-CICDLog "DRY RUN: Would execute rotation for $type" -Level "INFO"
                }
                
            } catch {
                Write-CICDLog "Error during rotation of ${type}: $_" -Level "ERROR"
                Send-Notification -Message "ERROR during $type secret rotation: $_" -Severity "critical" -Config $config
            }
        }
        
        Write-CICDLog "CI/CD secret rotation completed" -Level "SUCCESS"
        
    } catch {
        Write-CICDLog "Critical error in CI/CD rotation: $_" -Level "ERROR"
        Send-Notification -Message "CRITICAL ERROR in secret rotation pipeline: $_" -Severity "critical" -Config $config
        throw
    }
}

# GitHub Actions workflow generator
function New-GitHubWorkflow {
    $workflowContent = @"
name: Secret Rotation

on:
  schedule:
    # Root and Database secrets - Every 90 days
    - cron: '0 2 1 */3 *'
    # Application secrets - Every 45 days
    - cron: '0 3 */45 * *'
    # TLS secrets - Every 60 days
    - cron: '0 4 */60 * *'
    # Internal secrets - Daily
    - cron: '0 1 * * *'
  
  workflow_dispatch:
    inputs:
      secret_type:
        description: 'Secret type to rotate'
        required: true
        default: 'all'
        type: choice
        options:
        - all
        - root
        - application
        - tls
        - internal
        - database
      force_rotation:
        description: 'Force rotation even if not due'
        required: false
        type: boolean
        default: false
      dry_run:
        description: 'Dry run mode'
        required: false
        type: boolean
        default: false

jobs:
  rotate-secrets:
    runs-on: windows-latest
    environment: production
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Setup PowerShell
      uses: microsoft/setup-msbuild@v1
      
    - name: Configure Vault
      env:
        VAULT_ADDR: `${{ secrets.VAULT_ADDR }}
        VAULT_TOKEN: `${{ secrets.VAULT_TOKEN }}
      run: |
        # Vault configuration steps
        
    - name: Run Secret Rotation
      env:
        VAULT_ADDR: `${{ secrets.VAULT_ADDR }}
        VAULT_TOKEN: `${{ secrets.VAULT_TOKEN }}
        SLACK_WEBHOOK_URL: `${{ secrets.SLACK_WEBHOOK_URL }}
        PAGERDUTY_INTEGRATION_KEY: `${{ secrets.PAGERDUTY_INTEGRATION_KEY }}
        BACKUP_ENCRYPTION_KEY: `${{ secrets.BACKUP_ENCRYPTION_KEY }}
      run: |
        `$params = @{
          Environment = "production"
          SecretType = "`${{ github.event.inputs.secret_type || 'all' }}"
        }
        
        if ("`${{ github.event.inputs.force_rotation }}" -eq "true") {
          `$params.ForceRotation = `$true
        }
        
        if ("`${{ github.event.inputs.dry_run }}" -eq "true") {
          `$params.DryRun = `$true
        }
        
        ./cicd-secret-rotation.ps1 @params
        
    - name: Upload Logs
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: rotation-logs
        path: logs/
        retention-days: 30
"@

    $workflowPath = "$ScriptRoot/.github/workflows/secret-rotation.yml"
    $workflowDir = Split-Path $workflowPath -Parent
    
    if (!(Test-Path $workflowDir)) {
        New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
    }
    
    Set-Content -Path $workflowPath -Value $workflowContent -Encoding UTF8
    Write-CICDLog "GitHub Actions workflow created: $workflowPath" -Level "SUCCESS"
}

# Task scheduler for Windows
function Install-WindowsScheduledTask {
    try {
        # Daily internal secret rotation
        $internalAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File `"$ScriptRoot\cicd-secret-rotation.ps1`" -SecretType internal -Environment $Environment"
        $internalTrigger = New-ScheduledTaskTrigger -Daily -At "01:00"
        Register-ScheduledTask -TaskName "GameForge-InternalSecretRotation" -Action $internalAction -Trigger $internalTrigger -Force
        
        # Application secret rotation (every 45 days)
        $appAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File `"$ScriptRoot\cicd-secret-rotation.ps1`" -SecretType application -Environment $Environment"
        $appTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddDays(45) -RepetitionInterval (New-TimeSpan -Days 45)
        Register-ScheduledTask -TaskName "GameForge-ApplicationSecretRotation" -Action $appAction -Trigger $appTrigger -Force
        
        Write-CICDLog "Windows scheduled tasks installed successfully" -Level "SUCCESS"
    } catch {
        Write-CICDLog "Failed to install Windows scheduled tasks: $_" -Level "ERROR"
    }
}

# Main execution
try {
    switch ($args[0]) {
        "install-workflow" { New-GitHubWorkflow }
        "install-scheduler" { Install-WindowsScheduledTask }
        default { Invoke-CICDRotation }
    }
} catch {
    Write-CICDLog "Fatal error: $_" -Level "ERROR"
    exit 1
}
