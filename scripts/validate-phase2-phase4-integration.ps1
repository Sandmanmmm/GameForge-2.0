#!/usr/bin/env pwsh
# ========================================================================
# Phase 2 + Phase 4 Integration Validation Script
# Validate Enhanced Multi-stage Dockerfile with CPU/GPU Variants + Model Asset Security
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpu", "cpu", "both")]
    [string]$Variant = "both",
    
    [Parameter(Mandatory=$false)]
    [switch]$QuickTest,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuildTests,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Blue
Write-Host "Phase 2 + Phase 4 Integration Validation" -ForegroundColor Blue
Write-Host "Testing variants: $Variant" -ForegroundColor Blue
Write-Host "========================================================================" -ForegroundColor Blue

$script:TestResults = @()
$script:TestsPassed = 0
$script:TestsFailed = 0

# Function to log test results
function Add-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = "",
        [string]$Details = ""
    )
    
    $result = @{
        TestName = $TestName
        Passed = $Passed
        Message = $Message
        Details = $Details
        Timestamp = Get-Date
    }
    
    $script:TestResults += $result
    
    if ($Passed) {
        $script:TestsPassed++
        Write-Host "[PASS] $TestName" -ForegroundColor Green
        if ($Message -and $Verbose) {
            Write-Host "  $Message" -ForegroundColor Gray
        }
    } else {
        $script:TestsFailed++
        Write-Host "[FAIL] $TestName" -ForegroundColor Red
        if ($Message) {
            Write-Host "  $Message" -ForegroundColor Red
        }
        if ($Details -and $Verbose) {
            Write-Host "  Details: $Details" -ForegroundColor DarkRed
        }
    }
}

# Function to test Phase 2 file structure
function Test-Phase2FileStructure {
    Write-Host "Testing Phase 2 file structure..." -ForegroundColor Yellow
    
    $requiredFiles = @(
        @{ Path = "Dockerfile.production.enhanced"; Description = "Enhanced multi-stage Dockerfile" },
        @{ Path = "docker-compose.production-hardened.yml"; Description = "Production compose configuration" },
        @{ Path = ".env.phase2"; Description = "Phase 2 environment configuration" },
        @{ Path = "build-phase2-phase4-integration.ps1"; Description = "Integration build script" },
        @{ Path = "deploy-phase2-phase4-production.ps1"; Description = "Production deployment script" }
    )
    
    foreach ($file in $requiredFiles) {
        $exists = Test-Path $file.Path
        Add-TestResult -TestName "File exists: $($file.Path)" -Passed $exists -Message $file.Description
    }
}

# Function to test Dockerfile structure
function Test-DockerfileStructure {
    Write-Host "Testing Dockerfile structure..." -ForegroundColor Yellow
    
    if (-not (Test-Path "Dockerfile.production.enhanced")) {
        Add-TestResult -TestName "Dockerfile structure test" -Passed $false -Message "Dockerfile not found"
        return
    }
    
    $dockerfileContent = Get-Content "Dockerfile.production.enhanced" -Raw
    
    # Test for multi-stage structure
    $stages = @("system-foundation", "build-deps", "python-builder", "app-builder", "production")
    foreach ($stage in $stages) {
        $hasStage = $dockerfileContent -match "FROM .+ AS $stage"
        Add-TestResult -TestName "Dockerfile stage: $stage" -Passed $hasStage -Message "Multi-stage build stage"
    }
    
    # Test for build arguments
    $buildArgs = @("VARIANT", "BUILD_VERSION", "VCS_REF", "ENABLE_GPU", "COMPILE_BYTECODE")
    foreach ($arg in $buildArgs) {
        $hasArg = $dockerfileContent -match "ARG $arg"
        Add-TestResult -TestName "Build argument: $arg" -Passed $hasArg -Message "Phase 2 build argument"
    }
    
    # Test for security hardening
    $securityFeatures = @("USER gameforge", "COPY --chown=", "chmod 644")
    foreach ($feature in $securityFeatures) {
        $hasFeature = $dockerfileContent -match [regex]::Escape($feature)
        Add-TestResult -TestName "Security feature: $feature" -Passed $hasFeature -Message "Security hardening"
    }
}

