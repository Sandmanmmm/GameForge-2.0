# GameForge Production-Hardened Testing Script
# ==============================================
# Comprehensive testing for docker-compose.production-hardened.yml
# Tests all Phase 4 features and production security hardening

param(
    [switch]$SkipBuild,
    [switch]$TestOnly,
    [switch]$Cleanup,
    [string]$Service = "all"
)

Write-Host "GameForge Production-Hardened Testing" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

$composeFile = "docker-compose.production-hardened.yml"
$script:testResults = @()

function Test-ComposeFile {
    Write-Host "`nValidating compose file syntax..." -ForegroundColor Yellow
    
    try {
        $validateResult = docker-compose -f $composeFile config 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Compose file syntax is valid" -ForegroundColor Green
            $script:testResults += "Compose Syntax: PASS"
        } else {
            Write-Host "ERROR: Compose file validation failed" -ForegroundColor Red
            Write-Host $validateResult -ForegroundColor Red
            $script:testResults += "Compose Syntax: FAIL"
            return $false
        }
    } catch {
        Write-Host "ERROR: Failed to validate compose file: $_" -ForegroundColor Red
        $script:testResults += "Compose Syntax: FAIL"
        return $false
    }
    
    return $true
}

function Test-RequiredFiles {
    Write-Host "`nChecking required files..." -ForegroundColor Yellow
    
    $requiredFiles = @(
        "Dockerfile.production.enhanced",
        "scripts/model-manager.sh",
        "scripts/entrypoint-phase4.sh",
        ".env"
    )
    
    $allFilesExist = $true
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Host "SUCCESS: Found $file" -ForegroundColor Green
            $script:testResults += "File ${file}: PASS"
        } else {
            Write-Host "WARNING: Missing $file" -ForegroundColor Yellow
            $script:testResults += "File ${file}: MISSING"
            $allFilesExist = $false
        }
    }
    
    return $allFilesExist
}

function Test-EnvironmentVariables {
    Write-Host "`nChecking environment variables..." -ForegroundColor Yellow
    
    $requiredEnvVars = @(
        "POSTGRES_PASSWORD",
        "JWT_SECRET_KEY", 
        "SECRET_KEY",
        "VAULT_ROOT_TOKEN",
        "VAULT_TOKEN"
    )
    
    # Load .env file if it exists
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^([^#=]+)=(.*)$") {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
            }
        }
    }
    
    $allVarsSet = $true
    
    foreach ($var in $requiredEnvVars) {
        $value = [Environment]::GetEnvironmentVariable($var, "Process")
        if ($value) {
            Write-Host "SUCCESS: $var is set" -ForegroundColor Green
            $script:testResults += "EnvVar ${var}: PASS"
        } else {
            Write-Host "WARNING: $var is not set" -ForegroundColor Yellow
            $script:testResults += "EnvVar ${var}: MISSING"
            $allVarsSet = $false
        }
    }
    
    return $allVarsSet
}

function Start-ProductionServices {
    param([string]$ServiceFilter = "")
    
    Write-Host "`nStarting production services..." -ForegroundColor Yellow
    
    try {
        if ($ServiceFilter -and $ServiceFilter -ne "all") {
            Write-Host "Starting specific service: $ServiceFilter" -ForegroundColor Cyan
            docker-compose -f $composeFile up -d $ServiceFilter
        } else {
            Write-Host "Starting all services..." -ForegroundColor Cyan
            docker-compose -f $composeFile up -d
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Services started successfully" -ForegroundColor Green
            $testResults += "Service Startup: PASS"
            return $true
        } else {
            Write-Host "ERROR: Failed to start services" -ForegroundColor Red
            $testResults += "Service Startup: FAIL"
            return $false
        }
    } catch {
        Write-Host "ERROR: Exception during service startup: $_" -ForegroundColor Red
        $testResults += "Service Startup: FAIL"
        return $false
    }
}

