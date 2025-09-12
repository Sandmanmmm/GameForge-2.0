# ========================================================================
# GameForge Production Deployment Validation Script (PowerShell)
# Validates complete production environment and infrastructure
# ========================================================================

param(
    [switch]$Detailed
)

# Set error handling
$ErrorActionPreference = "Continue"

# Colors for output
function Write-Success { param([string]$Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Warning { param([string]$Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Failure { param([string]$Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Header { param([string]$Message) Write-Host "`n=== $Message ===" -ForegroundColor Cyan }
function Write-Info { param([string]$Message) Write-Host "$Message" -ForegroundColor Blue }

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "GameForge Production Deployment Validation (Windows)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Validation counters
$totalChecks = 0
$passedChecks = 0
$failedChecks = 0
$warningChecks = 0

# Function to run a check
function Test-Requirement {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [bool]$Required = $true
    )
    
    $script:totalChecks++
    
    try {
        $result = & $Test
        if ($result) {
            $script:passedChecks++
            Write-Success "$Name"
            return $true
        } else {
            if ($Required) {
                $script:failedChecks++
                Write-Failure "$Name"
            } else {
                $script:warningChecks++
                Write-Warning "$Name"
            }
            return $false
        }
    } catch {
        if ($Required) {
            $script:failedChecks++
            Write-Failure "$Name - $($_.Exception.Message)"
        } else {
            $script:warningChecks++
            Write-Warning "$Name - $($_.Exception.Message)"
        }
        return $false
    }
}

# ========================================================================
# Phase 0-6 Infrastructure Validation
# ========================================================================

Write-Header "Phase 0-6 Infrastructure Validation"

# Phase 0: Docker Infrastructure
Test-Requirement "Docker Engine" { 
    try { docker --version | Out-Null; return $true } catch { return $false } 
}

Test-Requirement "Docker Compose" { 
    try { docker-compose --version | Out-Null; return $true } catch { return $false } 
}

Test-Requirement "Docker Service Running" { 
    try { docker info | Out-Null; return $true } catch { return $false } 
}

# Phase 1: SSL/TLS Infrastructure
Test-Requirement "SSL Certificate Directory" { Test-Path "./ssl/certs" }
Test-Requirement "SSL Private Key Directory" { Test-Path "./ssl/private" }
Test-Requirement "Nginx Configuration" { Test-Path "./nginx/nginx.conf" }
Test-Requirement "Nginx Site Configuration" { Test-Path "./nginx/conf.d/gameforge.conf" }

# Phase 2: Secrets Management (Vault)
Test-Requirement "Vault Docker Compose" { Test-Path "./docker-compose.vault.yml" }
Test-Requirement "Vault Configuration" { Test-Path "./vault/config/vault.hcl" } $false

# Phase 3: Elasticsearch Infrastructure
Test-Requirement "Elasticsearch Docker Compose" { Test-Path "./docker-compose.elasticsearch.yml" }
Test-Requirement "Elasticsearch Configuration" { Test-Path "./elasticsearch/config" }

# Phase 4: Security Scanning Infrastructure
Test-Requirement "Security Docker Compose" { Test-Path "./docker-compose.security.yml" }

# Phase 5: Audit Logging Infrastructure
Test-Requirement "Audit Docker Compose" { Test-Path "./docker-compose.audit.yml" }

# Phase 6: Advanced Monitoring Infrastructure
Test-Requirement "GPU Monitoring Docker Compose" { Test-Path "./docker-compose.gpu-monitoring.yml" }
Test-Requirement "AlertManager Docker Compose" { Test-Path "./docker-compose.alertmanager.yml" }
Test-Requirement "Log Pipeline Docker Compose" { Test-Path "./docker-compose.log-pipeline.yml" }
Test-Requirement "Monitoring Configuration Directory" { Test-Path "./monitoring/configs" }
Test-Requirement "Monitoring Dashboards" { Test-Path "./monitoring/dashboards" }
Test-Requirement "Monitoring Alerting" { Test-Path "./monitoring/alerting" }

# ========================================================================
# Production Files Validation
# ========================================================================

Write-Header "Production Files Validation"

Test-Requirement "Production Dockerfile" { Test-Path "./Dockerfile.production" }
Test-Requirement "Production Docker Compose" { Test-Path "./docker-compose.production-secure.yml" }
Test-Requirement "Production Environment" { Test-Path ".env.production" }
Test-Requirement "Production Setup Script (Bash)" { Test-Path "setup-production.sh" } $false
Test-Requirement "Windows Setup Script" { Test-Path "./setup-production.ps1" }

# ========================================================================
# Backup Infrastructure Validation
# ========================================================================

Write-Header "Backup Infrastructure Validation"

Test-Requirement "Backup Directory" { Test-Path "./backup" }
Test-Requirement "Backup Dockerfile" { Test-Path "./backup/Dockerfile.backup" }
Test-Requirement "Backup Scripts Directory" { Test-Path "./backup/scripts" }
Test-Requirement "Backup Main Script" { Test-Path "./backup/scripts/backup.sh" }
Test-Requirement "Backup Maintenance Script" { Test-Path "./backup/scripts/maintenance.sh" }
Test-Requirement "Backup Crontab" { Test-Path "./backup/crontab" }

# ========================================================================
# Application Files Validation
# ========================================================================

Write-Header "Application Files Validation"

Test-Requirement "Production Server Script" { Test-Path "./gameforge_production_server.py" }
Test-Requirement "RTX4090 Optimized Server" { Test-Path "./gameforge_rtx4090_server.py" }
Test-Requirement "Custom SDXL Pipeline" { Test-Path "./custom_sdxl_pipeline.py" }
Test-Requirement "Backend GPU Integration" { Test-Path "./backend_gpu_integration.py" }
Test-Requirement "Requirements File" { Test-Path "./requirements.txt" }
Test-Requirement "Package.json" { Test-Path "./package.json" }

# ========================================================================
# Configuration Files Validation
# ========================================================================

Write-Header "Configuration Files Validation"

Test-Requirement "Database Setup SQL" { Test-Path "./database_setup.sql" }
Test-Requirement "Redis Configuration" { Test-Path "./redis/redis.conf" }
Test-Requirement "Auth Middleware" { Test-Path "./auth_middleware.py" }

# ========================================================================
# Docker Compose Syntax Validation
# ========================================================================

Write-Header "Docker Compose Syntax Validation"

# Main production compose file
if (Test-Path "docker-compose.production-secure.yml") {
    Test-Requirement "Production Compose Syntax" { 
        try { 
            docker-compose -f docker-compose.production-secure.yml config | Out-Null
            return $true 
        } catch { 
            return $false 
        } 
    }
}

# Infrastructure compose files
Get-ChildItem -Path "." -Filter "docker-compose.*.yml" | ForEach-Object {
    $filename = $_.BaseName
    Test-Requirement "$filename Syntax" { 
        try { 
            docker-compose -f $_.Name config | Out-Null
            return $true 
        } catch { 
            return $false 
        } 
    } $false
}

# ========================================================================
# Monitoring Configuration Validation
# ========================================================================

Write-Header "Monitoring Configuration Validation"

# GPU monitoring configurations
if (Test-Path "monitoring/configs") {
    Test-Requirement "GPU Prometheus Config" { Test-Path "./monitoring/configs/gpu-prometheus.yml" }
    Test-Requirement "GPU Exporter Config" { Test-Path "./monitoring/configs/gpu-exporter.yml" }
    Test-Requirement "Prometheus Rules" { Test-Path "./monitoring/configs/prometheus-rules.yml" }
}

# Dashboard configurations
if (Test-Path "monitoring/dashboards") {
    Test-Requirement "GPU Dashboard" { Test-Path "./monitoring/dashboards/gpu-monitoring.json" }
    Test-Requirement "Game Analytics Dashboard" { Test-Path "./monitoring/dashboards/game-analytics.json" }
    Test-Requirement "Business Intelligence Dashboard" { Test-Path "./monitoring/dashboards/business-intelligence.json" }
    Test-Requirement "System Overview Dashboard" { Test-Path "./monitoring/dashboards/system-overview.json" }
}

# AlertManager configurations
if (Test-Path "monitoring/alerting") {
    Test-Requirement "AlertManager Config" { Test-Path "./monitoring/alerting/alertmanager.yml" }
    Test-Requirement "Alert Rules" { Test-Path "./monitoring/alerting/alert-rules.yml" }
    Test-Requirement "Notification Templates" { Test-Path "./monitoring/alerting/templates.tmpl" }
}

# ========================================================================
# Security Configuration Validation
# ========================================================================

Write-Header "Security Configuration Validation"

# Check for default passwords (should be changed)
if (Test-Path ".env.production") {
    $envContent = Get-Content ".env.production" -Raw
    if ($envContent -match "change-this") {
        Test-Requirement "Production Passwords Updated" { $false }
        Write-Failure "Default passwords found in .env.production - MUST be changed before deployment!"
    } else {
        Test-Requirement "Production Passwords Updated" { $true }
    }
}

# ========================================================================
# Volume Directory Structure Validation
# ========================================================================

Write-Header "Volume Directory Structure Validation"

$volumes = @(
    "volumes/logs",
    "volumes/cache",
    "volumes/assets",
    "volumes/models",
    "volumes/postgres",
    "volumes/redis",
    "volumes/elasticsearch",
    "volumes/nginx-logs",
    "volumes/backup-logs"
)

    foreach ($volume in $volumes) {
        Test-Requirement "Volume Directory: $volume" { Test-Path "./$volume" } $false
    }

# ========================================================================
# Final Validation Summary
# ========================================================================

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

Write-Info "Total Checks: $totalChecks"
Write-Success "Passed: $passedChecks"

if ($warningChecks -gt 0) {
    Write-Warning "Warnings: $warningChecks"
}

if ($failedChecks -gt 0) {
    Write-Failure "Failed: $failedChecks"
} else {
    Write-Success "Failed: 0"
}

# Calculate success rate
$successRate = [math]::Round(($passedChecks * 100) / $totalChecks, 1)

Write-Host ""

if ($failedChecks -eq 0) {
    Write-Success "✓ ALL CRITICAL CHECKS PASSED - Production environment ready!"
    Write-Success "Success Rate: $successRate%"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Info "1. Update passwords in .env.production"
    Write-Info "2. Configure OAuth and AWS credentials"
    Write-Info "3. Run: .\setup-production.ps1"
    Write-Info "4. Deploy: docker-compose -f docker-compose.production-secure.yml up -d"
    exit 0
} else {
    Write-Failure "✗ CRITICAL ISSUES FOUND - Fix before deployment!"
    Write-Failure "Success Rate: $successRate%"
    Write-Host ""
    Write-Failure "Please address the failed checks above before proceeding with deployment."
    exit 1
}
