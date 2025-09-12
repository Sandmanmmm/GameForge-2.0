# GameForge Production Guardrails - PowerShell Version
# Run this before committing: .\scripts\guardrails-check.ps1

param(
    [switch]$Verbose,
    [switch]$FixMode
)

Write-Host "🛡️ GameForge Production Guardrails Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$violations = 0
$warnings = 0

# ========================================================================
# Security Checks
# ========================================================================
Write-Host ""
Write-Host "🔒 SECURITY CHECKS" -ForegroundColor Yellow
Write-Host "------------------" -ForegroundColor Yellow

# Check for .env files
Write-Host "Checking for .env files..." -ForegroundColor White
$envFiles = Get-ChildItem -Recurse -File -Name "*.env*" | Where-Object { 
    $_ -notlike "*.example" -and $_ -notlike "*.template" -and $_ -notlike "*node_modules*" 
}

if ($envFiles) {
    Write-Host "X BLOCKED: .env files detected!" -ForegroundColor Red
    $envFiles | ForEach-Object { Write-Host "  $($_)" -ForegroundColor Red }
    Write-Host "Solution: Use .env.example instead and add secrets to Vault/K8s" -ForegroundColor Yellow
    $violations++
    
    if ($FixMode) {
        Write-Host "Fix Mode: Moving .env files to .env.backup..." -ForegroundColor Cyan
        $envFiles | ForEach-Object { 
            Move-Item $_ "$($_).backup"
            Write-Host "  Moved $($_) to $($_).backup" -ForegroundColor Green
        }
    }
} else {
    Write-Host "OK No .env files found" -ForegroundColor Green
}

# Check for certificate/key files
Write-Host "Checking for certificate/key files..." -ForegroundColor White
$certFiles = Get-ChildItem -Recurse -File | Where-Object { 
    $_.Extension -in @('.pem', '.key', '.crt', '.p12', '.pfx') -and 
    $_.FullName -notlike "*node_modules*" 
}

if ($certFiles) {
    Write-Host "❌ BLOCKED: Certificate/key files detected!" -ForegroundColor Red
    $certFiles | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor Red }
    Write-Host "💡 Use K8s TLS secrets or certificate managers" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "✅ No certificate/key files found" -ForegroundColor Green
}

# ========================================================================
# Structure Checks
# ========================================================================
Write-Host ""
Write-Host "🏗️ STRUCTURE CHECKS" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow

