# GameForge Production Phase 2 Validation Script
# Comprehensive Testing for CPU/GPU Variants

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("cpu", "gpu", "both")]
    [string]$Variant = "both",
    
    [Parameter(Mandatory=$false)]
    [string]$Registry = "your-registry.com/gameforge",
    
    [Parameter(Mandatory=$false)]
    [string]$Tag = "latest",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSizeCheck,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSecurityCheck,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipFunctionalCheck,
    
    [Parameter(Mandatory=$false)]
    [switch]$Detailed
)

# Colors
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

function Test-ImageExists {
    param([string]$ImageTag)
    
    try {
        docker images $ImageTag --format "{{.Repository}}:{{.Tag}}" | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Test-ImageSecurity {
    param([string]$ImageTag)
    
    Write-ColorOutput "🔒 Security Tests for: $ImageTag" -Color $InfoColor
    $tests = @{}
    
    # Test 1: Non-root user
    try {
        $userId = docker run --rm $ImageTag id -u 2>$null
        if ($userId -eq "1001") {
            Write-ColorOutput "  ✅ Non-root user (UID: $userId)" -Color $SuccessColor
            $tests['non_root'] = $true
        }
        else {
            Write-ColorOutput "  ❌ Wrong user ID: $userId (expected: 1001)" -Color $ErrorColor
            $tests['non_root'] = $false
        }
    }
    catch {
        Write-ColorOutput "  ❌ Failed to check user ID" -Color $ErrorColor
        $tests['non_root'] = $false
    }
    
    # Test 2: Environment validation
    try {
        $result = docker run --rm -e GAMEFORGE_ENV=development $ImageTag echo "test" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "  ✅ Environment validation (rejects non-production)" -Color $SuccessColor
            $tests['env_validation'] = $true
        }
        else {
            Write-ColorOutput "  ❌ Environment validation failed" -Color $ErrorColor
            $tests['env_validation'] = $false
        }
    }
    catch {
        Write-ColorOutput "  ✅ Environment validation (caught by entrypoint)" -Color $SuccessColor
        $tests['env_validation'] = $true
    }
    
    # Test 3: Directory permissions
    try {
        $dirTest = docker run --rm $ImageTag bash -c "
            for dir in logs cache generated_assets models_cache tmp; do
                if [ ! -w \"/app/\$dir\" ]; then
                    echo \"FAIL: \$dir not writable\"
                    exit 1
                fi
            done
            echo 'All directories writable'
        "
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "  ✅ Directory permissions correct" -Color $SuccessColor
            $tests['permissions'] = $true
        }
        else {
            Write-ColorOutput "  ❌ Directory permission issues" -Color $ErrorColor
            $tests['permissions'] = $false
        }
    }
    catch {
        Write-ColorOutput "  ❌ Failed to check directory permissions" -Color $ErrorColor
        $tests['permissions'] = $false
    }
    
    # Test 4: Python environment
    try {
        $pythonTest = docker run --rm $ImageTag python3 -c "
import sys
import os
print(f'Python {sys.version}')
print(f'User: {os.getuid()}')
print(f'Env: {os.environ.get(\"GAMEFORGE_ENV\", \"NOT_SET\")}')
"
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "  ✅ Python environment working" -Color $SuccessColor
            $tests['python_env'] = $true
            
            if ($Detailed) {
                $pythonTest | ForEach-Object { Write-ColorOutput "    $_" -Color "Gray" }
            }
        }
        else {
            Write-ColorOutput "  ❌ Python environment issues" -Color $ErrorColor
            $tests['python_env'] = $false
        }
    }
    catch {
        Write-ColorOutput "  ❌ Failed to test Python environment" -Color $ErrorColor
        $tests['python_env'] = $false
    }
    
    return $tests
}

