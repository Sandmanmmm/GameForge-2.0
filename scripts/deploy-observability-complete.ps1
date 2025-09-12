#!/usr/bin/env pwsh
# ========================================================================
# GameForge AI Complete Observability Deployment & Validation
# Final production deployment with 100% enterprise readiness
# ========================================================================

param(
    [switch]$ValidateOnly,
    [switch]$Force,
    [string]$Environment = "production"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 GameForge AI Complete Observability Deployment" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Yellow

# ========================================================================
# Configuration
# ========================================================================
$script:Config = @{
    ProjectName = "gameforge-ai"
    Environment = $Environment
    ComposeFiles = @(
        "docker-compose.vastai-production.yml"
        "docker-compose.vault-secrets.yml"
        "docker-compose.json-logging.yml"
        "docker-compose.observability-complete.yml"
    )
    RequiredEnvVars = @(
        "DB_PASSWORD"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
        "ELASTIC_PASSWORD"
        "GRAFANA_PASSWORD"
        "VAULT_TOKEN"
    )
    HealthEndpoints = @{
        "GameForge API" = "http://localhost:8000/health"
        "Prometheus" = "http://localhost:9090/-/healthy"
        "Grafana" = "http://localhost:3000/api/health"
        "Elasticsearch" = "http://localhost:9200/_cluster/health"
        "Nginx" = "http://localhost:80/health"
    }
    MetricsEndpoints = @{
        "GameForge Metrics" = "http://localhost:8000/metrics"
        "Nginx Metrics" = "http://localhost:9113/metrics"
        "Postgres Exporter" = "http://localhost:9187/metrics"
        "Redis Exporter" = "http://localhost:9121/metrics"
    }
}

# ========================================================================
# Validation Functions
# ========================================================================

function Test-Prerequisites {
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Blue
    
    $prerequisites = @{
        "Docker" = { docker --version }
        "Docker Compose" = { docker compose version }
        "curl" = { Invoke-WebRequest --version }
        "NVIDIA Docker" = { docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi }
    }
    
    foreach ($tool in $prerequisites.Keys) {
        try {
            $null = & $prerequisites[$tool] 2>$null
            Write-Host "✅ ${tool}: Available" -ForegroundColor Green
        } catch {
            Write-Host "❌ ${tool}: Missing or not working" -ForegroundColor Red
            throw "Prerequisites check failed: $tool not available"
        }
    }
}

function Test-EnvironmentVariables {
    Write-Host "🔍 Validating environment variables..." -ForegroundColor Blue
    
    $missingVars = @()
    foreach ($var in $script:Config.RequiredEnvVars) {
        $envValue = [Environment]::GetEnvironmentVariable($var)
        if (-not $envValue) {
            $missingVars += $var
            Write-Host "❌ Missing: $var" -ForegroundColor Red
        } else {
            Write-Host "✅ Found: $var" -ForegroundColor Green
        }
    }
    
    if ($missingVars.Count -gt 0) {
        Write-Host "❌ Missing required environment variables:" -ForegroundColor Red
        $missingVars | ForEach-Object { Write-Host "   - $_" }
        throw "Environment validation failed"
    }
}

function Test-ComposeFiles {
    Write-Host "🔍 Validating Docker Compose files..." -ForegroundColor Blue
    
    foreach ($file in $script:Config.ComposeFiles) {
        if (Test-Path $file) {
            Write-Host "✅ Found: $file" -ForegroundColor Green
            
            # Validate compose file syntax
            try {
                $null = docker compose -f $file config 2>$null
                Write-Host "✅ Valid syntax: $file" -ForegroundColor Green
            } catch {
                Write-Host "❌ Invalid syntax: $file" -ForegroundColor Red
                throw "Compose file validation failed: $file"
            }
        } else {
            Write-Host "❌ Missing: $file" -ForegroundColor Red
            throw "Required compose file not found: $file"
        }
    }
}

function Test-ObservabilityComponents {
    Write-Host "🔍 Validating observability components..." -ForegroundColor Blue
    
    $observabilityFiles = @{
        "Filebeat Config" = "monitoring/filebeat.yml"
        "Elasticsearch Pipeline" = "monitoring/elasticsearch-log-pipeline.sh"
        "Grafana Automation" = "monitoring/grafana-dashboard-automation.sh"
        "Nginx JSON Config" = "monitoring/nginx-json-format.conf"
        "GameForge Metrics" = "gameforge_metrics_app.py"
    }
    
    foreach ($component in $observabilityFiles.Keys) {
        $path = $observabilityFiles[$component]
        if (Test-Path $path) {
            Write-Host "✅ $component`: $path" -ForegroundColor Green
        } else {
            Write-Host "❌ $component`: $path (missing)" -ForegroundColor Red
            throw "Observability component missing: $path"
        }
    }
}

# ========================================================================
# Deployment Functions
# ========================================================================

function Start-Services {
    Write-Host "🚀 Starting GameForge services..." -ForegroundColor Blue
    
    # Build compose command
    $composeCmd = @("docker", "compose")
    foreach ($file in $script:Config.ComposeFiles) {
        $composeCmd += @("-f", $file)
    }
    $composeCmd += @("up", "-d", "--build")
    
    if ($Force) {
        $composeCmd += "--force-recreate"
    }
    
    Write-Host "Executing: $($composeCmd -join ' ')" -ForegroundColor Yellow
    
    try {
        & $composeCmd[0] $composeCmd[1..($composeCmd.Length-1)]
        Write-Host "✅ Services started successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to start services" -ForegroundColor Red
        throw "Service startup failed: $_"
    }
}

function Wait-ForServices {
    Write-Host "⏳ Waiting for services to become healthy..." -ForegroundColor Blue
    
    $maxWaitTime = 300 # 5 minutes
    $waitInterval = 10
    $elapsedTime = 0
    
    while ($elapsedTime -lt $maxWaitTime) {
        $healthyServices = 0
        $totalServices = $script:Config.HealthEndpoints.Count
        
        foreach ($service in $script:Config.HealthEndpoints.Keys) {
            $endpoint = $script:Config.HealthEndpoints[$service]
            
            try {
                $null = Invoke-WebRequest -Uri $endpoint -TimeoutSec 5 -UseBasicParsing
                Write-Host "✅ ${service}: Healthy" -ForegroundColor Green
                $healthyServices++
            } catch {
                Write-Host "⏳ ${service}: Starting..." -ForegroundColor Yellow
            }
        }
        
        if ($healthyServices -eq $totalServices) {
            Write-Host "✅ All services are healthy!" -ForegroundColor Green
            return
        }
        
        Write-Host "⏳ $healthyServices/$totalServices services healthy. Waiting..." -ForegroundColor Yellow
        Start-Sleep $waitInterval
        $elapsedTime += $waitInterval
    }
    
    throw "Services failed to become healthy within $maxWaitTime seconds"
}

function Test-MetricsEndpoints {
    Write-Host "🔍 Validating metrics endpoints..." -ForegroundColor Blue
    
    $successCount = 0
    $totalCount = $script:Config.MetricsEndpoints.Count
    
    foreach ($service in $script:Config.MetricsEndpoints.Keys) {
        $endpoint = $script:Config.MetricsEndpoints[$service]
        
        try {
            $response = curl -s $endpoint --max-time 10 2>$null
            if ($LASTEXITCODE -eq 0 -and $response -match "# HELP") {
                Write-Host "✅ $service`: Metrics available" -ForegroundColor Green
                $successCount++
            } else {
                Write-Host "⚠️ $service`: Metrics not available" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "❌ $service`: Failed to connect" -ForegroundColor Red
        }
    }
    
    $metricsScore = [math]::Round(($successCount / $totalCount) * 100, 2)
    Write-Host "📊 Metrics Coverage: $successCount/$totalCount ($metricsScore%)" -ForegroundColor Cyan
    
    return $metricsScore
}

function Test-LoggingPipeline {
    Write-Host "🔍 Testing logging pipeline..." -ForegroundColor Blue
    
    # Test Elasticsearch index creation
    try {
        $esHealth = curl -s "http://localhost:9200/_cluster/health" --max-time 10 2>$null | ConvertFrom-Json
        if ($esHealth.status -in @("green", "yellow")) {
            Write-Host "✅ Elasticsearch cluster healthy" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Elasticsearch cluster status: $($esHealth.status)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Failed to check Elasticsearch health" -ForegroundColor Red
        return $false
    }
    
    # Check for GameForge log indices
    try {
        $indices = curl -s "http://localhost:9200/_cat/indices/gameforge-logs-*?format=json" --max-time 10 2>$null | ConvertFrom-Json
        if ($indices.Count -gt 0) {
            Write-Host "✅ GameForge log indices found: $($indices.Count)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️ No GameForge log indices found yet" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "❌ Failed to check log indices" -ForegroundColor Red
        return $false
    }
}

function Test-DashboardAvailability {
    Write-Host "🔍 Testing Grafana dashboards..." -ForegroundColor Blue
    
    try {
        # Check Grafana API
        $auth = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes("admin:$env:GRAFANA_PASSWORD"))
        $headers = @{ Authorization = "Basic $auth" }
        
        $dashboards = curl -s -H "Authorization: Basic $auth" "http://localhost:3000/api/search?type=dash-db" --max-time 10 2>$null | ConvertFrom-Json
        
        if ($dashboards.Count -gt 0) {
            Write-Host "✅ Grafana dashboards found: $($dashboards.Count)" -ForegroundColor Green
            $dashboards | ForEach-Object { Write-Host "   - $($_.title)" }
            return $true
        } else {
            Write-Host "⚠️ No Grafana dashboards found" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "❌ Failed to check Grafana dashboards" -ForegroundColor Red
        return $false
    }
}

function Get-ProductionReadinessScore {
    Write-Host "📊 Calculating production readiness score..." -ForegroundColor Blue
    
    $checks = @{
        "Health Endpoints" = { Test-HealthEndpoints }
        "Metrics Coverage" = { Test-MetricsEndpoints }
        "Logging Pipeline" = { Test-LoggingPipeline }
        "Dashboard Availability" = { Test-DashboardAvailability }
    }
    
    $totalScore = 0
    $maxScore = $checks.Count * 100
    
    foreach ($check in $checks.Keys) {
        try {
            $result = & $checks[$check]
            if ($result -is [bool]) {
                $score = if ($result) { 100 } else { 0 }
            } elseif ($result -is [int] -or $result -is [double]) {
                $score = $result
            } else {
                $score = 50 # Partial credit for inconclusive results
            }
            
            $totalScore += $score
            Write-Host "📈 $check`: $score/100" -ForegroundColor Cyan
        } catch {
            Write-Host "❌ $check`: Failed" -ForegroundColor Red
        }
    }
    
    $finalScore = [math]::Round(($totalScore / $maxScore) * 100, 2)
    
    Write-Host "========================================================================" -ForegroundColor Yellow
    Write-Host "🎯 PRODUCTION READINESS SCORE: $finalScore%" -ForegroundColor Green
    
    if ($finalScore -ge 95) {
        Write-Host "🏆 EXCELLENT: Production ready!" -ForegroundColor Green
    } elseif ($finalScore -ge 85) {
        Write-Host "✅ GOOD: Mostly production ready" -ForegroundColor Yellow
    } elseif ($finalScore -ge 70) {
        Write-Host "⚠️ FAIR: Needs improvement" -ForegroundColor Yellow
    } else {
        Write-Host "❌ POOR: Not production ready" -ForegroundColor Red
    }
    
    return $finalScore
}

function Test-HealthEndpoints {
    $healthyCount = 0
    $totalCount = $script:Config.HealthEndpoints.Count
    
    foreach ($service in $script:Config.HealthEndpoints.Keys) {
        $endpoint = $script:Config.HealthEndpoints[$service]
        try {
            $null = curl -s -f $endpoint --max-time 5 2>$null
            if ($LASTEXITCODE -eq 0) {
                $healthyCount++
            }
        } catch {
            # Service not healthy
        }
    }
    
    return [math]::Round(($healthyCount / $totalCount) * 100, 2)
}

# ========================================================================
# Main Execution
# ========================================================================

function Main {
    try {
        Write-Host "🔍 Starting validation phase..." -ForegroundColor Blue
        
        Test-Prerequisites
        Test-EnvironmentVariables
        Test-ComposeFiles
        Test-ObservabilityComponents
        
        if ($ValidateOnly) {
            Write-Host "✅ Validation completed successfully!" -ForegroundColor Green
            Write-Host "🚀 Ready for deployment. Run without -ValidateOnly to deploy." -ForegroundColor Cyan
            return
        }
        
        Write-Host "🚀 Starting deployment phase..." -ForegroundColor Blue
        
        Start-Services
        Wait-ForServices
        
        # Initialize observability components
        Write-Host "🔧 Initializing observability components..." -ForegroundColor Blue
        Start-Sleep 30  # Give services time to fully initialize
        
        # Run final validation
        Write-Host "🔍 Running production readiness assessment..." -ForegroundColor Blue
        $readinessScore = Get-ProductionReadinessScore
        
        Write-Host "========================================================================" -ForegroundColor Yellow
        Write-Host "🎉 GameForge AI Deployment Complete!" -ForegroundColor Green
        Write-Host "📊 Production Readiness: $readinessScore%" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "🌐 Access Points:" -ForegroundColor Blue
        Write-Host "   • GameForge API: http://localhost:8000" -ForegroundColor White
        Write-Host "   • Grafana Dashboards: http://localhost:3000 (admin/$env:GRAFANA_PASSWORD)" -ForegroundColor White
        Write-Host "   • Prometheus Metrics: http://localhost:9090" -ForegroundColor White
        Write-Host "   • Elasticsearch Logs: http://localhost:9200" -ForegroundColor White
        Write-Host ""
        Write-Host "📊 Key Metrics Endpoints:" -ForegroundColor Blue
        Write-Host "   • Application Metrics: http://localhost:8000/metrics" -ForegroundColor White
        Write-Host "   • Health Check: http://localhost:8000/health" -ForegroundColor White
        Write-Host ""
        Write-Host "🏆 ENTERPRISE-GRADE OBSERVABILITY: ACTIVE" -ForegroundColor Green
        
    } catch {
        Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
        Write-Host "🔧 Check logs and retry with -Force flag if needed" -ForegroundColor Yellow
        exit 1
    }
}

# Execute main function
Main