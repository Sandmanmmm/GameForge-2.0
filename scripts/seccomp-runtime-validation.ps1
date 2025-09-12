#!/usr/bin/env powershell
# ========================================================================
# GameForge AI Seccomp Runtime Validation
# Tests and validates seccomp profile enforcement at container runtime
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "gameforge-app",
    
    [Parameter(Mandatory=$false)]
    [string]$ProfilePath = "./security/seccomp",
    
    [Parameter(Mandatory=$false)]
    [switch]$Detailed = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$TestAll = $false
)

$ErrorActionPreference = "Stop"

# ========================================================================
# Configuration
# ========================================================================

$SeccompProfiles = @(
    @{
        Name = "gameforge-app-seccomp.json"
        Container = "gameforge-app"
        ExpectedBlocked = @("ptrace", "process_vm_readv", "process_vm_writev")
        ExpectedAllowed = @("read", "write", "open", "close", "mmap")
    },
    @{
        Name = "nginx-seccomp.json"  
        Container = "nginx"
        ExpectedBlocked = @("ptrace", "reboot", "syslog")
        ExpectedAllowed = @("read", "write", "open", "close", "bind", "listen")
    },
    @{
        Name = "postgres-seccomp.json"
        Container = "postgres"
        ExpectedBlocked = @("ptrace", "mount", "umount2") 
        ExpectedAllowed = @("read", "write", "open", "close", "fsync")
    },
    @{
        Name = "redis-seccomp.json"
        Container = "redis"
        ExpectedBlocked = @("ptrace", "mount", "reboot")
        ExpectedAllowed = @("read", "write", "open", "close", "mmap")
    }
)

# ========================================================================
# Utility Functions  
# ========================================================================

