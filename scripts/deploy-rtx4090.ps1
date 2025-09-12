# GameForge AI System - RTX 4090 Production PowerShell Deployment Script
# Phase 0: Foundation Containerization with RTX 4090 Optimization

param(
    [switch]$SkipChecks = $false,
    [switch]$Rebuild = $false,
    [switch]$Monitoring = $true,
    [switch]$CPUFallback = $false
)

# Colors for output
$colors = @{
    Red = 'Red'
    Green = 'Green'
    Yellow = 'Yellow'
    Blue = 'Blue'
    Cyan = 'Cyan'
    Magenta = 'Magenta'
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $colors.Red
}

function Write-RTXInfo {
    param([string]$Message)
    Write-Host "[RTX 4090] $Message" -ForegroundColor $colors.Magenta
}

Write-Host "🚀 GameForge AI RTX 4090 Production Deployment - Phase 0" -ForegroundColor $colors.Cyan
Write-Host "=====================================================" -ForegroundColor $colors.Cyan

# Check prerequisites
if (-not $SkipChecks) {
    Write-Status "Checking prerequisites for RTX 4090 deployment..."

    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker found: $dockerVersion"
    }
    catch {
        Write-Error "Docker is not installed or not in PATH!"
        exit 1
    }

    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Success "Docker Compose found: $composeVersion"
    }
    catch {
        Write-Error "Docker Compose is not installed or not in PATH!"
        exit 1
    }

    # Check if Docker is running
    try {
        docker ps | Out-Null
        Write-Success "Docker daemon is running"
    }
    catch {
        Write-Error "Docker daemon is not running!"
        exit 1
    }

    # RTX 4090 GPU Detection
    Write-RTXInfo "Detecting RTX 4090 GPU support..."
    
    try {
        # Check for NVIDIA drivers
        $nvidiaDrivers = Get-WmiObject Win32_SystemDriver | Where-Object { $_.Name -like "*nvidia*" }
        if ($nvidiaDrivers) {
            Write-Success "NVIDIA drivers detected"
            
            # Check for RTX 4090 specifically
            try {
                $gpuInfo = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*RTX*" -or $_.Name -like "*GeForce*" }
                if ($gpuInfo) {
                    foreach ($gpu in $gpuInfo) {
                        if ($gpu.Name -like "*RTX 4090*") {
                            Write-RTXInfo "RTX 4090 detected: $($gpu.Name)"
                            $RTX4090Detected = $true
                        }
                        elseif ($gpu.Name -like "*RTX*") {
                            Write-Warning "RTX GPU detected but not 4090: $($gpu.Name)"
                        }
                    }
                }
            }
            catch {
                Write-Warning "Could not detect specific GPU model"
            }

            # Test NVIDIA Docker runtime
            try {
                $dockerGpuTest = docker run --rm --gpus all ubuntu:22.04 nvidia-smi
                Write-Success "NVIDIA Docker runtime is working"
                $GPUSupported = $true
            }
            catch {
                Write-Warning "NVIDIA Docker runtime test failed"
                $GPUSupported = $false
            }
        }
        else {
            Write-Warning "NVIDIA drivers not detected"
            $GPUSupported = $false
        }
    }
    catch {
        Write-Warning "GPU detection failed: $($_.Exception.Message)"
        $GPUSupported = $false
    }

    if ($CPUFallback -or -not $GPUSupported) {
        Write-Warning "Running in CPU fallback mode"
        $deploymentMode = "cpu"
    }
    elseif ($RTX4090Detected) {
        Write-RTXInfo "RTX 4090 high-performance mode enabled"
        $deploymentMode = "rtx4090"
    }
    else {
        Write-Status "Standard GPU mode enabled"
        $deploymentMode = "gpu"
    }

    Write-Success "Prerequisites check completed - Mode: $deploymentMode"
}

# Create necessary directories
Write-Status "Creating necessary directories..."
$directories = @(
    "generated_assets",
    "logs", 
    "static",
    "config",
    "nginx\ssl",
    "monitoring\grafana\dashboards",
    "monitoring\grafana\datasources",
    "models"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Status "Created directory: $dir"
    }
}

Write-Success "Directories created"

# Build or rebuild the GameForge AI RTX 4090 image
if ($Rebuild -or -not (docker images gameforge-ai-rtx4090:latest -q)) {
    Write-RTXInfo "Building GameForge AI RTX 4090 optimized Docker image..."
    
    try {
        docker build -f gameforge-ai-rtx4090.Dockerfile -t gameforge-ai-rtx4090:latest .
        Write-Success "GameForge AI RTX 4090 image built successfully"
    }
    catch {
        Write-Error "Failed to build GameForge AI RTX 4090 image: $($_.Exception.Message)"
        exit 1
    }
}
else {
    Write-Status "Using existing GameForge AI RTX 4090 image"
}

# Pull other required images
Write-Status "Pulling required images..."
$images = @(
    "redis:7.2-alpine",
    "nginx:1.25-alpine",
    "prom/prometheus:v2.47.2",
    "grafana/grafana:10.2.0"
)

if ($GPUSupported -and -not $CPUFallback) {
    $images += "mindprince/nvidia_gpu_prometheus_exporter:0.1"
}

foreach ($image in $images) {
    try {
        docker pull $image
        Write-Status "Pulled: $image"
    }
    catch {
        Write-Warning "Failed to pull: $image"
    }
}

Write-Success "Images pulled successfully"

# Stop existing containers
Write-Status "Stopping existing containers..."
try {
    docker-compose -f docker-compose.rtx4090.yml down --remove-orphans
    Write-Status "Existing containers stopped"
}
catch {
    Write-Warning "No existing containers to stop"
}

