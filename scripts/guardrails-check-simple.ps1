# GameForge Production Guardrails - PowerShell Version
# Run this before committing: .\scripts\guardrails-check-simple.ps1

param(
    [switch]$Verbose,
    [switch]$FixMode
)

Write-Host "GameForge Production Guardrails Check" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

$violations = 0
$warnings = 0

# Security Checks
Write-Host ""
Write-Host "SECURITY CHECKS" -ForegroundColor Yellow
Write-Host "---------------" -ForegroundColor Yellow

# Check for .env files
Write-Host "Checking for .env files..." -ForegroundColor White
$envFiles = Get-ChildItem -Recurse -File -Name "*.env*" | Where-Object { 
    $_ -notlike "*.example" -and $_ -notlike "*.template" -and $_ -notlike "*node_modules*" 
}

if ($envFiles) {
    Write-Host "[X] BLOCKED: .env files detected!" -ForegroundColor Red
    $envFiles | ForEach-Object { Write-Host "  $($_)" -ForegroundColor Red }
    Write-Host "Solution: Use .env.example instead and add secrets to Vault/K8s" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No .env files found" -ForegroundColor Green
}

# Check for certificate/key files
Write-Host "Checking for certificate/key files..." -ForegroundColor White
$certFiles = Get-ChildItem -Recurse -File | Where-Object { 
    $_.Extension -in @('.pem', '.key', '.crt', '.p12', '.pfx') -and 
    $_.FullName -notlike "*node_modules*" 
}

if ($certFiles) {
    Write-Host "[X] BLOCKED: Certificate/key files detected!" -ForegroundColor Red
    $certFiles | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor Red }
    Write-Host "Solution: Use K8s TLS secrets or certificate managers" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No certificate/key files found" -ForegroundColor Green
}

# Structure Checks
Write-Host ""
Write-Host "STRUCTURE CHECKS" -ForegroundColor Yellow
Write-Host "----------------" -ForegroundColor Yellow

# Check Docker Compose file count
Write-Host "Checking Docker Compose file count..." -ForegroundColor White
$composeFiles = Get-ChildItem -Recurse -File -Name "docker-compose*.yml", "docker-compose*.yaml"
$composeCount = $composeFiles.Count

if ($composeCount -gt 4) {
    Write-Host "[X] BLOCKED: Too many Docker Compose files ($composeCount > 4)!" -ForegroundColor Red
    Write-Host "Solution: Consolidate compose files or use overrides" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] Docker Compose file count OK ($composeCount/4)" -ForegroundColor Green
}

# Check Dockerfile count
Write-Host "Checking Dockerfile count..." -ForegroundColor White
$dockerfiles = Get-ChildItem -Recurse -File -Name "Dockerfile*" | Where-Object { $_ -notlike "*node_modules*" }
$dockerfileCount = $dockerfiles.Count

if ($dockerfileCount -gt 10) {
    Write-Host "[X] BLOCKED: Too many Dockerfiles ($dockerfileCount > 10)!" -ForegroundColor Red
    Write-Host "Solution: Use multi-stage builds instead" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] Dockerfile count reasonable ($dockerfileCount/10)" -ForegroundColor Green
}

# Dependency Checks
Write-Host ""
Write-Host "DEPENDENCY CHECKS" -ForegroundColor Yellow
Write-Host "-----------------" -ForegroundColor Yellow

# Check for mixed package managers
$npmLocks = @(Get-ChildItem -Recurse -File -Name "package-lock.json" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*node_modules*" })
$yarnLocks = @(Get-ChildItem -Recurse -File -Name "yarn.lock" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*node_modules*" })

if ($npmLocks -and $yarnLocks) {
    Write-Host "[X] BLOCKED: Mixed package managers detected!" -ForegroundColor Red
    Write-Host "Solution: Choose either npm or yarn consistently" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] Package manager consistency maintained" -ForegroundColor Green
}

# File Size Checks
Write-Host ""
Write-Host "FILE SIZE CHECKS" -ForegroundColor Yellow
Write-Host "----------------" -ForegroundColor Yellow

$largeFiles = Get-ChildItem -Recurse -File | Where-Object { 
    $_.Length -gt 50MB -and $_.FullName -notlike "*node_modules*" -and $_.FullName -notlike "*\.git*"
}

if ($largeFiles) {
    Write-Host "[X] BLOCKED: Large files detected (>50MB)!" -ForegroundColor Red
    $largeFiles | ForEach-Object { 
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  $($_.Name) ($sizeMB MB)" -ForegroundColor Red 
    }
    Write-Host "Solution: Use Git LFS for large files or external storage" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No large files detected" -ForegroundColor Green
}

# Final Report
Write-Host ""
Write-Host "GUARDRAILS SUMMARY" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

if ($violations -eq 0) {
    Write-Host "[PASS] ALL CHECKS PASSED - Ready to commit!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your repository maintains:" -ForegroundColor White
    Write-Host "  [OK] Security standards (no secrets)" -ForegroundColor Green
    Write-Host "  [OK] Clean structure (proper organization)" -ForegroundColor Green
    Write-Host "  [OK] Reasonable file counts" -ForegroundColor Green
    Write-Host "  [OK] Consistent dependency management" -ForegroundColor Green
    
    if ($warnings -gt 0) {
        Write-Host ""
        Write-Host "WARNING: $warnings warning(s) - consider addressing these" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Ready for production deployment!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] $violations VIOLATION(S) DETECTED!" -ForegroundColor Red
    
    if ($warnings -gt 0) {
        Write-Host "WARNING: $warnings warning(s) also found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Please fix the issues above and try again" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Quick fixes:" -ForegroundColor White
    Write-Host "  - Remove .env files and use .env.example" -ForegroundColor White
    Write-Host "  - Move top-level files to proper directories" -ForegroundColor White
    Write-Host "  - Consolidate redundant Docker files" -ForegroundColor White
    Write-Host "  - Use secure secret management" -ForegroundColor White
    
    exit 1
}