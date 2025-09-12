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
        Write-Host "   Error: $_" -ForegroundColor Gray
    }
}

# Check for processes using busy ports
if ($busyPorts.Count -gt 0) {
    Write-Host "`nIdentifying processes using busy ports..." -ForegroundColor Yellow
    
    foreach ($busyPort in $busyPorts) {
        $portNumber = $busyPort.Split('(')[0].Trim()
        try {
            $processes = Get-NetTCPConnection -LocalPort $portNumber -ErrorAction SilentlyContinue | 
                         Select-Object LocalPort, OwningProcess | 
                         ForEach-Object { 
                             $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
                             if ($proc) {
                                 "   Process: $($proc.ProcessName) (PID: $($proc.Id))"
                             }
                         }
            
            if ($processes) {
                Write-Host "🔍 Port $portNumber used by:" -ForegroundColor Cyan
                $processes | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
            }
        } catch {
            Write-Host "   Could not identify process for port $portNumber" -ForegroundColor Gray
        }
    }
}

# Check Docker containers using ports
Write-Host "`nChecking Docker containers..." -ForegroundColor Yellow

try {
    $dockerContainers = docker ps --format "table {{.Names}}\t{{.Ports}}" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $containerLines = $dockerContainers -split "`n" | Select-Object -Skip 1
        $foundContainers = $false
        
        foreach ($line in $containerLines) {
            if ($line.Trim() -ne "") {
                $parts = $line -split "`t"
                if ($parts.Length -ge 2) {
                    $containerName = $parts[0].Trim()
                    $ports = $parts[1].Trim()
                    
                    # Check if any production ports are mentioned
                    foreach ($prodPort in $productionPorts.Keys) {
                        if ($ports -match ":$prodPort->") {
                            Write-Host "🐳 Container '$containerName' using port $prodPort" -ForegroundColor Cyan
                            Write-Host "   Ports: $ports" -ForegroundColor Gray
                            $foundContainers = $true
                        }
                    }
                }
            }
        }
        
        if (-not $foundContainers) {
            Write-Host "✅ No Docker containers using production ports" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠️ Could not check Docker containers" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Docker check failed: $_" -ForegroundColor Yellow
}

# Generate port conflict resolution suggestions
if ($conflictFound) {
    Write-Host "`nPort Conflict Resolution Options:" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    
    Write-Host "1. Stop conflicting services:" -ForegroundColor Yellow
    foreach ($busyPort in $busyPorts) {
        Write-Host "   - Stop service using port $busyPort" -ForegroundColor White
    }
    
    Write-Host "`n2. Use alternative ports in docker-compose:" -ForegroundColor Yellow
    Write-Host "   - Modify port mappings in production compose file" -ForegroundColor White
    Write-Host "   - Example: '127.0.0.1:15432:5432' instead of '5432:5432'" -ForegroundColor White
    
    Write-Host "`n3. Use Docker networks (recommended):" -ForegroundColor Yellow
    Write-Host "   - Keep services on internal networks without host port exposure" -ForegroundColor White
    Write-Host "   - Only expose necessary ports (80, 443 for web access)" -ForegroundColor White
}
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
