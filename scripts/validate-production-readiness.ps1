# ========================================================================
# GameForge AI Production Validation Script
# Comprehensive testing of production-grade features
# ========================================================================

param(
    [string]$ComposeFile = "docker-compose.vastai-production.yml",
    [switch]$SkipSecurity = $false,
    [switch]$SkipMetrics = $false,
    [switch]$SkipStorage = $false,
    [switch]$Verbose = $false
)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "GameForge Production Validation" -ForegroundColor Cyan
Write-Host "Testing production-grade features" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0
$TestResults = @()

function Write-TestResult {
    param(
        [string]$TestName,
        [string]$Status,
        [string]$Message = "",
        [string]$Severity = "INFO"
    )
    
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        "SKIP" { "Cyan" }
        default { "White" }
    }
    
    Write-Host "[$Status] $TestName" -ForegroundColor $color
    if ($Message) {
        Write-Host "    $Message" -ForegroundColor Gray
    }
    
    $TestResults += @{
        Test = $TestName
        Status = $Status
        Message = $Message
        Severity = $Severity
    }
    
    if ($Status -eq "FAIL") { $script:ErrorCount++ }
    if ($Status -eq "WARN") { $script:WarningCount++ }
}

# ========================================================================
# 1. Validate Docker Compose Configuration
# ========================================================================
Write-Host "`n1. Docker Compose Configuration Validation" -ForegroundColor Yellow

