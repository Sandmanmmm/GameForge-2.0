# GameForge Windows Docker Bind Mount Fix Script
# ==============================================
# This script resolves Windows Docker bind mount issues in docker-compose.production-hardened.yml

Write-Host "GameForge Windows Docker Bind Mount Fix" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# Get current directory in Windows format
$currentDir = Get-Location
$windowsPath = $currentDir.Path

Write-Host "Current Directory: $windowsPath" -ForegroundColor Yellow

# Check if Docker Desktop is running
$dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProcess) {
    Write-Warning "Docker Desktop doesn't appear to be running. Please start Docker Desktop first."
    Read-Host "Press Enter when Docker Desktop is running..."
}

# Check Docker configuration
Write-Host "Checking Docker configuration..." -ForegroundColor Green
try {
    $dockerInfo = docker version --format json | ConvertFrom-Json
    Write-Host "Docker Client Version: $($dockerInfo.Client.Version)" -ForegroundColor Green
    Write-Host "Docker Server Version: $($dockerInfo.Server.Version)" -ForegroundColor Green
} catch {
    Write-Error "Docker is not responding. Please ensure Docker Desktop is running."
    exit 1
}

# Backup original file
$backupFile = "docker-compose.production-hardened.yml.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Write-Host "Creating backup: $backupFile" -ForegroundColor Yellow
Copy-Item "docker-compose.production-hardened.yml" $backupFile

# Create Windows-compatible environment file for volumes
Write-Host "Creating Windows volume environment file..." -ForegroundColor Green

$envContent = @"
# Windows Docker Volume Environment Configuration
# This file provides Windows-compatible path variables for Docker Compose

# Convert Windows path to Docker-compatible format
COMPOSE_CONVERT_WINDOWS_PATHS=1
DOCKER_BUILDKIT=1

# Volume base path (Windows format converted to Docker format)
VOLUME_BASE_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))

# Individual volume paths
GAMEFORGE_LOGS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/logs
GAMEFORGE_CACHE_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/cache
GAMEFORGE_ASSETS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/assets
GAMEFORGE_MODELS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/models
MONITORING_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/monitoring
VAULT_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/vault/data
VAULT_LOGS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/vault/logs
POSTGRES_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/postgres
POSTGRES_LOGS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/postgres-logs
REDIS_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/redis
ELASTICSEARCH_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/elasticsearch
ELASTICSEARCH_LOGS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/elasticsearch-logs
LOGSTASH_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/logstash
NGINX_LOGS_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/nginx-logs
STATIC_FILES_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/static
BACKUP_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/backups
PROMETHEUS_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/prometheus
GRAFANA_DATA_PATH=$($windowsPath.Replace('\', '/').Replace('C:', '/c'))/volumes/grafana
"@

$envContent | Out-File -FilePath ".env.windows" -Encoding UTF8
Write-Host "Created .env.windows with Windows-compatible paths" -ForegroundColor Green

# Create Windows-compatible docker-compose override
Write-Host "Creating Windows Docker Compose override..." -ForegroundColor Green

$overrideContent = @"
# Windows Docker Compose Override
# This file provides Windows-compatible volume configurations
version: '3.8'

# Override volume definitions to use Windows-compatible paths
volumes:
  gameforge-logs:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\logs
      o: bind

  gameforge-cache:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\cache
      o: bind

  gameforge-assets:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\assets
      o: bind

  gameforge-models:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\models
      o: bind

  monitoring-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\monitoring
      o: bind

  vault-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\vault\data
      o: bind

  vault-logs:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\vault\logs
      o: bind

  postgres-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\postgres
      o: bind

  postgres-logs:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\postgres-logs
      o: bind

  redis-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\redis
      o: bind

  elasticsearch-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\elasticsearch
      o: bind

  elasticsearch-logs:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\elasticsearch-logs
      o: bind

  logstash-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\logstash
      o: bind

  nginx-logs:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\nginx-logs
      o: bind

  static-files:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\static
      o: bind

  backup-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\backups
      o: bind

  prometheus-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\prometheus
      o: bind

  grafana-data:
    driver: local
    driver_opts:
      type: none
      device: $windowsPath\volumes\grafana
      o: bind
"@

$overrideContent | Out-File -FilePath "docker-compose.windows.override.yml" -Encoding UTF8
Write-Host "Created docker-compose.windows.override.yml" -ForegroundColor Green

# Test the configuration
Write-Host "Testing Windows Docker configuration..." -ForegroundColor Green

try {
    # Test with override file
    $testResult = docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml config 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker Compose configuration is valid with Windows override" -ForegroundColor Green
    } else {
        Write-Warning "Configuration validation had issues: $testResult"
    }
} catch {
    Write-Warning "Could not validate configuration: $_"
}

# Create test script for Windows
Write-Host "Creating Windows test script..." -ForegroundColor Green

$testScript = @"
# Windows Docker Compose Test Script
# ==================================

Write-Host "🚀 Starting GameForge Windows Docker Test" -ForegroundColor Cyan

# Set environment variables for Windows Docker
`$env:COMPOSE_CONVERT_WINDOWS_PATHS = "1"
`$env:DOCKER_BUILDKIT = "1"

# Test with core services first
Write-Host "🧪 Testing core services (Vault, PostgreSQL, Redis)..." -ForegroundColor Yellow

try {
    # Start core services with Windows override
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml up -d vault postgres redis
    
    Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Check service health
    Write-Host "🔍 Checking service health..." -ForegroundColor Green
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml ps
    
    Write-Host "📊 Service logs (last 20 lines):" -ForegroundColor Yellow
    docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml logs --tail=20
    
} catch {
    Write-Error "❌ Test failed: `$_"
}

Write-Host "✅ Windows Docker test completed" -ForegroundColor Green
Write-Host "📋 To stop services: docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml down" -ForegroundColor Cyan
"@

$testScript | Out-File -FilePath "test-windows-docker.ps1" -Encoding UTF8
Write-Host "Created test-windows-docker.ps1" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "Windows Docker Bind Mount Fix Complete!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created Files:" -ForegroundColor Yellow
Write-Host "   • $backupFile (backup)" -ForegroundColor White
Write-Host "   • .env.windows (Windows environment variables)" -ForegroundColor White
Write-Host "   • docker-compose.windows.override.yml (Windows volume overrides)" -ForegroundColor White
Write-Host "   • test-windows-docker.ps1 (Windows test script)" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Run: .\test-windows-docker.ps1" -ForegroundColor White
Write-Host "   2. Or manually: docker-compose -f docker-compose.production-hardened.yml -f docker-compose.windows.override.yml up -d" -ForegroundColor White
Write-Host ""
Write-Host "Key Changes:" -ForegroundColor Yellow
Write-Host "   • Removed Linux-specific mount options (noexec, nosuid, etc.)" -ForegroundColor White
Write-Host "   • Used absolute Windows paths instead of PWD variable" -ForegroundColor White
Write-Host "   • Added COMPOSE_CONVERT_WINDOWS_PATHS environment variable" -ForegroundColor White
Write-Host "   • Created override file to avoid modifying original configuration" -ForegroundColor White
Write-Host ""
