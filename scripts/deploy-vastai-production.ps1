# ========================================================================
# GameForge AI Production Platform - Vast.ai Deployment Script (PowerShell)
# Comprehensive deployment script for cloud GPU instances
# ========================================================================

param(
    [switch]$SkipBuild = $false,
    [switch]$ShowLogs = $false,
    [switch]$Cleanup = $false,
    [switch]$Help = $false
)

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Blue"

# ========================================================================
# Configuration
# ========================================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ComposeFile = "docker-compose.vastai-production.yml"
$EnvFile = ".env.vastai-production"
$DockerIgnoreFile = ".dockerignore.vastai"

# Vast.ai specific settings
$VastaiDeployment = $true
$DefaultMemoryLimit = "24G"
$DefaultCpuLimit = "12.0"

# ========================================================================
# Helper Functions
# ========================================================================
function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $BLUE
}

function Write-LogSuccess {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $GREEN
}

function Write-LogWarning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $YELLOW
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $RED
}

function Write-LogSection {
    param([string]$Message)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $BLUE
    Write-Host $Message -ForegroundColor $BLUE
    Write-Host "========================================" -ForegroundColor $BLUE
    Write-Host ""
}

function Test-Requirements {
    Write-LogSection "Checking Requirements"
    
    # Check if running on Vast.ai (look for common indicators)
    if ((Test-Path "/etc/vast-ai") -or ($env:VAST_INSTANCE_ID) -or ($env:CUDA_VISIBLE_DEVICES)) {
        Write-LogSuccess "Vast.ai environment detected"
        $env:VASTAI_DETECTED = "true"
    } else {
        Write-LogWarning "Vast.ai environment not detected, but continuing..."
        $env:VASTAI_DETECTED = "false"
    }
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-LogSuccess "Docker found: $dockerVersion"
    } catch {
        Write-LogError "Docker is not installed or not in PATH"
        exit 1
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-LogSuccess "Docker Compose found: $composeVersion"
    } catch {
        Write-LogError "Docker Compose is not installed or not in PATH"
        exit 1
    }
    
    # Check NVIDIA Docker runtime
    $dockerInfo = docker info 2>$null
    if ($dockerInfo -match "nvidia") {
        Write-LogSuccess "NVIDIA Docker runtime detected"
    } else {
        Write-LogWarning "NVIDIA Docker runtime not detected - GPU features may not work"
    }
    
    # Check GPU availability
    try {
        $nvidiaSmi = nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits 2>$null
        Write-LogSuccess "NVIDIA GPU detected:"
        $nvidiaSmi | ForEach-Object {
            Write-LogInfo "  GPU: $_"
        }
    } catch {
        Write-LogWarning "nvidia-smi not found - GPU may not be available"
    }
}

function Initialize-Environment {
    Write-LogSection "Setting Up Environment"
    
    Set-Location $ProjectRoot
    
    # Copy dockerignore for optimized builds
    if (Test-Path $DockerIgnoreFile) {
        Copy-Item $DockerIgnoreFile .dockerignore -Force
        Write-LogSuccess "Applied Vast.ai optimized .dockerignore"
    }
    
    # Check if environment file exists
    if (-not (Test-Path $EnvFile)) {
        Write-LogError "Environment file $EnvFile not found!"
        Write-LogInfo "Please create $EnvFile with your configuration"
        exit 1
    }
    
    # Load environment variables from file
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
    
    # Set Vast.ai specific environment variables
    $env:VASTAI_DEPLOYMENT = "true"
    $env:BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    
    try {
        $env:VCS_REF = (git rev-parse --short HEAD 2>$null)
    } catch {
        $env:VCS_REF = "unknown"
    }
    
    $env:BUILD_VERSION = "vastai-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    
    # Auto-detect Vast.ai instance ID if available
    if (-not $env:VASTAI_INSTANCE_ID) {
        try {
            $hostname = Get-Content /etc/hostname -ErrorAction SilentlyContinue
            if ($hostname -match 'C\d+') {
                $env:VASTAI_INSTANCE_ID = $matches[0]
                Write-LogInfo "Auto-detected Vast.ai instance ID: $($env:VASTAI_INSTANCE_ID)"
            }
        } catch {
            $env:VASTAI_INSTANCE_ID = "unknown"
        }
    }
    
    Write-LogSuccess "Environment configured for Vast.ai deployment"
    Write-LogInfo "Build version: $($env:BUILD_VERSION)"
    Write-LogInfo "Instance ID: $($env:VASTAI_INSTANCE_ID)"
}

