#!/usr/bin/env powershell
# GameForge Enterprise Secret Rotation - Production Deployment Script
# Production-ready deployment and configuration of the enterprise secret rotation system

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SetupMonitoring,
    
    [Parameter(Mandatory=$false)]
    [switch]$SetupScheduling,
    
    [Parameter(Mandatory=$false)]
    [switch]$SetupCI,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Set default values for switches
if (!$PSBoundParameters.ContainsKey('SetupMonitoring')) { $SetupMonitoring = $true }
if (!$PSBoundParameters.ContainsKey('SetupScheduling')) { $SetupScheduling = $true }
if (!$PSBoundParameters.ContainsKey('SetupCI')) { $SetupCI = $true }

# Configuration
$ScriptRoot = $PSScriptRoot
$LogDir = "$ScriptRoot/logs/deployment"
$MonitoringDir = "$ScriptRoot/monitoring"
$StateDir = "$ScriptRoot/state"

# Ensure directories exist
@($LogDir, $MonitoringDir, $StateDir, "$MonitoringDir/prometheus", "$MonitoringDir/grafana/dashboards", "$MonitoringDir/grafana/datasources") | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Enhanced logging function
function Write-DeployLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "DEPLOY"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] [$Component] $Message"
    
    # Console output with colors
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN" { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        default { Write-Host $logMessage -ForegroundColor White }
    }
    
    # File logging
    $logFile = "$LogDir/deployment-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

# Install missing tools for production readiness
function Install-MissingTools {
    param([array]$MissingTools)
    
    Write-DeployLog "Installing missing tools for production readiness..." -Level "INFO"
    
    foreach ($tool in $MissingTools) {
        switch ($tool) {
            "vault" {
                Write-DeployLog "Installing HashiCorp Vault CLI..." -Level "INFO"
                try {
                    $vaultUrl = "https://releases.hashicorp.com/vault/1.15.2/vault_1.15.2_windows_amd64.zip"
                    $downloadPath = "$env:TEMP\vault.zip"
                    $installPath = "C:\tools\vault"
                    
                    Invoke-WebRequest -Uri $vaultUrl -OutFile $downloadPath
                    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
                    Expand-Archive -Path $downloadPath -DestinationPath $installPath -Force
                    
                    $env:PATH += ";$installPath"
                    [Environment]::SetEnvironmentVariable("PATH", $env:PATH, [EnvironmentVariableTarget]::User)
                    
                    Write-DeployLog "Vault CLI installed successfully" -Level "SUCCESS"
                } catch {
                    Write-DeployLog "Failed to install Vault CLI: $_" -Level "ERROR"
                }
            }
            "gh" {
                Write-DeployLog "Installing GitHub CLI..." -Level "INFO"
                try {
                    $ghUrl = "https://github.com/cli/cli/releases/download/v2.37.0/gh_2.37.0_windows_amd64.zip"
                    $downloadPath = "$env:TEMP\gh.zip"
                    $installPath = "C:\tools\gh"
                    
                    Invoke-WebRequest -Uri $ghUrl -OutFile $downloadPath
                    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
                    Expand-Archive -Path $downloadPath -DestinationPath $installPath -Force
                    
                    $env:PATH += ";$installPath\bin"
                    [Environment]::SetEnvironmentVariable("PATH", $env:PATH, [EnvironmentVariableTarget]::User)
                    
                    Write-DeployLog "GitHub CLI installed successfully" -Level "SUCCESS"
                } catch {
                    Write-DeployLog "Failed to install GitHub CLI: $_" -Level "ERROR"
                }
            }
            "docker" {
                Write-DeployLog "Docker installation requires manual setup. Please install Docker Desktop from https://docker.com/products/docker-desktop" -Level "WARN"
            }
            "docker-compose" {
                Write-DeployLog "Docker Compose is included with Docker Desktop" -Level "INFO"
            }
        }
    }
}

