#!/usr/bin/env pwsh
# ========================================================================
# Phase 2 + Phase 4 Production Build Integration Script
# Enhanced Multi-stage Dockerfile with CPU/GPU Variants + Model Asset Security
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpu", "cpu")]
    [string]$Variant = "gpu",
    
    [Parameter(Mandatory=$false)]
    [string]$BuildVersion = "latest",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTests,
    
    [Parameter(Mandatory=$false)]
    [switch]$PushToRegistry,
    
    [Parameter(Mandatory=$false)]
    [switch]$ValidateOnly,
    
    [Parameter(Mandatory=$false)]
    [string]$Registry = "localhost:5000"
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "Phase 2 + Phase 4 Production Build Integration" -ForegroundColor Cyan
Write-Host "Variant: $Variant | Version: $BuildVersion" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Function to check prerequisites
function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Host "✓ Docker: $dockerVersion" -ForegroundColor Green
    } catch {
        throw "Docker is not installed or not in PATH"
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker compose version
        Write-Host "✓ Docker Compose: $composeVersion" -ForegroundColor Green
    } catch {
        throw "Docker Compose is not installed or not in PATH"
    }
    
    # Check required files
    $requiredFiles = @(
        "docker-compose.production-hardened.yml",
        "Dockerfile.production.enhanced",
        ".env.phase2"
    )
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Host "✓ Found: $file" -ForegroundColor Green
        } else {
            throw "Required file not found: $file"
        }
    }
    
    # Check for GPU support if variant is gpu
    if ($Variant -eq "gpu") {
        try {
            $nvidiaTest = docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi --query-gpu=name --format=csv,noheader,nounits 2>$null
            if ($nvidiaTest) {
                Write-Host "✓ GPU Support: Available" -ForegroundColor Green
            }
        } catch {
            Write-Warning "GPU support check failed - continuing with CPU fallback"
            $script:Variant = "cpu"
        }
    }
}

# Function to set environment variables based on variant
function Set-VariantEnvironment {
    Write-Host "Configuring environment for $Variant variant..." -ForegroundColor Yellow
    
    # Set base environment
    $env:BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $env:VCS_REF = try { git rev-parse --short HEAD } catch { "unknown" }
    $env:BUILD_VERSION = $BuildVersion
    $env:GAMEFORGE_VARIANT = $Variant
    
    if ($Variant -eq "gpu") {
        # GPU Configuration
        $env:DOCKER_RUNTIME = "nvidia"
        $env:ENABLE_GPU = "true"
        $env:MEMORY_LIMIT = "12G"
        $env:CPU_LIMIT = "6.0"
        $env:MEMORY_RESERVATION = "4G"
        $env:CPU_RESERVATION = "2.0"
        $env:GPU_COUNT = "1"
        $env:NVIDIA_VISIBLE_DEVICES = "all"
        $env:NVIDIA_DRIVER_CAPABILITIES = "compute,utility"
        Write-Host "✓ GPU environment configured" -ForegroundColor Green
    } else {
        # CPU Configuration
        $env:DOCKER_RUNTIME = "runc"
        $env:ENABLE_GPU = "false"
        $env:MEMORY_LIMIT = "8G"
        $env:CPU_LIMIT = "4.0"
        $env:MEMORY_RESERVATION = "2G"
        $env:CPU_RESERVATION = "1.0"
        $env:GPU_COUNT = "0"
        Write-Host "✓ CPU environment configured" -ForegroundColor Green
    }
    
    # Common optimization settings
    $env:COMPILE_BYTECODE = "true"
    $env:SECURITY_HARDENING = "true"
    $env:WORKERS = "4"
    $env:MAX_WORKERS = "8"
    $env:WORKER_TIMEOUT = "300"
    $env:WORKER_CLASS = "uvicorn.workers.UvicornWorker"
    
    # BuildKit settings
    $env:COMPOSE_DOCKER_CLI_BUILD = "1"
    $env:DOCKER_BUILDKIT = "1"
    $env:BUILDKIT_PROGRESS = "plain"
}

# Function to validate configuration
function Test-Configuration {
    Write-Host "Validating Phase 2 + Phase 4 configuration..." -ForegroundColor Yellow
    
    # Test docker-compose configuration
    try {
        docker compose -f docker-compose.production-hardened.yml config --quiet
        Write-Host "✓ Docker Compose configuration is valid" -ForegroundColor Green
    } catch {
        throw "Docker Compose configuration validation failed: $_"
    }
    
    # Test Dockerfile syntax
    try {
        docker build --dry-run -f Dockerfile.production.enhanced --target production . 2>$null
        Write-Host "✓ Dockerfile syntax is valid" -ForegroundColor Green
    } catch {
        Write-Warning "Dockerfile dry-run not supported, skipping syntax check"
    }
}