function New-VolumeDirectories {
    Write-LogSection "Creating Volume Directories"
    
    # Create necessary volume directories
    $volumePaths = @(
        "volumes/training-data",
        "volumes/model-checkpoints",
        "volumes/security/harbor-secret",
        "volumes/security/harbor-ca",
        "volumes/security/clair-data",
        "volumes/security/clair-logs",
        "volumes/security/notary-data",
        "volumes/security/notary-certs"
    )
    
    foreach ($path in $volumePaths) {
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
    
    Write-LogSuccess "Volume directories created"
}

function Build-Images {
    Write-LogSection "Building Docker Images"
    
    Write-LogInfo "Building optimized images for Vast.ai..."
    
    # Build with Vast.ai optimizations
    $buildArgs = @(
        "--parallel",
        "--compress",
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "--build-arg", "BUILD_DATE=$($env:BUILD_DATE)",
        "--build-arg", "VCS_REF=$($env:VCS_REF)",
        "--build-arg", "BUILD_VERSION=$($env:BUILD_VERSION)"
    )
    
    docker-compose -f $ComposeFile build @buildArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-LogSuccess "Images built successfully"
    } else {
        Write-LogError "Image build failed"
        exit 1
    }
}

function Deploy-Services {
    Write-LogSection "Deploying Services"
    
    Write-LogInfo "Starting security bootstrap..."
    docker-compose -f $ComposeFile up -d security-bootstrap
    
    # Wait for bootstrap to complete
    Write-LogInfo "Waiting for security bootstrap to complete..."
    docker-compose -f $ComposeFile wait security-bootstrap
    
    Write-LogInfo "Starting core infrastructure services..."
    docker-compose -f $ComposeFile up -d security-monitor postgres redis vault elasticsearch
    
    # Wait for core services to be healthy
    Write-LogInfo "Waiting for core services to be ready..."
    Start-Sleep -Seconds 30
    
    Write-LogInfo "Starting GPU services..."
    docker-compose -f $ComposeFile up -d gameforge-gpu-inference gameforge-gpu-training
    
    # Wait for GPU services
    Write-LogInfo "Waiting for GPU services to initialize..."
    Start-Sleep -Seconds 60
    
    Write-LogInfo "Starting application services..."
    docker-compose -f $ComposeFile up -d gameforge-app gameforge-worker nginx
    
    Write-LogInfo "Starting monitoring services..."
    docker-compose -f $ComposeFile up -d prometheus grafana
    
    Write-LogSuccess "All services deployed"
}

function Test-ServiceHealth {
    Write-LogSection "Checking Service Health"
    
    Write-LogInfo "Waiting for services to become healthy..."
    
    # Check core services
    $services = @("postgres", "redis", "vault", "elasticsearch", "gameforge-gpu-inference", "gameforge-app")
    
    foreach ($service in $services) {
        Write-LogInfo "Checking $service..."
        $attempts = 0
        $maxAttempts = 30
        
        while ($attempts -lt $maxAttempts) {
            $status = docker-compose -f $ComposeFile ps $service
            if ($status -match "healthy|Up") {
                Write-LogSuccess "$service is healthy"
                break
            }
            
            $attempts++
            if ($attempts -eq $maxAttempts) {
                Write-LogError "$service failed to become healthy"
                docker-compose -f $ComposeFile logs --tail=20 $service
                return $false
            }
            
            Start-Sleep -Seconds 10
        }
    }
    
    Write-LogSuccess "All critical services are healthy"
    return $true
}

