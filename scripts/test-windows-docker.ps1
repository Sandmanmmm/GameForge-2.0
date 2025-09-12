# Windows Docker Compose Test Script
# ==================================

Write-Host "ðŸš€ Starting GameForge Windows Docker Test" -ForegroundColor Cyan

# Set environment variables for Windows Docker
$env:COMPOSE_CONVERT_WINDOWS_PATHS = "1"
$env:DOCKER_BUILDKIT = "1"

# Test with core services first
Write-Host "ðŸ§ª Testing core services (Vault, PostgreSQL, Redis)..." -ForegroundColor Yellow

try {
    # Start core services with Windows override
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml up -d vault postgres redis
    
    Write-Host "â³ Waiting for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Check service health
    Write-Host "ðŸ” Checking service health..." -ForegroundColor Green
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml ps
    
    Write-Host "ðŸ“Š Service logs (last 20 lines):" -ForegroundColor Yellow
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml logs --tail=20
    
} catch {
    Write-Error "âŒ Test failed: $_"
}

Write-Host "âœ… Windows Docker test completed" -ForegroundColor Green
Write-Host "ðŸ“‹ To stop services: docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml down" -ForegroundColor Cyan
