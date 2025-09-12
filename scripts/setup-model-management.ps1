# GameForge AI - Model Management Setup (PowerShell)
# Quick setup for external model storage on Windows

Write-Host "🚀 GameForge AI - Model Management Quick Setup" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Install Python dependencies
Write-Host "📦 Installing model management dependencies..." -ForegroundColor Yellow
pip install -r requirements-model-management.txt

# Check if MinIO container already exists
$existingContainer = docker ps -a --filter "name=gameforge-minio" --format "{{.Names}}"

if ($existingContainer -eq "gameforge-minio") {
    Write-Host "🗄️  Starting existing MinIO container..." -ForegroundColor Yellow
    docker start gameforge-minio
} else {
    Write-Host "🗄️  Creating new MinIO container..." -ForegroundColor Yellow
    docker run -d --name gameforge-minio -p 9000:9000 -p 9001:9001 -e "MINIO_ROOT_USER=admin" -e "MINIO_ROOT_PASSWORD=password123" -v minio-data:/data minio/minio server /data --console-address ":9001"
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
    } catch {
        # MinIO not ready yet
    }
    
    if (-not $minioReady) {
        Write-Host "Waiting for MinIO..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
        $attempt++
    }
}

if ($minioReady) {
    Write-Host "✅ MinIO is ready at http://localhost:9001 (admin/password123)" -ForegroundColor Green
} else {
    Write-Host "❌ MinIO failed to start within timeout" -ForegroundColor Red
    exit 1
}

# Test model downloader setup
Write-Host "🔧 Testing model downloader configuration..." -ForegroundColor Yellow
python -c @"
from scripts.model_management.model_downloader import SmartModelDownloader
try:
    downloader = SmartModelDownloader()
    print('✅ Model downloader configured successfully')
except Exception as e:
    print(f'⚠️  Model downloader setup issue: {e}')
"@

# Show current model status
Write-Host "📊 Current Model Status:" -ForegroundColor Cyan
Write-Host "======================="

if (Test-Path "services\asset-gen\models\stable-diffusion-xl-base-1.0") {
    $currentSize = (Get-ChildItem -Path "services\asset-gen\models" -Recurse | Measure-Object -Property Length -Sum).Sum
    $currentSizeGB = [math]::Round($currentSize / 1GB, 2)
    Write-Host "• Local models: $currentSizeGB GB" -ForegroundColor White
    Write-Host "• Status: Ready for migration" -ForegroundColor Green
} else {
    Write-Host "• Local models: Not found" -ForegroundColor Yellow
    Write-Host "• Status: External storage mode" -ForegroundColor Blue
}

Write-Host ""
Write-Host "🎯 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "============="
Write-Host "1. Migrate models to external storage:" -ForegroundColor White
Write-Host "   bash scripts/migrate-model-storage.sh" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Test model downloading:" -ForegroundColor White
Write-Host "   python scripts/model-management/model-downloader.py stable-diffusion-xl-base-1.0" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Run health check:" -ForegroundColor White
Write-Host "   python scripts/model-management/health-check.py" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Start application with model management:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.model-storage.yml up" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 MinIO Console: http://localhost:9001" -ForegroundColor Magenta
Write-Host "🔑 Credentials: admin / password123" -ForegroundColor Magenta