# Validate prerequisites
function Test-Prerequisites {
    Write-DeployLog "Validating deployment prerequisites..." -Level "INFO"
    
    $missingTools = @()
    
    # Check for required tools
    $requiredTools = @{
        "vault" = "HashiCorp Vault CLI for secret management"
        "gh" = "GitHub CLI for CI/CD integration"
        "docker" = "Docker for containerized monitoring stack"
        "docker-compose" = "Docker Compose for orchestration"
    }
    
    foreach ($tool in $requiredTools.Keys) {
        try {
            $null = Get-Command $tool -ErrorAction Stop
            Write-DeployLog "Found: $tool" -Level "SUCCESS"
        } catch {
            $missingTools += $tool
            Write-DeployLog "Missing: $tool - $($requiredTools[$tool])" -Level "WARN"
        }
    }
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-DeployLog "PowerShell 5.0 or higher required" -Level "ERROR"
        throw "PowerShell version not supported"
    } else {
        Write-DeployLog "PowerShell $($PSVersionTable.PSVersion) is supported" -Level "SUCCESS"
    }
    
    # Check required environment variables
    $requiredEnvVars = @("VAULT_ADDR", "VAULT_TOKEN")
    
    foreach ($envVar in $requiredEnvVars) {
        $envValue = [Environment]::GetEnvironmentVariable($envVar)
        if ([string]::IsNullOrEmpty($envValue)) {
            Write-DeployLog "Environment variable $envVar not set" -Level "WARN"
        } else {
            Write-DeployLog "Environment variable $envVar configured" -Level "SUCCESS"
        }
    }
    
    # Handle missing tools
    if ($missingTools.Count -gt 0) {
        Write-DeployLog "Missing prerequisites: $($missingTools -join ', ')" -Level "WARN"
        
        if (!$DryRun) {
            $install = Read-Host "Install missing tools automatically? (y/n)"
            if ($install -eq "y" -or $install -eq "yes") {
                Install-MissingTools -MissingTools $missingTools
                
                # Re-verify after installation
                $stillMissing = @()
                foreach ($tool in $missingTools) {
                    try {
                        $null = Get-Command $tool -ErrorAction Stop
                        Write-DeployLog "$tool now available" -Level "SUCCESS"
                    } catch {
                        $stillMissing += $tool
                    }
                }
                
                if ($stillMissing.Count -gt 0) {
                    Write-DeployLog "Still missing: $($stillMissing -join ', ')" -Level "ERROR"
                    throw "Some prerequisites could not be installed automatically."
                }
            } else {
                Write-DeployLog "Continuing without missing tools (some features may not work)" -Level "WARN"
            }
        } else {
            Write-DeployLog "DRY RUN: Would attempt to install missing tools" -Level "INFO"
        }
    }
    
    Write-DeployLog "Prerequisites validation completed" -Level "SUCCESS"
}

