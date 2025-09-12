#!/usr/bin/env pwsh
# ========================================================================
# Phase 2 + Phase 4 Production Deployment Script
# Deploy Enhanced Multi-stage Dockerfile with CPU/GPU Variants + Model Asset Security
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpu", "cpu")]
    [string]$Variant = "gpu",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipHealthCheck,
    
    [Parameter(Mandatory=$false)]
    [string]$ComposeFile = "docker-compose.production-hardened.yml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Magenta
Write-Host "Phase 2 + Phase 4 Production Deployment" -ForegroundColor Magenta
Write-Host "Variant: $Variant | Environment: $Environment" -ForegroundColor Magenta
Write-Host "========================================================================" -ForegroundColor Magenta

# Function to set deployment environment
function Set-DeploymentEnvironment {
    Write-Host "Configuring deployment environment..." -ForegroundColor Yellow
    
    # Load Phase 2 environment configuration
    if (Test-Path ".env.phase2") {
        Get-Content ".env.phase2" | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.+)$') {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], [EnvironmentVariableTarget]::Process)
            }
        }
        Write-Host "✓ Loaded Phase 2 environment configuration" -ForegroundColor Green
    }
    
    # Override with variant-specific settings
    $env:GAMEFORGE_VARIANT = $Variant
    $env:DEPLOYMENT_ENVIRONMENT = $Environment
    
    if ($Variant -eq "cpu") {
        $env:DOCKER_RUNTIME = "runc"
        $env:ENABLE_GPU = "false"
        $env:MEMORY_LIMIT = "8G"
        $env:CPU_LIMIT = "4.0"
        Write-Host "✓ CPU variant deployment configured" -ForegroundColor Green
    } else {
        $env:DOCKER_RUNTIME = "nvidia"
        $env:ENABLE_GPU = "true"
        $env:MEMORY_LIMIT = "12G"
        $env:CPU_LIMIT = "6.0"
        Write-Host "✓ GPU variant deployment configured" -ForegroundColor Green
    }
}

