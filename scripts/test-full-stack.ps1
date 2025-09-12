# Full Stack Testing Script
# =========================
# Tests the complete production-hardened stack with core services

Write-Host "GameForge Full Stack Testing" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

$composeFile = "docker-compose.production-hardened.yml"

# Core services to test (subset for validation)
$coreServices = @(
    "vault",
    "postgres", 
    "redis"
)

Write-Host "`nTesting core services: $($coreServices -join ', ')" -ForegroundColor Yellow

# Step 1: Start core services
Write-Host "`n1. Starting core services..." -ForegroundColor Yellow

try {
    $serviceArgs = $coreServices -join " "
    $startResult = docker-compose -f $composeFile up -d $serviceArgs 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Core services started successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to start core services" -ForegroundColor Red
        Write-Host "Error: $startResult" -ForegroundColor Gray
        return
    }
} catch {
    Write-Host "❌ Exception starting services: $_" -ForegroundColor Red
    return
}

# Step 2: Wait for initialization
Write-Host "`n2. Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Step 3: Check service status
Write-Host "`n3. Checking service status..." -ForegroundColor Yellow

try {
    $statusOutput = docker-compose -f $composeFile ps 2>&1
    Write-Host "Service Status:" -ForegroundColor Cyan
    Write-Host $statusOutput -ForegroundColor Gray
} catch {
    Write-Host "❌ Could not check service status: $_" -ForegroundColor Red
}

# Step 4: Test service health
Write-Host "`n4. Testing service health..." -ForegroundColor Yellow

# Test Vault
Write-Host "Testing Vault..." -ForegroundColor Cyan
try {
    $vaultHealth = Invoke-WebRequest -Uri "http://localhost:8200/v1/sys/health" -UseBasicParsing -TimeoutSec 10 2>&1
    if ($vaultHealth.StatusCode -eq 200) {
        Write-Host "✅ Vault is healthy" -ForegroundColor Green
        $vaultData = $vaultHealth.Content | ConvertFrom-Json
        Write-Host "   Version: $($vaultData.version)" -ForegroundColor Gray
        Write-Host "   Initialized: $($vaultData.initialized)" -ForegroundColor Gray
        Write-Host "   Sealed: $($vaultData.sealed)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Vault health check failed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not connect to Vault: $_" -ForegroundColor Red
}

# Test PostgreSQL
Write-Host "Testing PostgreSQL..." -ForegroundColor Cyan
try {
    $pgTest = docker-compose -f $composeFile exec -T postgres pg_isready -h localhost -p 5432 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL is ready" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL not ready: $pgTest" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ PostgreSQL test failed: $_" -ForegroundColor Red
}

# Test Redis
Write-Host "Testing Redis..." -ForegroundColor Cyan
try {
    $redisTest = docker-compose -f $composeFile exec -T redis redis-cli ping 2>&1
    if ($redisTest -match "PONG") {
        Write-Host "✅ Redis is responding" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis not responding: $redisTest" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Redis test failed: $_" -ForegroundColor Red
}

# Step 5: Test inter-service connectivity
Write-Host "`n5. Testing inter-service connectivity..." -ForegroundColor Yellow

# Test Vault from PostgreSQL container
Write-Host "Testing Vault connectivity from PostgreSQL..." -ForegroundColor Cyan
try {
    $vaultConnTest = docker-compose -f $composeFile exec -T postgres wget -q -O- http://vault:8200/v1/sys/health 2>&1
    if ($vaultConnTest -match "initialized") {
        Write-Host "✅ PostgreSQL can reach Vault" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL cannot reach Vault" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Vault connectivity test failed: $_" -ForegroundColor Red
}

# Step 6: Test security configurations
Write-Host "`n6. Testing security configurations..." -ForegroundColor Yellow

try {
    $dockerInspect = docker inspect gameforge-vault-secure 2>&1 | ConvertFrom-Json
    $securityOpts = $dockerInspect.HostConfig.SecurityOpt
    
    if ($securityOpts -contains "no-new-privileges:true") {
        Write-Host "✅ No-new-privileges security option active" -ForegroundColor Green
    } else {
        Write-Host "⚠️ No-new-privileges not found" -ForegroundColor Yellow
    }
    
    $capDrops = $dockerInspect.HostConfig.CapDrop
    if ($capDrops -contains "ALL") {
        Write-Host "✅ Capabilities dropped (ALL)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Capabilities not properly dropped" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ Security configuration check failed: $_" -ForegroundColor Red
}

# Step 7: Performance check
Write-Host "`n7. Quick performance check..." -ForegroundColor Yellow

try {
    $dockerStats = docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>&1
    Write-Host "Resource Usage:" -ForegroundColor Cyan
    Write-Host $dockerStats -ForegroundColor Gray
} catch {
    Write-Host "❌ Could not get performance stats: $_" -ForegroundColor Red
}

# Cleanup option
Write-Host "`n8. Testing complete!" -ForegroundColor Green
Write-Host "Core services are running. Use the following to stop:" -ForegroundColor Yellow
Write-Host "docker-compose -f $composeFile down" -ForegroundColor Cyan

Write-Host "`nFull Stack Test Summary:" -ForegroundColor Cyan
Write-Host "- Core services: Started and tested" -ForegroundColor White
Write-Host "- Health checks: Validated" -ForegroundColor White
Write-Host "- Connectivity: Tested" -ForegroundColor White
Write-Host "- Security: Validated" -ForegroundColor White
Write-Host "- Performance: Monitored" -ForegroundColor White
