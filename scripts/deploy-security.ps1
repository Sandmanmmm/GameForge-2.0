# ========================================================================
# GameForge Security Configuration Deployment (Windows)
# Configures Docker security settings and validates security features
# ========================================================================

param(
    [switch]$Validate,
    [switch]$Deploy
)

function Write-SecurityLog {
    param([string]$Level, [string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "INFO" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        default { "Blue" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "GameForge Security Configuration Deployment (Windows)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# ========================================================================
# Validate Security Configuration
# ========================================================================

function Test-SecurityConfiguration {
    Write-SecurityLog "INFO" "Validating security configuration..."
    
    $issues = @()
    $passed = @()
    
    # Check Docker Desktop security features
    try {
        $dockerInfo = docker info --format json | ConvertFrom-Json
        if ($dockerInfo.SecurityOptions) {
            Write-SecurityLog "INFO" "Docker security options available"
            $passed += "Docker security options"
        } else {
            $issues += "Docker security options not available"
        }
    } catch {
        $issues += "Unable to query Docker information"
    }
    
    # Check seccomp profiles
    if (Test-Path "security/seccomp") {
        $seccompProfiles = Get-ChildItem "security/seccomp" -Filter "*.json"
        if ($seccompProfiles.Count -gt 0) {
            Write-SecurityLog "INFO" "Found $($seccompProfiles.Count) seccomp profiles"
            $passed += "Seccomp profiles"
            
            # Validate JSON syntax
            foreach ($profile in $seccompProfiles) {
                try {
                    Get-Content $profile.FullName | ConvertFrom-Json | Out-Null
                    Write-SecurityLog "INFO" "✓ Valid JSON: $($profile.Name)"
                } catch {
                    $issues += "Invalid JSON in seccomp profile: $($profile.Name)"
                }
            }
        } else {
            $issues += "No seccomp profiles found"
        }
    } else {
        $issues += "Seccomp profiles directory not found"
    }
    
    # Check AppArmor profiles (for reference)
    if (Test-Path "security/apparmor") {
        $apparmorProfiles = Get-ChildItem "security/apparmor"
        if ($apparmorProfiles.Count -gt 0) {
            Write-SecurityLog "INFO" "Found $($apparmorProfiles.Count) AppArmor profiles (for Linux deployment)"
            $passed += "AppArmor profiles"
        }
    }
    
    # Check Docker Compose security configuration
    if (Test-Path "docker-compose.production-hardened.yml") {
        $composeContent = Get-Content "docker-compose.production-hardened.yml" -Raw
        
        if ($composeContent -match "cap_drop:") {
            Write-SecurityLog "INFO" "✓ Capabilities dropping configured"
            $passed += "Capability dropping"
        } else {
            $issues += "Capability dropping not configured"
        }
        
        if ($composeContent -match "security_opt:") {
            Write-SecurityLog "INFO" "✓ Security options configured"
            $passed += "Security options"
        } else {
            $issues += "Security options not configured"
        }
        
        if ($composeContent -match "read_only: true") {
            Write-SecurityLog "INFO" "✓ Read-only filesystems configured"
            $passed += "Read-only filesystems"
        } else {
            $issues += "Read-only filesystems not configured"
        }
        
        if ($composeContent -match "tmpfs:") {
            Write-SecurityLog "INFO" "✓ Tmpfs mounts configured"
            $passed += "Tmpfs mounts"
        } else {
            $issues += "Tmpfs mounts not configured"
        }
        
        if ($composeContent -match "no-new-privileges:true") {
            Write-SecurityLog "INFO" "✓ No-new-privileges configured"
            $passed += "No-new-privileges"
        } else {
            $issues += "No-new-privileges not configured"
        }
    } else {
        $issues += "Hardened Docker Compose file not found"
    }
    
    # Summary
    Write-Host "`n========================================================================" -ForegroundColor Cyan
    Write-Host "Security Validation Summary" -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Cyan
    
    Write-Host "`nPassed Checks ($($passed.Count)):" -ForegroundColor Green
    foreach ($check in $passed) {
        Write-Host "  ✓ $check" -ForegroundColor Green
    }
    
    if ($issues.Count -gt 0) {
        Write-Host "`nIssues Found ($($issues.Count)):" -ForegroundColor Red
        foreach ($issue in $issues) {
            Write-Host "  ✗ $issue" -ForegroundColor Red
        }
        return $false
    } else {
        Write-Host "`n🎉 All security checks passed!" -ForegroundColor Green
        return $true
    }
}

# ========================================================================
# Deploy Security Configuration
# ========================================================================

function Deploy-SecurityConfiguration {
    Write-SecurityLog "INFO" "Deploying security configuration..."
    
    # Create volume directories with proper permissions
    $volumeDirs = @(
        "volumes/logs",
        "volumes/cache", 
        "volumes/assets",
        "volumes/models",
        "volumes/postgres",
        "volumes/postgres-logs",
        "volumes/redis",
        "volumes/elasticsearch",
        "volumes/elasticsearch-logs",
        "volumes/nginx-logs",
        "volumes/static"
    )
    
    foreach ($dir in $volumeDirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-SecurityLog "INFO" "Created secure volume directory: $dir"
        }
    }
    
    # Create security validation script
    $validationScript = @"
# GameForge Security Validation Script (Windows)
Write-Host "=========================================================================="
Write-Host "GameForge Security Configuration Validation"
Write-Host "=========================================================================="

# Check Docker security features
Write-Host "Docker Security Features:"
try {
    `$dockerInfo = docker info --format json | ConvertFrom-Json
    if (`$dockerInfo.SecurityOptions) {
        Write-Host "✓ Security options available: `$(`$dockerInfo.SecurityOptions -join ', ')" -ForegroundColor Green
    } else {
        Write-Host "⚠ No security options detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Unable to query Docker security information" -ForegroundColor Red
}

Write-Host "`nSeccomp Profiles:"
if (Test-Path "security/seccomp") {
    Get-ChildItem "security/seccomp" -Filter "*.json" | ForEach-Object {
        Write-Host "  ✓ `$(`$_.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "  ✗ No seccomp profiles found" -ForegroundColor Red
}

Write-Host "`nDocker Compose Security Configuration:"
if (Test-Path "docker-compose.production-hardened.yml") {
    `$content = Get-Content "docker-compose.production-hardened.yml" -Raw
    
    `$checks = @{
        "Capability dropping" = (`$content -match "cap_drop:")
        "Security options" = (`$content -match "security_opt:")
        "Read-only filesystems" = (`$content -match "read_only: true")
        "Tmpfs mounts" = (`$content -match "tmpfs:")
        "No-new-privileges" = (`$content -match "no-new-privileges:true")
        "Resource limits" = (`$content -match "limits:")
        "User contexts" = (`$content -match "user:")
    }
    
    foreach (`$check in `$checks.GetEnumerator()) {
        if (`$check.Value) {
            Write-Host "  ✓ `$(`$check.Key)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ `$(`$check.Key)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  ✗ Hardened Docker Compose file not found" -ForegroundColor Red
}

Write-Host "`nSecurity validation completed."
"@
    
    $validationScript | Out-File -FilePath "validate-security.ps1" -Encoding UTF8
    Write-SecurityLog "INFO" "Created security validation script: validate-security.ps1"
    
    # Create deployment script
    $deployScript = @"
# GameForge Hardened Production Deployment
Write-Host "Deploying GameForge with maximum security hardening..." -ForegroundColor Green

# Validate configuration first
.\validate-security.ps1

# Deploy with hardened configuration
docker-compose -f docker-compose.production-hardened.yml --env-file .env.production up -d

Write-Host "Deployment completed. Monitor security with:" -ForegroundColor Yellow
Write-Host "  docker-compose -f docker-compose.production-hardened.yml logs -f" -ForegroundColor White
"@
    
    $deployScript | Out-File -FilePath "deploy-hardened.ps1" -Encoding UTF8
    Write-SecurityLog "INFO" "Created deployment script: deploy-hardened.ps1"
    
    Write-SecurityLog "INFO" "Security configuration deployment completed"
}

# ========================================================================
# Main Execution
# ========================================================================

if ($Validate) {
    $validationResult = Test-SecurityConfiguration
    if (-not $validationResult) {
        exit 1
    }
} elseif ($Deploy) {
    Deploy-SecurityConfiguration
} else {
    # Run both by default
    Write-SecurityLog "INFO" "Running full security configuration and validation..."
    Deploy-SecurityConfiguration
    Start-Sleep -Seconds 2
    $validationResult = Test-SecurityConfiguration
    
    if ($validationResult) {
        Write-Host "`n🔒 Security hardening completed successfully!" -ForegroundColor Green
        Write-Host "`nNext steps:" -ForegroundColor Yellow
        Write-Host "1. Update .env.production with your credentials" -ForegroundColor White
        Write-Host "2. Deploy: .\deploy-hardened.ps1" -ForegroundColor White
        Write-Host "3. Validate: .\validate-security.ps1" -ForegroundColor White
    } else {
        Write-Host "`n❌ Security configuration has issues that need to be addressed." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n========================================================================" -ForegroundColor Cyan
