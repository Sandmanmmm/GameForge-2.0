# GameForge Resource Optimization Validation Script
# Validates optimized resource limits and GPU configuration

Write-Host "=== GameForge Resource Optimization Validation ===" -ForegroundColor Cyan
Write-Host "Checking resource limits and GPU configuration..." -ForegroundColor Yellow

$ValidationResults = @{
    "Resource Limits Configured" = $false
    "GPU Access Enabled" = $false
    "GPU Worker Configuration" = $false
    "Memory Optimization" = $false
    "CPU Optimization" = $false
    "GPU Memory Limits" = $false
    "CUDA Configuration" = $false
}

# Check Docker Compose configuration
Write-Host "`n1. Analyzing Docker Compose Configuration..." -ForegroundColor Green

try {
    $ComposeFile = Get-Content "docker-compose.production-hardened.yml" -Raw
    
    # Check GPU configuration for main app
    if ($ComposeFile -match "driver: nvidia" -and $ComposeFile -match "capabilities: \[gpu, compute, utility\]") {
        $ValidationResults["GPU Access Enabled"] = $true
        Write-Host "   ✓ GPU access configured for main application" -ForegroundColor Green
    } else {
        Write-Host "   ✗ GPU access not properly configured" -ForegroundColor Red
    }
    
    # Check GPU worker configuration
    if ($ComposeFile -match "gameforge-worker:[\s\S]*?driver: nvidia") {
        $ValidationResults["GPU Worker Configuration"] = $true
        Write-Host "   ✓ GPU access configured for workers" -ForegroundColor Green
    } else {
        Write-Host "   ✗ GPU access missing for worker service" -ForegroundColor Red
    }
    
    # Check GPU memory limits
    if ($ComposeFile -match 'memory=\d+m') {
        $ValidationResults["GPU Memory Limits"] = $true
        Write-Host "   ✓ GPU memory limits configured" -ForegroundColor Green
    } else {
        Write-Host "   ✗ GPU memory limits not configured" -ForegroundColor Red
    }
    
    # Check CUDA optimizations
    if ($ComposeFile -match "PYTORCH_CUDA_ALLOC_CONF.*garbage_collection_threshold" -and $ComposeFile -match "PYTORCH_JIT") {
        $ValidationResults["CUDA Configuration"] = $true
        Write-Host "   ✓ Advanced CUDA configuration present" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Advanced CUDA configuration missing" -ForegroundColor Red
    }
    
    # Check resource limits
    if ($ComposeFile -match "limits:" -and $ComposeFile -match "reservations:") {
        $ValidationResults["Resource Limits Configured"] = $true
        Write-Host "   ✓ Resource limits and reservations configured" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Resource limits not properly configured" -ForegroundColor Red
    }
    
} catch {
    Write-Host "   ✗ Error reading Docker Compose configuration" -ForegroundColor Red
}

# Analyze resource allocation
Write-Host "`n2. Analyzing Resource Allocation..." -ForegroundColor Green