function Test-ServiceHealth {
    Write-Host "`nTesting service health..." -ForegroundColor Yellow
    
    # Wait for services to initialize
    Write-Host "Waiting 60 seconds for services to initialize..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
    
    # Test Vault health
    Write-Host "Testing Vault health..." -ForegroundColor Cyan
    try {
        $vaultStatus = docker-compose -f $composeFile exec -T vault vault status 2>&1
        if ($vaultStatus -match "Sealed.*false" -or $vaultStatus -match "Initialized.*true") {
            Write-Host "SUCCESS: Vault is healthy" -ForegroundColor Green
            $testResults += "Vault Health: PASS"
        } else {
            Write-Host "WARNING: Vault status unclear: $vaultStatus" -ForegroundColor Yellow
            $testResults += "Vault Health: UNCLEAR"
        }
    } catch {
        Write-Host "ERROR: Could not check Vault status: $_" -ForegroundColor Red
        $testResults += "Vault Health: FAIL"
    }
    
    # Test Database health
    Write-Host "Testing Database health..." -ForegroundColor Cyan
    try {
        $dbStatus = docker-compose -f $composeFile exec -T postgres pg_isready -h localhost -p 5432 2>&1
        if ($dbStatus -match "accepting connections") {
            Write-Host "SUCCESS: Database is healthy" -ForegroundColor Green
            $testResults += "Database Health: PASS"
        } else {
            Write-Host "WARNING: Database not ready: $dbStatus" -ForegroundColor Yellow
            $testResults += "Database Health: FAIL"
        }
    } catch {
        Write-Host "ERROR: Could not check database status: $_" -ForegroundColor Red
        $testResults += "Database Health: FAIL"
    }
    
    # Test Redis health
    Write-Host "Testing Redis health..." -ForegroundColor Cyan
    try {
        $redisStatus = docker-compose -f $composeFile exec -T redis redis-cli ping 2>&1
        if ($redisStatus -match "PONG") {
            Write-Host "SUCCESS: Redis is healthy" -ForegroundColor Green
            $testResults += "Redis Health: PASS"
        } else {
            Write-Host "WARNING: Redis not responding: $redisStatus" -ForegroundColor Yellow
            $testResults += "Redis Health: FAIL"
        }
    } catch {
        Write-Host "ERROR: Could not check Redis status: $_" -ForegroundColor Red
        $testResults += "Redis Health: FAIL"
    }
    
    # Test GameForge app health
    Write-Host "Testing GameForge app health..." -ForegroundColor Cyan
    try {
        $appStatus = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 10 | Select-Object -ExpandProperty StatusCode
        if ($appStatus -eq "200") {
            Write-Host "SUCCESS: GameForge app is healthy" -ForegroundColor Green
            $testResults += "App Health: PASS"
        } else {
            Write-Host "WARNING: GameForge app returned status: $appStatus" -ForegroundColor Yellow
            $testResults += "App Health: FAIL"
        }
    } catch {
        Write-Host "ERROR: Could not check app health: $_" -ForegroundColor Red
        $testResults += "App Health: FAIL"
    }
}

