# GameForge Production Guardrails - AI-Aware ASCII Version
# Designed specifically for AI gaming projects
# Run this before committing: .\scripts\guardrails-check-ai.ps1

param(
    [switch]$Verbose,
    [switch]$FixMode
)

Write-Host "GameForge Production Guardrails Check (AI-Aware)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$violations = 0
$warnings = 0

# AI Gaming Project Exclusions
$aiModelExtensions = @('.safetensors', '.onnx', '.msgpack', '.bin', '.pth', '.pkl')
$aiLibraryFiles = @('cv2.pyd', 'torch_cpu.dll', 'dnnl.lib', 'kineto.lib')
$modelDirectories = @('models', 'ai-models', 'checkpoints', 'weights', 'huggingface')

# Security Checks
Write-Host ""
Write-Host "SECURITY CHECKS" -ForegroundColor Yellow
Write-Host "---------------" -ForegroundColor Yellow

# Check for .env files
Write-Host "Checking for .env files..." -ForegroundColor White
$envFiles = @(Get-ChildItem -Recurse -File -Name "*.env*" -ErrorAction SilentlyContinue | Where-Object { 
    $_ -notlike "*.example" -and $_ -notlike "*.template" -and $_ -notlike "*node_modules*" 
})

if ($envFiles.Count -gt 0) {
    Write-Host "[X] BLOCKED: .env files detected!" -ForegroundColor Red
    $envFiles | ForEach-Object { Write-Host "  $($_)" -ForegroundColor Red }
    Write-Host "Solution: Use .env.example instead and add secrets to Vault/K8s" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No .env files found" -ForegroundColor Green
}

# Check for certificate/key files (excluding test certs)
Write-Host "Checking for certificate/key files..." -ForegroundColor White
$certFiles = @(Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Where-Object { 
    $_.Extension -in @('.pem', '.key', '.crt', '.p12', '.pfx') -and 
    $_.FullName -notlike "*node_modules*" -and
    $_.FullName -notlike "*test*" -and
    $_.FullName -notlike "*ai-models*" -and
    $_.Name -ne "cacert.pem"
})

if ($certFiles.Count -gt 0) {
    Write-Host "[X] BLOCKED: Certificate/key files detected!" -ForegroundColor Red
    $certFiles | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor Red }
    Write-Host "Solution: Use K8s TLS secrets or certificate managers" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No production certificate/key files found" -ForegroundColor Green
}

# Structure Checks
Write-Host ""
Write-Host "STRUCTURE CHECKS" -ForegroundColor Yellow
Write-Host "----------------" -ForegroundColor Yellow

# Check top-level file organization
Write-Host "Checking top-level file organization..." -ForegroundColor White
$allowedTopLevel = @(
    'src', 'docker', 'k8s', 'ci', 'scripts', 'docs', 'tests', 'ai-models',
    'package.json', 'package-lock.json', 'yarn.lock', 'README.md', 'LICENSE',
    '.gitignore', '.dockerignore', 'Dockerfile', 'docker-compose.yml',
    'requirements.txt', 'setup.py', '.env.example', 'components.json'
)

$topLevelItems = @(Get-ChildItem -Path . -ErrorAction SilentlyContinue | Where-Object { 
    $_.Name -notlike '.*' -or $_.Name -in @('.gitignore', '.dockerignore', '.env.example')
})

$violations_here = 0
foreach ($item in $topLevelItems) {
    $isAllowed = $false
    foreach ($allowed in $allowedTopLevel) {
        if ($item.Name -eq $allowed -or $item.Name -like "$allowed*") {
            $isAllowed = $true
            break
        }
    }
    
    # Allow markdown files and build/deploy scripts
    if (-not $isAllowed -and $item.Name -notlike "*.md" -and $item.Name -notlike "build-*" -and $item.Name -notlike "deploy-*") {
        if ($Verbose) {
            Write-Host "  [!] Unexpected top-level item: $($item.Name)" -ForegroundColor Yellow
        }
        $violations_here++
    }
}

if ($violations_here -gt 10) {
    Write-Host "[X] BLOCKED: Too many unexpected top-level files ($violations_here)!" -ForegroundColor Red
    Write-Host "Solution: Organize files into /src, /docker, /k8s, /ci directories" -ForegroundColor Yellow
    $violations++
} elseif ($violations_here -gt 5) {
    Write-Host "[!] WARNING: $violations_here unexpected top-level items" -ForegroundColor Yellow
    $warnings++
} else {
    Write-Host "[OK] Top-level organization acceptable ($violations_here minor items)" -ForegroundColor Green
}

# Check Docker Compose file count
Write-Host "Checking Docker Compose file count..." -ForegroundColor White
$composeFiles = @(Get-ChildItem -Recurse -File -Name "docker-compose*.yml", "docker-compose*.yaml" -ErrorAction SilentlyContinue)

if ($composeFiles.Count -gt 4) {
    Write-Host "[X] BLOCKED: Too many Docker Compose files ($($composeFiles.Count) > 4)!" -ForegroundColor Red
    Write-Host "Solution: Consolidate compose files or use overrides" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] Docker Compose file count OK ($($composeFiles.Count)/4)" -ForegroundColor Green
}