try {
    # Extract memory allocations
    $MemoryMatches = [regex]::Matches($ComposeFile, "memory: (\d+)G")
    $TotalMemoryLimits = 0
    foreach ($Match in $MemoryMatches) {
        $TotalMemoryLimits += [int]$Match.Groups[1].Value
    }
    
    # Extract CPU allocations
    $CPUMatches = [regex]::Matches($ComposeFile, "cpus: '([\d.]+)'")
    $TotalCPULimits = 0
    foreach ($Match in $CPUMatches) {
        $TotalCPULimits += [float]$Match.Groups[1].Value
    }
    
    Write-Host "   Total Memory Limits: ${TotalMemoryLimits}GB" -ForegroundColor White
    Write-Host "   Total CPU Limits: ${TotalCPULimits} cores" -ForegroundColor White
    
    # Validate resource optimization
    if ($TotalMemoryLimits -le 30 -and $TotalMemoryLimits -ge 20) {
        $ValidationResults["Memory Optimization"] = $true
        Write-Host "   ✓ Memory allocation optimized (${TotalMemoryLimits}GB within recommended 20-30GB)" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Memory allocation needs optimization (${TotalMemoryLimits}GB, recommended 20-30GB)" -ForegroundColor Yellow
    }
    
    if ($TotalCPULimits -le 16 -and $TotalCPULimits -ge 10) {
        $ValidationResults["CPU Optimization"] = $true
        Write-Host "   ✓ CPU allocation optimized (${TotalCPULimits} cores within recommended 10-16 cores)" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ CPU allocation needs optimization (${TotalCPULimits} cores, recommended 10-16 cores)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "   ✗ Error analyzing resource allocation" -ForegroundColor Red
}

# Check GPU availability (if Docker is running)
Write-Host "`n3. Checking GPU Availability..." -ForegroundColor Green

try {
    $DockerInfo = docker info 2>$null
    if ($DockerInfo -match "nvidia") {
        Write-Host "   ✓ NVIDIA Docker runtime detected" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ NVIDIA Docker runtime not detected" -ForegroundColor Yellow
    }
    
    # Try to get GPU information
    $GPUInfo = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null
    if ($GPUInfo) {
        Write-Host "   ✓ GPU detected: $($GPUInfo -split ',' | Select-Object -First 1)" -ForegroundColor Green
        $GPUMemory = ($GPUInfo -split ',')[1]
        Write-Host "   ✓ GPU Memory: ${GPUMemory}MB" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ GPU information not available (nvidia-smi not found)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠ Unable to check GPU availability" -ForegroundColor Yellow
}

# Performance recommendations
Write-Host "`n4. Performance Analysis..." -ForegroundColor Green

$ServiceResources = @{
    "gameforge-app" = @{ Memory = 12; CPU = 6.0; GPU = $true }
    "gameforge-worker" = @{ Memory = 4; CPU = 2.0; GPU = $true }
    "postgres" = @{ Memory = 4; CPU = 2.0; GPU = $false }
    "elasticsearch" = @{ Memory = 4; CPU = 2.0; GPU = $false }
    "redis" = @{ Memory = 2; CPU = 1.0; GPU = $false }
}

foreach ($Service in $ServiceResources.GetEnumerator()) {
    $Name = $Service.Key
    $Resources = $Service.Value
    $GPUStatus = if ($Resources.GPU) { "GPU-enabled" } else { "CPU-only" }
    Write-Host "   $Name: ${Resources.Memory}GB RAM, ${Resources.CPU} CPU cores ($GPUStatus)" -ForegroundColor White
}

# Summary
Write-Host "`n=== Validation Summary ===" -ForegroundColor Cyan

$SuccessCount = ($ValidationResults.Values | Where-Object { $_ -eq $true }).Count
$TotalChecks = $ValidationResults.Count
$SuccessPercentage = [math]::Round(($SuccessCount / $TotalChecks) * 100, 1)

foreach ($Check in $ValidationResults.GetEnumerator()) {
    $Status = if ($Check.Value) { "✓ PASS" } else { "✗ FAIL" }
    $Color = if ($Check.Value) { "Green" } else { "Red" }
    Write-Host "   $($Check.Key): $Status" -ForegroundColor $Color
}

Write-Host "`nOverall Optimization Score: $SuccessPercentage% ($SuccessCount/$TotalChecks)" -ForegroundColor $(if ($SuccessPercentage -gt 85) { "Green" } elseif ($SuccessPercentage -gt 70) { "Yellow" } else { "Red" })

# Recommendations
Write-Host "`n=== Optimization Recommendations ===" -ForegroundColor Cyan

if (-not $ValidationResults["GPU Worker Configuration"]) {
    Write-Host "   • Enable GPU access for worker service for AI task acceleration" -ForegroundColor Yellow
}

if (-not $ValidationResults["GPU Memory Limits"]) {
    Write-Host "   • Add GPU memory limits to prevent resource exhaustion" -ForegroundColor Yellow
}

if (-not $ValidationResults["CUDA Configuration"]) {
    Write-Host "   • Implement advanced CUDA configuration for better GPU utilization" -ForegroundColor Yellow
}

if (-not $ValidationResults["Memory Optimization"]) {
    Write-Host "   • Optimize memory allocation to reduce resource waste" -ForegroundColor Yellow
}

if (-not $ValidationResults["CPU Optimization"]) {
    Write-Host "   • Balance CPU allocation across services for better performance" -ForegroundColor Yellow
}

# Hardware recommendations
Write-Host "`n=== Hardware Recommendations ===" -ForegroundColor Cyan
Write-Host "   Minimum Production Hardware:" -ForegroundColor White
Write-Host "   • RAM: 32GB (current config needs ~${TotalMemoryLimits}GB)" -ForegroundColor White
Write-Host "   • CPU: 16 cores (current config needs ~${TotalCPULimits} cores)" -ForegroundColor White
Write-Host "   • GPU: NVIDIA RTX 4090 (24GB VRAM recommended)" -ForegroundColor White
Write-Host "   • Storage: 1TB NVMe SSD for optimal performance" -ForegroundColor White

if ($SuccessPercentage -eq 100) {
    Write-Host "`n🎉 Resource optimization is complete and production-ready!" -ForegroundColor Green
} elseif ($SuccessPercentage -gt 85) {
    Write-Host "`n✅ Resource configuration is well-optimized with minor improvements needed" -ForegroundColor Yellow
} else {
    Write-Host "`n⚠️  Resource configuration needs optimization for production deployment" -ForegroundColor Red
}

Write-Host "`n=== Resource Optimization Validation Complete ===" -ForegroundColor Cyan