# Function to build if needed
function Invoke-ConditionalBuild {
    if ($SkipBuild) {
        Write-Host "Skipping build as requested" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Building Phase 2 + Phase 4 images..." -ForegroundColor Yellow
    
    try {
        & ".\build-phase2-phase4-integration.ps1" -Variant $Variant -SkipTests
        Write-Host "✓ Build completed successfully" -ForegroundColor Green
    } catch {
        throw "Build failed: $_"
    }
}

# Function to deploy services
function Invoke-ProductionDeployment {
    Write-Host "Deploying Phase 2 + Phase 4 production stack..." -ForegroundColor Yellow
    
    try {
        # Pull latest base images
        Write-Host "Pulling latest base images..." -ForegroundColor Cyan
        docker compose -f $ComposeFile pull --ignore-pull-failures
        
        # Deploy infrastructure services first
        Write-Host "Starting infrastructure services..." -ForegroundColor Cyan
        docker compose -f $ComposeFile up -d postgres redis elasticsearch vault
        
        # Wait for infrastructure
        Write-Host "Waiting for infrastructure services..." -ForegroundColor Cyan
        Start-Sleep -Seconds 45
        
        # Deploy security services
        Write-Host "Starting security services..." -ForegroundColor Cyan
        docker compose -f $ComposeFile up -d trivy-server clair-scanner cosign-service harbor-registry opa-server security-metrics security-dashboard
        
        # Wait for security services
        Write-Host "Waiting for security services..." -ForegroundColor Cyan
        Start-Sleep -Seconds 30
        
        # Deploy application
        Write-Host "Starting GameForge application..." -ForegroundColor Cyan
        docker compose -f $ComposeFile up -d gameforge-app nginx
        
        # Wait for application startup
        Write-Host "Waiting for application startup..." -ForegroundColor Cyan
        Start-Sleep -Seconds 60
        
        Write-Host "✓ Phase 2 + Phase 4 deployment completed" -ForegroundColor Green
        
    } catch {
        throw "Deployment failed: $_"
    }
}

# Function to run health checks
function Test-DeploymentHealth {
    if ($SkipHealthCheck) {
        Write-Host "Skipping health checks as requested" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Running comprehensive health checks..." -ForegroundColor Yellow
    
    $healthChecks = @(
        @{ Name = "PostgreSQL"; Command = "docker compose -f $ComposeFile exec -T postgres pg_isready -U gameforge" },
        @{ Name = "Redis"; Command = "docker compose -f $ComposeFile exec -T redis redis-cli ping" },
        @{ Name = "Vault"; Command = "docker compose -f $ComposeFile exec -T vault vault status" },
        @{ Name = "GameForge App"; Command = "docker compose -f $ComposeFile exec -T gameforge-app curl -f http://localhost:8080/health" },
        @{ Name = "Nginx"; Command = "docker compose -f $ComposeFile exec -T nginx wget --spider -q http://localhost/health" }
    )
    
    $failedChecks = @()
    
    foreach ($check in $healthChecks) {
        try {
            Write-Host "Checking $($check.Name)..." -ForegroundColor Cyan
            Invoke-Expression $check.Command 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ $($check.Name): Healthy" -ForegroundColor Green
            } else {
                Write-Host "❌ $($check.Name): Unhealthy" -ForegroundColor Red
                $failedChecks += $check.Name
            }
        } catch {
            Write-Host "❌ $($check.Name): Error - $_" -ForegroundColor Red
            $failedChecks += $check.Name
        }
    }
    
    # Variant-specific health checks
    if ($Variant -eq "gpu") {
        try {
            Write-Host "Checking GPU availability..." -ForegroundColor Cyan
            $gpuCheck = docker compose -f $ComposeFile exec -T gameforge-app python -c "import torch; print('GPU:', torch.cuda.is_available())"
            if ($gpuCheck -match "True") {
                Write-Host "✓ GPU: Available" -ForegroundColor Green
            } else {
                Write-Host "⚠ GPU: Not available" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "⚠ GPU check failed: $_" -ForegroundColor Yellow
        }
    }
    
    if ($failedChecks.Count -gt 0) {
        throw "Health checks failed for: $($failedChecks -join ', ')"
    }
    
    Write-Host "✓ All health checks passed" -ForegroundColor Green
}

# Function to show deployment status
function Show-DeploymentStatus {
    Write-Host "========================================================================" -ForegroundColor Magenta
    Write-Host "Phase 2 + Phase 4 Deployment Status" -ForegroundColor Magenta
    Write-Host "========================================================================" -ForegroundColor Magenta
    
    try {
        Write-Host "Container Status:" -ForegroundColor White
        docker compose -f $ComposeFile ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
        
        Write-Host "`nResource Usage:" -ForegroundColor White
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        
        Write-Host "`nVariant Configuration:" -ForegroundColor White
        Write-Host "Variant: $Variant" -ForegroundColor Gray
        Write-Host "Runtime: $env:DOCKER_RUNTIME" -ForegroundColor Gray
        Write-Host "GPU Enabled: $env:ENABLE_GPU" -ForegroundColor Gray
        Write-Host "Memory Limit: $env:MEMORY_LIMIT" -ForegroundColor Gray
        Write-Host "CPU Limit: $env:CPU_LIMIT" -ForegroundColor Gray
        
    } catch {
        Write-Warning "Could not retrieve deployment status: $_"
    }
    
    Write-Host "========================================================================" -ForegroundColor Magenta
}

# Function to show access information
function Show-AccessInformation {
    Write-Host "Access Information:" -ForegroundColor White
    Write-Host "GameForge Application: http://localhost:8080" -ForegroundColor Cyan
    Write-Host "Security Dashboard: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "Elasticsearch: http://localhost:9200" -ForegroundColor Cyan
    Write-Host "Vault UI: http://localhost:8200" -ForegroundColor Cyan
    Write-Host "Harbor Registry: http://localhost:8888" -ForegroundColor Cyan
    
    Write-Host "`nManagement Commands:" -ForegroundColor White
    Write-Host "View logs: docker compose -f $ComposeFile logs -f gameforge-app" -ForegroundColor Gray
    Write-Host "Scale app: docker compose -f $ComposeFile up -d --scale gameforge-app=3" -ForegroundColor Gray
    Write-Host "Stop stack: docker compose -f $ComposeFile down" -ForegroundColor Gray
    Write-Host "Restart app: docker compose -f $ComposeFile restart gameforge-app" -ForegroundColor Gray
}

# Main execution
try {
    Set-DeploymentEnvironment
    Invoke-ConditionalBuild
    Invoke-ProductionDeployment
    Test-DeploymentHealth
    Show-DeploymentStatus
    Show-AccessInformation
    
    Write-Host "✅ Phase 2 + Phase 4 deployment completed successfully!" -ForegroundColor Green
    Write-Host "The enhanced multi-stage application with $Variant variant is now running." -ForegroundColor Green
    
} catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    Write-Host "Checking container logs for more information..." -ForegroundColor Yellow
    
    try {
        docker compose -f $ComposeFile logs --tail=50 gameforge-app
    } catch {
        Write-Warning "Could not retrieve container logs"
    }
    
    exit 1
}
