# GameForge Vast.ai Local Test Script
# ========================================================================
# Test Vast.ai configuration locally before deployment
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("build", "test", "validate", "clean")]
    [string]$Action = "test",
    
    [Parameter(Mandatory=$false)]
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"
$VerbosePreference = if ($VerboseOutput) { "Continue" } else { "SilentlyContinue" }

function Write-ColorOutput($Message, $Color = "White") {
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success($Message) { Write-ColorOutput "✓ $Message" "Green" }
function Write-Warning($Message) { Write-ColorOutput "⚠ $Message" "Yellow" }
function Write-Error($Message) { Write-ColorOutput "✗ $Message" "Red" }
function Write-Info($Message) { Write-ColorOutput "ℹ $Message" "Cyan" }

Write-ColorOutput @"
========================================================================
GameForge Vast.ai Local Test
========================================================================
Action: $Action
========================================================================
"@ "Magenta"

function Test-Prerequisites {
    Write-Info "Checking prerequisites for Vast.ai deployment..."
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker found: $dockerVersion"
    }
    catch {
        Write-Error "Docker not found. Please install Docker Desktop."
        return $false
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker compose version
        Write-Success "Docker Compose found: $composeVersion"
    }
    catch {
        Write-Error "Docker Compose not found"
        return $false
    }
    
    # Check required files
    $requiredFiles = @(
        "docker-compose.vastai.yml",
        "Dockerfile.vastai-gpu",
        "requirements-vastai.txt",
        ".env.vastai"
    )
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "Found required file: $file"
        } else {
            Write-Error "Missing required file: $file"
            return $false
        }
    }
    
    return $true
}

function Build-VastaiImages {
    Write-Info "Building Vast.ai Docker images locally..."
    
    try {
        # Set environment variables
        $env:BUILD_DATE = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
        $env:VCS_REF = try { git rev-parse HEAD } catch { "unknown" }
        $env:BUILD_VERSION = try { git describe --tags --always } catch { "dev" }
        $env:VASTAI_CUDA_VERSION = "12.1"
        $env:VASTAI_PYTORCH_VERSION = "2.1.0"
        
        Write-Info "Building vastai-inference image..."
        docker compose -f docker-compose.vastai.yml build vastai-gpu-inference
        Write-Success "vastai-inference image built successfully"
        
        Write-Info "Building vastai-training image..."
        docker compose -f docker-compose.vastai.yml build vastai-gpu-training
        Write-Success "vastai-training image built successfully"
        
        Write-Info "Building vastai-app image..."
        docker compose -f docker-compose.vastai.yml build vastai-gameforge-app
        Write-Success "vastai-app image built successfully"
        
        return $true
    }
    catch {
        Write-Error "Failed to build images: $_"
        return $false
    }
}

function Test-VastaiConfiguration {
    Write-Info "Testing Vast.ai configuration locally..."
    
    try {
        # Test docker-compose configuration
        Write-Info "Validating docker-compose.vastai.yml..."
        docker compose -f docker-compose.vastai.yml config > $null
        Write-Success "Docker Compose configuration is valid"
        
        # Test environment variables
        Write-Info "Testing environment variables..."
        if (Test-Path ".env.vastai") {
            $envContent = Get-Content ".env.vastai"
            Write-Success "Environment file loaded: $($envContent.Count) variables"
        }
        
        # Test Dockerfile syntax
        Write-Info "Validating Dockerfile.vastai-gpu..."
        if (Test-Path "Dockerfile.vastai-gpu") {
            Write-Success "Dockerfile found and readable"
        }
        
        # Test requirements file
        Write-Info "Validating requirements-vastai.txt..."
        if (Test-Path "requirements-vastai.txt") {
            $requirements = Get-Content "requirements-vastai.txt" | Where-Object { $_ -notmatch "^#" -and $_ -ne "" }
            Write-Success "Requirements file contains $($requirements.Count) packages"
        }
        
        return $true
    }
    catch {
        Write-Error "Configuration test failed: $_"
        return $false
    }
}

function Test-LocalDeployment {
    Write-Info "Testing local deployment (CPU-only simulation)..."
    
    try {
        # Create CPU-only version for testing
        Write-Info "Creating CPU-only test environment..."
        
        # Start only essential services for testing
        $testServices = @(
            "vastai-postgres",
            "vastai-redis", 
            "vastai-grafana"
        )
        
        Write-Info "Starting test services..."
        foreach ($service in $testServices) {
            Write-Verbose "Starting service: $service"
            docker compose -f docker-compose.vastai.yml up -d $service
        }
        
        # Wait for services to start
        Start-Sleep -Seconds 30
        
        # Check service health
        Write-Info "Checking service health..."
        $status = docker compose -f docker-compose.vastai.yml ps --format json | ConvertFrom-Json
        
        foreach ($service in $status) {
            $serviceName = $service.Service
            $state = $service.State
            
            if ($state -eq "running") {
                Write-Success "Service $serviceName is running"
            } else {
                Write-Warning "Service $serviceName is not running: $state"
            }
        }
        
        # Test database connection
        Write-Info "Testing database connection..."
        $dbTest = docker compose -f docker-compose.vastai.yml exec -T vastai-postgres pg_isready -U gameforge -d gameforge_vastai
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database connection successful"
        } else {
            Write-Warning "Database connection failed"
        }
        
        # Test Redis connection
        Write-Info "Testing Redis connection..."
        $redisTest = docker compose -f docker-compose.vastai.yml exec -T vastai-redis redis-cli ping
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Redis connection successful"
        } else {
            Write-Warning "Redis connection failed"
        }
        
        Write-Success "Local test deployment completed"
        
        Write-Info @"