# Function to build Phase 2 + Phase 4 images
function Invoke-Phase2Phase4Build {
    Write-Host "Building Phase 2 + Phase 4 production images..." -ForegroundColor Yellow
    
    try {
        $buildCommand = "docker compose -f docker-compose.production-hardened.yml build gameforge-app"
        Write-Host "Executing: $buildCommand" -ForegroundColor Cyan
        Invoke-Expression $buildCommand
        
        Write-Host "✓ Phase 2 + Phase 4 build completed successfully" -ForegroundColor Green
    } catch {
        throw "Build failed: $_"
    }
}

# Function to run validation tests
function Test-Phase2Phase4Integration {
    if ($SkipTests) {
        Write-Host "Skipping tests as requested" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Running Phase 2 + Phase 4 integration tests..." -ForegroundColor Yellow
    
    try {
        # Start services for testing
        docker compose -f docker-compose.production-hardened.yml up -d postgres redis vault
        Start-Sleep -Seconds 30
        
        # Test application startup
        docker compose -f docker-compose.production-hardened.yml up -d gameforge-app
        Start-Sleep -Seconds 60
        
        # Check health endpoints
        $healthCheck = docker compose -f docker-compose.production-hardened.yml exec -T gameforge-app curl -f http://localhost:8080/health
        if ($healthCheck -match "healthy") {
            Write-Host "✓ Health check passed" -ForegroundColor Green
        } else {
            throw "Health check failed"
        }
        
        # Check variant-specific functionality
        if ($Variant -eq "gpu") {
            $gpuCheck = docker compose -f docker-compose.production-hardened.yml exec -T gameforge-app python -c "import torch; print('GPU available:', torch.cuda.is_available())"
            Write-Host "GPU Check: $gpuCheck" -ForegroundColor Cyan
        }
        
        Write-Host "✓ Phase 2 + Phase 4 integration tests passed" -ForegroundColor Green
    } catch {
        Write-Error "Integration tests failed: $_"
        # Cleanup on failure
        docker compose -f docker-compose.production-hardened.yml down
        throw
    } finally {
        # Cleanup test environment
        docker compose -f docker-compose.production-hardened.yml down
    }
}

# Function to push to registry
function Push-ToRegistry {
    if (-not $PushToRegistry) {
        Write-Host "Skipping registry push" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Pushing to registry: $Registry" -ForegroundColor Yellow
    
    $imageName = "gameforge:phase2-phase4-production-$Variant"
    $registryTag = "$Registry/$imageName"
    
    try {
        docker tag $imageName $registryTag
        docker push $registryTag
        Write-Host "✓ Successfully pushed $registryTag" -ForegroundColor Green
    } catch {
        throw "Registry push failed: $_"
    }
}

# Function to display build summary
function Show-BuildSummary {
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host "Phase 2 + Phase 4 Build Summary" -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host "Variant: $Variant" -ForegroundColor White
    Write-Host "Build Version: $BuildVersion" -ForegroundColor White
    Write-Host "VCS Ref: $env:VCS_REF" -ForegroundColor White
    Write-Host "Build Date: $env:BUILD_DATE" -ForegroundColor White
    Write-Host "GPU Enabled: $env:ENABLE_GPU" -ForegroundColor White
    Write-Host "Runtime: $env:DOCKER_RUNTIME" -ForegroundColor White
    
    # Show image sizes
    $imageName = "gameforge:phase2-phase4-production-$Variant"
    try {
        $imageInfo = docker images $imageName --format "table {{.Size}}\t{{.CreatedAt}}"
        Write-Host "Image Info:" -ForegroundColor White
        Write-Host $imageInfo -ForegroundColor Gray
    } catch {
        Write-Warning "Could not retrieve image information"
    }
    
    Write-Host "========================================================================" -ForegroundColor Cyan
}

# Main execution
try {
    Test-Prerequisites
    Set-VariantEnvironment
    
    if ($ValidateOnly) {
        Test-Configuration
        Write-Host "✓ Validation completed successfully" -ForegroundColor Green
        exit 0
    }
    
    Test-Configuration
    Invoke-Phase2Phase4Build
    Test-Phase2Phase4Integration
    Push-ToRegistry
    Show-BuildSummary
    
    Write-Host "✓ Phase 2 + Phase 4 production build completed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Build failed: $_" -ForegroundColor Red
    exit 1
}