function Test-ImageSize {
    param([string]$ImageTag, [string]$Variant)
    
    Write-ColorOutput "📦 Size Tests for: $ImageTag" -Color $InfoColor
    
    try {
        $sizeInfo = docker images $ImageTag --format "table {{.Size}}" | Select-Object -Skip 1
        $size = $sizeInfo.Trim()
        
        Write-ColorOutput "  Image size: $size" -Color "Gray"
        
        # Size targets
        $targets = @{
            "cpu" = @{ Target = 500; Unit = "MB" }
            "gpu" = @{ Target = 3000; Unit = "MB" }
        }
        
        if ($size -match "(\d+(?:\.\d+)?)(MB|GB)") {
            $sizeValue = [float]$matches[1]
            $unit = $matches[2]
            
            if ($unit -eq "GB") {
                $sizeValue = $sizeValue * 1024
            }
            
            $target = $targets[$Variant].Target
            if ($sizeValue -le $target) {
                Write-ColorOutput "  ✅ Size within target ($target MB)" -Color $SuccessColor
                return @{ Pass = $true; Size = $size; SizeMB = $sizeValue }
            }
            else {
                Write-ColorOutput "  ⚠️  Size exceeds target ($target MB)" -Color $WarningColor
                return @{ Pass = $false; Size = $size; SizeMB = $sizeValue }
            }
        }
        else {
            Write-ColorOutput "  ⚠️  Could not parse size format" -Color $WarningColor
            return @{ Pass = $false; Size = $size; SizeMB = 0 }
        }
    }
    catch {
        Write-ColorOutput "  ❌ Failed to get image size" -Color $ErrorColor
        return @{ Pass = $false; Size = "Error"; SizeMB = 0 }
    }
}

function Test-ImageFunctionality {
    param([string]$ImageTag, [string]$Variant)
    
    Write-ColorOutput "⚙️ Functionality Tests for: $ImageTag" -Color $InfoColor
    $tests = @{}
    
    # Test 1: Container startup
    try {
        Write-ColorOutput "  Testing container startup..." -Color "Gray"
        $containerId = docker run -d -p 0:8080 -e GAMEFORGE_ENV=production $ImageTag
        
        if ($containerId) {
            Start-Sleep -Seconds 10  # Wait for startup
            
            # Check if container is still running
            $containerStatus = docker ps --filter "id=$containerId" --format "{{.Status}}"
            
            if ($containerStatus -like "*Up*") {
                Write-ColorOutput "  ✅ Container starts successfully" -Color $SuccessColor
                $tests['startup'] = $true
                
                # Test health check endpoint
                try {
                    $port = docker port $containerId 8080 | ForEach-Object { $_.Split(':')[1] }
                    $healthUrl = "http://localhost:$port/health"
                    
                    # Wait a bit more for the app to be ready
                    Start-Sleep -Seconds 20
                    
                    $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 30 -UseBasicParsing
                    
                    if ($response.StatusCode -eq 200) {
                        Write-ColorOutput "  ✅ Health check endpoint responding" -Color $SuccessColor
                        $tests['health_check'] = $true
                    }
                    else {
                        Write-ColorOutput "  ❌ Health check returned: $($response.StatusCode)" -Color $ErrorColor
                        $tests['health_check'] = $false
                    }
                }
                catch {
                    Write-ColorOutput "  ⚠️  Health check endpoint not accessible: $($_.Exception.Message)" -Color $WarningColor
                    $tests['health_check'] = $false
                }
            }
            else {
                Write-ColorOutput "  ❌ Container failed to start properly" -Color $ErrorColor
                $tests['startup'] = $false
                
                # Show logs for debugging
                if ($Detailed) {
                    Write-ColorOutput "  Container logs:" -Color "Gray"
                    docker logs $containerId | ForEach-Object { Write-ColorOutput "    $_" -Color "Gray" }
                }
            }
            
            # Cleanup
            docker stop $containerId | Out-Null
            docker rm $containerId | Out-Null
        }
        else {
            Write-ColorOutput "  ❌ Failed to start container" -Color $ErrorColor
            $tests['startup'] = $false
        }
    }
    catch {
        Write-ColorOutput "  ❌ Container startup test failed: $($_.Exception.Message)" -Color $ErrorColor
        $tests['startup'] = $false
        $tests['health_check'] = $false
    }
    
    # Test 2: GPU availability (for GPU variant)
    if ($Variant -eq "gpu") {
        try {
            Write-ColorOutput "  Testing GPU availability..." -Color "Gray"
            $gpuTest = docker run --rm --gpus all $ImageTag nvidia-smi --query-gpu=name --format=csv,noheader,nounits
            
            if ($LASTEXITCODE -eq 0 -and $gpuTest) {
                Write-ColorOutput "  ✅ GPU accessible: $($gpuTest -join ', ')" -Color $SuccessColor
                $tests['gpu_access'] = $true
            }
            else {
                Write-ColorOutput "  ❌ GPU not accessible" -Color $ErrorColor
                $tests['gpu_access'] = $false
            }
        }
        catch {
            Write-ColorOutput "  ⚠️  GPU test failed (may be expected in non-GPU environment)" -Color $WarningColor
            $tests['gpu_access'] = $false
        }
    }
    
    return $tests
}

