# Enhanced Production Guardrails - Hardened Standards Enforcement
# Enforces Alpine/Distroless base images and prevents service definition duplication
# Run this before committing: .\scripts\guardrails-hardened.ps1

param(
    [switch]$Verbose,
    [switch]$FixMode,
    [switch]$Strict
)

Write-Host "GameForge Hardened Production Guardrails" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$violations = 0
$warnings = 0

# Hardened Standards Configuration
$approvedBaseImages = @(
    # Distroless (Preferred)
    'gcr.io/distroless/*',
    'gcr.io/google-appengine/python',
    # Alpine (Acceptable)
    '*:*-alpine*',
    'alpine:*',
    # Specific approved minimal images
    'nginx:alpine',
    'redis:*-alpine',
    'postgres:*-alpine',
    'node:*-alpine',
    'python:*-alpine',
    # GPU (Special case - must be CUDA runtime, not devel)
    'nvidia/cuda:*-runtime-*'
)

$prohibitedBaseImages = @(
    # Bloated full distributions
    'ubuntu:*',
    'debian:*',
    'centos:*',
    'fedora:*',
    # Development images in production
    '*:*-devel*',
    '*:*-dev*',
    'nvidia/cuda:*-devel-*',
    # Latest tags (unpinned)
    '*:latest'
)

$requiredDirectoryStructure = @(
    'src', 'docker', 'k8s', 'ci', 'scripts', 'docs', 'tests', 'config'
)

# Security Checks
Write-Host ""
Write-Host "HARDENED SECURITY CHECKS" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow

# Check for .env files (unchanged from AI-aware version)
Write-Host "Checking for .env files..." -ForegroundColor White
$envFiles = @(Get-ChildItem -Recurse -File -Name "*.env*" -ErrorAction SilentlyContinue | Where-Object { 
    $_ -notlike "*.example" -and $_ -notlike "*.template" -and $_ -notlike "*node_modules*" 
})

if ($envFiles.Count -gt 0) {
    Write-Host "[X] BLOCKED: .env files detected!" -ForegroundColor Red
    $envFiles | ForEach-Object { Write-Host "  $($_)" -ForegroundColor Red }
    Write-Host "Solution: Use .env.example and external secret management" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] No .env files found" -ForegroundColor Green
}

# Docker Image Hardening Checks
Write-Host ""
Write-Host "DOCKER HARDENING CHECKS" -ForegroundColor Yellow
Write-Host "-----------------------" -ForegroundColor Yellow

Write-Host "Checking base image compliance..." -ForegroundColor White
$dockerfiles = @(Get-ChildItem -Recurse -File -Name "Dockerfile*" -ErrorAction SilentlyContinue | Where-Object { $_ -notlike "*node_modules*" })

$nonCompliantImages = @()
$compliantImages = @()

foreach ($dockerfile in $dockerfiles) {
    $content = Get-Content $dockerfile -ErrorAction SilentlyContinue
    $fromLines = $content | Where-Object { $_ -match '^FROM\s+(.+)' }
    
    foreach ($fromLine in $fromLines) {
        if ($fromLine -match '^FROM\s+(.+?)(\s+AS\s+.*)?$') {
            $baseImage = $matches[1].Trim()
            
            # Skip build args and variables
            if ($baseImage -like '*$*' -or $baseImage -like '*{*') {
                continue
            }
            
            $isCompliant = $false
            $isProhibited = $false
            
            # Check against approved patterns
            foreach ($approved in $approvedBaseImages) {
                if ($baseImage -like $approved) {
                    $isCompliant = $true
                    break
                }
            }
            
            # Check against prohibited patterns
            foreach ($prohibited in $prohibitedBaseImages) {
                if ($baseImage -like $prohibited) {
                    $isProhibited = $true
                    break
                }
            }
            
            if ($isProhibited -or -not $isCompliant) {
                $nonCompliantImages += @{
                    File = $dockerfile
                    Image = $baseImage
                    Line = $fromLine
                }
            } else {
                $compliantImages += @{
                    File = $dockerfile
                    Image = $baseImage
                }
            }
        }
    }
}

