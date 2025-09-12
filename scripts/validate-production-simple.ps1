# ========================================================================
# GameForge Production Deployment Validation Script (PowerShell - Simple)
# ========================================================================

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "GameForge Production Deployment Validation" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

$checks = @()

# Add check results
function Add-Check($name, $result) {
    $color = if ($result) { "Green" } else { "Red" }
    $symbol = if ($result) { "[PASS]" } else { "[FAIL]" }
    
    Write-Host "$symbol $name" -ForegroundColor $color
    $script:checks += @{ Name = $name; Result = $result }
}

Write-Host "`n=== Infrastructure Validation ===" -ForegroundColor Cyan

# Docker checks
Add-Check "Docker Engine" (Get-Command docker -ErrorAction SilentlyContinue)
Add-Check "Docker Compose" (Get-Command docker-compose -ErrorAction SilentlyContinue)

# Production files
Add-Check "Production Dockerfile" (Test-Path "Dockerfile.production")
Add-Check "Production Docker Compose" (Test-Path "docker-compose.production-secure.yml")
Add-Check "Production Environment" (Test-Path ".env.production")

# Monitoring infrastructure
Add-Check "GPU Monitoring Compose" (Test-Path "docker-compose.gpu-monitoring.yml")
Add-Check "AlertManager Compose" (Test-Path "docker-compose.alertmanager.yml")
Add-Check "Log Pipeline Compose" (Test-Path "docker-compose.log-pipeline.yml")
Add-Check "Monitoring Configs" (Test-Path "monitoring/configs")
Add-Check "Monitoring Dashboards" (Test-Path "monitoring/dashboards")
Add-Check "Monitoring Alerting" (Test-Path "monitoring/alerting")

# Backup infrastructure
Add-Check "Backup Directory" (Test-Path "backup")
Add-Check "Backup Dockerfile" (Test-Path "backup/Dockerfile.backup")
Add-Check "Backup Scripts" (Test-Path "backup/scripts")

# Application files
Add-Check "Production Server Script" (Test-Path "gameforge_production_server.py")
Add-Check "Backend GPU Integration" (Test-Path "backend_gpu_integration.py")
Add-Check "Custom SDXL Pipeline" (Test-Path "custom_sdxl_pipeline.py")

# Configuration files
Add-Check "Nginx Configuration" (Test-Path "nginx/nginx.conf")
Add-Check "Database Setup" (Test-Path "database_setup.sql")
Add-Check "Auth Middleware" (Test-Path "auth_middleware.py")

Write-Host "`n=== Summary ===" -ForegroundColor Cyan

$total = $checks.Count
$passed = ($checks | Where-Object { $_.Result }).Count
$failed = $total - $passed
$successRate = [math]::Round(($passed * 100) / $total, 1)

Write-Host "Total Checks: $total" -ForegroundColor Blue
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host "Success Rate: $successRate%" -ForegroundColor Yellow

if ($failed -eq 0) {
    Write-Host "`n[SUCCESS] ALL CHECKS PASSED - Production environment ready!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Run: .\setup-production.ps1" -ForegroundColor White
    Write-Host "2. Update .env.production with your credentials" -ForegroundColor White
    Write-Host "3. Deploy: docker-compose -f docker-compose.production-secure.yml up -d" -ForegroundColor White
} else {
    Write-Host "`n[ERROR] ISSUES FOUND - Address failed checks before deployment" -ForegroundColor Red
}

Write-Host "`n========================================================================" -ForegroundColor Cyan