function New-ValidationReport {
    param([hashtable]$Results)
    
    Write-Section "Validation Report"
    
    $overallPass = $true
    $totalTests = 0
    $passedTests = 0
    
    foreach ($variant in $Results.Keys) {
        Write-ColorOutput "`n${variant.ToUpper()} Variant Results:" -Color $InfoColor
        
        $variantResults = $Results[$variant]
        
        # Image existence
        if ($variantResults.Exists) {
            Write-ColorOutput "  ✅ Image exists" -Color $SuccessColor
        }
        else {
            Write-ColorOutput "  ❌ Image not found" -Color $ErrorColor
            $overallPass = $false
            continue
        }
        
        # Size results
        if ($variantResults.ContainsKey('Size')) {
            $sizeResult = $variantResults.Size
            $status = if ($sizeResult.Pass) { "✅" } else { "⚠️" }
            Write-ColorOutput "  $status Size: $($sizeResult.Size)" -Color $(if ($sizeResult.Pass) { $SuccessColor } else { $WarningColor })
        }
        
        # Security results
        if ($variantResults.ContainsKey('Security')) {
            $securityResults = $variantResults.Security
            foreach ($testName in $securityResults.Keys) {
                $testResult = $securityResults[$testName]
                $status = if ($testResult) { "✅" } else { "❌" }
                $color = if ($testResult) { $SuccessColor } else { $ErrorColor }
                Write-ColorOutput "  $status Security: $testName" -Color $color
                
                $totalTests++
                if ($testResult) { $passedTests++ } else { $overallPass = $false }
            }
        }
        
        # Functionality results
        if ($variantResults.ContainsKey('Functionality')) {
            $funcResults = $variantResults.Functionality
            foreach ($testName in $funcResults.Keys) {
                $testResult = $funcResults[$testName]
                $status = if ($testResult) { "✅" } else { "❌" }
                $color = if ($testResult) { $SuccessColor } else { $ErrorColor }
                Write-ColorOutput "  $status Function: $testName" -Color $color
                
                $totalTests++
                if ($testResult) { $passedTests++ } else { $overallPass = $false }
            }
        }
    }
    
    # Overall summary
    Write-ColorOutput "`nOverall Results:" -Color $InfoColor
    Write-ColorOutput "  Tests Passed: $passedTests/$totalTests" -Color $(if ($overallPass) { $SuccessColor } else { $WarningColor })
    
    if ($overallPass) {
        Write-ColorOutput "🎉 All validation tests passed!" -Color $SuccessColor
        return $true
    }
    else {
        Write-ColorOutput "💥 Some validation tests failed." -Color $ErrorColor
        return $false
    }
}

# ========================================================================
# Main Execution
# ========================================================================

Write-Section "GameForge Production Phase 2 Validation"
Write-ColorOutput "Comprehensive Testing for CPU/GPU Variants" -Color $InfoColor

# Determine variants to test
$variants = switch ($Variant) {
    "both" { @("cpu", "gpu") }
    default { @($Variant) }
}

$validationResults = @{}

foreach ($testVariant in $variants) {
    $imageTag = "${Registry}:${Tag}-${testVariant}"
    Write-ColorOutput "`nTesting variant: $testVariant" -Color $InfoColor
    Write-ColorOutput "Image tag: $imageTag" -Color "Gray"
    
    $variantResults = @{}
    
    # Check if image exists
    if (Test-ImageExists -ImageTag $imageTag) {
        $variantResults.Exists = $true
        Write-ColorOutput "✅ Image found" -Color $SuccessColor
        
        # Size check
        if (-not $SkipSizeCheck) {
            $variantResults.Size = Test-ImageSize -ImageTag $imageTag -Variant $testVariant
        }
        
        # Security check
        if (-not $SkipSecurityCheck) {
            $variantResults.Security = Test-ImageSecurity -ImageTag $imageTag
        }
        
        # Functionality check
        if (-not $SkipFunctionalCheck) {
            $variantResults.Functionality = Test-ImageFunctionality -ImageTag $imageTag -Variant $testVariant
        }
    }
    else {
        $variantResults.Exists = $false
        Write-ColorOutput "❌ Image not found: $imageTag" -Color $ErrorColor
    }
    
    $validationResults[$testVariant] = $variantResults
}

# Generate final report
$success = New-ValidationReport -Results $validationResults

if ($success) {
    exit 0
}
else {
    exit 1
}
