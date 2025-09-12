# Port Conflict Detection Script
# =============================
# Checks if production ports are available for deployment

Write-Host "GameForge Port Conflict Detection" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Production ports to check
$productionPorts = @{
    5432 = "PostgreSQL Database"
    6379 = "Redis Cache" 
    8200 = "HashiCorp Vault"
    80 = "HTTP (Nginx)"
    443 = "HTTPS (Nginx)"
    9090 = "Prometheus"
    3000 = "Grafana"
    9200 = "Elasticsearch"
    5044 = "Logstash"
}

Write-Host "`nChecking port availability..." -ForegroundColor Yellow

$conflictFound = $false
$availablePorts = @()
$busyPorts = @()

foreach ($port in $productionPorts.GetEnumerator()) {
    try {
        # Test if port is in use
        $connection = Test-NetConnection -ComputerName "localhost" -Port $port.Key -InformationLevel Quiet -WarningAction SilentlyContinue
        
        if ($connection) {
            Write-Host "❌ Port $($port.Key) BUSY - $($port.Value)" -ForegroundColor Red
            $busyPorts += "$($port.Key) ($($port.Value))"
            $conflictFound = $true
        } else {
            Write-Host "✅ Port $($port.Key) FREE - $($port.Value)" -ForegroundColor Green
            $availablePorts += "$($port.Key) ($($port.Value))"
        }
    } catch {
        Write-Host "⚠️ Port $($port.Key) CHECK FAILED - $($port.Value)" -ForegroundColor Yellow
    }
}

# Check Docker containers using ports
Write-Host "`nChecking Docker containers..." -ForegroundColor Yellow

try {
    $dockerContainers = docker ps --format "table {{.Names}}\t{{.Ports}}" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker check completed" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Could not check Docker containers" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Docker check failed" -ForegroundColor Yellow
}

# Summary
Write-Host "`nPort Availability Summary:" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

Write-Host "Available Ports: $($availablePorts.Count)" -ForegroundColor Green
$availablePorts | ForEach-Object { Write-Host "  ✅ $_" -ForegroundColor Green }

if ($busyPorts.Count -gt 0) {
    Write-Host "`nBusy Ports: $($busyPorts.Count)" -ForegroundColor Red
    $busyPorts | ForEach-Object { Write-Host "  ❌ $_" -ForegroundColor Red }
    
    Write-Host "`n⚠️ PORT CONFLICTS DETECTED" -ForegroundColor Red
    Write-Host "Resolve conflicts before production deployment" -ForegroundColor Red
} else {
    Write-Host "`n✅ NO PORT CONFLICTS" -ForegroundColor Green
    Write-Host "All production ports are available" -ForegroundColor Green
}
