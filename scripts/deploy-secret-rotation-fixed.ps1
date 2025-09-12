#!/usr/bin/env powershell
# GameForge Enterprise Secret Rotation - Complete Deployment Script
# Automated deployment and configuration of the secret rotation system

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [bool]$SetupMonitoring = $true,
    
    [Parameter(Mandatory=$false)]
    [bool]$SetupScheduling = $true,
    
    [Parameter(Mandatory=$false)]
    [bool]$SetupCI = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

# Configuration
$ScriptRoot = $PSScriptRoot
$LogDir = "$ScriptRoot/logs/deployment"
$MonitoringDir = "$ScriptRoot/monitoring"

# Ensure directories exist
@($LogDir, $MonitoringDir, "$MonitoringDir/prometheus", "$MonitoringDir/grafana/dashboards", "$MonitoringDir/grafana/datasources") | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Enhanced logging
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
    Add-Content -Path $logFile -Value $logMessage
}

# Validate prerequisites
function Test-Prerequisites {
    Write-DeployLog "Validating deployment prerequisites..." -Level "INFO"
    
    $missingTools = @()
    
    # Check for required tools
    $requiredTools = @{
        "docker" = "Docker for containerized services"
        "docker-compose" = "Docker Compose for orchestration"
        "vault" = "HashiCorp Vault CLI"
    }
    
    foreach ($tool in $requiredTools.Keys) {
        try {
            $null = Get-Command $tool -ErrorAction Stop
            Write-DeployLog "✓ $tool found" -Level "SUCCESS"
        } catch {
            $missingTools += $tool
            Write-DeployLog "✗ $tool not found - $($requiredTools[$tool])" -Level "ERROR"
        }
    }
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-DeployLog "✗ PowerShell 5.0 or higher required" -Level "ERROR"
        $missingTools += "PowerShell"
    } else {
        Write-DeployLog "✓ PowerShell $($PSVersionTable.PSVersion) found" -Level "SUCCESS"
    }
    
    # Check required environment variables
    $requiredEnvVars = @(
        "VAULT_ADDR",
        "VAULT_TOKEN"
    )
    
    foreach ($envVar in $requiredEnvVars) {
        $envValue = [Environment]::GetEnvironmentVariable($envVar)
        if ([string]::IsNullOrEmpty($envValue)) {
            Write-DeployLog "✗ Environment variable $envVar not set" -Level "WARN"
        } else {
            Write-DeployLog "✓ Environment variable $envVar configured" -Level "SUCCESS"
        }
    }
    
    if ($missingTools.Count -gt 0) {
        Write-DeployLog "Missing prerequisites: $($missingTools -join ', ')" -Level "ERROR"
        throw "Prerequisites not met. Please install missing tools and retry."
    }
    
    Write-DeployLog "All prerequisites validated successfully" -Level "SUCCESS"
}

