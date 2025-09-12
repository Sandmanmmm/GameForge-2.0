# GameForge Resource Optimization Validation Script
# Simple validation for resource limits and GPU configuration

Write-Host "=== GameForge Resource Optimization Validation ===" -ForegroundColor Cyan

# Check GPU configuration in docker-compose
Write-Host "`nChecking GPU Configuration..." -ForegroundColor Green

$ComposeContent = Get-Content "docker-compose.production-hardened.yml" -Raw

if ($ComposeContent -match "driver: nvidia") {
    Write-Host "✓ NVIDIA GPU driver configured" -ForegroundColor Green
} else {
    Write-Host "✗ NVIDIA GPU driver not found" -ForegroundColor Red
}

if ($ComposeContent -match "gameforge-worker:[\s\S]*?driver: nvidia") {
    Write-Host "✓ GPU access enabled for workers" -ForegroundColor Green
} else {
    Write-Host "✗ GPU access missing for workers" -ForegroundColor Red
}

if ($ComposeContent -match 'memory=\d+m') {
    Write-Host "✓ GPU memory limits configured" -ForegroundColor Green
} else {
    Write-Host "✗ GPU memory limits not configured" -ForegroundColor Red
}

# Check CUDA optimizations
Write-Host "`nChecking CUDA Configuration..." -ForegroundColor Green

if ($ComposeContent -match "PYTORCH_CUDA_ALLOC_CONF") {
    Write-Host "✓ PyTorch CUDA allocation configured" -ForegroundColor Green
} else {
    Write-Host "✗ PyTorch CUDA allocation not configured" -ForegroundColor Red
}

if ($ComposeContent -match "PYTORCH_JIT") {
    Write-Host "✓ PyTorch JIT compilation enabled" -ForegroundColor Green
} else {
    Write-Host "✗ PyTorch JIT compilation not enabled" -ForegroundColor Red
}

# Check resource limits
Write-Host "`nChecking Resource Limits..." -ForegroundColor Green

$MemoryMatches = [regex]::Matches($ComposeContent, "memory: (\d+)G")
$TotalMemory = 0
foreach ($Match in $MemoryMatches) {
    $TotalMemory += [int]$Match.Groups[1].Value
}

$CPUMatches = [regex]::Matches($ComposeContent, "cpus: '([\d.]+)'")
$TotalCPU = 0
foreach ($Match in $CPUMatches) {
    $TotalCPU += [double]$Match.Groups[1].Value
}

Write-Host "Total Memory Allocation: $TotalMemory GB" -ForegroundColor White
Write-Host "Total CPU Allocation: $TotalCPU cores" -ForegroundColor White

if ($TotalMemory -le 30) {
    Write-Host "✓ Memory allocation optimized" -ForegroundColor Green
} else {
    Write-Host "⚠ Memory allocation could be optimized" -ForegroundColor Yellow
}

if ($TotalCPU -le 16) {
    Write-Host "✓ CPU allocation optimized" -ForegroundColor Green
} else {
    Write-Host "⚠ CPU allocation could be optimized" -ForegroundColor Yellow
}

Write-Host "`nResource Optimization Summary:" -ForegroundColor Cyan
Write-Host "- gameforge-app: 12GB RAM, 6 CPU cores (GPU-enabled)" -ForegroundColor White
Write-Host "- gameforge-worker: 4GB RAM, 2 CPU cores (GPU-enabled)" -ForegroundColor White  
Write-Host "- postgres: 4GB RAM, 2 CPU cores" -ForegroundColor White
Write-Host "- elasticsearch: 4GB RAM, 2 CPU cores" -ForegroundColor White
Write-Host "- Other services: ~6GB RAM, ~4 CPU cores" -ForegroundColor White

Write-Host "`n=== Validation Complete ===" -ForegroundColor Cyan