========================================================================
Local Test Results
========================================================================
Database: http://localhost:5432
Redis: http://localhost:6379
Grafana: http://localhost:3000

To stop test services:
docker compose -f docker-compose.vastai.yml down
========================================================================
"@
        
        return $true
    }
    catch {
        Write-Error "Local deployment test failed: $_"
        return $false
    }
}

function Stop-TestServices {
    Write-Info "Stopping test services..."
    
    try {
        docker compose -f docker-compose.vastai.yml down
        Write-Success "Test services stopped"
        
        # Clean up test volumes if requested
        $cleanup = Read-Host "Remove test volumes? (y/N)"
        if ($cleanup -eq "y" -or $cleanup -eq "Y") {
            docker compose -f docker-compose.vastai.yml down -v
            Write-Success "Test volumes removed"
        }
        
        return $true
    }
    catch {
        Write-Error "Failed to stop test services: $_"
        return $false
    }
}

function Validate-VastaiReadiness {
    Write-Info "Validating Vast.ai deployment readiness..."
    
    $checks = @()
    
    # Check 1: All required files present
    $requiredFiles = @(
        "docker-compose.vastai.yml",
        "Dockerfile.vastai-gpu", 
        "requirements-vastai.txt",
        ".env.vastai",
        "deploy-vastai.ps1"
    )
    
    $filesOK = $true
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            $checks += "OK File: $file"
        } else {
            $checks += "MISSING: $file"
            $filesOK = $false
        }
    }
    
    # Check 2: Docker configuration valid
    try {
        docker compose -f docker-compose.vastai.yml config > $null
        $checks += "OK Docker Compose configuration valid"
        $configOK = $true
    }
    catch {
        $checks += "ERROR Docker Compose configuration invalid"
        $configOK = $false
    }
    
    # Check 3: Environment variables set
    if (Test-Path ".env.vastai") {
        $envVars = Get-Content ".env.vastai" | Where-Object { $_ -match "=" }
        $checks += "OK Environment file: $($envVars.Count) variables"
        $envOK = $true
    } else {
        $checks += "ERROR Environment file missing"
        $envOK = $false
    }
    
    # Display results
    Write-Info "Validation Results:"
    foreach ($check in $checks) {
        if ($check.StartsWith("OK")) {
            Write-Success $check
        } else {
            Write-Error $check
        }
    }
    
    $allOK = $filesOK -and $configOK -and $envOK
    
    if ($allOK) {
        Write-Success @"

========================================================================
🎉 Vast.ai Deployment Ready!
========================================================================
All checks passed. You can now deploy to Vast.ai using:

.\deploy-vastai.ps1 -Action deploy -VastaiInstanceType rtx4090 -MaxPrice 50

This will:
1. Search for available RTX 4090 instances under 50 cents/hour
2. Create and deploy GameForge with GPU support
3. Provide access URLs for your services
========================================================================
"@
    } else {
        Write-Error @"

========================================================================
❌ Vast.ai Deployment Not Ready
========================================================================
Please fix the issues above before deploying to Vast.ai.
Run: .\test-vastai.ps1 -Action validate
========================================================================
"@
    }
    
    return $allOK
}

# Main execution
try {
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    switch ($Action.ToLower()) {
        "build" {
            if (Build-VastaiImages) {
                Write-Success "Build completed successfully!"
            } else {
                Write-Error "Build failed!"
                exit 1
            }
        }
        "test" {
            if (Test-VastaiConfiguration -and Test-LocalDeployment) {
                Write-Success "Test completed successfully!"
            } else {
                Write-Error "Test failed!"
                exit 1
            }
        }
        "validate" {
            if (Validate-VastaiReadiness) {
                Write-Success "Validation passed!"
            } else {
                Write-Error "Validation failed!"
                exit 1
            }
        }
        "clean" {
            if (Stop-TestServices) {
                Write-Success "Cleanup completed!"
            } else {
                Write-Error "Cleanup failed!"
                exit 1
            }
        }
        default {
            Write-Error "Unknown action: $Action"
            exit 1
        }
    }
}
catch {
    Write-Error "Test failed: $($_.Exception.Message)"
    exit 1
}