if ($nonCompliantImages.Count -gt 0) {
    Write-Host "[X] BLOCKED: Non-hardened base images detected!" -ForegroundColor Red
    foreach ($image in $nonCompliantImages) {
        Write-Host "  $($image.File): $($image.Image)" -ForegroundColor Red
    }
    Write-Host "Solution: Use Alpine or Distroless base images" -ForegroundColor Yellow
    Write-Host "  Approved: gcr.io/distroless/*, *:*-alpine, nvidia/cuda:*-runtime-*" -ForegroundColor Yellow
    Write-Host "  Prohibited: ubuntu:*, debian:*, *:latest, *:*-devel*" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "[OK] All base images are hardened ($($compliantImages.Count) compliant)" -ForegroundColor Green
    if ($Verbose -and $compliantImages.Count -gt 0) {
        Write-Host "  Compliant images:" -ForegroundColor Green
        $compliantImages | ForEach-Object { Write-Host "    $($_.File): $($_.Image)" -ForegroundColor Green }
    }
}

# Single Source of Truth Checks
Write-Host ""
Write-Host "SINGLE SOURCE OF TRUTH CHECKS" -ForegroundColor Yellow
Write-Host "-----------------------------" -ForegroundColor Yellow

Write-Host "Checking for service definition duplication..." -ForegroundColor White

# Check if single source config exists
$configExists = Test-Path "config/services.yaml"
$generatorExists = Test-Path "scripts/generate-configs.py"

if (-not $configExists) {
    Write-Host "[X] BLOCKED: Single source of truth config missing!" -ForegroundColor Red
    Write-Host "Solution: Create config/services.yaml with all service definitions" -ForegroundColor Yellow
    $violations++
} elseif (-not $generatorExists) {
    Write-Host "[!] WARNING: Configuration generator missing" -ForegroundColor Yellow
    Write-Host "Solution: Use scripts/generate-configs.py to maintain consistency" -ForegroundColor Yellow
    $warnings++
} else {
    Write-Host "[OK] Single source of truth configuration exists" -ForegroundColor Green
}

# Check for duplicate service definitions
$composeFiles = @(Get-ChildItem -Recurse -File -Include "docker-compose*.yml", "docker-compose*.yaml" -ErrorAction SilentlyContinue)
$k8sFiles = @()
if (Test-Path "k8s") {
    $k8sFiles = @(Get-ChildItem -Recurse -File -Path "k8s" -Include "*.yaml", "*.yml" -ErrorAction SilentlyContinue)
}

$duplicateServices = @()
$allServices = @{}

# Analyze compose files for services
foreach ($file in $composeFiles) {
    try {
        $content = Get-Content $file | ConvertFrom-Yaml -ErrorAction SilentlyContinue
        if ($content.services) {
            foreach ($serviceName in $content.services.Keys) {
                if ($allServices.ContainsKey($serviceName)) {
                    $duplicateServices += @{
                        Service = $serviceName
                        Files = @($allServices[$serviceName], $file)
                    }
                } else {
                    $allServices[$serviceName] = $file
                }
            }
        }
    } catch {
        if ($Verbose) {
            Write-Host "  Could not parse $file for service analysis" -ForegroundColor Gray
        }
    }
}

if ($duplicateServices.Count -gt 0) {
    Write-Host "[!] WARNING: Potential service definition duplication detected!" -ForegroundColor Yellow
    foreach ($dup in $duplicateServices) {
        Write-Host "  Service '$($dup.Service)' defined in multiple files" -ForegroundColor Yellow
    }
    Write-Host "Solution: Use single source of truth (config/services.yaml)" -ForegroundColor Yellow
    $warnings++
} else {
    Write-Host "[OK] No obvious service duplication detected" -ForegroundColor Green
}

# Repository Structure Checks
Write-Host ""
Write-Host "REPOSITORY STRUCTURE CHECKS" -ForegroundColor Yellow
Write-Host "---------------------------" -ForegroundColor Yellow

Write-Host "Checking directory structure compliance..." -ForegroundColor White
$missingDirs = @()
$extraTopLevel = @()

# Check required directories exist
foreach ($dir in $requiredDirectoryStructure) {
    if (-not (Test-Path $dir)) {
        $missingDirs += $dir
    }
}

# Check for excessive top-level items
$topLevelItems = @(Get-ChildItem -Path . -ErrorAction SilentlyContinue | Where-Object { 
    $_.Name -notlike '.*' -or $_.Name -in @('.gitignore', '.dockerignore', '.env.example')
})

$allowedTopLevel = @(
    'src', 'docker', 'k8s', 'ci', 'scripts', 'docs', 'tests', 'config',
    'package.json', 'package-lock.json', 'yarn.lock', 'requirements.txt',
    'README.md', 'LICENSE', '.gitignore', '.dockerignore', '.env.example',
    'Dockerfile', 'docker-compose.yml', 'docker-compose.prod.yml', 'docker-compose.dev.yml',
    'Makefile', 'setup.py'
)

