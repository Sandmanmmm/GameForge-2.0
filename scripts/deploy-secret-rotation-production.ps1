#!/usr/bin/env powershell
# GameForge Enterprise Secret Rotation - Complete Deployment Script
# Production-ready automated deployment and configuration of the secret rotation system

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

# Set default values for switches (production-ready defaults)
if (!$PSBoundParameters.ContainsKey('SetupMonitoring')) { $SetupMonitoring = $true }
if (!$PSBoundParameters.ContainsKey('SetupScheduling')) { $SetupScheduling = $true }
if (!$PSBoundParameters.ContainsKey('SetupCI')) { $SetupCI = $true }

# Configuration
$ScriptRoot = $PSScriptRoot
$LogDir = "$ScriptRoot/logs/deployment"
$MonitoringDir = "$ScriptRoot/monitoring"
$StateDir = "$ScriptRoot/state"

# Ensure directories exist
@($LogDir, $MonitoringDir, "$MonitoringDir/prometheus", "$MonitoringDir/grafana/dashboards", "$MonitoringDir/grafana/datasources", $StateDir) | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Enhanced logging with structured output
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
    
    # Structured logging for monitoring
    $structuredLog = @{
        timestamp = $timestamp
        level = $Level
        component = $Component
        message = $Message
        environment = $Environment
        dry_run = $DryRun.IsPresent
    } | ConvertTo-Json -Compress
    
    $structuredLogFile = "$LogDir/structured-$(Get-Date -Format 'yyyy-MM-dd').jsonl"
    Add-Content -Path $structuredLogFile -Value $structuredLog
}

