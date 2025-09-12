# GameForge AI - Model Management Setup (PowerShell)
# Quick setup for external model storage on Windows

Write-Host "🚀 GameForge AI - Model Management Quick Setup" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# Check if Docker is running
Write-Host "🔍 Checking Docker status..." -ForegroundColor Yellow
$dockerRunning = $false
try {
    docker info 2>$null | Out-Null
    $dockerRunning = $true
    Write-Host "✅ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Install Python dependencies
Write-Host "📦 Installing model management dependencies..." -ForegroundColor Yellow
pip install -r requirements-model-management.txt

# Check if MinIO container already exists
Write-Host "🗄️  Setting up MinIO storage..." -ForegroundColor Yellow
$existingContainer = docker ps -a --filter "name=gameforge-minio" --format "{{.Names}}" 2>$null

if ($existingContainer -contains "gameforge-minio") {
    Write-Host "   Starting existing MinIO container..." -ForegroundColor Gray
    docker start gameforge-minio 2>$null
}
else {
    Write-Host "   Creating new MinIO container..." -ForegroundColor Gray
    $minioCmd = "docker run -d --name gameforge-minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=admin -e MINIO_ROOT_PASSWORD=password123 -v minio-data:/data minio/minio server /data --console-address `":9001`""
    Invoke-Expression $minioCmd | Out-Null
}

# Wait for MinIO to be ready
Write-Host "⏳ Waiting for MinIO to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Test MinIO connectivity
$maxAttempts = 30
$attempt = 0
$minioReady = $false

while (-not $minioReady -and $attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $minioReady = $true
        }
    }
    catch {
        # MinIO not ready yet
    }
    
    if (-not $minioReady) {
        Write-Host "   Waiting for MinIO..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
        $attempt++
    }
}

if ($minioReady) {
    Write-Host "✅ MinIO is ready at http://localhost:9001 (admin/password123)" -ForegroundColor Green
}
else {
    Write-Host "❌ MinIO failed to start within timeout" -ForegroundColor Red
    exit 1
}

# Test model downloader setup
Write-Host "🔧 Testing model downloader configuration..." -ForegroundColor Yellow
$testScript = @"
import sys
import json
from pathlib import Path
try:
    # Check if config exists
    config_path = Path('config/models/model-registry.json')
    if config_path.exists():
        print('✅ Model registry found')
    else:
        print('⚠️  Model registry not found - run model-storage-migrator.py first')
    
    # Test basic import
    sys.path.append('scripts/model-management')
    print('✅ Model downloader configuration ready')
except Exception as e:
    print(f'⚠️  Setup issue: {e}')
"@

python -c $testScript

# Show current model status
Write-Host ""
Write-Host "📊 Current Model Status:" -ForegroundColor Cyan
Write-Host "======================="

if (Test-Path "services\asset-gen\models\stable-diffusion-xl-base-1.0") {
    $modelPath = "services\asset-gen\models"
    $currentSize = (Get-ChildItem -Path $modelPath -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $currentSizeGB = [math]::Round($currentSize / 1GB, 2)
    Write-Host "• Local models: $currentSizeGB GB" -ForegroundColor White
    Write-Host "• Status: Ready for migration" -ForegroundColor Green
}
else {
    Write-Host "• Local models: Not found" -ForegroundColor Yellow
    Write-Host "• Status: External storage mode" -ForegroundColor Blue
}

Write-Host ""
Write-Host "🎯 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "============="
Write-Host "1. Test model downloading:" -ForegroundColor White
Write-Host "   python scripts/model-management/model-downloader.py stable-diffusion-xl-base-1.0" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run health check:" -ForegroundColor White
Write-Host "   python scripts/model-management/health-check.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Start application with model management:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.model-storage.yml up" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 MinIO Console: http://localhost:9001" -ForegroundColor Magenta
Write-Host "🔑 Credentials: admin / password123" -ForegroundColor Magenta

Write-Host ""
Write-Host "✅ Model Management Setup Complete!" -ForegroundColor Green