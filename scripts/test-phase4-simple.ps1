# Simple Phase 4 Testing Script
Write-Host "🔍 GameForge Phase 4 - Quick Test" -ForegroundColor Blue
Write-Host "=================================" -ForegroundColor Blue

# Check if required files exist
$requiredFiles = @(
    "Dockerfile.production.enhanced",
    "scripts\model-manager.sh",
    "scripts\entrypoint-phase4.sh",
    "docker-compose.phase4.yml"
)

Write-Host "`n📁 Checking required files..." -ForegroundColor Cyan
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file exists" -ForegroundColor Green
    }
    else {
        Write-Host "❌ $file missing" -ForegroundColor Red
    }
}

# Check Docker
Write-Host "`n🐳 Checking Docker..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker available: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker not available" -ForegroundColor Red
}

# Check Docker Compose
Write-Host "`n🔧 Checking Docker Compose..." -ForegroundColor Cyan
try {
    $composeVersion = docker-compose --version
    Write-Host "✅ Docker Compose available: $composeVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker Compose not available" -ForegroundColor Red
}

# Check script permissions
Write-Host "`n🔐 Checking script files..." -ForegroundColor Cyan
$scripts = @("scripts\model-manager.sh", "scripts\entrypoint-phase4.sh")
foreach ($script in $scripts) {
    if (Test-Path $script) {
        $content = Get-Content $script -Raw
        if ($content.Contains("#!/bin/bash")) {
            Write-Host "✅ $script has proper shebang" -ForegroundColor Green
        }
        else {
            Write-Host "⚠️  $script missing shebang" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n🎯 Phase 4 components check completed!" -ForegroundColor Blue