# Function to test Docker Compose configuration
function Test-DockerComposeConfiguration {
    Write-Host "Testing Docker Compose configuration..." -ForegroundColor Yellow
    
    try {
        # Test compose file syntax
        $configTest = docker compose -f docker-compose.production-hardened.yml config --quiet 2>&1
        $syntaxValid = $LASTEXITCODE -eq 0
        Add-TestResult -TestName "Docker Compose syntax" -Passed $syntaxValid -Message "Configuration syntax validation"
        
        if (-not $syntaxValid) {
            Add-TestResult -TestName "Compose config details" -Passed $false -Details $configTest
            return
        }
        
        # Test for Phase 2 + Phase 4 integration
        $composeContent = Get-Content "docker-compose.production-hardened.yml" -Raw
        
        $integrationFeatures = @(
            @{ Pattern = "GAMEFORGE_VARIANT"; Description = "Variant configuration" },
            @{ Pattern = "phase2-phase4-production"; Description = "Phase 2+4 image naming" },
            @{ Pattern = "ENABLE_GPU"; Description = "GPU enablement" },
            @{ Pattern = "DOCKER_RUNTIME"; Description = "Dynamic runtime" },
            @{ Pattern = "BUILD_VERSION"; Description = "Build versioning" },
            @{ Pattern = "VCS_REF"; Description = "VCS reference" }
        )
        
        foreach ($feature in $integrationFeatures) {
            $hasFeature = $composeContent -match [regex]::Escape($feature.Pattern)
            Add-TestResult -TestName "Compose feature: $($feature.Pattern)" -Passed $hasFeature -Message $feature.Description
        }
        
    } catch {
        Add-TestResult -TestName "Docker Compose test" -Passed $false -Message "Failed to test compose configuration" -Details $_.Exception.Message
    }
}

