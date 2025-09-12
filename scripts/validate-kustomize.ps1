#!/usr/bin/env powershell
# GameForge Production Readiness Validation Script

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "prerequisites", "kustomize", "security", "deployment", "monitoring")]
    [string]$TestSuite = "all",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipDeployment,
    
    [Parameter(Mandatory=$false)]
    [switch]$Detailed
)

# Configuration
$ScriptRoot = $PSScriptRoot
$K8sDir = "$ScriptRoot/k8s"
$LogDir = "$ScriptRoot/logs/validation"
$TestResults = @()

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Test result tracking
class TestResult {
    [string]$TestName
    [string]$Category
    [string]$Status
    [string]$Message
    [string]$Details
    [datetime]$Timestamp
}

function New-TestResult {
    param(
        [string]$TestName,
        [string]$Category,
        [string]$Status,
        [string]$Message,
        [string]$Details = ""
    )
    
    $result = [TestResult]::new()
    $result.TestName = $TestName
    $result.Category = $Category
    $result.Status = $Status
    $result.Message = $Message
    $result.Details = $Details
    $result.Timestamp = Get-Date
    
    return $result
}

function Write-ValidationLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "VALIDATION"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] [$Component] $Message"
    
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN" { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        default { Write-Host $logMessage -ForegroundColor White }
    }
    
    $logFile = "$LogDir/validation-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

# Test Prerequisites
function Test-Prerequisites {
    Write-ValidationLog "Testing prerequisites..." -Level "INFO"
    
    # Test kubectl
    try {
        $kubectlVersion = kubectl version --client=true --output=json 2>$null | ConvertFrom-Json
        $kustomizeVersion = $kubectlVersion.clientVersion.gitVersion
        $script:TestResults += New-TestResult -TestName "kubectl" -Category "Prerequisites" -Status "PASS" -Message "kubectl available: $kustomizeVersion"
        Write-ValidationLog "kubectl version: $kustomizeVersion" -Level "SUCCESS"
    } catch {
        $script:TestResults += New-TestResult -TestName "kubectl" -Category "Prerequisites" -Status "FAIL" -Message "kubectl not available" -Details $_.Exception.Message
        Write-ValidationLog "kubectl not available: $_" -Level "ERROR"
    }
    
    # Test cluster connectivity
    try {
        $clusterInfo = kubectl cluster-info 2>&1
        if ($LASTEXITCODE -eq 0) {
            $script:TestResults += New-TestResult -TestName "cluster-connectivity" -Category "Prerequisites" -Status "PASS" -Message "Cluster connectivity verified"
            Write-ValidationLog "Cluster connectivity verified" -Level "SUCCESS"
        } else {
            throw "Cluster not accessible"
        }
    } catch {
        $script:TestResults += New-TestResult -TestName "cluster-connectivity" -Category "Prerequisites" -Status "FAIL" -Message "Cluster not accessible" -Details $_.Exception.Message
        Write-ValidationLog "Cluster not accessible: $_" -Level "ERROR"
    }
}

# Test Kustomize Configuration
function Test-KustomizeConfiguration {
    Write-ValidationLog "Testing Kustomize configuration..." -Level "INFO"
    
    # Test base directory
    $basePath = "$K8sDir/base"
    if (Test-Path $basePath) {
        $script:TestResults += New-TestResult -TestName "base-directory" -Category "Kustomize" -Status "PASS" -Message "Base directory exists"
        Write-ValidationLog "Base directory found: $basePath" -Level "SUCCESS"
    } else {
        $script:TestResults += New-TestResult -TestName "base-directory" -Category "Kustomize" -Status "FAIL" -Message "Base directory missing"
        Write-ValidationLog "Base directory missing: $basePath" -Level "ERROR"
        return
    }
    
    # Test overlays
    $overlayPath = "$K8sDir/overlays/$Environment"
    if (Test-Path $overlayPath) {
        $script:TestResults += New-TestResult -TestName "overlay-$Environment" -Category "Kustomize" -Status "PASS" -Message "Overlay directory exists"
        Write-ValidationLog "Overlay directory found: $overlayPath" -Level "SUCCESS"
    } else {
        $script:TestResults += New-TestResult -TestName "overlay-$Environment" -Category "Kustomize" -Status "FAIL" -Message "Overlay directory missing"
        Write-ValidationLog "Overlay directory missing: $overlayPath" -Level "ERROR"
        return
    }
    
    # Test kustomize build
    try {
        Push-Location $overlayPath
        $buildOutput = kubectl kustomize . 2>&1
        if ($LASTEXITCODE -eq 0) {
            $script:TestResults += New-TestResult -TestName "kustomize-build" -Category "Kustomize" -Status "PASS" -Message "Kustomize build successful"
            Write-ValidationLog "Kustomize build successful" -Level "SUCCESS"
            
            # Count resources
            $resourceCount = ($buildOutput | Select-String "^---").Count
            Write-ValidationLog "Resources in build: $resourceCount" -Level "INFO"
        } else {
            throw "Build failed: $buildOutput"
        }
    } catch {
        $script:TestResults += New-TestResult -TestName "kustomize-build" -Category "Kustomize" -Status "FAIL" -Message "Kustomize build failed" -Details $_.Exception.Message
        Write-ValidationLog "Kustomize build failed: $_" -Level "ERROR"
    } finally {
        Pop-Location
    }
}

