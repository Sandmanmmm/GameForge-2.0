# Security Profiles Validation Script
# ===================================
# Validates seccomp and AppArmor profiles for production deployment

Write-Host "GameForge Security Profiles Validation" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Test 1: Validate Seccomp Profiles
Write-Host "`n1. Validating Seccomp Profiles..." -ForegroundColor Yellow

$seccompProfiles = @(
    "security/seccomp/vault.json",
    "security/seccomp/gameforge-app.json", 
    "security/seccomp/database.json",
    "security/seccomp/nginx.json"
)

$seccompValid = $true
foreach ($seccompProfile in $seccompProfiles) {
    if (Test-Path $seccompProfile) {
        try {
            $content = Get-Content $seccompProfile | ConvertFrom-Json -ErrorAction Stop
            if ($content.defaultAction -and $content.syscalls) {
                Write-Host "✅ Valid: $seccompProfile" -ForegroundColor Green
                Write-Host "   Default Action: $($content.defaultAction)" -ForegroundColor Gray
                Write-Host "   Syscalls Rules: $($content.syscalls.Count)" -ForegroundColor Gray
            } else {
                Write-Host "❌ Invalid structure: $seccompProfile" -ForegroundColor Red
                $seccompValid = $false
            }
        } catch {
            Write-Host "❌ JSON parsing failed: $seccompProfile - $_" -ForegroundColor Red
            $seccompValid = $false
        }
    } else {
        Write-Host "❌ Missing: $seccompProfile" -ForegroundColor Red
        $seccompValid = $false
    }
}

# Test 2: Check AppArmor Profile References
Write-Host "`n2. Checking AppArmor Profile References..." -ForegroundColor Yellow

$composeContent = Get-Content "docker-compose.production-hardened.yml" -Raw
$appArmorProfiles = @(
    "gameforge-app",
    "nginx-container", 
    "database-container"
)

$appArmorValid = $true
foreach ($appArmorProfile in $appArmorProfiles) {
    if ($composeContent -match "apparmor:$appArmorProfile") {
        Write-Host "✅ Referenced: apparmor:$appArmorProfile" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Not found: apparmor:$appArmorProfile" -ForegroundColor Yellow
        $appArmorValid = $false
    }
}

# Test 3: Validate Vault Security Configuration  
Write-Host "`n3. Validating Vault Security Configuration..." -ForegroundColor Yellow

$vaultConfigFiles = @(
    "vault/config/vault.hcl",
    "vault/policies/gameforge-app.hcl"
)

$vaultValid = $true
foreach ($file in $vaultConfigFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        if ($content.Length -gt 0) {
            Write-Host "✅ Valid: $file" -ForegroundColor Green
            Write-Host "   Size: $($content.Length) bytes" -ForegroundColor Gray
        } else {
            Write-Host "❌ Empty: $file" -ForegroundColor Red
            $vaultValid = $false
        }
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        $vaultValid = $false
    }
}

# Test 4: Security Options Validation
Write-Host "`n4. Validating Security Options in Compose..." -ForegroundColor Yellow

$securityChecks = @{
    "no-new-privileges:true" = "No new privileges enforcement"
    "seccomp=" = "Seccomp profile configuration"
    "apparmor:" = "AppArmor profile configuration" 
    "cap_drop:" = "Capability dropping"
    "cap_add:" = "Specific capability grants"
    "read_only:" = "Read-only filesystem"
    "tmpfs:" = "Temporary filesystem mounts"
}

$securityValid = $true
foreach ($check in $securityChecks.GetEnumerator()) {
    if ($composeContent -match [regex]::Escape($check.Key)) {
        Write-Host "✅ Found: $($check.Key) - $($check.Value)" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $($check.Key) - $($check.Value)" -ForegroundColor Red
        $securityValid = $false
    }
}

# Test 5: User/Permission Configuration
Write-Host "`n5. Validating User/Permission Configuration..." -ForegroundColor Yellow

$userConfigs = @(
    "user.*1001:1001.*# App user",
    "user.*999:999.*# Database user", 
    "user.*101:101.*# Nginx user",
    "user.*100:1000.*# Vault user"
)

foreach ($config in $userConfigs) {
    if ($composeContent -match $config.Split('#')[0].Trim()) {
        $description = $config.Split('#')[1].Trim()
        Write-Host "✅ Found: $description" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Check: $config" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`nSecurity Validation Summary:" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan

$overall = $seccompValid -and $appArmorValid -and $vaultValid -and $securityValid

if ($overall) {
    Write-Host "✅ SECURITY VALIDATION PASSED" -ForegroundColor Green
    Write-Host "All security profiles and configurations are valid" -ForegroundColor Green
} else {
    Write-Host "⚠️ SECURITY VALIDATION WARNINGS" -ForegroundColor Yellow
    Write-Host "Some security configurations need attention" -ForegroundColor Yellow
}

Write-Host "`nSecurity Status:" -ForegroundColor White
Write-Host "- Seccomp Profiles: $(if($seccompValid){'✅ Valid'}else{'❌ Issues'})" -ForegroundColor White
Write-Host "- AppArmor References: $(if($appArmorValid){'✅ Valid'}else{'⚠️ Check'})" -ForegroundColor White  
Write-Host "- Vault Security: $(if($vaultValid){'✅ Valid'}else{'❌ Issues'})" -ForegroundColor White
Write-Host "- Security Options: $(if($securityValid){'✅ Valid'}else{'❌ Issues'})" -ForegroundColor White

Write-Host "`nNote: AppArmor requires Linux host with AppArmor enabled" -ForegroundColor Yellow