# Function to test build process
function Test-BuildProcess {
    if ($SkipBuildTests) {
        Write-Host "Skipping build tests as requested" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Testing build process..." -ForegroundColor Yellow
    
    $variantsToTest = switch ($Variant) {
        "gpu" { @("gpu") }
        "cpu" { @("cpu") }
        "both" { @("gpu", "cpu") }
    }
    
    foreach ($testVariant in $variantsToTest) {
        try {
            Write-Host "Testing $testVariant variant build..." -ForegroundColor Cyan
            
            # Set environment for build test
            $env:GAMEFORGE_VARIANT = $testVariant
            $env:BUILD_VERSION = "test"
            $env:VCS_REF = "test"
            $env:ENABLE_GPU = if ($testVariant -eq "gpu") { "true" } else { "false" }
            
            # Test build validation only
            & ".\build-phase2-phase4-integration.ps1" -Variant $testVariant -ValidateOnly
            
            Add-TestResult -TestName "Build validation: $testVariant" -Passed ($LASTEXITCODE -eq 0) -Message "Build process validation"
            
        } catch {
            Add-TestResult -TestName "Build validation: $testVariant" -Passed $false -Message "Build validation failed" -Details $_.Exception.Message
        }
    }
}

# Function to test environment configuration
function Test-EnvironmentConfiguration {
    Write-Host "Testing environment configuration..." -ForegroundColor Yellow
    
    if (Test-Path ".env.phase2") {
        try {
            $envContent = Get-Content ".env.phase2"
            $validEnvVars = 0
            $totalEnvVars = 0
            
            foreach ($line in $envContent) {
                if ($line -match '^([^#][^=]+)=(.+)$') {
                    $totalEnvVars++
                    $varName = $matches[1]
                    $varValue = $matches[2]
                    
                    if ($varName -and $varValue) {
                        $validEnvVars++
                    }
                }
            }
            
            $envValid = $validEnvVars -gt 0 -and ($validEnvVars -eq $totalEnvVars)
            Add-TestResult -TestName "Environment configuration" -Passed $envValid -Message "$validEnvVars/$totalEnvVars variables valid"
            
        } catch {
            Add-TestResult -TestName "Environment configuration" -Passed $false -Message "Failed to parse .env.phase2" -Details $_.Exception.Message
        }
    } else {
        Add-TestResult -TestName "Environment configuration" -Passed $false -Message ".env.phase2 file not found"
    }
}

# Function to test Phase 4 integration
function Test-Phase4Integration {
    Write-Host "Testing Phase 4 integration..." -ForegroundColor Yellow
    
    $composeContent = Get-Content "docker-compose.production-hardened.yml" -Raw
    
    $phase4Features = @(
        @{ Pattern = "vault:"; Description = "Vault integration" },
        @{ Pattern = "trivy-server:"; Description = "Trivy security scanning" },
        @{ Pattern = "security-dashboard:"; Description = "Security dashboard" },
        @{ Pattern = "phase4.vault-integration=enabled"; Description = "Phase 4 labels" },
        @{ Pattern = "MODEL_SECURITY_ENABLED"; Description = "Model security" }
    )
    
    foreach ($feature in $phase4Features) {
        $hasFeature = $composeContent -match [regex]::Escape($feature.Pattern)
        Add-TestResult -TestName "Phase 4: $($feature.Description)" -Passed $hasFeature -Message $feature.Description
    }
}

# Function to test script permissions and syntax
function Test-ScriptIntegrity {
    Write-Host "Testing script integrity..." -ForegroundColor Yellow
    
    $scripts = @(
        "build-phase2-phase4-integration.ps1",
        "deploy-phase2-phase4-production.ps1"
    )
    
    foreach ($script in $scripts) {
        if (Test-Path $script) {
            try {
                # Test PowerShell syntax
                $syntaxErrors = $null
                [System.Management.Automation.PSParser]::Tokenize((Get-Content $script -Raw), [ref]$syntaxErrors)
                
                $syntaxValid = $syntaxErrors.Count -eq 0
                Add-TestResult -TestName "Script syntax: $script" -Passed $syntaxValid -Message "PowerShell syntax validation"
                
                if (-not $syntaxValid -and $Verbose) {
                    Write-Host "Syntax errors in $script" -ForegroundColor Red
                    $syntaxErrors | ForEach-Object { Write-Host "  $($_.Message)" -ForegroundColor DarkRed }
                }
                
            } catch {
                Add-TestResult -TestName "Script syntax: $script" -Passed $false -Message "Syntax check failed" -Details $_.Exception.Message
            }
        } else {
            Add-TestResult -TestName "Script exists: $script" -Passed $false -Message "Script file not found"
        }
    }
}

# Function to generate validation report
function New-ValidationReport {
    Write-Host "========================================================================" -ForegroundColor Blue
    Write-Host "Phase 2 + Phase 4 Integration Validation Report" -ForegroundColor Blue
    Write-Host "========================================================================" -ForegroundColor Blue
    
    Write-Host "Test Summary:" -ForegroundColor White
    Write-Host "  Total Tests: $($script:TestsPassed + $script:TestsFailed)" -ForegroundColor Gray
    Write-Host "  Passed: $script:TestsPassed" -ForegroundColor Green
    Write-Host "  Failed: $script:TestsFailed" -ForegroundColor Red
    
    $successRate = if (($script:TestsPassed + $script:TestsFailed) -gt 0) {
        [math]::Round(($script:TestsPassed / ($script:TestsPassed + $script:TestsFailed)) * 100, 2)
    } else { 0 }
    
    Write-Host "  Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 90) { "Green" } elseif ($successRate -ge 70) { "Yellow" } else { "Red" })
    
    if ($script:TestsFailed -gt 0 -and $Verbose) {
        Write-Host "`nFailed Tests:" -ForegroundColor Red
        $script:TestResults | Where-Object { -not $_.Passed } | ForEach-Object {
            Write-Host "  [FAIL] $($_.TestName): $($_.Message)" -ForegroundColor Red
            if ($_.Details) {
                Write-Host "     Details: $($_.Details)" -ForegroundColor DarkRed
            }
        }
    }
    
    Write-Host "`nValidation completed at: $(Get-Date)" -ForegroundColor Gray
    Write-Host "========================================================================" -ForegroundColor Blue
    
    return $script:TestsFailed -eq 0
}

# Main execution
try {
    Test-Phase2FileStructure
    Test-DockerfileStructure
    Test-DockerComposeConfiguration
    Test-EnvironmentConfiguration
    Test-Phase4Integration
    Test-ScriptIntegrity
    
    if (-not $QuickTest) {
        Test-BuildProcess
    }
    
    $validationPassed = New-ValidationReport
    
    if ($validationPassed) {
        Write-Host "[SUCCESS] Phase 2 + Phase 4 integration validation completed successfully!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[FAILED] Phase 2 + Phase 4 integration validation failed!" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "[ERROR] Validation process failed: $_" -ForegroundColor Red
    exit 1
}
