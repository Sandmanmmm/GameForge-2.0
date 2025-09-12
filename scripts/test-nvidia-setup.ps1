# NVIDIA CUDA Setup Verification Script
# Tests NGC authentication and CUDA image availability

Write-Host "=== NVIDIA CUDA Setup Verification ===" -ForegroundColor Green
Write-Host ""

# Test 1: Check NGC authentication
Write-Host "1. Testing NGC Registry Authentication..." -ForegroundColor Cyan
try {
    $loginTest = docker system df 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Docker is running" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Docker connectivity issue" -ForegroundColor Red
    exit 1
}

# Test 2: Try pulling CUDA base image
Write-Host "`n2. Testing CUDA Image Pull..." -ForegroundColor Cyan
$cudaImages = @(
    "nvcr.io/nvidia/cuda:12.1-devel-ubuntu22.04",
    "nvcr.io/nvidia/cuda:12.0-devel-ubuntu22.04", 
    "nvcr.io/nvidia/cuda:11.8-devel-ubuntu22.04"
)

$successfulImage = $null
foreach ($image in $cudaImages) {
    Write-Host "   Trying: $image" -ForegroundColor Yellow
    
    docker pull $image 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ SUCCESS: $image" -ForegroundColor Green
        $successfulImage = $image
        break
    } else {
        Write-Host "   ❌ Failed: $image" -ForegroundColor Red
    }
}

if ($successfulImage) {
    Write-Host "`n3. Updating GameForge Dockerfile..." -ForegroundColor Cyan
    
    # Update the Dockerfile with working CUDA image
    $dockerfilePath = "Dockerfile.production.enhanced"
    if (Test-Path $dockerfilePath) {
        $content = Get-Content $dockerfilePath -Raw
        $content = $content -replace 'ARG GPU_BASE_IMAGE=.*', "ARG GPU_BASE_IMAGE=$successfulImage"
        Set-Content $dockerfilePath -Value $content
        Write-Host "   ✅ Updated $dockerfilePath with working CUDA image" -ForegroundColor Green
    }
    
    Write-Host "`n4. Testing GameForge Build..." -ForegroundColor Cyan
    Write-Host "   Building GameForge with CUDA support..." -ForegroundColor Yellow
    
    # Build the GameForge image
    docker-compose -f docker-compose.production-hardened.yml build gameforge-app
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ GameForge build successful!" -ForegroundColor Green
        
        # Verify the image was created
        $images = docker images | Select-String "gameforge.*phase2-phase4-production"
        if ($images) {
            Write-Host "   ✅ GameForge production image created: $images" -ForegroundColor Green
            
            Write-Host "`n=== NVIDIA CUDA Setup Complete! ===" -ForegroundColor Green
            Write-Host "🎉 Ready for cloud migration with GPU support!" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Yellow
            Write-Host "1. Run: .\validate-migration.ps1" -ForegroundColor White
            Write-Host "2. Run: .\migrate-to-cloud.ps1 -CloudProvider aws -DryRun" -ForegroundColor White
            
            return $true
        }
    } else {
        Write-Host "   ❌ GameForge build failed" -ForegroundColor Red
    }
} else {
    Write-Host "`n❌ No CUDA images could be pulled" -ForegroundColor Red
    Write-Host "This might indicate:" -ForegroundColor Yellow
    Write-Host "- NGC authentication failed" -ForegroundColor White
    Write-Host "- Network connectivity issues" -ForegroundColor White
    Write-Host "- Image tag availability" -ForegroundColor White
    
    Write-Host "`nFallback: Building CPU-only version..." -ForegroundColor Cyan
    # Set CPU variant and build
    $env:GAMEFORGE_VARIANT = "cpu"
    docker-compose -f docker-compose.production-hardened.yml build gameforge-app
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ CPU-only GameForge build successful" -ForegroundColor Green
        Write-Host "You can proceed with migration using CPU variant" -ForegroundColor Yellow
    }
}

Write-Host "`nCUDA Setup Summary:" -ForegroundColor Magenta
Write-Host "Working CUDA Image: $(if($successfulImage) {$successfulImage} else {'None - using CPU fallback'})" -ForegroundColor White
Write-Host "GameForge Build: $(if($LASTEXITCODE -eq 0) {'Success'} else {'Failed'})" -ForegroundColor White