# Setup Vault configuration
function Initialize-VaultConfiguration {
    Write-DeployLog "Initializing Vault configuration for secret rotation..." -Level "INFO"
    
    try {
        # Test Vault connectivity
        $vaultStatus = vault status -format=json 2>$null | ConvertFrom-Json
        if ($vaultStatus.sealed) {
            throw "Vault is sealed. Please unseal Vault before proceeding."
        }
        
        Write-DeployLog "Vault is accessible and unsealed" -Level "SUCCESS"
        
        # Create Vault policy file
        $rotationPolicy = @"
# GameForge Secret Rotation Policy
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "auth/token/create" {
  capabilities = ["create", "update"]
}

path "auth/token/renew/*" {
  capabilities = ["update"]
}

path "auth/token/revoke/*" {
  capabilities = ["update"]
}

path "auth/token/lookup/*" {
  capabilities = ["read"]
}

path "sys/auth" {
  capabilities = ["read"]
}

path "sys/policies/acl/*" {
  capabilities = ["read", "list"]
}
"@
        
        $policyFile = Join-Path $env:TEMP "rotation-policy.hcl"
        Set-Content -Path $policyFile -Value $rotationPolicy
        
        if (!$DryRun) {
            vault policy write gameforge-rotation $policyFile
            Remove-Item $policyFile -Force
            Write-DeployLog "Vault rotation policy created" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would create Vault rotation policy" -Level "INFO"
            Remove-Item $policyFile -Force
        }
        
        # Create dedicated rotation token
        if (!$DryRun) {
            $rotationToken = vault token create -policy=gameforge-rotation -ttl=8760h -renewable=true -format=json | ConvertFrom-Json
            Write-DeployLog "Dedicated rotation token created" -Level "SUCCESS"
            
            # Store token securely
            $tokenFile = "$StateDir/rotation-token.json"
            $rotationToken | ConvertTo-Json | Set-Content $tokenFile
            Write-DeployLog "Token stored in state directory (secure this file!)" -Level "WARN"
        } else {
            Write-DeployLog "DRY RUN: Would create dedicated rotation token" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to initialize Vault configuration: $_" -Level "ERROR"
        if ($_.Exception.Message -like "*vault*not recognized*") {
            Write-DeployLog "Vault CLI not found. Please ensure Vault is installed." -Level "ERROR"
        }
        throw
    }
}

# Setup monitoring stack
function Install-MonitoringStack {
    Write-DeployLog "Setting up monitoring stack (Prometheus + Grafana + AlertManager)..." -Level "INFO"
    
    try {
        # Create Prometheus configuration
        $prometheusConfig = @"
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'vault-rotation-metrics'
    static_configs:
      - targets: ['host.docker.internal:9091']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'vault-server'
    static_configs:
      - targets: ['host.docker.internal:8200']
    metrics_path: '/v1/sys/metrics'
    params:
      format: ['prometheus']
"@

        Set-Content -Path "$MonitoringDir/prometheus/prometheus.yml" -Value $prometheusConfig
        
        # Create AlertManager configuration
        $alertManagerConfig = @"
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'vault-alerts@gameforge.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'SLACK_WEBHOOK_URL_PLACEHOLDER'
        channel: '#security-alerts'
        title: 'GameForge Vault Alert'
        text: 'Alert: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
"@

        Set-Content -Path "$MonitoringDir/alertmanager.yml" -Value $alertManagerConfig
        
        # Create Grafana datasource configuration
        $grafanaDatasource = @"
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
"@

        Set-Content -Path "$MonitoringDir/grafana/datasources/prometheus.yml" -Value $grafanaDatasource
        
        # Create Docker Compose configuration
        $dockerCompose = @"
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: gameforge-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    networks:
      - monitoring
      
  grafana:
    image: grafana/grafana:latest
    container_name: gameforge-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - monitoring
      
  alertmanager:
    image: prom/alertmanager:latest
    container_name: gameforge-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
"@

        Set-Content -Path "$MonitoringDir/docker-compose.yml" -Value $dockerCompose
        
        if (!$DryRun) {
            # Deploy monitoring stack
            Push-Location $MonitoringDir
            try {
                Write-DeployLog "Starting monitoring stack with Docker Compose..." -Level "INFO"
                docker-compose up -d
                Start-Sleep 10
                
                # Verify services are running
                $services = docker-compose ps --services --filter status=running 2>$null
                if ($services -and $services.Count -gt 0) {
                    Write-DeployLog "Monitoring stack deployed successfully" -Level "SUCCESS"
                    Write-DeployLog "Grafana: http://localhost:3000 (admin/admin123)" -Level "INFO"
                    Write-DeployLog "Prometheus: http://localhost:9090" -Level "INFO"
                    Write-DeployLog "AlertManager: http://localhost:9093" -Level "INFO"
                } else {
                    Write-DeployLog "Some monitoring services may not be running. Check Docker." -Level "WARN"
                }
            } catch {
                Write-DeployLog "Error deploying monitoring stack: $_" -Level "ERROR"
            } finally {
                Pop-Location
            }
        } else {
            Write-DeployLog "DRY RUN: Would deploy monitoring stack with Docker Compose" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to setup monitoring stack: $_" -Level "ERROR"
        throw
    }
}

# Setup scheduled tasks
function Install-ScheduledTasks {
    Write-DeployLog "Installing Windows scheduled tasks for automated rotation..." -Level "INFO"
    
    if (!$DryRun) {
        try {
            # Internal secrets - Daily at 1 AM
            $internalAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptRoot\enterprise-secret-rotation.ps1`" -SecretType internal -Environment $Environment"
            $internalTrigger = New-ScheduledTaskTrigger -Daily -At "01:00"
            $internalPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
            $internalSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
            
            Register-ScheduledTask -TaskName "GameForge-InternalSecretRotation" -Action $internalAction -Trigger $internalTrigger -Principal $internalPrincipal -Settings $internalSettings -Force
            Write-DeployLog "Installed scheduled task: GameForge-InternalSecretRotation" -Level "SUCCESS"
            
            # Application secrets - Every 45 days at 3 AM
            $appAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptRoot\enterprise-secret-rotation.ps1`" -SecretType application -Environment $Environment"
            $appTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date "03:00") -RepetitionInterval (New-TimeSpan -Days 45)
            $appPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
            $appSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
            
            Register-ScheduledTask -TaskName "GameForge-ApplicationSecretRotation" -Action $appAction -Trigger $appTrigger -Principal $appPrincipal -Settings $appSettings -Force
            Write-DeployLog "Installed scheduled task: GameForge-ApplicationSecretRotation" -Level "SUCCESS"
            
            # TLS secrets - Every 60 days at 4 AM
            $tlsAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptRoot\enterprise-secret-rotation.ps1`" -SecretType tls -Environment $Environment"
            $tlsTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date "04:00") -RepetitionInterval (New-TimeSpan -Days 60)
            $tlsPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
            $tlsSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
            
            Register-ScheduledTask -TaskName "GameForge-TLSSecretRotation" -Action $tlsAction -Trigger $tlsTrigger -Principal $tlsPrincipal -Settings $tlsSettings -Force
            Write-DeployLog "Installed scheduled task: GameForge-TLSSecretRotation" -Level "SUCCESS"
            
            # Database secrets - Every 90 days at 5 AM (with notification for approval)
            $dbAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptRoot\enterprise-secret-rotation.ps1`" -SecretType database -DryRun -Environment $Environment"
            $dbTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date "05:00") -RepetitionInterval (New-TimeSpan -Days 90)
            $dbPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
            $dbSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
            
            Register-ScheduledTask -TaskName "GameForge-DatabaseSecretRotationCheck" -Action $dbAction -Trigger $dbTrigger -Principal $dbPrincipal -Settings $dbSettings -Force
            Write-DeployLog "Installed scheduled task: GameForge-DatabaseSecretRotationCheck (requires manual approval)" -Level "SUCCESS"
            
            Write-DeployLog "All scheduled tasks installed successfully" -Level "SUCCESS"
            
        } catch {
            Write-DeployLog "Failed to install scheduled tasks: $_" -Level "ERROR"
            throw
        }
    } else {
        Write-DeployLog "DRY RUN: Would install 4 scheduled tasks for automated rotation" -Level "INFO"
    }
}