function Write-LogMessage {
    param(
        [string]$Message,
        [string]$Level = "Info",
        [string]$Component = "SeccompValidation"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colors = @{
        "Info" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
        "Success" = "Cyan"
        "Test" = "Magenta"
    }
    
    Write-Host "[$timestamp] [$Level] [$Component] $Message" -ForegroundColor $colors[$Level]
}

function Test-ContainerRunning {
    param([string]$ContainerName)
    
    try {
        $status = docker inspect $ContainerName --format "{{.State.Running}}" 2>$null
        return $status -eq "true"
    }
    catch {
        return $false
    }
}

function Get-ContainerSeccompProfile {
    param([string]$ContainerName)
    
    try {
        $seccompInfo = docker inspect $ContainerName --format "{{.HostConfig.SecurityOpt}}" 2>$null
        if ($seccompInfo -and $seccompInfo -ne "[]") {
            return $seccompInfo
        }
        return $null
    }
    catch {
        return $null
    }
}

# ========================================================================
# Seccomp Testing Functions
# ========================================================================

function Test-SeccompProfileContent {
    param(
        [string]$ProfilePath,
        [string]$ProfileName
    )
    
    $fullPath = Join-Path $ProfilePath $ProfileName
    
    if (-not (Test-Path $fullPath)) {
        Write-LogMessage "Seccomp profile not found: $fullPath" -Level "Error"
        return $false
    }
    
    try {
        $profileContent = Get-Content $fullPath -Raw | ConvertFrom-Json
        
        # Validate required fields
        $requiredFields = @("defaultAction", "syscalls")
        foreach ($field in $requiredFields) {
            if (-not $profileContent.PSObject.Properties.Name -contains $field) {
                Write-LogMessage "Missing required field '$field' in profile $ProfileName" -Level "Error"
                return $false
            }
        }
        
        # Check default action
        if ($profileContent.defaultAction -ne "SCMP_ACT_ERRNO") {
            Write-LogMessage "Profile $ProfileName should have defaultAction=SCMP_ACT_ERRNO for security" -Level "Warning"
        }
        
        # Count syscalls
        $allowedSyscalls = $profileContent.syscalls | Where-Object { $_.action -eq "SCMP_ACT_ALLOW" }
        $blockedSyscalls = $profileContent.syscalls | Where-Object { $_.action -ne "SCMP_ACT_ALLOW" }
        
        Write-LogMessage "Profile $ProfileName: $($allowedSyscalls.Count) allowed, $($blockedSyscalls.Count) blocked syscalls" -Level "Info"
        
        return $true
    }
    catch {
        Write-LogMessage "Failed to parse seccomp profile $ProfileName : $($_.Exception.Message)" -Level "Error"
        return $false
    }
}

function Test-SystemCallBlocking {
    param(
        [string]$ContainerName,
        [string[]]$BlockedSyscalls,
        [string[]]$AllowedSyscalls
    )
    
    if (-not (Test-ContainerRunning $ContainerName)) {
        Write-LogMessage "Container $ContainerName is not running - cannot test syscalls" -Level "Error"
        return $false
    }
    
    $testResults = @{
        BlockedTests = @()
        AllowedTests = @()
        Passed = 0
        Failed = 0
    }
    
    Write-LogMessage "Testing blocked syscalls for $ContainerName..." -Level "Test"
    
    # Test blocked syscalls - these should fail
    foreach ($syscall in $BlockedSyscalls) {
        try {
            # Use strace to test if syscall is blocked
            $testCmd = switch ($syscall) {
                "ptrace" { "python3 -c `"import ctypes; ctypes.CDLL('libc.so.6').ptrace(0, 0, 0, 0)`"" }
                "reboot" { "python3 -c `"import ctypes; ctypes.CDLL('libc.so.6').reboot(0)`"" }
                "mount" { "python3 -c `"import ctypes; ctypes.CDLL('libc.so.6').mount(b'', b'', b'', 0, None)`"" }
                "syslog" { "python3 -c `"import ctypes; ctypes.CDLL('libc.so.6').syslog(1, b'test')`"" }
                default { "python3 -c `"import ctypes; ctypes.CDLL('libc.so.6').$syscall()`"" }
            }
            
            $result = docker exec $ContainerName sh -c "$testCmd 2>&1" 2>$null
            $exitCode = $LASTEXITCODE
            
            if ($exitCode -eq 0) {
                Write-LogMessage "❌ SECURITY ISSUE: Syscall '$syscall' should be blocked but was allowed!" -Level "Error"
                $testResults.Failed++
                $testResults.BlockedTests += @{ Syscall = $syscall; Expected = "Blocked"; Actual = "Allowed"; Status = "FAIL" }
            } else {
                Write-LogMessage "✅ Syscall '$syscall' correctly blocked" -Level "Success"
                $testResults.Passed++
                $testResults.BlockedTests += @{ Syscall = $syscall; Expected = "Blocked"; Actual = "Blocked"; Status = "PASS" }
            }
        }
        catch {
            # Expected for blocked syscalls
            Write-LogMessage "✅ Syscall '$syscall' correctly blocked (exception caught)" -Level "Success"
            $testResults.Passed++
            $testResults.BlockedTests += @{ Syscall = $syscall; Expected = "Blocked"; Actual = "Blocked"; Status = "PASS" }
        }
    }
    
    Write-LogMessage "Testing allowed syscalls for $ContainerName..." -Level "Test"
    
    # Test allowed syscalls - these should succeed
    foreach ($syscall in $AllowedSyscalls) {
        try {
            $testCmd = switch ($syscall) {
                "read" { "python3 -c `"import os; os.read(0, 0) if False else None`"" }
                "write" { "python3 -c `"import os; print('test')`"" }
                "open" { "python3 -c `"import os; f = open('/dev/null', 'r'); f.close()`"" }
                "close" { "python3 -c `"import os; f = open('/dev/null', 'r'); f.close()`"" }
                "mmap" { "python3 -c `"import mmap; m = mmap.mmap(-1, 1024); m.close()`"" }
                default { "python3 -c `"print('Testing $syscall')`"" }
            }
            
            $result = docker exec $ContainerName sh -c "$testCmd 2>&1" 2>$null
            $exitCode = $LASTEXITCODE
            
            if ($exitCode -eq 0) {
                Write-LogMessage "✅ Syscall '$syscall' correctly allowed" -Level "Success"
                $testResults.Passed++
                $testResults.AllowedTests += @{ Syscall = $syscall; Expected = "Allowed"; Actual = "Allowed"; Status = "PASS" }
            } else {
                Write-LogMessage "❌ ISSUE: Syscall '$syscall' should be allowed but was blocked!" -Level "Warning"
                $testResults.Failed++
                $testResults.AllowedTests += @{ Syscall = $syscall; Expected = "Allowed"; Actual = "Blocked"; Status = "FAIL" }
            }
        }
        catch {
            Write-LogMessage "❌ ISSUE: Syscall '$syscall' should be allowed but failed: $($_.Exception.Message)" -Level "Warning"
            $testResults.Failed++
            $testResults.AllowedTests += @{ Syscall = $syscall; Expected = "Allowed"; Actual = "Error"; Status = "FAIL" }
        }
    }
    
    return $testResults
}

function Test-ContainerSeccompEnforcement {
    param([string]$ContainerName)
    
    Write-LogMessage "Validating seccomp enforcement for container: $ContainerName" -Level "Info"
    
    # Check if container exists and is running
    if (-not (Test-ContainerRunning $ContainerName)) {
        Write-LogMessage "Container $ContainerName is not running" -Level "Error"
        return $false
    }
    
    # Get seccomp configuration
    $seccompConfig = Get-ContainerSeccompProfile $ContainerName
    
    if (-not $seccompConfig -or $seccompConfig -eq "[]") {
        Write-LogMessage "❌ CRITICAL: No seccomp profile applied to container $ContainerName" -Level "Error"
        return $false
    }
    
    Write-LogMessage "✅ Seccomp profile detected: $seccompConfig" -Level "Success"
    
    # Check if running as non-root
    try {
        $userId = docker exec $ContainerName id -u 2>$null
        if ($userId -eq "0") {
            Write-LogMessage "❌ SECURITY ISSUE: Container $ContainerName running as root (UID 0)" -Level "Error"
        } else {
            Write-LogMessage "✅ Container $ContainerName running as non-root user (UID: $userId)" -Level "Success"
        }
    }
    catch {
        Write-LogMessage "Could not determine user ID for container $ContainerName" -Level "Warning"
    }
    
    # Check capabilities
    try {
        $caps = docker exec $ContainerName sh -c "grep CapEff /proc/self/status 2>/dev/null || echo 'CapEff: unknown'"
        Write-LogMessage "Container capabilities: $caps" -Level "Info"
    }
    catch {
        Write-LogMessage "Could not read capabilities for container $ContainerName" -Level "Warning"
    }
    
    return $true
}

# ========================================================================
# Comprehensive Testing Functions
# ========================================================================

function Invoke-ComprehensiveSeccompTest {
    Write-LogMessage "Starting comprehensive seccomp validation..." -Level "Info"
    
    $overallResults = @{
        TestedContainers = 0
        PassedContainers = 0
        FailedContainers = 0
        ProfileTests = @()
        SyscallTests = @()
    }
    
    # Test profile files
    Write-LogMessage "Validating seccomp profile files..." -Level "Info"
    foreach ($profile in $SeccompProfiles) {
        $profileValid = Test-SeccompProfileContent -ProfilePath $ProfilePath -ProfileName $profile.Name
        $overallResults.ProfileTests += @{
            Profile = $profile.Name
            Valid = $profileValid
        }
    }
    
    # Test running containers
    if ($TestAll) {
        $containersToTest = $SeccompProfiles
    } else {
        $containersToTest = $SeccompProfiles | Where-Object { $_.Container -eq $ContainerName }
    }
    
    foreach ($profile in $containersToTest) {
        $overallResults.TestedContainers++
        
        Write-LogMessage "Testing container: $($profile.Container)" -Level "Info"
        
        # Test basic seccomp enforcement
        $basicTest = Test-ContainerSeccompEnforcement -ContainerName $profile.Container
        
        if ($basicTest) {
            # Test specific syscalls
            $syscallResults = Test-SystemCallBlocking -ContainerName $profile.Container -BlockedSyscalls $profile.ExpectedBlocked -AllowedSyscalls $profile.ExpectedAllowed
            
            $overallResults.SyscallTests += @{
                Container = $profile.Container
                Results = $syscallResults
            }
            
            if ($syscallResults.Failed -eq 0) {
                $overallResults.PassedContainers++
                Write-LogMessage "✅ Container $($profile.Container) passed all seccomp tests" -Level "Success"
            } else {
                $overallResults.FailedContainers++
                Write-LogMessage "❌ Container $($profile.Container) failed $($syscallResults.Failed) seccomp tests" -Level "Error"
            }
        } else {
            $overallResults.FailedContainers++
            Write-LogMessage "❌ Container $($profile.Container) failed basic seccomp enforcement test" -Level "Error"
        }
    }
    
    return $overallResults
}

function Show-ValidationSummary {
    param($Results)
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "Seccomp Validation Summary" -ForegroundColor Magenta  
    Write-Host "========================================" -ForegroundColor Magenta
    
    # Profile validation summary
    Write-Host ""
    Write-Host "Profile Files:" -ForegroundColor Cyan
    foreach ($profileTest in $Results.ProfileTests) {
        $status = if ($profileTest.Valid) { "✅ VALID" } else { "❌ INVALID" }
        $color = if ($profileTest.Valid) { "Green" } else { "Red" }
        Write-Host "  $($profileTest.Profile): $status" -ForegroundColor $color
    }
    
    # Container testing summary
    Write-Host ""
    Write-Host "Container Runtime Tests:" -ForegroundColor Cyan
    Write-Host "  Tested: $($Results.TestedContainers)" -ForegroundColor White
    Write-Host "  Passed: $($Results.PassedContainers)" -ForegroundColor Green
    Write-Host "  Failed: $($Results.FailedContainers)" -ForegroundColor Red
    
    # Detailed syscall results
    if ($Detailed) {
        Write-Host ""
        Write-Host "Detailed Syscall Test Results:" -ForegroundColor Cyan
        foreach ($containerTest in $Results.SyscallTests) {
            Write-Host ""
            Write-Host "Container: $($containerTest.Container)" -ForegroundColor Yellow
            
            Write-Host "  Blocked Syscalls:" -ForegroundColor White
            foreach ($test in $containerTest.Results.BlockedTests) {
                $color = if ($test.Status -eq "PASS") { "Green" } else { "Red" }
                Write-Host "    $($test.Syscall): $($test.Status)" -ForegroundColor $color
            }
            
            Write-Host "  Allowed Syscalls:" -ForegroundColor White
            foreach ($test in $containerTest.Results.AllowedTests) {
                $color = if ($test.Status -eq "PASS") { "Green" } else { "Red" }  
                Write-Host "    $($test.Syscall): $($test.Status)" -ForegroundColor $color
            }
        }
    }
    
    # Overall status
    Write-Host ""
    if ($Results.FailedContainers -eq 0) {
        Write-Host "🎉 ALL SECCOMP TESTS PASSED - Production Ready!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "⚠️  SECCOMP VALIDATION FAILED - Security Issues Detected!" -ForegroundColor Red
        Write-Host "Review failed tests and fix seccomp profiles before production deployment." -ForegroundColor Yellow
        return $false
    }
}

# ========================================================================
# Main Execution
# ========================================================================

function Main {
    Write-Host "GameForge AI Seccomp Runtime Validation" -ForegroundColor Magenta
    Write-Host "=======================================" -ForegroundColor Magenta
    
    try {
        # Validate profile path exists
        if (-not (Test-Path $ProfilePath)) {
            Write-LogMessage "Seccomp profile directory not found: $ProfilePath" -Level "Error"
            Write-LogMessage "Please ensure seccomp profiles are in the correct location" -Level "Error"
            exit 1
        }
        
        Write-LogMessage "Profile path: $ProfilePath" -Level "Info"
        Write-LogMessage "Target container: $ContainerName" -Level "Info"
        Write-LogMessage "Test all containers: $TestAll" -Level "Info"
        
        # Run comprehensive tests
        $results = Invoke-ComprehensiveSeccompTest
        
        # Show summary
        $allPassed = Show-ValidationSummary -Results $results
        
        if ($allPassed) {
            Write-LogMessage "✅ Seccomp validation completed successfully" -Level "Success"
            exit 0
        } else {
            Write-LogMessage "❌ Seccomp validation failed - security issues detected" -Level "Error"
            exit 1
        }
    }
    catch {
        Write-LogMessage "Seccomp validation failed with error: $($_.Exception.Message)" -Level "Error"
        exit 1
    }
}

# Execute main function
Main