foreach ($item in $topLevelItems) {
    if ($item.Name -notin $allowedTopLevel -and $item.Name -notlike "*.md") {
        $extraTopLevel += $item.Name
    }
}

if ($missingDirs.Count -gt 0) {
    Write-Host "[!] WARNING: Missing required directories!" -ForegroundColor Yellow
    $missingDirs | ForEach-Object { Write-Host "  Missing: $($_)/" -ForegroundColor Yellow }
    Write-Host "Solution: Create organized directory structure" -ForegroundColor Yellow
    $warnings++
}

if ($extraTopLevel.Count -gt 20) {
    Write-Host "[X] BLOCKED: Repository structure too disorganized ($($extraTopLevel.Count) extra top-level items)!" -ForegroundColor Red
    Write-Host "Solution: Use archive strategy to clean up repository" -ForegroundColor Yellow
    Write-Host "  Run: python scripts/archive-cleanup.py --dry-run" -ForegroundColor Yellow
    $violations++
} elseif ($extraTopLevel.Count -gt 10) {
    Write-Host "[!] WARNING: Repository structure needs cleanup ($($extraTopLevel.Count) extra items)" -ForegroundColor Yellow
    $warnings++
} else {
    Write-Host "[OK] Repository structure is well-organized" -ForegroundColor Green
}

# Configuration Management Checks
Write-Host ""
Write-Host "CONFIGURATION MANAGEMENT" -ForegroundColor Yellow
Write-Host "-----------------------" -ForegroundColor Yellow

Write-Host "Checking configuration consistency..." -ForegroundColor White

# Check if configs are generated vs manual
$generatedFiles = @(
    "docker-compose.generated.yml",
    "k8s/generated"
)

$hasGenerated = $false
foreach ($file in $generatedFiles) {
    if (Test-Path $file) {
        $hasGenerated = $true
        break
    }
}

if ($hasGenerated) {
    Write-Host "[OK] Generated configurations detected" -ForegroundColor Green
} else {
    Write-Host "[!] WARNING: No generated configurations found" -ForegroundColor Yellow
    Write-Host "Solution: Run 'python scripts/generate-configs.py --all'" -ForegroundColor Yellow
    $warnings++
}

# Final Report
Write-Host ""
Write-Host "HARDENED GUARDRAILS SUMMARY" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

if ($violations -eq 0) {
    Write-Host "[PASS] ALL HARDENED CHECKS PASSED!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your repository meets hardened production standards:" -ForegroundColor White
    Write-Host "  [OK] Security hardened (no secrets, minimal attack surface)" -ForegroundColor Green
    Write-Host "  [OK] Docker images hardened (Alpine/Distroless only)" -ForegroundColor Green
    Write-Host "  [OK] Single source of truth maintained" -ForegroundColor Green
    Write-Host "  [OK] Repository structure organized" -ForegroundColor Green
    Write-Host "  [OK] Configuration management consistent" -ForegroundColor Green
    
    if ($warnings -gt 0) {
        Write-Host ""
        Write-Host "NOTE: $warnings optimization opportunity(s) detected" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Ready for hardened production deployment!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] $violations HARDENING VIOLATION(S) DETECTED!" -ForegroundColor Red
    
    if ($warnings -gt 0) {
        Write-Host "WARNING: $warnings optimization opportunities found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Hardening requirements:" -ForegroundColor Yellow
    Write-Host "  1. Use only Alpine or Distroless base images" -ForegroundColor White
    Write-Host "  2. Maintain single source of truth for service definitions" -ForegroundColor White
    Write-Host "  3. Organize repository with proper directory structure" -ForegroundColor White
    Write-Host "  4. Use configuration generation to prevent duplication" -ForegroundColor White
    
    Write-Host ""
    Write-Host "Quick hardening steps:" -ForegroundColor Cyan
    Write-Host "  - Replace Ubuntu/Debian images with Alpine variants" -ForegroundColor White
    Write-Host "  - Run: python scripts/archive-cleanup.py --dry-run" -ForegroundColor White
    Write-Host "  - Run: python scripts/generate-configs.py --all" -ForegroundColor White
    Write-Host "  - Use docker/base/ hardened templates" -ForegroundColor White
    
    exit 1
}