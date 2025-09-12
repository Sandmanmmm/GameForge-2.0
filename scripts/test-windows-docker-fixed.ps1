# Windows Docker Compose Test Script
# ==================================

Write-Host "Starting GameForge Windows Docker Test" -ForegroundColor Cyan

# Set environment variables for Windows Docker
$env:COMPOSE_CONVERT_WINDOWS_PATHS = "1"
$env:DOCKER_BUILDKIT = "1"

# Test with core services first
Write-Host "Testing core services (Vault, PostgreSQL, Redis)..." -ForegroundColor Yellow

try {
    # Start core services with Windows override
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml up -d vault postgres redis
    
    Write-Host "Waiting for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Check service health
    Write-Host "Checking service health..." -ForegroundColor Green
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml ps
    
    Write-Host "Service logs (last 20 lines):" -ForegroundColor Yellow
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml logs --tail=20
    
} catch {
    Write-Error "Test failed: $_"
}

Write-Host "Windows Docker test completed" -ForegroundColor Green
Write-Host "To stop services: docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml down" -ForegroundColor Cyan
