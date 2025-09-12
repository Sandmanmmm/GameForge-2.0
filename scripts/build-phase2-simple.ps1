# GameForge Production Phase 2 Build Script - Simplified
# Enhanced Multi-stage Build with CPU/GPU Variants

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("cpu", "gpu", "both")]
    [string]$Variant = "gpu",
    
    [Parameter(Mandatory=$false)]
    [string]$Tag = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$Push,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoBuildArg,
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean,
    
    [Parameter(Mandatory=$false)]
    [switch]$Validate,
    
    [Parameter(Mandatory=$false)]
    [switch]$SizeCheck,
    
    [Parameter(Mandatory=$false)]
    [string]$Registry = "gameforge"
)

Write-Host "GameForge Production Phase 2 Build" -ForegroundColor Cyan
Write-Host "Enhanced Multi-stage Build with CPU/GPU Variants" -ForegroundColor Cyan
Write-Host ""

# Test Docker
try {
    docker version | Out-Null
    Write-Host "Docker: Available" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Docker not available" -ForegroundColor Red
    exit 1
}

# Get simple metadata
$buildDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$vcsRef = "latest"
$buildVersion = "test-build"

try {
    $vcsRef = git rev-parse --short HEAD 2>$null
    $buildVersion = git describe --tags --always 2>$null
    if (-not $buildVersion) { $buildVersion = $vcsRef }
}
catch {
    Write-Host "Git not available, using defaults" -ForegroundColor Yellow
}

Write-Host "Build Info:" -ForegroundColor White
Write-Host "  Date: $buildDate" -ForegroundColor Gray
Write-Host "  Commit: $vcsRef" -ForegroundColor Gray
Write-Host "  Version: $buildVersion" -ForegroundColor Gray
Write-Host ""

# Clean if requested
if ($Clean) {
    Write-Host "Cleaning up..." -ForegroundColor Yellow
    docker image prune -f | Out-Null
}

# Build variants
$variants = if ($Variant -eq "both") { @("cpu", "gpu") } else { @($Variant) }
$buildSuccess = $true

foreach ($buildVariant in $variants) {
    Write-Host "Building $($buildVariant.ToUpper()) Variant" -ForegroundColor Cyan
    Write-Host "=" * 40 -ForegroundColor Cyan
    
    # Generate tag
    $imageTag = if ($Tag) { "${Registry}:${Tag}-${buildVariant}" } else { "${Registry}:${buildVersion}-${buildVariant}" }
    
    Write-Host "Image Tag: $imageTag" -ForegroundColor White
    
    # Build arguments
    $buildArgs = @(
        "--build-arg", "BUILD_DATE=$buildDate",
        "--build-arg", "VCS_REF=$vcsRef", 
        "--build-arg", "BUILD_VERSION=$buildVersion",
        "--build-arg", "VARIANT=$buildVariant",
        "--build-arg", "PYTHON_VERSION=3.10"
    )
    
    # Variant-specific args
    if ($buildVariant -eq "cpu") {
        $buildArgs += @("--build-arg", "CPU_BASE_IMAGE=ubuntu:22.04")
    } else {
        $buildArgs += @("--build-arg", "GPU_BASE_IMAGE=nvidia/cuda:12.1-devel-ubuntu22.04")
    }
    
    # Execute build
    $startTime = Get-Date
    Write-Host "Starting build..." -ForegroundColor White
    
    $process = Start-Process -FilePath "docker" -ArgumentList (@("build", "-f", "Dockerfile.production.enhanced", "-t", $imageTag) + $buildArgs + @(".")) -Wait -PassThru -NoNewWindow
    
    $duration = ((Get-Date) - $startTime).TotalMinutes
    
    if ($process.ExitCode -eq 0) {
        Write-Host "SUCCESS: Build completed in $([math]::Round($duration, 1)) minutes" -ForegroundColor Green
        
        # Get image size
        try {
            $size = docker images $imageTag --format "{{.Size}}" 2>$null
            if ($size) {
                Write-Host "Image Size: $size" -ForegroundColor White
            }
        }
        catch {
            Write-Host "Could not determine image size" -ForegroundColor Yellow
        }
        
        # Security validation if requested
        if ($Validate) {
            Write-Host "Running security validation..." -ForegroundColor Yellow
            try {
                $userId = docker run --rm $imageTag id -u 2>$null
                if ($userId -eq "1001") {
                    Write-Host "Security: Non-root user OK" -ForegroundColor Green
                } else {
                    Write-Host "Security: User check failed (UID: $userId)" -ForegroundColor Red
                    $buildSuccess = $false
                }
            }
            catch {
                Write-Host "Security: Validation failed" -ForegroundColor Red
                $buildSuccess = $false
            }
        }
        
        # Push if requested
        if ($Push) {
            Write-Host "Pushing image..." -ForegroundColor Yellow
            $pushProcess = Start-Process -FilePath "docker" -ArgumentList @("push", $imageTag) -Wait -PassThru -NoNewWindow
            if ($pushProcess.ExitCode -eq 0) {
                Write-Host "Push: SUCCESS" -ForegroundColor Green
            } else {
                Write-Host "Push: FAILED" -ForegroundColor Red
                $buildSuccess = $false
            }
        }
    }
    else {
        Write-Host "ERROR: Build failed (Exit Code: $($process.ExitCode))" -ForegroundColor Red
        $buildSuccess = $false
    }
    
    Write-Host ""
}

# Final result
if ($buildSuccess) {
    Write-Host "All builds completed successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some builds failed!" -ForegroundColor Red
    exit 1
}
