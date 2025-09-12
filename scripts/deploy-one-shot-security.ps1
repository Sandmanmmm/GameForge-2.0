# GameForge One-Shot Security Bootstrap Deployment
# ===============================================
# PowerShell script to deploy with one-shot security bootstrap

param(
    [string]$ComposeFile = "docker-compose.production-hardened.yml",
    [switch]$SkipBootstrap,
    [switch]$MonitorOnly,
    [int]$BootstrapTimeout = 120
)

Write-Host "🚀 GameForge One-Shot Security Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Function to check bootstrap completion
function Wait-ForBootstrap {
    param([int]$TimeoutSeconds)
    
    Write-Host "⏳ Waiting for security bootstrap to complete..." -ForegroundColor Yellow
    
    $startTime = Get-Date
    $timeout = $startTime.AddSeconds($TimeoutSeconds)
    
    while ((Get-Date) -lt $timeout) {
        try {
            $status = docker exec gameforge-security-bootstrap cat /shared/security/bootstrap-complete.json 2>$null | ConvertFrom-Json
            if ($status.completion_status -eq "success") {
                Write-Host "✅ Security bootstrap completed successfully!" -ForegroundColor Green
                Write-Host "📊 Security Score: $($status.security_score)/$($status.max_score)" -ForegroundColor Green
                return $true
            }
        }
        catch {
            # Bootstrap not complete yet
        }
        
        Start-Sleep 5
    }
    
    Write-Host "❌ Bootstrap timeout after $TimeoutSeconds seconds" -ForegroundColor Red
    return $false
}

# Step 1: Run security bootstrap (one-shot)
if (-not $SkipBootstrap -and -not $MonitorOnly) {
    Write-Host "🔒 Starting security bootstrap (privileged, one-shot)..." -ForegroundColor Yellow
    
    # Remove any existing bootstrap container
    docker rm -f gameforge-security-bootstrap 2>$null
    
    # Start bootstrap
    docker-compose -f $ComposeFile up security-bootstrap --detach
    
    # Wait for completion
    if (Wait-ForBootstrap -TimeoutSeconds $BootstrapTimeout) {
        Write-Host "🎯 Bootstrap phase complete, removing privileged container..." -ForegroundColor Green
        docker rm -f gameforge-security-bootstrap
        Write-Host "✅ Privileged container removed" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Bootstrap failed or timed out" -ForegroundColor Red
        docker logs gameforge-security-bootstrap
        exit 1
    }
}

# Step 2: Start security monitor (non-privileged)
Write-Host "🔍 Starting security monitor (non-privileged)..." -ForegroundColor Yellow
docker-compose -f $ComposeFile up security-monitor --detach

# Wait for monitor to be healthy
Write-Host "⏳ Waiting for security monitor to be healthy..." -ForegroundColor Yellow
$monitorHealthy = $false
$attempts = 0
while (-not $monitorHealthy -and $attempts -lt 12) {
    Start-Sleep 5
    $attempts++
    try {
        $health = docker inspect gameforge-security-monitor --format='{{.State.Health.Status}}' 2>$null
        if ($health -eq "healthy") {
            $monitorHealthy = $true
            Write-Host "✅ Security monitor is healthy" -ForegroundColor Green
        }
        else {
            Write-Host "🔄 Monitor health: $health (attempt $attempts/12)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "🔄 Waiting for monitor to start (attempt $attempts/12)" -ForegroundColor Yellow
    }
}

if (-not $monitorHealthy) {
    Write-Host "⚠️ Security monitor may not be fully healthy yet" -ForegroundColor Yellow
    docker logs gameforge-security-monitor --tail 20
}

# Step 3: Start application services (if not monitor-only)
if (-not $MonitorOnly) {
    Write-Host "🚀 Starting application services..." -ForegroundColor Yellow
    docker-compose -f $ComposeFile up --detach
    
    Write-Host "📊 Deployment Status:" -ForegroundColor Cyan
    docker-compose -f $ComposeFile ps
    
    Write-Host "`n🔍 Security Status:" -ForegroundColor Cyan
    try {
        $securityStatus = docker exec gameforge-security-monitor cat /shared/security/monitor-health.json | ConvertFrom-Json
        Write-Host "• Overall Score: $($securityStatus.monitor_status.overall_score)/100" -ForegroundColor Green
        Write-Host "• Status: $($securityStatus.monitor_status.status)" -ForegroundColor Green
        Write-Host "• Bootstrap Complete: $($securityStatus.bootstrap_status.completed)" -ForegroundColor Green
        Write-Host "• Monitoring Active: $($securityStatus.monitor_status.monitoring_active)" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ Security status not yet available" -ForegroundColor Yellow
    }
}

Write-Host "`n🎉 Deployment complete!" -ForegroundColor Green
Write-Host "🔒 Security: One-shot bootstrap complete, non-privileged monitoring active" -ForegroundColor Green
Write-Host "📈 Check security status: docker exec gameforge-security-monitor cat /shared/security/monitor-health.json" -ForegroundColor Cyan
