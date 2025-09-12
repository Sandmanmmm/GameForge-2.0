# GameForge AI Production Deployment Script
param([switch]$DryRun = $false)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GameForge AI Production Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Validation
Write-Host "Running validation..." -ForegroundColor Yellow
& .\validate-production-readiness.ps1

# Environment Setup
$env:BUILD_VERSION = "vastai-prod-v1.0"
$env:BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

# Security Check
$seccompProfiles = @(
    "security/seccomp/gameforge-app.json",
    "security/seccomp/database.json",
    "security/seccomp/nginx.json",
    "security/seccomp/vault.json"
)

foreach ($profile in $seccompProfiles) {
    if (Test-Path $profile) {
        Write-Host "Found: $(Split-Path $profile -Leaf)" -ForegroundColor Green
    } else {
        Write-Host "Missing: $profile" -ForegroundColor Red
        exit 1
    }
}

# Deploy
Write-Host "Deploying services..." -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "DRY RUN: Configuration validation..." -ForegroundColor Cyan
    docker-compose -f docker-compose.vastai-production.yml config --quiet
    Write-Host "SUCCESS: Ready for production deployment" -ForegroundColor Green
} else {
    docker-compose -f docker-compose.vastai-production.yml up -d
    Write-Host "SUCCESS: Production deployment completed" -ForegroundColor Green
}

Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  Application: http://localhost:8080" -ForegroundColor Gray
Write-Host "  Monitoring: http://localhost:3000" -ForegroundColor Gray
Write-Host "  Metrics: http://localhost:9090" -ForegroundColor Gray

exit 0