# Show validation report
function Show-ValidationReport {
    Write-Host "`n" -NoNewline
    Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                            VALIDATION REPORT                                ║" -ForegroundColor Cyan
    Write-Host "╠══════════════════════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║ Environment: $($Environment.PadRight(63)) ║" -ForegroundColor Cyan
    Write-Host "║ Test Suite: $($TestSuite.PadRight(64)) ║" -ForegroundColor Cyan
    Write-Host "║ Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss').PadRight(63) ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    # Summary by category
    $categories = $TestResults | Group-Object Category | Sort-Object Name
    foreach ($category in $categories) {
        Write-Host "`n$($category.Name) Tests:" -ForegroundColor Yellow
        
        $passed = ($category.Group | Where-Object Status -eq "PASS").Count
        $failed = ($category.Group | Where-Object Status -eq "FAIL").Count
        $warned = ($category.Group | Where-Object Status -eq "WARN").Count
        $total = $category.Count
        
        Write-Host "  [PASS] Passed: $passed" -ForegroundColor Green
        Write-Host "  [FAIL] Failed: $failed" -ForegroundColor Red
        Write-Host "  [WARN] Warnings: $warned" -ForegroundColor Yellow
        Write-Host "  Total: $total" -ForegroundColor White
        
        if ($Detailed) {
            Write-Host "`n  Detailed Results:" -ForegroundColor Gray
            foreach ($test in $category.Group | Sort-Object Status, TestName) {
                $icon = switch ($test.Status) {
                    "PASS" { "[PASS]" }
                    "FAIL" { "[FAIL]" }
                    "WARN" { "[WARN]" }
                    default { "[UNKN]" }
                }
                
                $color = switch ($test.Status) {
                    "PASS" { "Green" }
                    "FAIL" { "Red" }
                    "WARN" { "Yellow" }
                    default { "White" }
                }
                
                Write-Host "    $icon $($test.TestName): $($test.Message)" -ForegroundColor $color
                if ($test.Details -and $Detailed) {
                    Write-Host "      Details: $($test.Details)" -ForegroundColor Gray
                }
            }
        }
    }
    
    # Overall summary
    $totalPassed = ($TestResults | Where-Object Status -eq "PASS").Count
    $totalFailed = ($TestResults | Where-Object Status -eq "FAIL").Count
    $totalWarned = ($TestResults | Where-Object Status -eq "WARN").Count
    $totalTests = $TestResults.Count
    
    Write-Host "`n" -NoNewline
    Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                              OVERALL SUMMARY                                ║" -ForegroundColor Cyan
    Write-Host "╠══════════════════════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║ Total Tests: $($totalTests.ToString().PadRight(63)) ║" -ForegroundColor Cyan
    Write-Host "║ Passed: $($totalPassed.ToString().PadRight(68)) ║" -ForegroundColor Green
    Write-Host "║ Failed: $($totalFailed.ToString().PadRight(68)) ║" -ForegroundColor Red
    Write-Host "║ Warnings: $($totalWarned.ToString().PadRight(66)) ║" -ForegroundColor Yellow
    
    $successRate = if ($totalTests -gt 0) { [math]::Round(($totalPassed / $totalTests) * 100, 1) } else { 0 }
    Write-Host "║ Success Rate: $($successRate)%$(' ' * (57 - $successRate.ToString().Length)) ║" -ForegroundColor Cyan
    
    $status = if ($totalFailed -eq 0 -and $totalWarned -eq 0) { "READY FOR PRODUCTION" } 
              elseif ($totalFailed -eq 0) { "READY WITH WARNINGS" }
              else { "NOT READY - FIXES REQUIRED" }
    
    $statusColor = if ($totalFailed -eq 0 -and $totalWarned -eq 0) { "Green" } 
                   elseif ($totalFailed -eq 0) { "Yellow" }
                   else { "Red" }
    
    Write-Host "║ Status: $($status.PadRight(68)) ║" -ForegroundColor $statusColor
    Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    return $totalFailed -eq 0
}

# Main execution
function Start-ValidationSuite {
    Write-ValidationLog "Starting validation suite: $TestSuite for $Environment" -Level "INFO"
    
    try {
        switch ($TestSuite) {
            "prerequisites" { Test-Prerequisites }
            "kustomize" { Test-KustomizeConfiguration }
            "all" {
                Test-Prerequisites
                Test-KustomizeConfiguration
            }
        }
        
        $success = Show-ValidationReport
        
        if ($success) {
            Write-ValidationLog "Validation completed successfully - Ready for production!" -Level "SUCCESS"
            exit 0
        } else {
            Write-ValidationLog "Validation completed with failures - Please fix issues before deployment" -Level "ERROR"
            exit 1
        }
        
    } catch {
        Write-ValidationLog "Validation suite failed: $_" -Level "ERROR"
        exit 1
    }
}

# Execute validation
Start-ValidationSuite
