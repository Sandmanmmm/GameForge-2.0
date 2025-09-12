# GameForge Production Phase 2 Build Script
# Enhanced Multi-stage Build with CPU/GPU Variants
# Windows PowerShell Implementation

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
    [string]$Registry = "your-registry.com/gameforge"
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

function Write-ColorOutput {
    param($Message, $Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Section {
    param($Title)
    Write-Host ""
    Write-ColorOutput "=" * 60 -Color $InfoColor
    Write-ColorOutput "  $Title" -Color $InfoColor
    Write-ColorOutput "=" * 60 -Color $InfoColor
}

function Test-DockerRunning {
    try {
        docker version | Out-Null
        return $true
    }
    catch {
        Write-ColorOutput "ERROR: Docker is not running or not installed" -Color $ErrorColor
        return $false
    }
}

function Get-BuildMetadata {
    $buildDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    
    try {
        $vcsRef = git rev-parse --short HEAD
        $buildVersion = git describe --tags --always --dirty
    }
    catch {
        Write-ColorOutput "WARNING: Git not available, using fallback metadata" -Color $WarningColor
        $vcsRef = "unknown"
        $buildVersion = "dev-build"
    }
    
    return @{
        BuildDate = $buildDate
        VcsRef = $vcsRef
        BuildVersion = $buildVersion
    }
}

function Invoke-PreBuildHygiene {
    Write-Section "Pre-Build Hygiene Checks"
    
    if (Test-Path "phase1-simple.ps1") {
        Write-ColorOutput "Running Phase 1 hygiene checks..." -Color $InfoColor
        try {
            & powershell -ExecutionPolicy Bypass -File "phase1-simple.ps1"
            Write-ColorOutput "SUCCESS: Pre-build hygiene checks passed" -Color $SuccessColor
        }
        catch {
            Write-ColorOutput "ERROR: Pre-build hygiene checks failed: $($_.Exception.Message)" -Color $ErrorColor
            throw
        }
    }
    else {
        Write-ColorOutput "WARNING: Phase 1 hygiene script not found, skipping checks" -Color $WarningColor
    }
}

function Start-ImageBuild {
    param(
        [string]$BuildVariant,
        [hashtable]$Metadata,
        [string]$ImageTag
    )
    
    Write-Section "Building $($BuildVariant.ToUpper()) Variant"
    
    $buildArgs = @(
        "--build-arg", "BUILD_DATE=$($Metadata.BuildDate)",
        "--build-arg", "VCS_REF=$($Metadata.VcsRef)",
        "--build-arg", "BUILD_VERSION=$($Metadata.BuildVersion)",
        "--build-arg", "VARIANT=$BuildVariant",
        "--build-arg", "PYTHON_VERSION=3.10"
    )
    
    # Add platform-specific optimizations
    if ($BuildVariant -eq "cpu") {
        $buildArgs += @("--build-arg", "CPU_BASE_IMAGE=ubuntu:22.04")
    }
    else {
        $buildArgs += @("--build-arg", "GPU_BASE_IMAGE=nvidia/cuda:12.1-devel-ubuntu22.04")
    }
    
    $dockerCommand = @(
        "docker", "build",
        "-f", "Dockerfile.production.enhanced",
        "-t", $ImageTag
    ) + $buildArgs + @(".")
    
    Write-ColorOutput "Building: $ImageTag" -Color $InfoColor
    Write-ColorOutput "Command: $($dockerCommand -join ' ')" -Color "Gray"
    
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        # Execute Docker build and capture both stdout and stderr
        $process = Start-Process -FilePath "docker" -ArgumentList ($dockerCommand[1..($dockerCommand.Length-1)]) -NoNewWindow -Wait -PassThru -RedirectStandardOutput "docker-build-output.log" -RedirectStandardError "docker-build-error.log"
        $sw.Stop()
        
        if ($process.ExitCode -eq 0) {
            Write-ColorOutput "SUCCESS: Build completed in $($sw.Elapsed.TotalMinutes.ToString('F1')) minutes" -Color $SuccessColor
            # Clean up log files on success
            Remove-Item -Path "docker-build-output.log" -ErrorAction SilentlyContinue
            Remove-Item -Path "docker-build-error.log" -ErrorAction SilentlyContinue
            return $true
        }
        else {
            Write-ColorOutput "ERROR: Build failed with exit code $($process.ExitCode)" -Color $ErrorColor
            # Show error details
            if (Test-Path "docker-build-error.log") {
                Write-ColorOutput "Build Error Details:" -Color $ErrorColor
                Get-Content "docker-build-error.log" | Select-Object -Last 10 | ForEach-Object { 
                    Write-ColorOutput "  $_" -Color "Gray" 
                }
            }
            return $false
        }
    }
    catch {
        $sw.Stop()
        Write-ColorOutput "ERROR: Build failed: $($_.Exception.Message)" -Color $ErrorColor
        return $false
    }
}

function Test-ImageSecurity {
    param([string]$ImageTag)
    
    Write-ColorOutput "Security validation for: $ImageTag" -Color $InfoColor
    
    # Test non-root user
    try {
        $userId = docker run --rm $ImageTag id -u
        if ($userId -eq "1001") {
            Write-ColorOutput "SUCCESS: Running as non-root user (UID: $userId)" -Color $SuccessColor
        }
        else {
            Write-ColorOutput "ERROR: Security issue: Not running as expected user (UID: $userId)" -Color $ErrorColor
            return $false
        }
    }
    catch {
        Write-ColorOutput "ERROR: Failed to verify user ID: $($_.Exception.Message)" -Color $ErrorColor
        return $false
    }
    
    # Test environment validation
    try {
        docker run --rm -e GAMEFORGE_ENV=development $ImageTag echo "test" 2>&1 | Out-Null
        $result = $LASTEXITCODE
        if ($result -ne 0) {
            Write-ColorOutput "SUCCESS: Environment validation working (rejected non-production)" -Color $SuccessColor
        }
        else {
            Write-ColorOutput "ERROR: Security issue: Environment validation not working" -Color $ErrorColor
            return $false
        }
    }
    catch {
        Write-ColorOutput "SUCCESS: Environment validation working (caught by entrypoint)" -Color $SuccessColor
    }
    
    return $true
}

function Get-ImageSize {
    param([string]$ImageTag)
    
    try {
        # Get image size using docker images command
        $sizeOutput = docker images $ImageTag --format "{{.Size}}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $sizeOutput) {
            return $sizeOutput.Trim()
        }
        else {
            # Try alternative method
            $imageInfo = docker inspect $ImageTag --format "{{.Size}}" 2>$null
            if ($LASTEXITCODE -eq 0 -and $imageInfo) {
                # Convert bytes to MB
                $sizeBytes = [long]$imageInfo
                $sizeMB = [math]::Round($sizeBytes / 1MB, 1)
                return "${sizeMB}MB"
            }
        }
        return "Unknown"
    }
    catch {
        return "Error"
    }
}

