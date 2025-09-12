# GameForge AI - Production Structure Validator
# Simple validation script to check migration success

param(
    [switch]$Detailed,
    [switch]$FixIssues
)

Write-Host "🔍 GameForge AI - Production Structure Validator" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$Passed = 0
$Failed = 0
$Warnings = 0

# Function to test directory
function Test-Directory {
    param([string]$Path, [string]$Description)
    
    if (Test-Path $Path) {
        Write-Host "   ✅ $Description" -ForegroundColor Green
        $script:Passed++
        return $true
    } else {
        Write-Host "   ❌ Missing: $Description ($Path)" -ForegroundColor Red
        $script:Failed++
        
        if ($FixIssues) {
            try {
                New-Item -ItemType Directory -Path $Path -Force | Out-Null
                Write-Host "      🔧 Created: $Path" -ForegroundColor Yellow
            } catch {
                Write-Host "      ❌ Failed to create: $Path" -ForegroundColor Red
            }
        }
        return $false
    }
}

Write-Host "`n📁 Validating Directory Structure" -ForegroundColor Magenta

# Core directory structure
$coreDirectories = @{
    ".github/workflows" = "CI/CD workflows"
    "docker" = "Docker containerization"
    "docker/base" = "Docker base images"
    "docker/services" = "Docker service images"
    "docker/compose" = "Docker compose files"
    "k8s" = "Kubernetes manifests"
    "k8s/base" = "K8s base configurations"
    "k8s/overlays" = "K8s environment overlays"
    "src" = "Source code"
    "src/frontend" = "Frontend applications"
    "src/backend" = "Backend services"
    "scripts" = "Automation scripts"
    "monitoring" = "Monitoring stack"
    "security" = "Security policies"
    "docs" = "Documentation"
    "tests" = "Test suites"
}

foreach ($dir in $coreDirectories.Keys) {
    Test-Directory $dir $coreDirectories[$dir] | Out-Null
}

Write-Host "`n🐳 Validating Docker Structure" -ForegroundColor Magenta

# Check for docker files in proper locations
$dockerServiceFiles = Get-ChildItem "docker/services" -Filter "Dockerfile*" -ErrorAction SilentlyContinue
$composeFiles = Get-ChildItem "docker/compose" -Filter "*.yml" -ErrorAction SilentlyContinue

if ($dockerServiceFiles.Count -gt 0) {
    Write-Host "   ✅ Docker service files: $($dockerServiceFiles.Count) found" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "   ⚠️  No Docker service files found in docker/services/" -ForegroundColor Yellow
    $Warnings++
}

if ($composeFiles.Count -gt 0) {
    Write-Host "   ✅ Docker compose files: $($composeFiles.Count) found" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "   ⚠️  No compose files found in docker/compose/" -ForegroundColor Yellow
    $Warnings++
}

Write-Host "`n💻 Validating Source Code Structure" -ForegroundColor Magenta

$sourceComponents = @{
    "src/frontend/web" = "Frontend web application"
    "src/backend" = "Backend services"
}

foreach ($component in $sourceComponents.Keys) {
    if (Test-Path $component) {
        $fileCount = (Get-ChildItem $component -Recurse -File -ErrorAction SilentlyContinue).Count
        Write-Host "   ✅ $($sourceComponents[$component]): $fileCount files" -ForegroundColor Green
        $Passed++
    } else {
        Write-Host "   ❌ Missing: $component" -ForegroundColor Red
        $Failed++
    }
}

Write-Host "`n🧹 Validating Root Directory Cleanness" -ForegroundColor Magenta

# Check for loose files at root
$allowedAtRoot = @(
    "package.json", "package-lock.json", "tsconfig.json", "components.json",
    "tailwind.config.js", "vite.config.ts", "Makefile", "LICENSE", "README.md",
    ".env", ".env.example", ".gitignore", ".dockerignore"
)

$rootFiles = Get-ChildItem -File | Where-Object { 
    $fileName = $_.Name
    $isAllowed = $allowedAtRoot -contains $fileName -or $fileName -like ".env.*"
    return -not $isAllowed
}

if ($rootFiles.Count -eq 0) {
    Write-Host "   ✅ Root directory is clean" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "   ⚠️  Found $($rootFiles.Count) loose files at root" -ForegroundColor Yellow
    $Warnings += $rootFiles.Count
    
    if ($Detailed) {
        foreach ($file in $rootFiles) {
            Write-Host "      - $($file.Name)" -ForegroundColor Gray
        }
    }
}

Write-Host "`n📋 VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host "✅ Passed: $Passed" -ForegroundColor Green
Write-Host "⚠️  Warnings: $Warnings" -ForegroundColor Yellow
Write-Host "❌ Failed: $Failed" -ForegroundColor Red

$totalChecks = $Passed + $Warnings + $Failed
if ($totalChecks -gt 0) {
    $successRate = [math]::Round(($Passed / $totalChecks) * 100, 1)
    Write-Host "`n📊 Overall Health: $successRate%" -ForegroundColor $(
        if ($successRate -ge 90) { "Green" }
        elseif ($successRate -ge 70) { "Yellow" }
        else { "Red" }
    )
}

if ($Failed -eq 0) {
    Write-Host "`n🎉 Repository structure is production-ready!" -ForegroundColor Green
    Write-Host "✨ GameForge AI is enterprise-grade and ready to compete!" -ForegroundColor Green
} elseif ($Failed -le 3) {
    Write-Host "`n⚠️  Repository structure is mostly ready with minor issues" -ForegroundColor Yellow
    Write-Host "💡 Run with -FixIssues to resolve automatically" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ Repository structure needs improvements" -ForegroundColor Red
    Write-Host "💡 Run with -FixIssues to resolve issues automatically" -ForegroundColor Yellow
}

Write-Host "`n💡 Next Steps:" -ForegroundColor Blue
Write-Host "   • Test builds: make build" -ForegroundColor White
Write-Host "   • Update import paths in source code" -ForegroundColor White
Write-Host "   • Test deployments: make deploy-dev" -ForegroundColor White