# Check top-level directory structure
Write-Host "Checking top-level structure..." -ForegroundColor White
$allowedDirs = @('src', 'docker', 'k8s', 'scripts', 'monitoring', 'security', 'tests', 'docs', 'backend', 'frontend', 'audit', 'backup', 'config', 'elasticsearch', 'kibana', 'logs', 'node_modules', 'secrets', 'ssl', 'volumes', 'backups', 'backup_local_changes', 'backup_20250912_004935', '.git', '.github', '.venv')
$allowedFiles = @('README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'package.json', 'package-lock.json', 'yarn.lock', 'tsconfig.json', 'Dockerfile', 'docker-compose.yml', 'docker-compose.dev.yml', 'docker-compose.prod.yml', '.gitignore', '.dockerignore', '.npmrc', '.env.example', '.env.template', 'docker.env.example', '.env.phase4.production.template', '.env.production.template', 'components.json', 'DOCKER_STRUCTURE.md')

$topLevelItems = Get-ChildItem . | Where-Object { $_.Name -notlike ".*" -or $_.Name -in @('.gitignore', '.dockerignore', '.npmrc', '.env.example', '.env.template') }
$violations_found = @()

foreach ($item in $topLevelItems) {
    if ($item.PSIsContainer) {
        if ($item.Name -notin $allowedDirs) {
            $violations_found += "📁 $($item.Name)/ (unauthorized directory)"
        }
    } else {
        if ($item.Name -notin $allowedFiles) {
            $violations_found += "📄 $($item.Name) (unauthorized file)"
        }
    }
}

if ($violations_found) {
    Write-Host "❌ BLOCKED: Unauthorized top-level items!" -ForegroundColor Red
    $violations_found | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "💡 Move files to appropriate subdirectories" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "✅ Repository structure is compliant" -ForegroundColor Green
}

# Check Docker Compose file count
Write-Host "Checking Docker Compose file count..." -ForegroundColor White
$composeFiles = Get-ChildItem -Recurse -File -Name "docker-compose*.yml", "docker-compose*.yaml"
$composeCount = $composeFiles.Count

if ($composeCount -gt 4) {
    Write-Host "❌ BLOCKED: Too many Docker Compose files ($composeCount > 4)!" -ForegroundColor Red
    Write-Host "💡 Consolidate compose files or use overrides" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "✅ Docker Compose file count OK ($composeCount/4)" -ForegroundColor Green
}

# ========================================================================
# Dockerfile Checks
# ========================================================================
Write-Host ""
Write-Host "🐳 DOCKERFILE CHECKS" -ForegroundColor Yellow
Write-Host "--------------------" -ForegroundColor Yellow

$dockerfiles = Get-ChildItem -Recurse -File -Name "Dockerfile*" | Where-Object { $_ -notlike "*node_modules*" }
$dockerfileCount = $dockerfiles.Count

if ($dockerfileCount -gt 10) {
    Write-Host "❌ BLOCKED: Too many Dockerfiles ($dockerfileCount > 10)!" -ForegroundColor Red
    Write-Host "💡 Use multi-stage builds instead" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "✅ Dockerfile count reasonable ($dockerfileCount/10)" -ForegroundColor Green
}

# ========================================================================
# Dependency Checks
# ========================================================================
Write-Host ""
Write-Host "📦 DEPENDENCY CHECKS" -ForegroundColor Yellow
Write-Host "--------------------" -ForegroundColor Yellow

# Check package.json count
$packageJsonFiles = Get-ChildItem -Recurse -File -Name "package.json" | Where-Object { $_ -notlike "*node_modules*" }
$packageJsonCount = $packageJsonFiles.Count

if ($packageJsonCount -gt 3) {
    Write-Host "⚠️  WARNING: Many package.json files ($packageJsonCount > 3)" -ForegroundColor Yellow
    Write-Host "💡 Consider monorepo structure" -ForegroundColor Yellow
    $warnings++
} else {
    Write-Host "✅ Package.json count reasonable ($packageJsonCount/3)" -ForegroundColor Green
}

# Check for mixed package managers
$npmLocks = Get-ChildItem -Recurse -File -Name "package-lock.json" | Where-Object { $_ -notlike "*node_modules*" }
$yarnLocks = Get-ChildItem -Recurse -File -Name "yarn.lock" | Where-Object { $_ -notlike "*node_modules*" }

if ($npmLocks -and $yarnLocks) {
    Write-Host "❌ BLOCKED: Mixed package managers detected!" -ForegroundColor Red
    Write-Host "💡 Choose either npm or yarn consistently" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "✅ Package manager consistency maintained" -ForegroundColor Green
}

# ========================================================================
# File Size Checks
# ========================================================================
Write-Host ""
Write-Host "📏 FILE SIZE CHECKS" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow

$largeFiles = Get-ChildItem -Recurse -File | Where-Object { 
    $_.Length -gt 50MB -and $_.FullName -notlike "*node_modules*" -and $_.FullName -notlike "*\.git*"
}

if ($largeFiles) {
    Write-Host "❌ BLOCKED: Large files detected (>50MB)!" -ForegroundColor Red
    $largeFiles | ForEach-Object { 
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  $($_.Name) ($sizeMB MB)" -ForegroundColor Red 
    }
    Write-Host "💡 Use Git LFS for large files or external storage" -ForegroundColor Yellow
    $violations++
} else {
    Write-Host "✅ No large files detected" -ForegroundColor Green
}

# ========================================================================
# Final Report
# ========================================================================
Write-Host ""
Write-Host "📊 GUARDRAILS SUMMARY" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

if ($violations -eq 0) {
    Write-Host "✅ ALL CHECKS PASSED - Ready to commit!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎯 Your repository maintains:" -ForegroundColor White
    Write-Host "  ✅ Security standards (no secrets)" -ForegroundColor Green
    Write-Host "  ✅ Clean structure (proper organization)" -ForegroundColor Green
    Write-Host "  ✅ Reasonable file counts" -ForegroundColor Green
    Write-Host "  ✅ Consistent dependency management" -ForegroundColor Green
    
    if ($warnings -gt 0) {
        Write-Host ""
        Write-Host "⚠️  $warnings warning(s) - consider addressing these" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🚀 Ready for production deployment!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ $violations VIOLATION(S) DETECTED!" -ForegroundColor Red
    
    if ($warnings -gt 0) {
        Write-Host "⚠️  $warnings warning(s) also found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🔧 Please fix the issues above and try again" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 Quick fixes:" -ForegroundColor White
    Write-Host "  - Remove .env files and use .env.example" -ForegroundColor White
    Write-Host "  - Move top-level files to proper directories" -ForegroundColor White
    Write-Host "  - Consolidate redundant Docker files" -ForegroundColor White
    Write-Host "  - Use secure secret management" -ForegroundColor White
    Write-Host ""
    Write-Host "🛠️  Run with -FixMode to auto-fix some issues:" -ForegroundColor Cyan
    Write-Host "   .\scripts\guardrails-check.ps1 -FixMode" -ForegroundColor Cyan
    
    exit 1
}