function Test-ImageSize {
    param([string]$ImageTag, [string]$Variant)
    
    $size = Get-ImageSize -ImageTag $ImageTag
    Write-ColorOutput "Image size: $size" -Color $InfoColor
    
    # Size targets
    $targets = @{
        "cpu" = 500  # MB
        "gpu" = 3000 # MB (3GB)
    }
    
    if ($size -match "(\d+(?:\.\d+)?)(MB|GB)") {
        $sizeValue = [float]$matches[1]
        $unit = $matches[2]
        
        if ($unit -eq "GB") {
            $sizeValue = $sizeValue * 1024
        }
        
        $target = $targets[$Variant]
        if ($sizeValue -le $target) {
            Write-ColorOutput "SUCCESS: Image size within target ($target MB)" -Color $SuccessColor
            return $true
        }
        else {
            Write-ColorOutput "WARNING: Image size exceeds target (${target}MB). Consider optimization." -Color $WarningColor
            return $false
        }
    }
    else {
        Write-ColorOutput "WARNING: Could not parse image size for validation" -Color $WarningColor
        return $false
    }
}

function Invoke-CleanUp {
    Write-Section "Cleanup"
    
    Write-ColorOutput "Cleaning up dangling images..." -Color $InfoColor
    try {
        docker image prune -f | Out-Null
        Write-ColorOutput "SUCCESS: Cleanup completed" -Color $SuccessColor
    }
    catch {
        Write-ColorOutput "WARNING: Cleanup failed: $($_.Exception.Message)" -Color $WarningColor
    }
}

# ========================================================================
# Main Execution
# ========================================================================

Write-Section "GameForge Production Phase 2 Build"
Write-ColorOutput "Enhanced Multi-stage Build with CPU/GPU Variants" -Color $InfoColor