# Check Dockerfile count
Write-Host "Checking Dockerfile count..." -ForegroundColor White
$dockerfiles = @(Get-ChildItem -Recurse -File -Name "Dockerfile*" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*node_modules*" })

if ($dockerfiles.Count -gt 10) {
    Write-Host "[X] BLOCKED: Too many Dockerfiles ($($dockerfiles.Count) > 10)!" -ForegroundColor Red
    Write-Host "Solution: Use multi-stage builds instead" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] Dockerfile count reasonable ($($dockerfiles.Count)/10)" -ForegroundColor Green
}

# Dependency Checks
Write-Host ""
Write-Host "DEPENDENCY CHECKS" -ForegroundColor Yellow
Write-Host "-----------------" -ForegroundColor Yellow

# Check for mixed package managers
$npmLocks = @(Get-ChildItem -Recurse -File -Name "package-lock.json" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*node_modules*" })
$yarnLocks = @(Get-ChildItem -Recurse -File -Name "yarn.lock" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*node_modules*" })

if ($npmLocks.Count -gt 0 -and $yarnLocks.Count -gt 0) {
    Write-Host "[X] BLOCKED: Mixed package managers detected!" -ForegroundColor Red
    Write-Host "Solution: Choose either npm or yarn consistently" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] Package manager consistency maintained" -ForegroundColor Green
}

# File Size Checks (AI-Aware)
Write-Host ""
Write-Host "FILE SIZE CHECKS (AI-Gaming Aware)" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

# Separate AI models from other large files
$allLargeFiles = @(Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Where-Object { 
    $_.Length -gt 50MB -and $_.FullName -notlike "*node_modules*" -and $_.FullName -notlike "*\.git*"
})

$aiModelFiles = @($allLargeFiles | Where-Object {
    $isAiFile = $false
    # Check if it's an AI model extension
    if ($_.Extension -in $aiModelExtensions) { $isAiFile = $true }
    # Check if it's a known AI library file
    if ($_.Name -in $aiLibraryFiles) { $isAiFile = $true }
    # Check if it's in a model directory
    foreach ($modelDir in $modelDirectories) {
        if ($_.FullName -like "*$modelDir*") { $isAiFile = $true; break }
    }
    return $isAiFile
})

$otherLargeFiles = @($allLargeFiles | Where-Object {
    $_ -notin $aiModelFiles
})

if ($aiModelFiles.Count -gt 0) {
    Write-Host "[INFO] AI Model files detected (allowed for AI gaming project):" -ForegroundColor Cyan
    $totalAiSize = 0
    $aiModelFiles | ForEach-Object { 
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        $totalAiSize += $sizeMB
        if ($Verbose) {
            Write-Host "  $($_.Name) ($sizeMB MB)" -ForegroundColor Cyan
        }
    }
    Write-Host "  Total AI models: $($aiModelFiles.Count) files, $([math]::Round($totalAiSize/1024, 2)) GB" -ForegroundColor Cyan
}

if ($otherLargeFiles.Count -gt 0) {
    Write-Host "[X] BLOCKED: Non-AI large files detected (>50MB)!" -ForegroundColor Red
    $otherLargeFiles | ForEach-Object { 
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  $($_.Name) ($sizeMB MB)" -ForegroundColor Red 
    }
    Write-Host "Solution: Use Git LFS for large files or external storage" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No problematic large files detected" -ForegroundColor Green
}

# Final Report
Write-Host ""
Write-Host "GUARDRAILS SUMMARY" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

if ($violations -eq 0) {
    Write-Host "[PASS] ALL CHECKS PASSED - Ready to commit!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your AI gaming repository maintains:" -ForegroundColor White
    Write-Host "  [OK] Security standards (no secrets)" -ForegroundColor Green
    Write-Host "  [OK] Clean structure (proper organization)" -ForegroundColor Green
    Write-Host "  [OK] Reasonable file counts" -ForegroundColor Green
    Write-Host "  [OK] Consistent dependency management" -ForegroundColor Green
    Write-Host "  [OK] AI model files properly managed" -ForegroundColor Green
    
    if ($warnings -gt 0) {
        Write-Host ""
        Write-Host "NOTE: $warnings warning(s) detected - minor issues to consider" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Ready for production deployment!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] $violations VIOLATION(S) DETECTED!" -ForegroundColor Red
    
    if ($warnings -gt 0) {
        Write-Host "WARNING: $warnings warning(s) also found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Please fix the issues above and try again" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Quick fixes for AI gaming projects:" -ForegroundColor White
    Write-Host "  - Remove .env files and use .env.example" -ForegroundColor White
    Write-Host "  - Move top-level files to /src, /docker, /k8s, /ci" -ForegroundColor White
    Write-Host "  - Consolidate redundant Docker files" -ForegroundColor White
    Write-Host "  - Use secure secret management" -ForegroundColor White
    Write-Host "  - AI model files are automatically allowed" -ForegroundColor Cyan
    
    exit 1
}