function Test-Phase4Features {
    Write-Host "`nTesting Phase 4 features..." -ForegroundColor Yellow
    
    # Test Vault connectivity from app
    Write-Host "Testing Vault connectivity..." -ForegroundColor Cyan
    try {
        $vaultTest = docker-compose -f $composeFile exec -T gameforge-app curl -s http://vault:8200/v1/sys/health 2>&1
        if ($vaultTest -match "initialized") {
            Write-Host "SUCCESS: App can connect to Vault" -ForegroundColor Green
            $testResults += "Vault Connectivity: PASS"
        } else {
            Write-Host "WARNING: Vault connectivity test unclear: $vaultTest" -ForegroundColor Yellow
            $testResults += "Vault Connectivity: UNCLEAR"
        }
    } catch {
        Write-Host "ERROR: Could not test Vault connectivity: $_" -ForegroundColor Red
        $testResults += "Vault Connectivity: FAIL"
    }
    
    # Test model cache directory
    Write-Host "Testing model cache directory..." -ForegroundColor Cyan
    try {
        $cacheTest = docker-compose -f $composeFile exec -T gameforge-app ls -la /tmp/models 2>&1
        if ($cacheTest -match "total" -or $cacheTest -match "drwx") {
            Write-Host "SUCCESS: Model cache directory accessible" -ForegroundColor Green
            $testResults += "Model Cache: PASS"
        } else {
            Write-Host "WARNING: Model cache directory issue: $cacheTest" -ForegroundColor Yellow
            $testResults += "Model Cache: FAIL"
        }
    } catch {
        Write-Host "ERROR: Could not test model cache: $_" -ForegroundColor Red
        $testResults += "Model Cache: FAIL"
    }
    
    # Test scripts availability
    Write-Host "Testing Phase 4 scripts..." -ForegroundColor Cyan
    try {
        docker-compose -f $composeFile exec -T gameforge-app test -f /app/scripts/model-manager.sh
        $script1Result = $LASTEXITCODE
        docker-compose -f $composeFile exec -T gameforge-app test -f /app/scripts/entrypoint-phase4.sh
        $script2Result = $LASTEXITCODE
        
        if ($script1Result -eq 0 -and $script2Result -eq 0) {
            Write-Host "SUCCESS: Phase 4 scripts are available" -ForegroundColor Green
            $testResults += "Phase4 Scripts: PASS"
        } else {
            Write-Host "WARNING: Phase 4 scripts not found" -ForegroundColor Yellow
            $testResults += "Phase4 Scripts: FAIL"
        }
    } catch {
        Write-Host "ERROR: Could not test Phase 4 scripts: $_" -ForegroundColor Red
        $testResults += "Phase4 Scripts: FAIL"
    }
}

function Show-TestResults {
    Write-Host "`n`nTest Results Summary" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Cyan
    
    $passCount = 0
    $failCount = 0
    $totalCount = $script:testResults.Count
    
    foreach ($result in $script:testResults) {
        if ($result -match "PASS") {
            Write-Host $result -ForegroundColor Green
            $passCount++
        } elseif ($result -match "FAIL") {
            Write-Host $result -ForegroundColor Red
            $failCount++
        } else {
            Write-Host $result -ForegroundColor Yellow
        }
    }
    
    Write-Host "`nOverall Results:" -ForegroundColor Cyan
    Write-Host "Total Tests: $totalCount" -ForegroundColor White
    Write-Host "Passed: $passCount" -ForegroundColor Green
    Write-Host "Failed: $failCount" -ForegroundColor Red
    
    if ($failCount -eq 0) {
        Write-Host "`nEXCELLENT! All tests passed!" -ForegroundColor Green
    } elseif ($failCount -le 2) {
        Write-Host "`nGOOD! Most tests passed with minor issues." -ForegroundColor Yellow
    } else {
        Write-Host "`nWARNING! Multiple test failures detected." -ForegroundColor Red
    }
}

function Stop-ProductionServices {
    Write-Host "`nStopping production services..." -ForegroundColor Yellow
    
    try {
        docker-compose -f $composeFile down
        Write-Host "SUCCESS: Services stopped" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to stop services: $_" -ForegroundColor Red
    }
}

# Main execution
if ($Cleanup) {
    Stop-ProductionServices
    exit 0
}

# Phase 1: Validation
if (-not (Test-ComposeFile)) {
    Write-Host "CRITICAL: Compose file validation failed. Aborting." -ForegroundColor Red
    exit 1
}

Test-RequiredFiles
Test-EnvironmentVariables

if ($TestOnly) {
    Show-TestResults
    exit 0
}

# Phase 2: Service startup
if (-not $SkipBuild) {
    if (-not (Start-ProductionServices -ServiceFilter $Service)) {
        Write-Host "CRITICAL: Service startup failed. Aborting." -ForegroundColor Red
        exit 1
    }
    
    # Phase 3: Health testing
    Test-ServiceHealth
    Test-Phase4Features
}

# Phase 4: Results
Show-TestResults

Write-Host "`nProduction testing complete!" -ForegroundColor Cyan
Write-Host "Use -Cleanup flag to stop services when done." -ForegroundColor Yellow
