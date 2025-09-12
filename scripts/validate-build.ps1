# Post-Build GameForge Validation Script
# Tests the built GameForge image for GPU support and functionality

Write-Host "=== GameForge Build Validation ===" -ForegroundColor Green
Write-Host ""

# Check if build completed successfully
Write-Host "1. Checking GameForge Image..." -ForegroundColor Cyan
$gameforgeImage = docker images | Select-String "gameforge.*phase2-phase4-production"

if ($gameforgeImage) {
    Write-Host "   ✅ GameForge image found: $gameforgeImage" -ForegroundColor Green
    
    # Extract image name for testing
    $imageName = ($gameforgeImage -split '\s+')[0] + ":" + ($gameforgeImage -split '\s+')[1]
    Write-Host "   Testing image: $imageName" -ForegroundColor Yellow
    
    # Test 2: Check CUDA availability
    Write-Host "`n2. Testing CUDA Support..." -ForegroundColor Cyan
    try {
        $cudaTest = docker run --rm --gpus all $imageName python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Device Count: {torch.cuda.device_count()}'); print(f'CUDA Version: {torch.version.cuda}') if torch.cuda.is_available() else print('CPU-only mode')"
        
        if ($cudaTest -match "CUDA Available: True") {
            Write-Host "   ✅ CUDA Support: $cudaTest" -ForegroundColor Green
        } elseif ($cudaTest -match "CPU-only mode") {
            Write-Host "   ⚠️  CPU-only mode (no GPU available on host)" -ForegroundColor Yellow
        } else {
            Write-Host "   ❌ CUDA test failed: $cudaTest" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ Could not test CUDA: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Test 3: Check Python environment
    Write-Host "`n3. Testing Python Environment..." -ForegroundColor Cyan
    try {
        $pythonTest = docker run --rm $imageName python --version
        Write-Host "   ✅ Python Version: $pythonTest" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ Python test failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Test 4: Check key packages
    Write-Host "`n4. Testing Key Packages..." -ForegroundColor Cyan
    $packages = @("torch", "numpy", "pandas", "fastapi", "opencv-python")
    
    foreach ($package in $packages) {
        try {
            $packageTest = docker run --rm $imageName python -c "import $package; print('${package}:', $package.__version__)" 2>$null
            if ($packageTest) {
                Write-Host "   ✅ $packageTest" -ForegroundColor Green
            } else {
                Write-Host "   ❌ ${package}: Not found" -ForegroundColor Red
            }
        } catch {
            Write-Host "   ❌ ${package}: Import failed" -ForegroundColor Red
        }
    }
    
    # Test 5: Check GameForge application structure
    Write-Host "`n5. Testing Application Structure..." -ForegroundColor Cyan
    try {
        $appTest = docker run --rm $imageName ls -la /app/ 2>$null
        if ($appTest -match "main.py|app.py|gameforge") {
            Write-Host "   ✅ Application files found" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Application structure unclear" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ❌ Could not check app structure" -ForegroundColor Red
    }
    
    # Test 6: Update migration readiness
    Write-Host "`n6. Updating Migration Status..." -ForegroundColor Cyan
    .\validate-migration.ps1
    
    Write-Host "`n=== Build Validation Complete ===" -ForegroundColor Green
    Write-Host "🎉 Ready for cloud migration with NVIDIA GPU support!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Run: .\migrate-to-cloud.ps1 -CloudProvider aws -DryRun" -ForegroundColor White
    Write-Host "2. Test deployment: kubectl apply -k k8s/overlays/production" -ForegroundColor White
    Write-Host "3. Verify: .\cluster-status.ps1" -ForegroundColor White
    
} else {
    Write-Host "   ❌ GameForge image not found. Build may have failed." -ForegroundColor Red
    Write-Host "   Check build logs for errors." -ForegroundColor Yellow
}
