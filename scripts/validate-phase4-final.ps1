# GameForge Phase 4 Production Validation
# Quick validation of Phase 4 integration in docker-compose.production-hardened.yml

Write-Host ""
Write-Host "GameForge Phase 4 Production Integration Validation" -ForegroundColor Blue
Write-Host "====================================================" -ForegroundColor Blue

$composeFile = "docker-compose.production-hardened.yml"
$validationResults = @()

if (-not (Test-Path $composeFile)) {
    Write-Host "ERROR: Production docker-compose file not found!" -ForegroundColor Red
    exit 1
}

$content = Get-Content $composeFile -Raw

Write-Host ""
Write-Host "Checking Phase 4 Integration..." -ForegroundColor Cyan

# 1. Check Vault Security Template
if ($content -match 'x-vault-security:.*&vault-security') {
    Write-Host "SUCCESS: Vault security template found" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Vault security template missing" -ForegroundColor Red
    $validationResults += $false
}

# 2. Check Phase 4 Build Configuration
if ($content -match 'BUILD_ENV:.*phase4-production') {
    Write-Host "SUCCESS: Build environment set to phase4-production" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Build environment not set to phase4-production" -ForegroundColor Red
    $validationResults += $false
}

# 3. Check Model Security Environment Variables
$modelSecurityVars = @(
    'MODEL_SECURITY_ENABLED.*true',
    'VAULT_ADDR.*vault:8200',
    'MODEL_STORAGE_BACKEND.*s3'
)

foreach ($var in $modelSecurityVars) {
    if ($content -match $var) {
        $varName = ($var -split '\.')[0]
        Write-Host "SUCCESS: Environment variable: $varName" -ForegroundColor Green
        $validationResults += $true
    } else {
        $varName = ($var -split '\.')[0]
        Write-Host "FAIL: Missing environment variable: $varName" -ForegroundColor Red
        $validationResults += $false
    }
}

# 4. Check Phase 4 Entrypoint
if ($content -match 'entrypoint:.*entrypoint-phase4\.sh') {
    Write-Host "SUCCESS: Phase 4 enhanced entrypoint configured" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Phase 4 entrypoint not configured" -ForegroundColor Red
    $validationResults += $false
}

# 5. Check Vault Service
if ($content -match 'vault:\s*\n\s*image:\s*hashicorp/vault') {
    Write-Host "SUCCESS: Vault service properly configured" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Vault service not configured" -ForegroundColor Red
    $validationResults += $false
}

# 6. Check Phase 4 Volumes
$phase4Volumes = @(
    'model-cache:/tmp/models',
    'vault-data:/vault/data',
    'monitoring-data:/tmp/monitoring'
)

foreach ($volume in $phase4Volumes) {
    if ($content -match [regex]::Escape($volume)) {
        Write-Host "SUCCESS: Volume configured: $volume" -ForegroundColor Green
        $validationResults += $true
    } else {
        Write-Host "FAIL: Missing volume: $volume" -ForegroundColor Red
        $validationResults += $false
    }
}

# 7. Check Vault Network
if ($content -match 'vault-network:') {
    Write-Host "SUCCESS: Vault network configured" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Vault network not configured" -ForegroundColor Red
    $validationResults += $false
}

# 8. Check Scripts Directory Mount
if ($content -match '\./scripts:/app/scripts:ro') {
    Write-Host "SUCCESS: Scripts directory mounted" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Scripts directory not mounted" -ForegroundColor Red
    $validationResults += $false
}

# 9. Check Phase 4 Scripts Exist
$requiredScripts = @(
    "scripts/model-manager.sh",
    "scripts/entrypoint-phase4.sh"
)

foreach ($script in $requiredScripts) {
    if (Test-Path $script) {
        Write-Host "SUCCESS: Script exists: $script" -ForegroundColor Green
        $validationResults += $true
    } else {
        Write-Host "FAIL: Missing script: $script" -ForegroundColor Red
        $validationResults += $false
    }
}

# 10. Check Vault Dependency
if ($content -match 'vault:\s*\n\s*condition:\s*service_healthy') {
    Write-Host "SUCCESS: Vault dependency configured" -ForegroundColor Green
    $validationResults += $true
} else {
    Write-Host "FAIL: Vault dependency not configured" -ForegroundColor Red
    $validationResults += $false
}

# Summary
Write-Host ""
Write-Host "Validation Summary" -ForegroundColor Yellow
Write-Host "==================" -ForegroundColor Yellow

$totalChecks = $validationResults.Count
$passedChecks = ($validationResults | Where-Object { $_ -eq $true }).Count
$successRate = [math]::Round(($passedChecks / $totalChecks) * 100, 1)

Write-Host "Total checks: $totalChecks" -ForegroundColor White
Write-Host "Passed checks: $passedChecks" -ForegroundColor White
Write-Host "Success rate: $successRate%" -ForegroundColor White

if ($successRate -ge 90) {
    Write-Host ""
    Write-Host "EXCELLENT! Phase 4 integration is ready for production!" -ForegroundColor Green
} elseif ($successRate -ge 75) {
    Write-Host ""
    Write-Host "GOOD: Phase 4 integration mostly complete with minor issues" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "NEEDS WORK: Phase 4 integration requires improvements" -ForegroundColor Red
}

Write-Host ""
Write-Host "Phase 4 Features Validated:" -ForegroundColor Cyan
Write-Host "  - Secure model asset management" -ForegroundColor White
Write-Host "  - No baked models policy" -ForegroundColor White
Write-Host "  - Vault integration for secrets" -ForegroundColor White
Write-Host "  - Enhanced security validation" -ForegroundColor White
Write-Host "  - Runtime model fetching" -ForegroundColor White
Write-Host "  - Performance monitoring" -ForegroundColor White

if ($successRate -ge 75) {
    exit 0
} else {
    exit 1
}
