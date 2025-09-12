# GameForge Production Phase 4 - Model Security Validation Script
# This PowerShell script provides comprehensive validation for Phase 4 model security implementation

[CmdletBinding()]
param(
    [Parameter()]
    [string]$ImageName = "gameforge-ai-phase4",
    
    [Parameter()]
    [string]$ContainerName = "gameforge-phase4-test",
    
    [Parameter()]
    [switch]$SkipImageBuild,
    
    [Parameter()]
    [switch]$VerboseOutput,
    
    [Parameter()]
    [string]$TestEnvironment = "development"
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
$Colors = @{
    Red = [System.ConsoleColor]::Red
    Green = [System.ConsoleColor]::Green
    Yellow = [System.ConsoleColor]::Yellow
    Blue = [System.ConsoleColor]::Blue
    Cyan = [System.ConsoleColor]::Cyan
    White = [System.ConsoleColor]::White
}

function Write-ColoredOutput {
    param(
        [string]$Message,
        [System.ConsoleColor]$Color = [System.ConsoleColor]::White
    )
    
    $previousColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Output $Message
    $Host.UI.RawUI.ForegroundColor = $previousColor
}

function Write-Header {
    param([string]$Title)
    
    Write-ColoredOutput "`n$('=' * 60)" -Color $Colors.Blue
    Write-ColoredOutput "🔍 $Title" -Color $Colors.Blue
    Write-ColoredOutput "$('=' * 60)" -Color $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColoredOutput "✅ $Message" -Color $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-ColoredOutput "⚠️  $Message" -Color $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-ColoredOutput "❌ $Message" -Color $Colors.Red
}

function Write-Info {
    param([string]$Message)
    Write-ColoredOutput "ℹ️  $Message" -Color $Colors.Cyan
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Header "Prerequisites Check"
    
    $checks = @()
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker is available: $($dockerVersion)"
        $checks += $true
    }
    catch {
        Write-Error "Docker is not available or not working"
        $checks += $false
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Success "Docker Compose is available: $($composeVersion)"
        $checks += $true
    }
    catch {
        Write-Error "Docker Compose is not available"
        $checks += $false
    }
    
    # Check required files
    $requiredFiles = @(
        "Dockerfile.production.enhanced",
        "docker-compose.phase4.yml",
        "scripts\model-manager.sh",
        "scripts\entrypoint-phase4.sh"
    )
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "Required file exists: $file"
            $checks += $true
        }
        else {
            Write-Error "Missing required file: $file"
            $checks += $false
        }
    }
    
    return ($checks | Where-Object { -not $_ }).Count -eq 0
}

