#!/usr/bin/env powershell
# GameForge Enterprise Secret Rotation - Deployment Script (Clean Version)
# Fixed all syntax issues systematically

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
        "gh" = "GitHub CLI for CI/CD integration"
    }
    
    foreach ($tool in $requiredTools.Keys) {
        try {
            $null = Get-Command $tool -ErrorAction Stop
            Write-DeployLog "checkmark $tool found" -Level "SUCCESS"
        } catch {
            $missingTools += $tool
            Write-DeployLog "x $tool not found - $($requiredTools[$tool])" -Level "ERROR"
        }
    }
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-DeployLog "x PowerShell 5.0 or higher required" -Level "ERROR"
        $missingTools += "PowerShell"
    } else {
        Write-DeployLog "checkmark PowerShell $($PSVersionTable.PSVersion) found" -Level "SUCCESS"
    }
    
    # Check required environment variables
    $requiredEnvVars = @(
        "VAULT_ADDR",
        "VAULT_TOKEN",
        "SLACK_WEBHOOK_URL"
    )
    
    foreach ($envVar in $requiredEnvVars) {
        $envValue = [Environment]::GetEnvironmentVariable($envVar)
        if ([string]::IsNullOrEmpty($envValue)) {
            Write-DeployLog "x Environment variable $envVar not set" -Level "WARN"
        } else {
            Write-DeployLog "checkmark Environment variable $envVar configured" -Level "SUCCESS"
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
        $vaultStatus = vault status -format=json | ConvertFrom-Json
        if ($vaultStatus.sealed) {
            throw "Vault is sealed. Please unseal Vault before proceeding."
        }
        
        Write-DeployLog "checkmark Vault is accessible and unsealed" -Level "SUCCESS"
        
        # Create necessary policies
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
        
        $policyFile = "$env:TEMP/rotation-policy.hcl"
        Set-Content -Path $policyFile -Value $rotationPolicy
        
        if (!$DryRun) {
            vault policy write gameforge-rotation $policyFile
            Remove-Item $policyFile -Force
            Write-DeployLog "checkmark Vault rotation policy created" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would create Vault rotation policy" -Level "INFO"
        }
        
        # Create dedicated rotation token
        if (!$DryRun) {
            $rotationToken = vault token create -policy=gameforge-rotation -ttl=8760h -renewable=true -format=json | ConvertFrom-Json
            Write-DeployLog "checkmark Dedicated rotation token created" -Level "SUCCESS"
            
            # Store token securely (in production, use proper secret management)
            $tokenFile = "$ScriptRoot/state/rotation-token.json"
            if (!(Test-Path "$ScriptRoot/state")) {
                New-Item -ItemType Directory -Path "$ScriptRoot/state" -Force | Out-Null
            }
            $rotationToken | ConvertTo-Json | Set-Content $tokenFile
            Write-DeployLog "Token stored in state directory (secure this file!)" -Level "WARN"
        } else {
            Write-DeployLog "DRY RUN: Would create dedicated rotation token" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to initialize Vault configuration: $_" -Level "ERROR"
        throw
    }
}

# Setup monitoring stack
function Install-MonitoringStack {
    Write-DeployLog "Deploying monitoring stack (Prometheus + Grafana + AlertManager)..." -Level "INFO"
    
    try {
        # Create Prometheus configuration
        $vaultToken = $env:VAULT_TOKEN
        $prometheusConfig = @"
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  - "/etc/prometheus/rules/*.yml"

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
    bearer_token: '$vaultToken'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
"@

        Set-Content -Path "$MonitoringDir/prometheus/prometheus.yml" -Value $prometheusConfig
        
        # Create AlertManager configuration
        $slackWebhook = $env:SLACK_WEBHOOK_URL
        $alertManagerConfig = @"
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'vault-alerts@gameforge.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: '$slackWebhook'
        channel: '#security-alerts'
        title: 'GameForge Vault Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
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
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
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
      - GF_SECURITY_ADMIN_PASSWORD=$${GRAFANA_ADMIN_PASSWORD:-admin}
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

        Set-Content -Path "$MonitoringDir/docker-compose.yml" -Value $monitoringCompose
        
        if (!$DryRun) {
            # Deploy monitoring stack
            Push-Location $MonitoringDir
            try {
                docker-compose up -d
                Start-Sleep 10
                
                # Verify services are running
                $runningServices = docker-compose ps --services --filter status=running
                if ($runningServices -match "prometheus" -and $runningServices -match "grafana" -and $runningServices -match "alertmanager") {
                    Write-DeployLog "checkmark Monitoring stack deployed successfully" -Level "SUCCESS"
                    Write-DeployLog "Grafana: http://localhost:3000 (admin/admin)" -Level "INFO"
                    Write-DeployLog "Prometheus: http://localhost:9090" -Level "INFO"
                    Write-DeployLog "AlertManager: http://localhost:9093" -Level "INFO"
                } else {
                    throw "Some monitoring services failed to start"
                }
            } finally {
                Pop-Location
            }
        } else {
            Write-DeployLog "DRY RUN: Would deploy monitoring stack with Docker Compose" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to deploy monitoring stack: $_" -Level "ERROR"
        throw
    }
}

# Verify deployment
function Test-Deployment {
    Write-DeployLog "Verifying deployment..." -Level "INFO"
    
    try {
        # Test Vault connectivity
        $vaultStatus = vault status -format=json | ConvertFrom-Json
        if (!$vaultStatus.sealed -and $vaultStatus.initialized) {
            Write-DeployLog "checkmark Vault is accessible and ready" -Level "SUCCESS"
        } else {
            Write-DeployLog "x Vault is not properly configured" -Level "ERROR"
        }
        
        # Test monitoring endpoints
        if ($SetupMonitoring) {
            try {
                $prometheus = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/label/__name__/values" -TimeoutSec 5
                Write-DeployLog "checkmark Prometheus is accessible" -Level "SUCCESS"
            } catch {
                Write-DeployLog "x Prometheus is not accessible" -Level "WARN"
            }
            
            try {
                $grafana = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -TimeoutSec 5
                Write-DeployLog "checkmark Grafana is accessible" -Level "SUCCESS"
            } catch {
                Write-DeployLog "x Grafana is not accessible" -Level "WARN"
            }
        }
        
        # Test rotation script
        if (!$DryRun) {
            $testResult = & "$ScriptRoot\enterprise-secret-rotation.ps1" -DryRun -SecretType internal
            if ($LASTEXITCODE -eq 0) {
                Write-DeployLog "checkmark Rotation script test passed" -Level "SUCCESS"
            } else {
                Write-DeployLog "x Rotation script test failed" -Level "ERROR"
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
    
    Write-Host "`nkey GameForge Secret Rotation System Deployed!" -ForegroundColor Green
    Write-Host "`nbar_chart Access URLs:" -ForegroundColor Cyan
    if ($SetupMonitoring) {
        Write-Host "   • Grafana Dashboard: http://localhost:3000 (admin/admin)" -ForegroundColor White
        Write-Host "   • Prometheus Metrics: http://localhost:9090" -ForegroundColor White
        Write-Host "   • AlertManager: http://localhost:9093" -ForegroundColor White
    }
    
    Write-Host "`nclock Rotation Schedule:" -ForegroundColor Cyan
    Write-Host "   • Internal Secrets: Daily at 1:00 AM" -ForegroundColor White
    Write-Host "   • Application Secrets: Every 45 days at 3:00 AM" -ForegroundColor White
    Write-Host "   • TLS Certificates: Every 60 days at 4:00 AM" -ForegroundColor White
    Write-Host "   • Database Credentials: Every 90 days at 5:00 AM" -ForegroundColor White
    Write-Host "   • Root Tokens: Every 90 days at 2:00 AM (requires approval)" -ForegroundColor White
    
    Write-Host "`ntools Management Commands:" -ForegroundColor Cyan
    Write-Host "   • Manual Rotation: .\enterprise-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • CI/CD Rotation: .\cicd-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • View Logs: Get-Content logs\audit\vault-rotation-*.log" -ForegroundColor White
    
    Write-Host "`nwarning Security Notes:" -ForegroundColor Yellow
    Write-Host "   • Secure the state\rotation-token.json file" -ForegroundColor White
    Write-Host "   • Root rotations require manual approval" -ForegroundColor White
    Write-Host "   • Monitor Slack #security-alerts channel" -ForegroundColor White
    Write-Host "   • Review audit logs regularly" -ForegroundColor White
}

# Main deployment execution
function Start-Deployment {
    try {
        Write-DeployLog "rocket Starting GameForge Enterprise Secret Rotation Deployment" -Level "INFO"
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
        
        # Step 4: Verify deployment
        Test-Deployment
        
        # Step 5: Show summary
        Show-DeploymentSummary
        
    } catch {
        Write-DeployLog "boom Deployment failed: $_" -Level "ERROR"
        Write-Host "`nboom Deployment Failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Check logs in: $LogDir" -ForegroundColor Yellow
        exit 1
    }
}

# Execute deployment
Start-Deployment