# Setup CI/CD integration
function Install-CIIntegration {
    Write-DeployLog "Setting up CI/CD integration..." -Level "INFO"
    
    try {
        # Create GitHub Actions workflow directory
        $workflowDir = "$ScriptRoot/.github/workflows"
        if (!(Test-Path $workflowDir)) {
            New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
        }
        
        # Create GitHub Actions workflow
        $workflowContent = @"
name: Secret Rotation

on:
  schedule:
    # Internal secrets - Daily at 1 AM UTC
    - cron: '0 1 * * *'
    # Application secrets - Every 45 days (manually triggered for now)
    # Database secrets - Every 90 days (manually triggered for now)
    
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
      shell: pwsh
      run: |
        Write-Host "PowerShell version: `$(`$PSVersionTable.PSVersion)"
        
    - name: Run Secret Rotation
      shell: pwsh
      env:
        VAULT_ADDR: `${{ secrets.VAULT_ADDR }}
        VAULT_TOKEN: `${{ secrets.VAULT_TOKEN }}
        SLACK_WEBHOOK_URL: `${{ secrets.SLACK_WEBHOOK_URL }}
      run: |
        `$params = @{
          Environment = "production"
          SecretType = "`${{ github.event.inputs.secret_type || 'internal' }}"
        }
        
        if ("`${{ github.event.inputs.force_rotation }}" -eq "true") {
          `$params.ForceRotation = `$true
        }
        
        if ("`${{ github.event.inputs.dry_run }}" -eq "true") {
          `$params.DryRun = `$true
        }
        
        ./enterprise-secret-rotation.ps1 @params
        
    - name: Upload Logs
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: rotation-logs
        path: logs/
        retention-days: 30
"@

        $workflowPath = "$workflowDir/secret-rotation.yml"
        Set-Content -Path $workflowPath -Value $workflowContent -Encoding UTF8
        Write-DeployLog "GitHub Actions workflow created: $workflowPath" -Level "SUCCESS"
        
        # Setup GitHub secrets (if GitHub CLI is available)
        try {
            $requiredSecrets = @{
                "VAULT_ADDR" = $env:VAULT_ADDR
                "VAULT_TOKEN" = $env:VAULT_TOKEN
                "SLACK_WEBHOOK_URL" = $env:SLACK_WEBHOOK_URL
            }
            
            foreach ($secret in $requiredSecrets.Keys) {
                if (![string]::IsNullOrEmpty($requiredSecrets[$secret])) {
                    if (!$DryRun) {
                        gh secret set $secret --body $requiredSecrets[$secret] 2>$null
                        Write-DeployLog "GitHub secret configured: $secret" -Level "SUCCESS"
                    } else {
                        Write-DeployLog "DRY RUN: Would configure GitHub secret: $secret" -Level "INFO"
                    }
                } else {
                    Write-DeployLog "Skipping empty secret: $secret" -Level "WARN"
                }
            }
        } catch {
            Write-DeployLog "GitHub CLI not available or not authenticated. Manually configure secrets in GitHub." -Level "WARN"
        }
        
    } catch {
        Write-DeployLog "Failed to setup CI/CD integration: $_" -Level "ERROR"
    }
}