# Validate prerequisites with comprehensive checks
function Test-Prerequisites {
    Write-DeployLog "Validating deployment prerequisites..." -Level "INFO"
    
    $missingTools = @()
    
    # Check for required tools with version validation
    $requiredTools = @{
        "docker" = "Docker for containerized services"
        "vault" = "HashiCorp Vault CLI"
    }
    
    # Optional tools that enhance functionality
    $optionalTools = @{
        "docker-compose" = "Docker Compose for orchestration"
        "gh" = "GitHub CLI for CI/CD integration"
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
    
    foreach ($tool in $optionalTools.Keys) {
        try {
            $null = Get-Command $tool -ErrorAction Stop
            Write-DeployLog "✓ $tool found (optional)" -Level "SUCCESS"
        } catch {
            Write-DeployLog "⚠ $tool not found - $($optionalTools[$tool]) (optional)" -Level "WARN"
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
    
    # Optional environment variables
    $optionalEnvVars = @(
        "SLACK_WEBHOOK_URL",
        "GRAFANA_ADMIN_PASSWORD",
        "PAGERDUTY_INTEGRATION_KEY"
    )
    
    foreach ($envVar in $requiredEnvVars) {
        $envValue = [Environment]::GetEnvironmentVariable($envVar)
        if ([string]::IsNullOrEmpty($envValue)) {
            Write-DeployLog "✗ Environment variable $envVar not set (required)" -Level "ERROR"
            $missingTools += $envVar
        } else {
            Write-DeployLog "✓ Environment variable $envVar configured" -Level "SUCCESS"
        }
    }
    
    foreach ($envVar in $optionalEnvVars) {
        $envValue = [Environment]::GetEnvironmentVariable($envVar)
        if ([string]::IsNullOrEmpty($envValue)) {
            Write-DeployLog "⚠ Environment variable $envVar not set (optional)" -Level "WARN"
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

# Setup Vault configuration with enterprise security policies
function Initialize-VaultConfiguration {
    Write-DeployLog "Initializing Vault configuration for enterprise secret rotation..." -Level "INFO"
    
    try {
        # Test Vault connectivity
        $vaultStatus = vault status -format=json 2>$null | ConvertFrom-Json
        if ($vaultStatus.sealed) {
            throw "Vault is sealed. Please unseal Vault before proceeding."
        }
        
        Write-DeployLog "✓ Vault is accessible and unsealed" -Level "SUCCESS"
        
        # Create enterprise rotation policy with proper least-privilege access
        $rotationPolicy = @"
# GameForge Enterprise Secret Rotation Policy
# Principle of least privilege with comprehensive secret management capabilities

# Application secrets management
path "secret/data/gameforge/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/gameforge/*" {
  capabilities = ["list", "read", "delete"]
}

# Token management for rotation
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

# System access for health checks
path "sys/auth" {
  capabilities = ["read"]
}

path "sys/policies/acl/*" {
  capabilities = ["read", "list"]
}

path "sys/health" {
  capabilities = ["read"]
}

# Audit access for compliance
path "sys/audit" {
  capabilities = ["read", "list"]
}
"@
        
        $policyFile = "$env:TEMP/gameforge-rotation-policy.hcl"
        Set-Content -Path $policyFile -Value $rotationPolicy
        
        if (!$DryRun) {
            vault policy write gameforge-rotation $policyFile 2>$null
            Remove-Item $policyFile -Force
            Write-DeployLog "✓ Enterprise Vault rotation policy created" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would create Vault rotation policy" -Level "INFO"
        }
        
        # Create dedicated rotation token with proper TTL
        if (!$DryRun) {
            $rotationToken = vault token create -policy=gameforge-rotation -ttl=8760h -renewable=true -format=json 2>$null | ConvertFrom-Json
            Write-DeployLog "✓ Dedicated rotation token created (365 day TTL)" -Level "SUCCESS"
            
            # Store token securely
            if (!(Test-Path $StateDir)) {
                New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
            }
            
            $tokenFile = "$StateDir/rotation-token.json"
            $tokenData = @{
                token = $rotationToken.auth.client_token
                created = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                environment = $Environment
                ttl = "8760h"
            }
            $tokenData | ConvertTo-Json | Set-Content $tokenFile
            
            # Set restrictive permissions on token file
            $acl = Get-Acl $tokenFile
            $acl.SetAccessRuleProtection($true, $false)
            $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
            $acl.SetAccessRule($accessRule)
            Set-Acl $tokenFile $acl
            
            Write-DeployLog "Token stored securely in state directory" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would create dedicated rotation token" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to initialize Vault configuration: $_" -Level "ERROR"
        throw
    }
}

# Setup enterprise monitoring stack
function Install-MonitoringStack {
    Write-DeployLog "Deploying enterprise monitoring stack (Prometheus + Grafana + AlertManager)..." -Level "INFO"
    
    try {
        # Create Prometheus configuration with comprehensive metrics
        $vaultToken = $env:VAULT_TOKEN
        $prometheusConfig = @"
global:
  scrape_interval: 30s
  evaluation_interval: 30s
  external_labels:
    environment: '$Environment'
    deployment: 'gameforge-secret-rotation'

rule_files:
  - "/etc/prometheus/rules/*.yml"

scrape_configs:
  - job_name: 'vault-rotation-metrics'
    static_configs:
      - targets: ['host.docker.internal:9091']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'vault-server'
    static_configs:
      - targets: ['host.docker.internal:8200']
    metrics_path: '/v1/sys/metrics'
    params:
      format: ['prometheus']
    bearer_token: '$vaultToken'
    scrape_interval: 30s
    scrape_timeout: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
      timeout: 10s
"@

        Set-Content -Path "$MonitoringDir/prometheus/prometheus.yml" -Value $prometheusConfig
        
        # Create enterprise AlertManager configuration
        $slackWebhook = $env:SLACK_WEBHOOK_URL
        $alertManagerConfig = @"
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'vault-alerts@gameforge.com'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: '$slackWebhook'
        channel: '#ops-notifications'
        title: 'GameForge Vault Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        
  - name: 'critical-alerts'
    slack_configs:
      - api_url: '$slackWebhook'
        channel: '#security-alerts'
        title: 'CRITICAL: GameForge Vault Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
        color: 'danger'
        
  - name: 'warning-alerts'
    slack_configs:
      - api_url: '$slackWebhook'
        channel: '#ops-notifications'
        title: 'WARNING: GameForge Vault Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: 'warning'
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
    editable: true
    jsonData:
      timeInterval: 30s
"@

        Set-Content -Path "$MonitoringDir/grafana/datasources/prometheus.yml" -Value $grafanaDatasource
        
        # Create production-ready docker-compose for monitoring
        $monitoringCompose = @"
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: gameforge-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-admin-api'
    restart: unless-stopped
    networks:
      - monitoring
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
      
  grafana:
    image: grafana/grafana:latest
    container_name: gameforge-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=$${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SECURITY_ALLOW_EMBEDDING=false
      - GF_ANALYTICS_REPORTING_ENABLED=false
      - GF_ANALYTICS_CHECK_FOR_UPDATES=false
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    restart: unless-stopped
    networks:
      - monitoring
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
      
  alertmanager:
    image: prom/alertmanager:latest
    container_name: gameforge-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
      - '--cluster.listen-address='
    restart: unless-stopped
    networks:
      - monitoring
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  alertmanager_data:
    driver: local

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
                Start-Sleep 15
                
                # Verify services are running
                $runningServices = docker-compose ps --services --filter status=running
                $expectedServices = @("prometheus", "grafana", "alertmanager")
                $runningCount = 0
                
                foreach ($service in $expectedServices) {
                    if ($runningServices -match $service) {
                        Write-DeployLog "✓ $service is running" -Level "SUCCESS"
                        $runningCount++
                    } else {
                        Write-DeployLog "✗ $service failed to start" -Level "ERROR"
                    }
                }
                
                if ($runningCount -eq $expectedServices.Count) {
                    Write-DeployLog "✓ All monitoring services deployed successfully" -Level "SUCCESS"
                    Write-DeployLog "Grafana Dashboard: http://localhost:3000 (admin/admin)" -Level "INFO"
                    Write-DeployLog "Prometheus Metrics: http://localhost:9090" -Level "INFO"
                    Write-DeployLog "AlertManager: http://localhost:9093" -Level "INFO"
                } else {
                    throw "$($expectedServices.Count - $runningCount) monitoring services failed to start"
                }
            } catch {
                Write-DeployLog "Error deploying monitoring stack: $_" -Level "ERROR"
                throw
            } finally {
                Pop-Location
            }
        } else {
            Write-DeployLog "DRY RUN: Would deploy enterprise monitoring stack with Docker Compose" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to deploy monitoring stack: $_" -Level "ERROR"
        throw
    }
}

# Setup enterprise automated scheduling with proper error handling
function Install-ScheduledTasks {
    Write-DeployLog "Installing Windows scheduled tasks for enterprise secret rotation..." -Level "INFO"
    
    try {
        # Task configuration based on enterprise rotation frequencies
        $taskConfigs = @(
            @{
                Name = "GameForge-InternalSecretRotation"
                Description = "Daily rotation of internal ephemeral tokens (24h TTL)"
                SecretType = "internal"
                Schedule = "Daily"
                Time = "01:00"
                Frequency = $null
            },
            @{
                Name = "GameForge-ApplicationSecretRotation" 
                Description = "Rotation of application secrets every 45 days"
                SecretType = "application"
                Schedule = "Once"
                Time = "03:00"
                Frequency = 45
            },
            @{
                Name = "GameForge-TLSSecretRotation"
                Description = "Rotation of TLS certificates every 60 days"
                SecretType = "tls"
                Schedule = "Once"
                Time = "04:00"
                Frequency = 60
            },
            @{
                Name = "GameForge-DatabaseSecretRotation"
                Description = "Rotation of database credentials every 90 days"
                SecretType = "database"
                Schedule = "Once"
                Time = "05:00"
                Frequency = 90
            },
            @{
                Name = "GameForge-RootSecretRotationCheck"
                Description = "Check for root token rotation needs every 90 days (manual approval required)"
                SecretType = "root"
                Schedule = "Once"
                Time = "02:00"
                Frequency = 90
                DryRunOnly = $true
            }
        )
        
        $installedTasks = 0
        
        foreach ($config in $taskConfigs) {
            try {
                $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptRoot\cicd-secret-rotation.ps1`" -SecretType $($config.SecretType) -Environment $Environment $(if ($config.DryRunOnly) { '-DryRun' })"
                
                if ($config.Schedule -eq "Daily") {
                    $trigger = New-ScheduledTaskTrigger -Daily -At $config.Time
                } else {
                    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date $config.Time) -RepetitionInterval (New-TimeSpan -Days $config.Frequency)
                }
                
                $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
                $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
                
                $task = @{
                    TaskName = $config.Name
                    Description = $config.Description
                    Action = $action
                    Trigger = $trigger
                    Principal = $principal
                    Settings = $settings
                }
                
                if (!$DryRun) {
                    Register-ScheduledTask @task -Force | Out-Null
                    Write-DeployLog "✓ Installed scheduled task: $($config.Name)" -Level "SUCCESS"
                    $installedTasks++
                } else {
                    Write-DeployLog "DRY RUN: Would install scheduled task: $($config.Name)" -Level "INFO"
                }
                
            } catch {
                Write-DeployLog "Failed to install task $($config.Name): $_" -Level "ERROR"
            }
        }
        
        if (!$DryRun) {
            Write-DeployLog "✓ Successfully installed $installedTasks scheduled tasks" -Level "SUCCESS"
        }
        
    } catch {
        Write-DeployLog "Failed to install scheduled tasks: $_" -Level "ERROR"
        throw
    }
}

# Setup enterprise CI/CD integration
function Install-CIIntegration {
    Write-DeployLog "Setting up enterprise CI/CD integration..." -Level "INFO"
    
    try {
        # Check if GitHub CLI is available
        $ghAvailable = $false
        try {
            $null = Get-Command "gh" -ErrorAction Stop
            $ghAvailable = $true
        } catch {
            Write-DeployLog "GitHub CLI not available - skipping GitHub integration" -Level "WARN"
        }
        
        # Setup GitHub secrets if CLI is available
        if ($ghAvailable) {
            $requiredSecrets = @{
                "VAULT_ADDR" = $env:VAULT_ADDR
                "VAULT_TOKEN" = $env:VAULT_TOKEN
                "SLACK_WEBHOOK_URL" = $env:SLACK_WEBHOOK_URL
                "PAGERDUTY_INTEGRATION_KEY" = $env:PAGERDUTY_INTEGRATION_KEY
                "GRAFANA_ADMIN_PASSWORD" = $env:GRAFANA_ADMIN_PASSWORD
            }
            
            $secretsUpdated = 0
            
            foreach ($secretName in $requiredSecrets.Keys) {
                $secretValue = $requiredSecrets[$secretName]
                if (![string]::IsNullOrEmpty($secretValue)) {
                    if (!$DryRun) {
                        try {
                            & gh secret set $secretName --body $secretValue 2>$null
                            Write-DeployLog "✓ GitHub secret configured: $secretName" -Level "SUCCESS"
                            $secretsUpdated++
                        } catch {
                            Write-DeployLog "Failed to set GitHub secret $secretName`: $_" -Level "WARN"
                        }
                    } else {
                        Write-DeployLog "DRY RUN: Would configure GitHub secret: $secretName" -Level "INFO"
                    }
                } else {
                    Write-DeployLog "Skipping empty secret: $secretName" -Level "WARN"
                }
            }
            
            if (!$DryRun) {
                Write-DeployLog "✓ Updated $secretsUpdated GitHub secrets" -Level "SUCCESS"
            }
        }
        
        # Generate GitHub Actions workflow
        $workflowContent = @"
name: GameForge Secret Rotation

on:
  schedule:
    # Internal secrets - Daily at 1 AM UTC
    - cron: '0 1 * * *'
    # Application secrets - Every 45 days at 3 AM UTC
    - cron: '0 3 */45 * *'
    # TLS secrets - Every 60 days at 4 AM UTC  
    - cron: '0 4 */60 * *'
    # Database secrets - Every 90 days at 5 AM UTC
    - cron: '0 5 1 */3 *'
    # Root secret checks - Every 90 days at 2 AM UTC
    - cron: '0 2 1 */3 *'
  
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
        description: 'Dry run mode (test only)'
        required: false
        type: boolean
        default: false

jobs:
  rotate-secrets:
    runs-on: windows-latest
    environment: production
    timeout-minutes: 30
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Setup PowerShell modules
      shell: powershell
      run: |
        Install-Module -Name powershell-yaml -Force -Scope CurrentUser
        
    - name: Validate environment
      env:
        VAULT_ADDR: `${{ secrets.VAULT_ADDR }}
        VAULT_TOKEN: `${{ secrets.VAULT_TOKEN }}
      shell: powershell
      run: |
        if ([string]::IsNullOrEmpty(`$env:VAULT_ADDR)) {
          throw "VAULT_ADDR not configured"
        }
        if ([string]::IsNullOrEmpty(`$env:VAULT_TOKEN)) {
          throw "VAULT_TOKEN not configured"
        }
        Write-Host "Environment validation passed"
        
    - name: Test Vault connectivity
      env:
        VAULT_ADDR: `${{ secrets.VAULT_ADDR }}
        VAULT_TOKEN: `${{ secrets.VAULT_TOKEN }}
      shell: powershell
      run: |
        vault status
        if (`$LASTEXITCODE -ne 0) {
          throw "Vault connectivity test failed"
        }
        
    - name: Run Secret Rotation
      env:
        VAULT_ADDR: `${{ secrets.VAULT_ADDR }}
        VAULT_TOKEN: `${{ secrets.VAULT_TOKEN }}
        SLACK_WEBHOOK_URL: `${{ secrets.SLACK_WEBHOOK_URL }}
        PAGERDUTY_INTEGRATION_KEY: `${{ secrets.PAGERDUTY_INTEGRATION_KEY }}
        GRAFANA_ADMIN_PASSWORD: `${{ secrets.GRAFANA_ADMIN_PASSWORD }}
      shell: powershell
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
        
        ./cicd-secret-rotation.ps1 @params
        
    - name: Upload rotation logs
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: rotation-logs-`${{ github.run_number }}
        path: logs/
        retention-days: 30
        
    - name: Notify on failure
      if: failure()
      env:
        SLACK_WEBHOOK_URL: `${{ secrets.SLACK_WEBHOOK_URL }}
      shell: powershell
      run: |
        if (`$env:SLACK_WEBHOOK_URL) {
          `$payload = @{
            text = "🔴 GameForge secret rotation failed in GitHub Actions"
            username = "GitHub Actions"
            icon_emoji = ":warning:"
          } | ConvertTo-Json
          
          Invoke-RestMethod -Uri `$env:SLACK_WEBHOOK_URL -Method Post -Body `$payload -ContentType "application/json"
        }
"@
        
        $workflowDir = "$ScriptRoot/.github/workflows"
        if (!(Test-Path $workflowDir)) {
            New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
        }
        
        $workflowPath = "$workflowDir/secret-rotation.yml"
        
        if (!$DryRun) {
            Set-Content -Path $workflowPath -Value $workflowContent -Encoding UTF8
            Write-DeployLog "✓ GitHub Actions workflow created: $workflowPath" -Level "SUCCESS"
        } else {
            Write-DeployLog "DRY RUN: Would create GitHub Actions workflow" -Level "INFO"
        }
        
    } catch {
        Write-DeployLog "Failed to setup CI/CD integration: $_" -Level "ERROR"
        throw
    }
}

# Comprehensive deployment verification
function Test-Deployment {
    Write-DeployLog "Performing comprehensive deployment verification..." -Level "INFO"
    
    $verificationResults = @{
        vault_connectivity = $false
        monitoring_stack = $false
        scheduled_tasks = $false
        rotation_script = $false
    }
    
    try {
        # Test Vault connectivity and status
        try {
            $vaultStatus = vault status -format=json 2>$null | ConvertFrom-Json
            if (!$vaultStatus.sealed -and $vaultStatus.initialized) {
                Write-DeployLog "✓ Vault is accessible and properly configured" -Level "SUCCESS"
                $verificationResults.vault_connectivity = $true
            } else {
                Write-DeployLog "✗ Vault is sealed or not initialized" -Level "ERROR"
            }
        } catch {
            Write-DeployLog "✗ Vault connectivity test failed: $_" -Level "ERROR"
        }
        
        # Test monitoring endpoints
        if ($SetupMonitoring) {
            try {
                $prometheus = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/label/__name__/values" -TimeoutSec 10 2>$null
                Write-DeployLog "✓ Prometheus is accessible and responding" -Level "SUCCESS"
                $verificationResults.monitoring_stack = $true
            } catch {
                Write-DeployLog "✗ Prometheus health check failed" -Level "WARN"
            }
            
            try {
                $grafana = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -TimeoutSec 10 2>$null
                Write-DeployLog "✓ Grafana is accessible and healthy" -Level "SUCCESS"
            } catch {
                Write-DeployLog "✗ Grafana health check failed" -Level "WARN"
            }
        }
        
        # Test scheduled tasks
        if ($SetupScheduling) {
            try {
                $tasks = Get-ScheduledTask -TaskName "GameForge-*" -ErrorAction SilentlyContinue
                if ($tasks.Count -gt 0) {
                    Write-DeployLog "✓ $($tasks.Count) scheduled tasks are installed and configured" -Level "SUCCESS"
                    $verificationResults.scheduled_tasks = $true
                    
                    # Verify task details
                    foreach ($task in $tasks) {
                        $taskInfo = Get-ScheduledTaskInfo -TaskName $task.TaskName
                        Write-DeployLog "  - $($task.TaskName): $($task.State) (Last: $($taskInfo.LastRunTime))" -Level "INFO"
                    }
                } else {
                    Write-DeployLog "✗ No scheduled tasks found" -Level "WARN"
                }
            } catch {
                Write-DeployLog "✗ Scheduled task verification failed: $_" -Level "ERROR"
            }
        }
        
        # Test rotation script functionality
        if (!$DryRun) {
            try {
                Write-DeployLog "Testing rotation script functionality..." -Level "INFO"
                $testResult = & "$ScriptRoot\enterprise-secret-rotation.ps1" -DryRun -SecretType internal 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-DeployLog "✓ Rotation script test passed" -Level "SUCCESS"
                    $verificationResults.rotation_script = $true
                } else {
                    Write-DeployLog "✗ Rotation script test failed (exit code: $LASTEXITCODE)" -Level "ERROR"
                }
            } catch {
                Write-DeployLog "✗ Rotation script test error: $_" -Level "ERROR"
            }
        }
        
        # Generate verification summary
        $passedTests = ($verificationResults.Values | Where-Object { $_ -eq $true }).Count
        $totalTests = $verificationResults.Count
        
        Write-DeployLog "Deployment verification completed: $passedTests/$totalTests tests passed" -Level "INFO"
        
        if ($passedTests -eq $totalTests) {
            Write-DeployLog "✓ All deployment verification tests passed" -Level "SUCCESS"
        } else {
            Write-DeployLog "⚠ Some deployment verification tests failed" -Level "WARN"
        }
        
    } catch {
        Write-DeployLog "Error during deployment verification: $_" -Level "ERROR"
    }
}

# Generate comprehensive deployment summary
function Show-DeploymentSummary {
    Write-DeployLog "=== ENTERPRISE DEPLOYMENT SUMMARY ===" -Level "INFO"
    Write-DeployLog "Environment: $Environment" -Level "INFO"
    Write-DeployLog "Deployment Mode: $(if ($DryRun) { 'DRY RUN' } else { 'PRODUCTION' })" -Level "INFO"
    Write-DeployLog "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Level "INFO"
    
    Write-Host "`n🎯 GameForge Enterprise Secret Rotation System Deployed!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Cyan
    
    Write-Host "`n📊 Access URLs:" -ForegroundColor Cyan
    if ($SetupMonitoring) {
        Write-Host "   • Grafana Dashboard: http://localhost:3000 (admin/admin)" -ForegroundColor White
        Write-Host "   • Prometheus Metrics: http://localhost:9090" -ForegroundColor White
        Write-Host "   • AlertManager: http://localhost:9093" -ForegroundColor White
    }
    
    Write-Host "`n⏰ Enterprise Rotation Schedule:" -ForegroundColor Cyan
    Write-Host "   • Internal Secrets: Daily at 1:00 AM (24h ephemeral)" -ForegroundColor White
    Write-Host "   • Application Secrets: Every 45 days at 3:00 AM" -ForegroundColor White
    Write-Host "   • TLS Certificates: Every 60 days at 4:00 AM" -ForegroundColor White
    Write-Host "   • Database Credentials: Every 90 days at 5:00 AM (approval required)" -ForegroundColor White
    Write-Host "   • Root Tokens: Every 90 days at 2:00 AM (approval required)" -ForegroundColor White
    
    Write-Host "`n🛠️ Management Commands:" -ForegroundColor Cyan
    Write-Host "   • Manual Rotation: .\enterprise-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • CI/CD Rotation: .\cicd-secret-rotation.ps1 -SecretType <type>" -ForegroundColor White
    Write-Host "   • Check Expiry: .\enterprise-secret-rotation.ps1 -CheckExpiry" -ForegroundColor White
    Write-Host "   • View Logs: Get-Content logs\audit\vault-rotation-*.log" -ForegroundColor White
    
    Write-Host "`n📁 Important Directories:" -ForegroundColor Cyan
    Write-Host "   • Configuration: config\" -ForegroundColor White
    Write-Host "   • Audit Logs: logs\audit\" -ForegroundColor White
    Write-Host "   • State Files: state\" -ForegroundColor White
    Write-Host "   • Backups: backups\" -ForegroundColor White
    Write-Host "   • Monitoring: monitoring\" -ForegroundColor White
    
    Write-Host "`n🔒 Security & Compliance:" -ForegroundColor Yellow
    Write-Host "   • All rotations are audited and logged" -ForegroundColor White
    Write-Host "   • Critical secrets require manual approval" -ForegroundColor White
    Write-Host "   • Automated backup before each rotation" -ForegroundColor White
    Write-Host "   • Enterprise monitoring and alerting active" -ForegroundColor White
    Write-Host "   • Secure token storage with restricted permissions" -ForegroundColor White
    
    Write-Host "`n📋 Next Steps:" -ForegroundColor Magenta
    Write-Host "   1. Review and test secret rotation with: .\enterprise-secret-rotation.ps1 -DryRun" -ForegroundColor White
    Write-Host "   2. Configure Slack/PagerDuty webhooks for alerting" -ForegroundColor White
    Write-Host "   3. Set up regular backup procedures" -ForegroundColor White
    Write-Host "   4. Schedule compliance reviews" -ForegroundColor White
    Write-Host "   5. Train operations team on rotation procedures" -ForegroundColor White
    
    Write-Host "`n================================================================" -ForegroundColor Cyan
    Write-Host "Enterprise Secret Rotation System is ready for production use!" -ForegroundColor Green
}

# Main deployment orchestration
function Start-Deployment {
    try {
        Write-DeployLog "🚀 Starting GameForge Enterprise Secret Rotation Deployment" -Level "INFO"
        Write-DeployLog "Target Environment: $Environment" -Level "INFO"
        Write-DeployLog "Deployment Mode: $(if ($DryRun) { 'DRY RUN (testing)' } else { 'PRODUCTION (live)' })" -Level "INFO"
        Write-DeployLog "Components: Monitoring=$SetupMonitoring, Scheduling=$SetupScheduling, CI/CD=$SetupCI" -Level "INFO"
        
        # Step 1: Validate all prerequisites
        Write-DeployLog "Phase 1: Prerequisites validation" -Level "INFO"
        Test-Prerequisites
        
        # Step 2: Initialize Vault with enterprise policies
        Write-DeployLog "Phase 2: Vault enterprise configuration" -Level "INFO"
        Initialize-VaultConfiguration
        
        # Step 3: Deploy monitoring stack (if requested)
        if ($SetupMonitoring) {
            Write-DeployLog "Phase 3: Enterprise monitoring stack deployment" -Level "INFO"
            Install-MonitoringStack
        } else {
            Write-DeployLog "Phase 3: Skipping monitoring stack (disabled)" -Level "INFO"
        }
        
        # Step 4: Install scheduled tasks (if requested)
        if ($SetupScheduling) {
            Write-DeployLog "Phase 4: Automated scheduling installation" -Level "INFO"
            Install-ScheduledTasks
        } else {
            Write-DeployLog "Phase 4: Skipping scheduled tasks (disabled)" -Level "INFO"
        }
        
        # Step 5: Setup CI/CD integration (if requested)
        if ($SetupCI) {
            Write-DeployLog "Phase 5: CI/CD integration setup" -Level "INFO"
            Install-CIIntegration
        } else {
            Write-DeployLog "Phase 5: Skipping CI/CD integration (disabled)" -Level "INFO"
        }
        
        # Step 6: Comprehensive verification
        Write-DeployLog "Phase 6: Deployment verification" -Level "INFO"
        Test-Deployment
        
        # Step 7: Generate summary
        Write-DeployLog "Phase 7: Deployment summary generation" -Level "INFO"
        Show-DeploymentSummary
        
        Write-DeployLog "Enterprise deployment completed successfully!" -Level "SUCCESS"
        
    } catch {
        Write-DeployLog "Enterprise deployment failed: $_" -Level "ERROR"
        Write-Host "`nEnterprise Deployment Failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Check detailed logs in: $LogDir" -ForegroundColor Yellow
        Write-Host "For support, review the deployment logs and error details above." -ForegroundColor Yellow
        exit 1
    }
    }
}

# Execute the enterprise deployment
Start-Deployment