if (Test-Path $ComposeFile) {
    Write-TestResult "Compose file exists" "PASS" "$ComposeFile found"
    
    # Test compose file syntax
    try {
        $composeContent = Get-Content $ComposeFile -Raw
        
        # Check for seccomp profiles
        if ($composeContent -match "seccomp=.*\.json") {
            Write-TestResult "Seccomp profiles configured" "PASS" "Found seccomp profile references"
        } else {
            Write-TestResult "Seccomp profiles configured" "WARN" "No seccomp profiles found in compose file"
        }
        
        # Check for non-root users
        if ($composeContent -match "user:\s*`"?1001:1001`"?") {
            Write-TestResult "Non-root user configuration" "PASS" "Found non-root user 1001:1001"
        } else {
            Write-TestResult "Non-root user configuration" "WARN" "No non-root user configuration found"
        }
        
        # Check for resource limits
        if ($composeContent -match "resources:" -and $composeContent -match "limits:") {
            Write-TestResult "Resource limits configured" "PASS" "Found resource limit configurations"
        } else {
            Write-TestResult "Resource limits configured" "WARN" "No resource limits found"
        }
        
        # Check for MinIO service
        if ($composeContent -match "minio:") {
            Write-TestResult "Model storage service" "PASS" "MinIO service configured"
        } else {
            Write-TestResult "Model storage service" "FAIL" "MinIO service not found"
        }
        
        # Check for metrics endpoints
        if ($composeContent -match "PROMETHEUS_METRICS_ENABLED") {
            Write-TestResult "Metrics endpoints" "PASS" "Prometheus metrics configuration found"
        } else {
            Write-TestResult "Metrics endpoints" "WARN" "No metrics configuration found"
        }
        
    } catch {
        Write-TestResult "Compose file syntax" "FAIL" "Error parsing compose file: $($_.Exception.Message)"
    }
} else {
    Write-TestResult "Compose file exists" "FAIL" "$ComposeFile not found"
}

# ========================================================================
# 2. Security Configuration Validation
# ========================================================================
if (-not $SkipSecurity) {
    Write-Host "`n2. Security Configuration Validation" -ForegroundColor Yellow
    
    # Check for seccomp profiles
    $seccompProfiles = @(
        "security/seccomp/gameforge-app.json",
        "security/seccomp/database.json", 
        "security/seccomp/nginx.json",
        "security/seccomp/vault.json"
    )
    
    foreach ($profile in $seccompProfiles) {
        if (Test-Path $profile) {
            Write-TestResult "Seccomp profile: $(Split-Path $profile -Leaf)" "PASS" "Profile found"
            
            # Validate JSON structure
            try {
                $profileContent = Get-Content $profile -Raw | ConvertFrom-Json
                if ($profileContent.defaultAction -and $profileContent.syscalls) {
                    Write-TestResult "Seccomp profile structure: $(Split-Path $profile -Leaf)" "PASS" "Valid structure"
                } else {
                    Write-TestResult "Seccomp profile structure: $(Split-Path $profile -Leaf)" "WARN" "Missing required fields"
                }
            } catch {
                Write-TestResult "Seccomp profile structure: $(Split-Path $profile -Leaf)" "FAIL" "Invalid JSON: $($_.Exception.Message)"
            }
        } else {
            Write-TestResult "Seccomp profile: $(Split-Path $profile -Leaf)" "FAIL" "Profile not found"
        }
    }
    
    # Check Dockerfile for non-root user
    if (Test-Path "Dockerfile.vastai-gpu") {
        $dockerfileContent = Get-Content "Dockerfile.vastai-gpu" -Raw
        if ($dockerfileContent -match "USER\s+[^0]" -or $dockerfileContent -match "RUN.*adduser") {
            Write-TestResult "Dockerfile non-root user" "PASS" "Non-root user configuration found"
        } else {
            Write-TestResult "Dockerfile non-root user" "WARN" "No non-root user found in Dockerfile"
        }
    } else {
        Write-TestResult "Dockerfile exists" "FAIL" "Dockerfile.vastai-gpu not found"
    }
}

# ========================================================================
# 3. Monitoring Configuration Validation
# ========================================================================
if (-not $SkipMetrics) {
    Write-Host "`n3. Monitoring Configuration Validation" -ForegroundColor Yellow
    
    # Check Prometheus configuration
    if (Test-Path "monitoring/prometheus-production.yml") {
        Write-TestResult "Prometheus config" "PASS" "Configuration file found"
        
        try {
            $prometheusConfig = Get-Content "monitoring/prometheus-production.yml" -Raw
            
            # Check for custom metrics endpoints
            if ($prometheusConfig -match "gameforge-app.*:8080") {
                Write-TestResult "App metrics endpoint" "PASS" "GameForge app metrics configured"
            } else {
                Write-TestResult "App metrics endpoint" "WARN" "App metrics endpoint not configured"
            }
            
            # Check for GPU metrics
            if ($prometheusConfig -match "gpu-inference.*:8080") {
                Write-TestResult "GPU metrics endpoint" "PASS" "GPU inference metrics configured"
            } else {
                Write-TestResult "GPU metrics endpoint" "WARN" "GPU metrics endpoint not configured"
            }
            
            # Check for security metrics
            if ($prometheusConfig -match "security.*metrics") {
                Write-TestResult "Security metrics" "PASS" "Security metrics configured"
            } else {
                Write-TestResult "Security metrics" "WARN" "Security metrics not configured"
            }
            
        } catch {
            Write-TestResult "Prometheus config syntax" "FAIL" "Error parsing: $($_.Exception.Message)"
        }
    } else {
        Write-TestResult "Prometheus config" "FAIL" "monitoring/prometheus-production.yml not found"
    }
    
    # Check Grafana dashboard
    if (Test-Path "monitoring/grafana-gameforge-dashboard.json") {
        Write-TestResult "Grafana dashboard" "PASS" "Dashboard configuration found"
        
        try {
            $dashboardConfig = Get-Content "monitoring/grafana-gameforge-dashboard.json" -Raw | ConvertFrom-Json
            $panelCount = $dashboardConfig.dashboard.panels.Count
            Write-TestResult "Dashboard panels" "PASS" "$panelCount panels configured"
        } catch {
            Write-TestResult "Dashboard JSON syntax" "FAIL" "Error parsing: $($_.Exception.Message)"
        }
    } else {
        Write-TestResult "Grafana dashboard" "WARN" "Dashboard configuration not found"
    }
}

# ========================================================================
# 4. Model Storage Configuration Validation
# ========================================================================
if (-not $SkipStorage) {
    Write-Host "`n4. Model Storage Configuration Validation" -ForegroundColor Yellow
    
    # Check model storage configuration
    if (Test-Path "config/model-storage.env") {
        Write-TestResult "Model storage config" "PASS" "Configuration file found"
        
        $storageConfig = Get-Content "config/model-storage.env" -Raw
        
        # Check for MinIO configuration
        if ($storageConfig -match "MINIO_ENDPOINT") {
            Write-TestResult "MinIO endpoint config" "PASS" "MinIO endpoint configured"
        } else {
            Write-TestResult "MinIO endpoint config" "WARN" "MinIO endpoint not configured"
        }
        
        # Check for model cache configuration
        if ($storageConfig -match "MODEL_CACHE_ENABLED") {
            Write-TestResult "Model cache config" "PASS" "Model caching configured"
        } else {
            Write-TestResult "Model cache config" "WARN" "Model caching not configured"
        }
        
        # Check for security scanning
        if ($storageConfig -match "MODEL_SECURITY_SCAN_ON_DOWNLOAD") {
            Write-TestResult "Model security scanning" "PASS" "Security scanning configured"
        } else {
            Write-TestResult "Model security scanning" "WARN" "Security scanning not configured"
        }
        
    } else {
        Write-TestResult "Model storage config" "FAIL" "config/model-storage.env not found"
    }
}

# ========================================================================
# 5. Docker Compose Syntax Validation
# ========================================================================
Write-Host "`n5. Docker Compose Syntax Validation" -ForegroundColor Yellow

try {
    $validateOutput = docker-compose -f $ComposeFile config 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-TestResult "Compose syntax validation" "PASS" "Docker Compose syntax is valid"
    } else {
        Write-TestResult "Compose syntax validation" "FAIL" "Syntax errors: $validateOutput"
    }
} catch {
    Write-TestResult "Compose syntax validation" "WARN" "Docker Compose not available for validation"
}

# ========================================================================
# 6. Production Readiness Checklist
# ========================================================================
Write-Host "`n6. Production Readiness Assessment" -ForegroundColor Yellow

$readinessChecks = @{
    "Security hardening (seccomp profiles)" = ($composeContent -match "seccomp=.*\.json")
    "Non-root container execution" = ($composeContent -match "user:\s*`"?1001:1001`"?")
    "Resource limits configured" = ($composeContent -match "resources:" -and $composeContent -match "limits:")
    "Monitoring and metrics" = ($composeContent -match "PROMETHEUS_METRICS_ENABLED")
    "External model storage" = ($composeContent -match "minio:")
    "Health checks configured" = ($composeContent -match "healthcheck:")
    "Logging configuration" = ($composeContent -match "logging:")
    "Secret management" = ($composeContent -match "VAULT")
    "GPU optimization" = ($composeContent -match "runtime: nvidia")
    "Network isolation" = ($composeContent -match "networks:")
}

foreach ($check in $readinessChecks.GetEnumerator()) {
    if ($check.Value) {
        Write-TestResult $check.Key "PASS"
    } else {
        Write-TestResult $check.Key "FAIL"
    }
}

# ========================================================================
# Summary Report
# ========================================================================
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Production Validation Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$totalTests = $TestResults.Count
if ($totalTests -eq 0) { $totalTests = 1 }  # Prevent division by zero
$passedTests = ($TestResults | Where-Object { $_.Status -eq "PASS" }).Count
$failedTests = ($TestResults | Where-Object { $_.Status -eq "FAIL" }).Count
$warningTests = ($TestResults | Where-Object { $_.Status -eq "WARN" }).Count
$skippedTests = ($TestResults | Where-Object { $_.Status -eq "SKIP" }).Count

Write-Host "Total Tests: $totalTests" -ForegroundColor White
Write-Host "Passed: $passedTests" -ForegroundColor Green
Write-Host "Failed: $failedTests" -ForegroundColor Red
Write-Host "Warnings: $warningTests" -ForegroundColor Yellow
Write-Host "Skipped: $skippedTests" -ForegroundColor Cyan

$successRate = [math]::Round(($passedTests / $totalTests) * 100, 1)
Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -gt 80) { "Green" } elseif ($successRate -gt 60) { "Yellow" } else { "Red" })

if ($failedTests -eq 0 -and $warningTests -le 2) {
    Write-Host "`n🎉 PRODUCTION READY!" -ForegroundColor Green
    Write-Host "The GameForge AI platform is ready for production deployment." -ForegroundColor Green
} elseif ($failedTests -le 2) {
    Write-Host "`n⚠️  NEARLY PRODUCTION READY" -ForegroundColor Yellow
    Write-Host "Minor issues need to be resolved before production deployment." -ForegroundColor Yellow
} else {
    Write-Host "`n❌ NOT PRODUCTION READY" -ForegroundColor Red
    Write-Host "Critical issues must be resolved before production deployment." -ForegroundColor Red
}

Write-Host "`nValidation completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Return appropriate exit code
if ($failedTests -gt 0) {
    exit 1
} else {
    exit 0
}