# Verify deployment
function Test-Deployment {
    Write-DeployLog "Verifying deployment..." -Level "INFO"
    
    try {
        # Test Vault connectivity
        try {
            $vaultStatus = vault status -format=json 2>$null | ConvertFrom-Json
            if (!$vaultStatus.sealed -and $vaultStatus.initialized) {
                Write-DeployLog "Vault is accessible and ready" -Level "SUCCESS"
            } else {
                Write-DeployLog "Vault is sealed or not initialized" -Level "ERROR"
            }
        } catch {
            Write-DeployLog "Vault CLI not available or Vault not accessible" -Level "WARN"
        }
        
        # Test enterprise rotation script
        if (Test-Path "$ScriptRoot/enterprise-secret-rotation.ps1") {
            Write-DeployLog "Enterprise rotation script found" -Level "SUCCESS"
            
            if (!$DryRun) {
                try {
                    & "$ScriptRoot/enterprise-secret-rotation.ps1" -CheckExpiry 2>$null | Out-Null
                    Write-DeployLog "Rotation script executed successfully" -Level "SUCCESS"
                } catch {
                    Write-DeployLog "Rotation script test failed: $_" -Level "ERROR"
                }
            }
        } else {
            Write-DeployLog "Enterprise rotation script not found" -Level "ERROR"
        }
        
        # Test monitoring endpoints (if monitoring was setup)
        if ($SetupMonitoring) {
            try {
                Invoke-RestMethod -Uri "http://localhost:9090/api/v1/label/__name__/values" -TimeoutSec 5 -ErrorAction SilentlyContinue | Out-Null
                Write-DeployLog "Prometheus is accessible" -Level "SUCCESS"
            } catch {
                Write-DeployLog "Prometheus not accessible (may still be starting)" -Level "WARN"
            }
            
            try {
                Invoke-RestMethod -Uri "http://localhost:3000/api/health" -TimeoutSec 5 -ErrorAction SilentlyContinue | Out-Null
                Write-DeployLog "Grafana is accessible" -Level "SUCCESS"
            } catch {
                Write-DeployLog "Grafana not accessible (may still be starting)" -Level "WARN"
            }
        }
        
        # Test scheduled tasks (if scheduling was setup)
        if ($SetupScheduling) {
            $tasks = Get-ScheduledTask -TaskName "GameForge-*" -ErrorAction SilentlyContinue
            if ($tasks.Count -gt 0) {
                Write-DeployLog "$($tasks.Count) scheduled tasks installed" -Level "SUCCESS"
            } else {
                Write-DeployLog "No scheduled tasks found" -Level "WARN"
            }
        }
        
        Write-DeployLog "Deployment verification completed" -Level "SUCCESS"
        
    } catch {
        Write-DeployLog "Error during deployment verification: $_" -Level "ERROR"
    }
}

