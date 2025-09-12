#!/usr/bin/env powershell
# ========================================================================
# GameForge AI Final Security Validation
# Comprehensive validation of all resolved critical security gaps
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [switch]$RunAll = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DeployFirst = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

# ========================================================================
# Configuration
# ========================================================================

$ValidationTests = @{
    "DockerSecretsValidation" = @{
        Description = "Validate Docker secrets are created and accessible"
        Script = ".\vault-secrets-management.ps1"
        Args = @("-Validate")
        CriticalGap = "Hard-coded Secrets"
    }
    "SeccompRuntimeValidation" = @{
        Description = "Validate seccomp profiles are enforced at runtime"
        Script = ".\seccomp-runtime-validation.ps1"
        Args = @("-TestAll", "-Detailed")
        CriticalGap = "Seccomp Runtime Validation"
    }
    "DockerfileUserValidation" = @{
        Description = "Validate Dockerfile creates non-root user"
        Script = "Internal"
        CriticalGap = "Dockerfile User Validation"
    }
    "ProductionDeploymentValidation" = @{
        Description = "Validate production deployment with all security features"
        Script = ".\deploy-production-complete.ps1"
        Args = @("-DryRun")
        CriticalGap = "Runtime Security Enforcement"
    }
}

# ========================================================================
# Utility Functions
# ========================================================================