# Function to validate Phase 4 Dockerfile
function Test-DockerfilePhase4 {
    Write-Header "Phase 4 Dockerfile Validation"
    
    $dockerfilePath = "Dockerfile.production.enhanced"
    $dockerfileContent = Get-Content $dockerfilePath -Raw
    
    $validations = @()
    
    # Check multi-stage build structure
    $stagePattern = 'FROM .+ AS .+'
    $stages = [regex]::Matches($dockerfileContent, $stagePattern)
    if ($stages.Count -ge 5) {
        Write-Success "Multi-stage build detected: $($stages.Count) stages"
        $validations += $true
    }
    else {
        Write-Error "Insufficient build stages: $($stages.Count) (expected >= 5)"
        $validations += $false
    }
    
    # Check that no model files are being copied
    $modelExtensions = @('*.safetensors', '*.bin', '*.pt', '*.pth', '*.ckpt', '*.pkl', '*.h5', '*.onnx')
    $modelCopyFound = $false
    
    foreach ($ext in $modelExtensions) {
        if ($dockerfileContent -match "COPY.*$ext") {
            Write-Error "Model file copy detected: $ext - violates Phase 4 security"
            $modelCopyFound = $true
        }
    }
    
    if (-not $modelCopyFound) {
        Write-Success "No model files copied into image - Phase 4 compliant"
        $validations += $true
    }
    else {
        $validations += $false
    }
    
    # Check for security best practices
    $securityChecks = @{
        "Non-root user" = "USER \w+"
        "Security scanner" = "(RUN.*trivy|RUN.*syft)"
        "Minimal base image" = "FROM.*distroless|FROM.*alpine"
        "Health check" = "HEALTHCHECK"
    }
    
    foreach ($check in $securityChecks.GetEnumerator()) {
        if ($dockerfileContent -match $check.Value) {
            Write-Success "$($check.Key) implemented"
            $validations += $true
        }
        else {
            Write-Warning "$($check.Key) not detected"
            $validations += $false
        }
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

# Function to build and test Phase 4 image
function Test-ImageBuild {
    Write-Header "Phase 4 Image Build Test"
    
    if ($SkipImageBuild) {
        Write-Info "Skipping image build as requested"
        return $true
    }
    
    try {
        Write-Info "Building Phase 4 image..."
        $buildResult = docker build -f Dockerfile.production.enhanced -t $ImageName . 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Image build completed successfully"
            
            # Analyze image
            Write-Info "Analyzing built image..."
            $imageInfo = docker inspect $ImageName | ConvertFrom-Json
            $imageSize = $imageInfo[0].Size
            $imageSizeGB = [math]::Round($imageSize / 1GB, 2)
            
            Write-Info "Image size: $imageSizeGB GB"
            
            if ($imageSizeGB -lt 5) {
                Write-Success "Image size is reasonable: $imageSizeGB GB"
                return $true
            }
            else {
                Write-Warning "Image size is large: $imageSizeGB GB"
                return $true
            }
        }
        else {
            Write-Error "Image build failed"
            if ($VerboseOutput) {
                Write-Output $buildResult
            }
            return $false
        }
    }
    catch {
        Write-Error "Error during image build: $($_.Exception.Message)"
        return $false
    }
}

# Function to scan image for baked models
function Test-BakedModels {
    Write-Header "Baked Models Security Scan"
    
    try {
        Write-Info "Scanning image for baked model files..."
        
        # Create temporary container to scan filesystem
        $containerId = docker create $ImageName
        
        # Model file extensions to check
        $modelExtensions = @('*.safetensors', '*.bin', '*.pt', '*.pth', '*.ckpt', '*.pkl', '*.h5', '*.onnx')
        $modelFiles = @()
        
        foreach ($ext in $modelExtensions) {
            try {
                $findResult = docker run --rm $ImageName find /app -name $ext -type f 2>/dev/null
                if ($findResult) {
                    $modelFiles += $findResult
                }
            }
            catch {
                # Ignore errors from find command
            }
        }
        
        # Clean up container
        docker rm $containerId | Out-Null
        
        if ($modelFiles.Count -eq 0) {
            Write-Success "No baked model files found - Phase 4 security compliant"
            return $true
        }
        else {
            Write-Error "Found $($modelFiles.Count) baked model files:"
            foreach ($file in $modelFiles) {
                Write-Error "  - $file"
            }
            return $false
        }
    }
    catch {
        Write-Error "Error during model scan: $($_.Exception.Message)"
        return $false
    }
}

# Function to test model management script
function Test-ModelManager {
    Write-Header "Model Manager Script Validation"
    
    $scriptPath = "scripts\model-manager.sh"
    
    if (-not (Test-Path $scriptPath)) {
        Write-Error "Model manager script not found: $scriptPath"
        return $false
    }
    
    $scriptContent = Get-Content $scriptPath -Raw
    $validations = @()
    
    # Check for required functions
    $requiredFunctions = @(
        'authenticate_vault',
        'get_model_credentials',
        'download_model',
        'cleanup_old_sessions'
    )
    
    foreach ($func in $requiredFunctions) {
        if ($scriptContent -match "$func\(\)") {
            Write-Success "Function implemented: $func"
            $validations += $true
        }
        else {
            Write-Error "Missing function: $func"
            $validations += $false
        }
    }
    
    # Check for security features
    $securityFeatures = @{
        'Vault authentication' = 'VAULT_TOKEN|authenticate_vault'
        'Checksum verification' = 'sha256sum|checksum'
        'Encryption support' = 'openssl|encryption'
        'Secure cleanup' = 'shred|secure.*cleanup'
    }
    
    foreach ($feature in $securityFeatures.GetEnumerator()) {
        if ($scriptContent -match $feature.Value) {
            Write-Success "Security feature: $($feature.Key)"
            $validations += $true
        }
        else {
            Write-Warning "Security feature not detected: $($feature.Key)"
            $validations += $false
        }
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

# Function to test enhanced entrypoint
function Test-EnhancedEntrypoint {
    Write-Header "Enhanced Entrypoint Validation"
    
    $entrypointPath = "scripts\entrypoint-phase4.sh"
    
    if (-not (Test-Path $entrypointPath)) {
        Write-Error "Enhanced entrypoint script not found: $entrypointPath"
        return $false
    }
    
    $entrypointContent = Get-Content $entrypointPath -Raw
    $validations = @()
    
    # Check for required validation functions
    $requiredChecks = @(
        'check_system_health',
        'check_vault_health',
        'perform_security_scan',
        'validate_model_security'
    )
    
    foreach ($check in $requiredChecks) {
        if ($entrypointContent -match "$check\(\)") {
            Write-Success "Validation check implemented: $check"
            $validations += $true
        }
        else {
            Write-Error "Missing validation check: $check"
            $validations += $false
        }
    }
    
    # Check for monitoring and signal handling
    $advancedFeatures = @{
        'Signal handling' = 'trap.*shutdown_handler'
        'Performance monitoring' = 'setup_monitoring'
        'Resource checks' = 'free -m|df.*tmp'
        'GPU monitoring' = 'nvidia-smi'
    }
    
    foreach ($feature in $advancedFeatures.GetEnumerator()) {
        if ($entrypointContent -match $feature.Value) {
            Write-Success "Advanced feature: $($feature.Key)"
            $validations += $true
        }
        else {
            Write-Warning "Advanced feature not detected: $($feature.Key)"
            $validations += $false
        }
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

# Function to test container runtime
function Test-ContainerRuntime {
    Write-Header "Container Runtime Test"
    
    try {
        Write-Info "Starting Phase 4 container test..."
        
        # Set test environment variables
        $env:GAMEFORGE_ENV = $TestEnvironment
        $env:MODEL_SECURITY_ENABLED = "true"
        $env:VAULT_HEALTH_CHECK_ENABLED = "false"  # Skip Vault for local testing
        $env:STRICT_MODEL_SECURITY = "true"
        
        # Run container with test command
        $testCommand = "echo 'Phase 4 container test completed'"
        $runResult = docker run --rm --name "$ContainerName-test" `
            -e GAMEFORGE_ENV=$env:GAMEFORGE_ENV `
            -e MODEL_SECURITY_ENABLED=$env:MODEL_SECURITY_ENABLED `
            -e VAULT_HEALTH_CHECK_ENABLED=$env:VAULT_HEALTH_CHECK_ENABLED `
            -e STRICT_MODEL_SECURITY=$env:STRICT_MODEL_SECURITY `
            $ImageName /bin/bash -c $testCommand 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Container runtime test passed"
            if ($VerboseOutput) {
                Write-Output $runResult
            }
            return $true
        }
        else {
            Write-Error "Container runtime test failed"
            Write-Output $runResult
            return $false
        }
    }
    catch {
        Write-Error "Error during container runtime test: $($_.Exception.Message)"
        return $false
    }
}

# Function to generate validation report
function New-ValidationReport {
    param(
        [hashtable]$Results
    )
    
    Write-Header "Phase 4 Validation Report"
    
    $totalTests = $Results.Count
    $passedTests = ($Results.Values | Where-Object { $_ -eq $true }).Count
    $successRate = [math]::Round(($passedTests / $totalTests) * 100, 1)
    
    Write-Info "Total tests: $totalTests"
    Write-Info "Passed tests: $passedTests"
    Write-Info "Success rate: $successRate%"
    
    Write-Output "`nDetailed Results:"
    foreach ($test in $Results.GetEnumerator()) {
        $status = if ($test.Value) { "✅ PASS" } else { "❌ FAIL" }
        $color = if ($test.Value) { $Colors.Green } else { $Colors.Red }
        Write-ColoredOutput "  $status - $($test.Key)" -Color $color
    }
    
    # Overall assessment
    if ($successRate -ge 90) {
        Write-Success "`nPhase 4 implementation is ready for production deployment"
    }
    elseif ($successRate -ge 75) {
        Write-Warning "`nPhase 4 implementation has minor issues - review failed tests"
    }
    else {
        Write-Error "`nPhase 4 implementation has significant issues - requires fixes"
    }
    
    return $successRate -ge 75
}

# Main execution
function Main {
    Write-ColoredOutput @"
🔐 GameForge Production Phase 4 - Model Security Validation
============================================================
Testing Environment: $TestEnvironment
Image Name: $ImageName
Container Name: $ContainerName
Verbose Output: $VerboseOutput
Skip Build: $SkipImageBuild
"@ -Color $Colors.Blue
    
    $results = @{}
    
    # Run all validation tests
    Write-Info "Starting comprehensive Phase 4 validation..."
    
    $results["Prerequisites"] = Test-Prerequisites
    $results["Dockerfile Phase 4"] = Test-DockerfilePhase4
    $results["Image Build"] = Test-ImageBuild
    $results["Baked Models Scan"] = Test-BakedModels
    $results["Model Manager"] = Test-ModelManager
    $results["Enhanced Entrypoint"] = Test-EnhancedEntrypoint
    $results["Container Runtime"] = Test-ContainerRuntime
    
    # Generate report
    $validationPassed = New-ValidationReport -Results $results
    
    if ($validationPassed) {
        Write-Success "`n🎉 Phase 4 validation completed successfully!"
        exit 0
    }
    else {
        Write-Error "`n❌ Phase 4 validation failed - review issues above"
        exit 1
    }
}

# Execute main function
Main