# Generate deployment summary
function Show-DeploymentSummary {
    Write-DeployLog "=== DEPLOYMENT SUMMARY ===" -Level "INFO"
    Write-DeployLog "Environment: $Environment" -Level "INFO"
    Write-DeployLog "Setup Options: Monitoring=$SetupMonitoring, Scheduling=$SetupScheduling, CI=$SetupCI" -Level "INFO"
    
    Write-Host "`nGameForge Secret Rotation System Deployed!" -ForegroundColor Green
    Write-Host "`nAccess URLs:" -ForegroundColor Cyan
    if ($SetupMonitoring) {
        Write-Host "   • Grafana Dashboard: http://localhost:3000 (admin/admin123)" -ForegroundColor White
        Write-Host "   • Prometheus Metrics: http://localhost:9090" -ForegroundColor White
        Write-Host "   • AlertManager: http://localhost:9093" -ForegroundColor White
    }
    
    Write-Host "`nRotation Schedule:" -ForegroundColor Cyan
    Write-Host "   • Internal Secrets: Daily at 1:00 AM" -ForegroundColor White
    Write-Host "   • Application Secrets: Every 45 days at 3:00 AM" -ForegroundColor White
    Write-Host "   • TLS Certificates: Every 60 days at 4:00 AM" -ForegroundColor White
    Write-Host "   • Database Credentials: Every 90 days at 5:00 AM (requires approval)" -ForegroundColor White
    Write-Host "   • Root Tokens: Manual rotation only (requires approval)" -ForegroundColor Yellow
    
    Write-Host "`nManagement Commands:" -ForegroundColor Cyan
    Write-Host "   • Manual Rotation: .\enterprise-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • Check Expiry: .\enterprise-secret-rotation.ps1 -CheckExpiry" -ForegroundColor White
    Write-Host "   • View Logs: Get-Content logs\audit\vault-rotation-*.log" -ForegroundColor White
    
    Write-Host "`nImportant Files:" -ForegroundColor Cyan
    Write-Host "   • Configuration: config\secret-rotation-config.yml" -ForegroundColor White
    Write-Host "   • Audit Logs: logs\audit\" -ForegroundColor White
    Write-Host "   • State Files: state\" -ForegroundColor White
    Write-Host "   • Backups: backups\" -ForegroundColor White
    
    Write-Host "`nSecurity Notes:" -ForegroundColor Yellow
    Write-Host "   • Secure the state\rotation-token.json file" -ForegroundColor White
    Write-Host "   • Database rotations require manual approval" -ForegroundColor White
    Write-Host "   • Root rotations require manual execution" -ForegroundColor White
    Write-Host "   • Review audit logs regularly" -ForegroundColor White
}

# Main deployment execution
function Start-Deployment {
    try {
        Write-DeployLog "Starting GameForge Enterprise Secret Rotation Deployment" -Level "INFO"
        Write-DeployLog "Environment: $Environment" -Level "INFO"
        Write-DeployLog "Dry Run: $($DryRun.IsPresent)" -Level "INFO"
        
        # Step 1: Validate prerequisites
        Test-Prerequisites
        
        # Step 2: Initialize Vault
        Initialize-VaultConfiguration
        
        # Step 3: Deploy monitoring (if requested)
        if ($SetupMonitoring) {
            Install-MonitoringStack
        }
        
        # Step 4: Install scheduled tasks (if requested)
        if ($SetupScheduling) {
            Install-ScheduledTasks
        }
        
        # Step 5: Setup CI/CD integration (if requested)
        if ($SetupCI) {
            Install-CIIntegration
        }
        
        # Step 6: Verify deployment
        Test-Deployment
        
        # Step 7: Show summary
        Show-DeploymentSummary
        
        Write-DeployLog "Deployment completed successfully!" -Level "SUCCESS"
        
    } catch {
        Write-DeployLog "Deployment failed: $_" -Level "ERROR"
        Write-Host "`nDeployment Failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Check logs in: $LogDir" -ForegroundColor Yellow
        exit 1
    }
}

# Execute deployment
Start-Deployment