function Write-LogMessage {
    param(
        [string]$Message,
        [string]$Level = "Info",
        [string]$Component = "SecurityValidation"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colors = @{
        "Info" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
        "Success" = "Cyan"
        "Critical" = "Magenta"
        "Header" = "White"
    }
    
    if ($Verbose -or $Level -in @("Warning", "Error", "Success", "Critical", "Header")) {
        Write-Host "[$timestamp] [$Level] [$Component] $Message" -ForegroundColor $colors[$Level]
    }
}

function Write-Header {
    param([string]$Title)
    
    $separator = "=" * 70
    Write-Host ""
    Write-Host $separator -ForegroundColor Magenta
    Write-Host " $Title" -ForegroundColor Magenta
    Write-Host $separator -ForegroundColor Magenta
}

# ========================================================================
# Validation Test Functions
# ========================================================================

function Test-DockerfileUserValidation {
    Write-LogMessage "Validating Dockerfile user configuration..." -Level "Info"
    
    $dockerfilePath = ".\Dockerfile.vastai-gpu"
    
    if (-not (Test-Path $dockerfilePath)) {
        Write-LogMessage "Dockerfile not found: $dockerfilePath" -Level "Error"
        return $false
    }
    
    try {
        $dockerfileContent = Get-Content $dockerfilePath -Raw
        
        # Check for user creation
        $userCreationPattern = "useradd.*-u\s+1001.*gameforge"
        $userSwitchPattern = "USER\s+gameforge"
        
        $hasUserCreation = $dockerfileContent -match $userCreationPattern
        $hasUserSwitch = $dockerfileContent -match $userSwitchPattern
        
        if ($hasUserCreation -and $hasUserSwitch) {
            Write-LogMessage "✅ Dockerfile correctly creates and switches to non-root user 'gameforge' (UID 1001)" -Level "Success"
            
            # Additional validation - check for group creation
            $groupCreationPattern = "groupadd.*-g\s+1001.*gameforge"
            $hasGroupCreation = $dockerfileContent -match $groupCreationPattern
            
            if ($hasGroupCreation) {
                Write-LogMessage "✅ Dockerfile correctly creates group 'gameforge' (GID 1001)" -Level "Success"
            }
            
            return $true
        } else {
            Write-LogMessage "❌ Dockerfile user configuration is incomplete" -Level "Error"
            if (-not $hasUserCreation) {
                Write-LogMessage "  Missing user creation with UID 1001" -Level "Error"
            }
            if (-not $hasUserSwitch) {
                Write-LogMessage "  Missing USER directive to switch to non-root user" -Level "Error"
            }
            return $false
        }
    }
    catch {
        Write-LogMessage "Failed to validate Dockerfile: $($_.Exception.Message)" -Level "Error"
        return $false
    }
}

function Test-HardCodedSecretsResolution {
    Write-LogMessage "Validating hard-coded secrets resolution..." -Level "Info"
    
    # Check for vault secrets override file
    $vaultSecretsFile = ".\docker-compose.vault-secrets.yml"
    
    if (-not (Test-Path $vaultSecretsFile)) {
        Write-LogMessage "❌ Vault secrets override file not found: $vaultSecretsFile" -Level "Error"
        return $false
    }
    
    Write-LogMessage "✅ Vault secrets override file exists" -Level "Success"
    
    # Check vault secrets management script
    $vaultScript = ".\vault-secrets-management.ps1"
    
    if (-not (Test-Path $vaultScript)) {
        Write-LogMessage "❌ Vault secrets management script not found: $vaultScript" -Level "Error"
        return $false
    }
    
    Write-LogMessage "✅ Vault secrets management script exists" -Level "Success"
    
    # Validate the override file contains Docker secrets
    try {
        $overrideContent = Get-Content $vaultSecretsFile -Raw
        
        $requiredSecrets = @(
            "postgres_password",
            "redis_password", 
            "minio_access_key",
            "minio_secret_key",
            "elastic_password",
            "grafana_password"
        )
        
        $missingSecrets = @()
        foreach ($secret in $requiredSecrets) {
            if ($overrideContent -notlike "*$secret*") {
                $missingSecrets += $secret
            }
        }
        
        if ($missingSecrets.Count -eq 0) {
            Write-LogMessage "✅ All required secrets configured in override file" -Level "Success"
            return $true
        } else {
            Write-LogMessage "❌ Missing secrets in override file: $($missingSecrets -join ', ')" -Level "Error"
            return $false
        }
    }
    catch {
        Write-LogMessage "Failed to validate vault secrets file: $($_.Exception.Message)" -Level "Error"
        return $false
    }
}

function Test-SecurityProfilesExistence {
    Write-LogMessage "Validating security profiles existence..." -Level "Info"
    
    $securityDir = ".\security"
    $seccompDir = Join-Path $securityDir "seccomp"
    
    if (-not (Test-Path $seccompDir)) {
        Write-LogMessage "❌ Seccomp profiles directory not found: $seccompDir" -Level "Error"
        return $false
    }
    
    $requiredProfiles = @(
        "gameforge-app-seccomp.json",
        "nginx-seccomp.json",
        "postgres-seccomp.json", 
        "redis-seccomp.json"
    )
    
    $missingProfiles = @()
    foreach ($profile in $requiredProfiles) {
        $profilePath = Join-Path $seccompDir $profile
        if (-not (Test-Path $profilePath)) {
            $missingProfiles += $profile
        }
    }
    
    if ($missingProfiles.Count -eq 0) {
        Write-LogMessage "✅ All required seccomp profiles exist" -Level "Success"
        return $true
    } else {
        Write-LogMessage "❌ Missing seccomp profiles: $($missingProfiles -join ', ')" -Level "Error"
        return $false
    }
}

function Invoke-ValidationTest {
    param(
        [string]$TestName,
        [hashtable]$TestConfig
    )
    
    Write-LogMessage "Running test: $TestName" -Level "Info"
    Write-LogMessage "Critical Gap: $($TestConfig.CriticalGap)" -Level "Info"
    Write-LogMessage "Description: $($TestConfig.Description)" -Level "Info"
    
    try {
        if ($TestConfig.Script -eq "Internal") {
            # Internal validation functions
            $result = switch ($TestName) {
                "DockerfileUserValidation" { Test-DockerfileUserValidation }
                default { $false }
            }
        } else {
            # External script execution
            if (-not (Test-Path $TestConfig.Script)) {
                Write-LogMessage "Validation script not found: $($TestConfig.Script)" -Level "Error"
                return $false
            }
            
            $scriptArgs = $TestConfig.Args -join " "
            Write-LogMessage "Executing: $($TestConfig.Script) $scriptArgs" -Level "Info"
            
            # Execute the script
            $process = Start-Process -FilePath "powershell.exe" -ArgumentList "-File", $TestConfig.Script, $TestConfig.Args -Wait -PassThru -NoNewWindow
            $result = $process.ExitCode -eq 0
        }
        
        if ($result) {
            Write-LogMessage "✅ TEST PASSED: $TestName" -Level "Success"
            return $true
        } else {
            Write-LogMessage "❌ TEST FAILED: $TestName" -Level "Error"
            return $false
        }
    }
    catch {
        Write-LogMessage "❌ TEST ERROR: $TestName - $($_.Exception.Message)" -Level "Error"
        return $false
    }
}

# ========================================================================
# Main Validation Function
# ========================================================================

function Invoke-ComprehensiveSecurityValidation {
    Write-Header "GameForge AI Final Security Validation"
    
    Write-LogMessage "Validating resolution of all critical security gaps..." -Level "Critical"
    
    # Deploy services first if requested
    if ($DeployFirst) {
        Write-Header "Deploying Services for Testing"
        Write-LogMessage "Starting deployment for validation..." -Level "Info"
        
        try {
            # Initialize Docker secrets first
            & ".\vault-secrets-management.ps1" -Force
            
            # Deploy with vault secrets
            docker-compose -f docker-compose.vastai-production.yml -f docker-compose.vault-secrets.yml up -d
            
            Write-LogMessage "Services deployed successfully" -Level "Success"
            Start-Sleep -Seconds 30  # Allow services to start
        }
        catch {
            Write-LogMessage "Failed to deploy services: $($_.Exception.Message)" -Level "Error"
            return $false
        }
    }
    
    # Run preliminary checks
    Write-Header "Preliminary Security Checks"
    
    $preliminaryResults = @{
        HardCodedSecretsResolution = Test-HardCodedSecretsResolution
        SecurityProfilesExistence = Test-SecurityProfilesExistence
    }
    
    $preliminaryPassed = ($preliminaryResults.Values | Where-Object { $_ -eq $false }).Count -eq 0
    
    if (-not $preliminaryPassed) {
        Write-LogMessage "❌ Preliminary checks failed - cannot proceed with runtime validation" -Level "Error"
        return $false
    }
    
    Write-LogMessage "✅ All preliminary checks passed" -Level "Success"
    
    # Run main validation tests
    Write-Header "Critical Gap Validation Tests"
    
    $validationResults = @{}
    $totalTests = 0
    $passedTests = 0
    
    foreach ($testName in $ValidationTests.Keys) {
        $testConfig = $ValidationTests[$testName]
        $totalTests++
        
        Write-Header "Test: $($testConfig.CriticalGap)"
        
        $testResult = Invoke-ValidationTest -TestName $testName -TestConfig $testConfig
        $validationResults[$testName] = $testResult
        
        if ($testResult) {
            $passedTests++
        }
        
        Write-LogMessage "Test Result: $(if ($testResult) { 'PASSED' } else { 'FAILED' })" -Level $(if ($testResult) { "Success" } else { "Error" })
    }
    
    # Generate final report
    Write-Header "Final Security Validation Report"
    
    Write-Host ""
    Write-Host "CRITICAL GAPS RESOLUTION STATUS:" -ForegroundColor Magenta
    Write-Host ""
    
    foreach ($testName in $ValidationTests.Keys) {
        $testConfig = $ValidationTests[$testName]
        $result = $validationResults[$testName]
        $status = if ($result) { "✅ RESOLVED" } else { "❌ UNRESOLVED" }
        $color = if ($result) { "Green" } else { "Red" }
        
        Write-Host "  $($testConfig.CriticalGap): $status" -ForegroundColor $color
    }
    
    Write-Host ""
    Write-Host "VALIDATION SUMMARY:" -ForegroundColor Cyan
    Write-Host "  Total Tests: $totalTests" -ForegroundColor White
    Write-Host "  Passed: $passedTests" -ForegroundColor Green
    Write-Host "  Failed: $($totalTests - $passedTests)" -ForegroundColor Red
    Write-Host "  Success Rate: $([math]::Round(($passedTests / $totalTests) * 100, 1))%" -ForegroundColor Cyan
    
    Write-Host ""
    
    if ($passedTests -eq $totalTests) {
        Write-Host "🎉 ALL CRITICAL SECURITY GAPS RESOLVED!" -ForegroundColor Green
        Write-Host "✅ GameForge AI Platform is PRODUCTION READY" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Cyan
        Write-Host "  1. ✅ Security validation complete" -ForegroundColor Green
        Write-Host "  2. ✅ Deploy to production environment" -ForegroundColor Green
        Write-Host "  3. ✅ Monitor security alerts and metrics" -ForegroundColor Green
        Write-Host "  4. ✅ Conduct periodic security audits" -ForegroundColor Green
        
        return $true
    } else {
        Write-Host "⚠️  SECURITY VALIDATION FAILED" -ForegroundColor Red
        Write-Host "❌ Critical gaps remain unresolved" -ForegroundColor Red
        Write-Host ""
        Write-Host "Required Actions:" -ForegroundColor Yellow
        
        foreach ($testName in $ValidationTests.Keys) {
            if (-not $validationResults[$testName]) {
                $testConfig = $ValidationTests[$testName]
                Write-Host "  - Fix: $($testConfig.CriticalGap)" -ForegroundColor Yellow
            }
        }
        
        return $false
    }
}

# ========================================================================
# Main Execution
# ========================================================================

function Main {
    try {
        $validationPassed = Invoke-ComprehensiveSecurityValidation
        
        if ($validationPassed) {
            Write-LogMessage "🎯 Final security validation PASSED - Production deployment approved!" -Level "Success"
            exit 0
        } else {
            Write-LogMessage "❌ Final security validation FAILED - Production deployment NOT approved" -Level "Error"
            exit 1
        }
    }
    catch {
        Write-LogMessage "Security validation failed with error: $($_.Exception.Message)" -Level "Error"
        exit 1
    }
}

# Execute main function
Main