# Start the RTX 4090 production stack
Write-RTXInfo "Starting GameForge AI RTX 4090 production stack..."
try {
    if ($deploymentMode -eq "cpu") {
        # CPU fallback mode - exclude GPU-dependent services
        docker-compose -f docker-compose.rtx4090.yml up -d redis gameforge-ai nginx prometheus grafana
    }
    elseif ($Monitoring) {
        # Full stack with monitoring
        docker-compose -f docker-compose.rtx4090.yml up -d
    }
    else {
        # Core services only
        docker-compose -f docker-compose.rtx4090.yml up -d redis gameforge-ai gameforge-worker nginx
    }
    Write-Success "RTX 4090 production stack started"
}
catch {
    Write-Error "Failed to start RTX 4090 production stack: $($_.Exception.Message)"
    exit 1
}

# Wait for services to be ready
Write-Status "Waiting for services to start..."
Start-Sleep -Seconds 45

# Health checks
Write-Status "Performing health checks..."

# Check Redis
try {
    $redisHealth = docker exec gameforge-redis redis-cli ping 2>$null
    if ($redisHealth -eq "PONG") {
        Write-Success "Redis is healthy"
    }
    else {
        Write-Warning "Redis health check returned: $redisHealth"
    }
}
catch {
    Write-Error "Redis health check failed: $($_.Exception.Message)"
}

# Check GameForge AI RTX 4090
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 15
    if ($response.StatusCode -eq 200) {
        Write-Success "GameForge AI RTX 4090 is healthy"
        
        # Test GPU functionality
        try {
            $gpuTest = Invoke-WebRequest -Uri "http://localhost:8080/api/gpu-status" -UseBasicParsing -TimeoutSec 10
            $gpuStatus = $gpuTest.Content | ConvertFrom-Json
            Write-RTXInfo "GPU Status: $($gpuStatus.gpu_available) - Mode: $($gpuStatus.mode)"
        }
        catch {
            Write-Warning "GPU status check failed, but service is running"
        }
    }
    else {
        Write-Warning "GameForge AI returned status code: $($response.StatusCode)"
    }
}
catch {
    Write-Error "GameForge AI health check failed: $($_.Exception.Message)"
}

# Check Nginx
try {
    $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Success "Nginx is healthy"
    }
    else {
        Write-Warning "Nginx returned status code: $($response.StatusCode)"
    }
}
catch {
    Write-Error "Nginx health check failed: $($_.Exception.Message)"
}

# Display service URLs
Write-Host ""
Write-Success "🎉 GameForge AI RTX 4090 Production Stack Deployed Successfully!"
Write-Host "==========================================================" -ForegroundColor $colors.Cyan
Write-Host "Service URLs:" -ForegroundColor $colors.Green
Write-Host "• GameForge AI API: http://localhost:8080"
Write-Host "• Load Balancer: http://localhost"
if ($Monitoring) {
    Write-Host "• Prometheus: http://localhost:9090"
    Write-Host "• Grafana: http://localhost:3000 (admin/gameforge123)"
    if ($GPUSupported) {
        Write-Host "• GPU Metrics: http://localhost:9445"
    }
}
Write-Host ""
Write-RTXInfo "RTX 4090 Optimizations:"
Write-Host "• CUDA 12.1 support with PyTorch optimization"
Write-Host "• Memory allocation: 512MB chunks for stability"
Write-Host "• Architecture target: 8.9 (RTX 4090 specific)"
Write-Host "• High-performance SDXL pipeline"
Write-Host ""
Write-Host "Quick Tests:" -ForegroundColor $colors.Blue
Write-Host "• Health: Invoke-WebRequest -Uri 'http://localhost/api/health'"
Write-Host "• GPU Status: Invoke-WebRequest -Uri 'http://localhost:8080/api/gpu-status'"
Write-Host "• Generate: POST to http://localhost/generate/image"
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor $colors.Yellow
Write-Host "• View logs: docker-compose -f docker-compose.rtx4090.yml logs -f gameforge-ai"
Write-Host "• Stop services: docker-compose -f docker-compose.rtx4090.yml down"
Write-Host "• Restart: docker-compose -f docker-compose.rtx4090.yml restart"
Write-Host "• Scale workers: docker-compose -f docker-compose.rtx4090.yml up -d --scale gameforge-worker=2"
Write-Host ""
Write-Success "Phase 0: RTX 4090 Foundation Containerization Complete! ✅"

# Optional: Performance test
$runTest = Read-Host "Run RTX 4090 performance test? (y/N)"
if ($runTest -eq 'y' -or $runTest -eq 'Y') {
    Write-RTXInfo "Running RTX 4090 performance test..."
    try {
        $testPayload = @{
            prompt = "RTX 4090 test generation - fantasy sword"
            style = "realistic"
            steps = 20
            width = 512
            height = 512
        } | ConvertTo-Json

        $testStart = Get-Date
        $testResponse = Invoke-WebRequest -Uri "http://localhost/generate/image" -Method POST -Body $testPayload -ContentType "application/json" -TimeoutSec 60
        $testEnd = Get-Date
        $duration = ($testEnd - $testStart).TotalSeconds

        if ($testResponse.StatusCode -eq 200) {
            Write-RTXInfo "Performance test completed successfully in $([math]::Round($duration, 2)) seconds"
        }
        else {
            Write-Warning "Performance test failed with status: $($testResponse.StatusCode)"
        }
    }
    catch {
        Write-Warning "Performance test failed: $($_.Exception.Message)"
    }
}

# Optional: Open browser to test endpoints
$openBrowser = Read-Host "Open browser to test services? (y/N)"
if ($openBrowser -eq 'y' -or $openBrowser -eq 'Y') {
    Start-Process "http://localhost"
    if ($Monitoring) {
        Start-Process "http://localhost:3000"
    }
}