# Setup Vault configuration
function Initialize-VaultConfiguration {
    Write-DeployLog "Initializing Vault configuration for secret rotation..." -Level "INFO"
    
    try {
        # Test Vault connectivity
        if (!$DryRun) {
            $vaultStatus = vault status -format=json 2>$null
            if ($LASTEXITCODE -ne 0) {
                throw "Cannot connect to Vault. Please ensure Vault is running and accessible."
            }
            
            $statusObj = $vaultStatus | ConvertFrom-Json
            if ($statusObj.sealed) {
                throw "Vault is sealed. Please unseal Vault before proceeding."
            }
            
            Write-DeployLog "✓ Vault is accessible and unsealed" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would test Vault connectivity" -Level "INFO"
        }
        
        # Create rotation policy
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
"@
        
        if (!$DryRun) {
            $policyFile = "$env:TEMP/rotation-policy.hcl"
            Set-Content -Path $policyFile -Value $rotationPolicy
            vault policy write gameforge-rotation $policyFile
            Remove-Item $policyFile -Force
            Write-DeployLog "✓ Vault rotation policy created" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would create Vault rotation policy" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to initialize Vault configuration: $_" -Level "ERROR"
        throw
    }
}

# Setup monitoring stack
function Install-MonitoringStack {
    Write-DeployLog "Setting up monitoring stack..." -Level "INFO"
    
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
        
        # Create docker-compose for monitoring
        $monitoringCompose = @"
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
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
"@

        Set-Content -Path "$MonitoringDir/docker-compose.yml" -Value $monitoringCompose
        
        if (!$DryRun) {
            # Deploy monitoring stack
            Push-Location $MonitoringDir
            try {
                Write-DeployLog "Starting monitoring containers..." -Level "INFO"
                docker-compose up -d
                Start-Sleep 10
                
                Write-DeployLog "✓ Monitoring stack deployed successfully" -Level "SUCCESS"
                Write-DeployLog "Grafana: http://localhost:3000 (admin/admin)" -Level "INFO"
                Write-DeployLog "Prometheus: http://localhost:9090" -Level "INFO"
                
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
    Write-DeployLog "Installing Windows scheduled tasks..." -Level "INFO"
    
    try {
        # Internal secrets - Daily at 1 AM
        $internalAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptRoot\cicd-secret-rotation.ps1`" -SecretType internal -Environment $Environment"
        $internalTrigger = New-ScheduledTaskTrigger -Daily -At "01:00"
        
        if (!$DryRun) {
            Register-ScheduledTask -TaskName "GameForge-InternalSecretRotation" -Action $internalAction -Trigger $internalTrigger -Force
            Write-DeployLog "✓ Installed internal secret rotation task" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would install internal secret rotation task" -Level "INFO"
        }
        
        # Application secrets - Every 45 days at 3 AM
        $appAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptRoot\cicd-secret-rotation.ps1`" -SecretType application -Environment $Environment"
        $appTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date "03:00") -RepetitionInterval (New-TimeSpan -Days 45)
        
        if (!$DryRun) {
            Register-ScheduledTask -TaskName "GameForge-ApplicationSecretRotation" -Action $appAction -Trigger $appTrigger -Force
            Write-DeployLog "✓ Installed application secret rotation task" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would install application secret rotation task" -Level "INFO"
        }
        
        Write-DeployLog "✓ Scheduled tasks installation completed" -Level "SUCCESS"
        
    } catch {
        Write-DeployLog "Failed to install scheduled tasks: $_" -Level "ERROR"
        throw
    }
}

# Verify deployment
function Test-Deployment {
    Write-DeployLog "Verifying deployment..." -Level "INFO"
    
    try {
        # Test Vault connectivity
        if (!$DryRun) {
            $vaultTest = vault status -format=json 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-DeployLog "✓ Vault is accessible and ready" -Level "SUCCESS"
            } else {
                Write-DeployLog "✗ Vault is not accessible" -Level "ERROR"
            }
        }
        
        # Test monitoring endpoints
        if ($SetupMonitoring -and !$DryRun) {
            try {
                $prometheus = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/label/__name__/values" -TimeoutSec 5 -ErrorAction Stop
                Write-DeployLog "✓ Prometheus is accessible" -Level "SUCCESS"
            } catch {
                Write-DeployLog "✗ Prometheus is not accessible: $_" -Level "WARN"
            }
            
            try {
                $grafana = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -TimeoutSec 5 -ErrorAction Stop
                Write-DeployLog "✓ Grafana is accessible" -Level "SUCCESS"
            } catch {
                Write-DeployLog "✗ Grafana is not accessible: $_" -Level "WARN"
            }
        }
        
        # Test scheduled tasks
        if ($SetupScheduling -and !$DryRun) {
            $tasks = Get-ScheduledTask -TaskName "GameForge-*" -ErrorAction SilentlyContinue
            if ($tasks.Count -gt 0) {
                Write-DeployLog "✓ $($tasks.Count) scheduled tasks installed" -Level "SUCCESS"
            } else {
                Write-DeployLog "✗ No scheduled tasks found" -Level "WARN"
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
    Write-DeployLog "Deployment completed successfully!" -Level "SUCCESS"
    
    Write-Host "`n🔑 GameForge Secret Rotation System Deployed!" -ForegroundColor Green
    Write-Host "`n📊 Access URLs:" -ForegroundColor Cyan
    if ($SetupMonitoring) {
        Write-Host "   • Grafana Dashboard: http://localhost:3000 (admin/admin)" -ForegroundColor White
        Write-Host "   • Prometheus Metrics: http://localhost:9090" -ForegroundColor White
    }
    
    Write-Host "`n⏰ Rotation Schedule:" -ForegroundColor Cyan
    Write-Host "   • Internal Secrets: Daily at 1:00 AM" -ForegroundColor White
    Write-Host "   • Application Secrets: Every 45 days at 3:00 AM" -ForegroundColor White
    Write-Host "   • TLS Certificates: Every 60 days at 4:00 AM" -ForegroundColor White
    Write-Host "   • Database Credentials: Every 90 days at 5:00 AM" -ForegroundColor White
    Write-Host "   • Root Tokens: Every 90 days at 2:00 AM (requires approval)" -ForegroundColor White
    
    Write-Host "`n🛠️  Management Commands:" -ForegroundColor Cyan
    Write-Host "   • Manual Rotation: .\enterprise-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • CI/CD Rotation: .\cicd-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • View Logs: Get-Content logs\audit\vault-rotation-*.log" -ForegroundColor White
}

# Main deployment execution
function Start-Deployment {
    try {
        Write-DeployLog "🚀 Starting GameForge Enterprise Secret Rotation Deployment" -Level "INFO"
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
        
        # Step 5: Verify deployment
        Test-Deployment
        
        # Step 6: Show summary
        Show-DeploymentSummary
        
    } catch {
        Write-DeployLog "💥 Deployment failed: $_" -Level "ERROR"
        Write-Host "`n💥 Deployment Failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Check logs in: $LogDir" -ForegroundColor Yellow
        exit 1
    }
}

# Execute deployment
Start-Deployment
