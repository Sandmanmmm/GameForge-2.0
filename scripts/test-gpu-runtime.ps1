# GPU Runtime Configuration Test
# ==============================
# Tests NVIDIA runtime configuration for production deployment

Write-Host "GameForge GPU Runtime Test" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Test 1: Check Docker NVIDIA runtime installation
Write-Host "`n1. Checking Docker NVIDIA runtime..." -ForegroundColor Yellow

try {
    $dockerInfo = docker info 2>&1
    if ($dockerInfo -match "nvidia") {
        Write-Host "✅ NVIDIA runtime detected in Docker" -ForegroundColor Green
    } else {
        Write-Host "⚠️ NVIDIA runtime not found in Docker info" -ForegroundColor Yellow
        Write-Host "   Install nvidia-container-toolkit if using GPU features" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Could not check Docker info: $_" -ForegroundColor Red
}

# Test 2: Check for NVIDIA drivers
Write-Host "`n2. Checking NVIDIA drivers..." -ForegroundColor Yellow

try {
    $nvidiaOutput = nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ NVIDIA drivers installed and working" -ForegroundColor Green
        Write-Host "NVIDIA-SMI output:" -ForegroundColor Cyan
        Write-Host $nvidiaOutput -ForegroundColor Gray
    } else {
        Write-Host "⚠️ nvidia-smi not available or failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ nvidia-smi command not found" -ForegroundColor Yellow
    Write-Host "   This is normal if no NVIDIA GPU is present" -ForegroundColor Gray
}

# Test 3: Test simple GPU container
Write-Host "`n3. Testing GPU container runtime..." -ForegroundColor Yellow

$testCompose = @"
version: '3.8'
services:
  gpu-test:
    image: nvidia/cuda:11.8-runtime-ubuntu20.04
    runtime: nvidia
    command: nvidia-smi
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
"@

try {
    $testCompose | Out-File -FilePath "gpu-test.yml" -Encoding UTF8
    
    Write-Host "   Running GPU test container..." -ForegroundColor Cyan
    $gpuTest = docker-compose -f gpu-test.yml run --rm gpu-test 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ GPU runtime test successful" -ForegroundColor Green
        Write-Host "GPU Test Output:" -ForegroundColor Cyan
        Write-Host $gpuTest -ForegroundColor Gray
    } else {
        Write-Host "⚠️ GPU runtime test failed (expected without GPU hardware)" -ForegroundColor Yellow
        Write-Host "Error: $gpuTest" -ForegroundColor Gray
    }
    
    # Cleanup
    Remove-Item "gpu-test.yml" -ErrorAction SilentlyContinue
    
} catch {
    Write-Host "❌ GPU test failed: $_" -ForegroundColor Red
}

# Test 4: Validate production GPU configuration
Write-Host "`n4. Validating production GPU configuration..." -ForegroundColor Yellow

try {
    $prodConfig = docker-compose -f docker-compose.production-hardened.yml config 2>&1
    
    if ($prodConfig -match "runtime.*nvidia") {
        Write-Host "✅ Production config has NVIDIA runtime configured" -ForegroundColor Green
    } else {
        Write-Host "❌ NVIDIA runtime not found in production config" -ForegroundColor Red
    }
    
    if ($prodConfig -match "NVIDIA_VISIBLE_DEVICES") {
        Write-Host "✅ NVIDIA environment variables configured" -ForegroundColor Green
    } else {
        Write-Host "❌ NVIDIA environment variables missing" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ Could not validate production config: $_" -ForegroundColor Red
}

Write-Host "`nGPU Runtime Test Summary:" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host "- Docker runtime: Check Docker info for 'nvidia'" -ForegroundColor White
Write-Host "- NVIDIA drivers: Run nvidia-smi to verify" -ForegroundColor White
Write-Host "- Production config: Validated for runtime: nvidia" -ForegroundColor White
Write-Host "`nNote: GPU features require NVIDIA GPU hardware and nvidia-container-toolkit" -ForegroundColor Yellow