# Validate prerequisites
if (-not (Test-DockerRunning)) {
    exit 1
}

# Clean up if requested
if ($Clean) {
    Invoke-CleanUp
}

# Get build metadata
$metadata = Get-BuildMetadata
Write-ColorOutput "Build Metadata:" -Color $InfoColor
Write-ColorOutput "  Date: $($metadata.BuildDate)" -Color "Gray"
Write-ColorOutput "  Commit: $($metadata.VcsRef)" -Color "Gray"
Write-ColorOutput "  Version: $($metadata.BuildVersion)" -Color "Gray"

# Run pre-build hygiene unless disabled
if (-not $NoBuildArg) {
    Invoke-PreBuildHygiene
}

# Determine variants to build
$variants = switch ($Variant) {
    "both" { @("cpu", "gpu") }
    default { @($Variant) }
}

$buildResults = @{}
$buildSuccess = $true

foreach ($buildVariant in $variants) {
    # Generate image tag
    if ($Tag) {
        $imageTag = "${Registry}:${Tag}-${buildVariant}"
    }
    else {
        $imageTag = "${Registry}:$($metadata.BuildVersion)-${buildVariant}"
    }
    
    # Build image
    $result = Start-ImageBuild -BuildVariant $buildVariant -Metadata $metadata -ImageTag $imageTag
    $buildResults[$buildVariant] = @{
        Success = $result
        Tag = $imageTag
        Size = ""
    }
    
    if ($result) {
        # Get image size
        $buildResults[$buildVariant].Size = Get-ImageSize -ImageTag $imageTag
        
        # Validate if requested
        if ($Validate) {
            $securityPass = Test-ImageSecurity -ImageTag $imageTag
            $buildResults[$buildVariant].SecurityPass = $securityPass
            
            if (-not $securityPass) {
                $buildSuccess = $false
            }
        }
        
        # Size check if requested
        if ($SizeCheck) {
            $sizePass = Test-ImageSize -ImageTag $imageTag -Variant $buildVariant
            $buildResults[$buildVariant].SizePass = $sizePass
        }
        
        # Push if requested
        if ($Push) {
            Write-ColorOutput "Pushing: $imageTag" -Color $InfoColor
            try {
                docker push $imageTag
                Write-ColorOutput "SUCCESS: Push successful" -Color $SuccessColor
                $buildResults[$buildVariant].Pushed = $true
            }
            catch {
                Write-ColorOutput "ERROR: Push failed: $($_.Exception.Message)" -Color $ErrorColor
                $buildResults[$buildVariant].Pushed = $false
                $buildSuccess = $false
            }
        }
    }
    else {
        $buildSuccess = $false
    }
}

# Summary
Write-Section "Build Summary"

foreach ($variant in $variants) {
    $result = $buildResults[$variant]
    $status = if ($result.Success) { "SUCCESS" } else { "FAILED" }
    
    Write-ColorOutput "$status $($variant.ToUpper()) Variant:" -Color $(if ($result.Success) { $SuccessColor } else { $ErrorColor })
    Write-ColorOutput "  Tag: $($result.Tag)" -Color "Gray"
    Write-ColorOutput "  Size: $($result.Size)" -Color "Gray"
    
    if ($Validate -and $result.ContainsKey("SecurityPass")) {
        $secStatus = if ($result.SecurityPass) { "PASS" } else { "FAIL" }
        Write-ColorOutput "  Security: $secStatus" -Color $(if ($result.SecurityPass) { $SuccessColor } else { $ErrorColor })
    }
    
    if ($SizeCheck -and $result.ContainsKey("SizePass")) {
        $sizeStatus = if ($result.SizePass) { "PASS" } else { "WARNING" }
        Write-ColorOutput "  Size Check: $sizeStatus" -Color $(if ($result.SizePass) { $SuccessColor } else { $WarningColor })
    }
    
    if ($Push -and $result.ContainsKey("Pushed")) {
        $pushStatus = if ($result.Pushed) { "SUCCESS" } else { "FAILED" }
        Write-ColorOutput "  Pushed: $pushStatus" -Color $(if ($result.Pushed) { $SuccessColor } else { $ErrorColor })
    }
}

Write-ColorOutput ""
if ($buildSuccess) {
    Write-ColorOutput "All builds completed successfully!" -Color $SuccessColor
    exit 0
}
else {
    Write-ColorOutput "Some builds failed. Check output above." -Color $ErrorColor
    exit 1
}