function Show-DeploymentStatus {
    Write-LogSection "Deployment Status"
    
    Write-Host "Service Status:"
    docker-compose -f $ComposeFile ps
    
    Write-Host "`nGPU Status:"
    try {
        $gpuInfo = nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null
        $gpuInfo | ForEach-Object {
            Write-Host "  $_"
        }
    } catch {
        Write-Host "  nvidia-smi not available"
    }
    
    Write-Host "`nService Endpoints:"
    $hostIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notmatch "Loopback"} | Select-Object -First 1).IPAddress
    if (-not $hostIp) { $hostIp = "localhost" }
    
    Write-Host "  GameForge App: http://${hostIp}:8080"
    Write-Host "  GPU Inference: http://${hostIp}:8081"
    Write-Host "  GPU Training: http://${hostIp}:8082"
    Write-Host "  Grafana: http://${hostIp}:3000"
    Write-Host "  Prometheus: http://${hostIp}:9090"
    
    Write-Host "`nResource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

function Remove-OldResources {
    Write-LogSection "Cleaning Up Old Resources"
    
    Write-LogInfo "Removing unused Docker resources..."
    docker system prune -f
    docker volume prune -f
    
    Write-LogInfo "Removing old images..."
    docker image prune -f
    
    Write-LogSuccess "Cleanup completed"
}

function Show-ServiceLogs {
    Write-LogSection "Recent Service Logs"
    
    Write-Host "GameForge App logs:"
    docker-compose -f $ComposeFile logs --tail=10 gameforge-app
    
    Write-Host "`nGPU Inference logs:"
    docker-compose -f $ComposeFile logs --tail=10 gameforge-gpu-inference
    
    Write-Host "`nGPU Training logs:"
    docker-compose -f $ComposeFile logs --tail=10 gameforge-gpu-training
}

function Show-Help {
    Write-Host "GameForge AI Vast.ai Deployment Script"
    Write-Host ""
    Write-Host "Usage: .\deploy-vastai-production.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -SkipBuild      Skip building Docker images"
    Write-Host "  -ShowLogs       Show recent service logs only"
    Write-Host "  -Cleanup        Clean up old resources only"
    Write-Host "  -Help           Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy-vastai-production.ps1                    # Full deployment"
    Write-Host "  .\deploy-vastai-production.ps1 -SkipBuild         # Deploy without rebuilding"
    Write-Host "  .\deploy-vastai-production.ps1 -ShowLogs          # Show logs only"
    Write-Host "  .\deploy-vastai-production.ps1 -Cleanup           # Cleanup only"
}

# ========================================================================
# Main Deployment Function
# ========================================================================
function Main {
    if ($Help) {
        Show-Help
        exit 0
    }
    
    if ($ShowLogs) {
        Show-ServiceLogs
        exit 0
    }
    
    if ($Cleanup) {
        Remove-OldResources
        exit 0
    }
    
    Write-LogSection "GameForge AI Vast.ai Deployment"
    Write-LogInfo "Starting deployment to Vast.ai cloud GPU instance..."
    
    # Full deployment process
    Test-Requirements
    Initialize-Environment
    New-VolumeDirectories
    
    if (-not $SkipBuild) {
        Build-Images
    } else {
        Write-LogInfo "Skipping image build as requested"
    }
    
    Deploy-Services
    $healthCheck = Test-ServiceHealth
    
    if ($healthCheck) {
        Show-DeploymentStatus
        
        Write-LogSection "Deployment Complete!"
        Write-LogSuccess "GameForge AI Platform is now running on Vast.ai"
        Write-LogInfo "Check the service endpoints above to access your deployment"
        Write-LogInfo "Use 'docker-compose -f $ComposeFile logs -f <service>' to follow logs"
        Write-LogInfo "Use '.\deploy-vastai-production.ps1 -ShowLogs' to see recent logs from all services"
    } else {
        Write-LogError "Deployment failed during health checks"
        exit 1
    }
}

# ========================================================================
# Error Handling and Execution
# ========================================================================
try {
    Main
} catch {
    Write-LogError "Deployment failed: $($_.Exception.Message)"
    exit 1
}
