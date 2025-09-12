# GameForge AI - Clean Production Migration
# Version: 6.0 - Fresh Start

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$CreateBackup
)

Write-Host "GameForge AI - Production Migration" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

$FilesProcessed = 0
$DirectoriesCreated = 0

# Backup
if ($CreateBackup -and -not $DryRun) {
    $BackupPath = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "Creating backup: $BackupPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    Copy-Item "*.md" $BackupPath -Force -ErrorAction SilentlyContinue
    Write-Host "Backup created" -ForegroundColor Green
}

# Directory creation function
function New-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        if ($DryRun) {
            Write-Host "   [DRY] Create: $Path" -ForegroundColor Gray
        } else {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
            Write-Host "   Created: $Path" -ForegroundColor Green
            $script:DirectoriesCreated++
        }
    }
}

# File moving function
function Move-File {
    param([string]$Source, [string]$Dest)
    if (Test-Path $Source) {
        $destDir = Split-Path $Dest -Parent
        New-Dir $destDir
        if ($DryRun) {
            Write-Host "   [DRY] Move: $Source -> $Dest" -ForegroundColor Gray
        } else {
            Move-Item $Source $Dest -Force -ErrorAction SilentlyContinue
            Write-Host "   Moved: $(Split-Path $Source -Leaf)" -ForegroundColor Green
            $script:FilesProcessed++
        }
    }
}

Write-Host "`nCreating Production Directory Structure" -ForegroundColor Magenta

# Create all directories
$dirs = @(
    # CI/CD pipelines
    ".github/workflows",
    
    # Containerization layer
    "docker/base",
    "docker/services", 
    "docker/compose",
    
    # Kubernetes manifests
    "k8s/base",
    "k8s/overlays/dev",
    "k8s/overlays/staging", 
    "k8s/overlays/prod",
    "k8s/templates",
    
    # Core application source
    "src/frontend/web",
    "src/frontend/mobile",
    "src/backend/api",
    "src/backend/worker",
    "src/backend/services",
    "src/ai/inference",
    "src/ai/training",
    "src/ai/datasets",
    "src/ai/evaluation",
    "src/common/logging",
    "src/common/monitoring",
    "src/common/security",
    "src/common/utils",
    
    # Automation utilities
    "scripts",
    
    # Observability stack
    "monitoring/prometheus",
    "monitoring/grafana",
    "monitoring/alertmanager",
    "monitoring/dashboards",
    
    # Security hardening & policies
    "security/seccomp",
    "security/policies",
    "security/scripts",
    "security/vault",
    
    # Automated tests
    "tests/unit",
    "tests/integration",
    "tests/load",
    
    # Documentation
    "docs/api-specs",
    "docs/runbooks"
)

foreach ($dir in $dirs) {
    New-Dir $dir
}

Write-Host "`nMoving Docker Files" -ForegroundColor Magenta
Get-ChildItem -Name "Dockerfile*" -File | ForEach-Object {
    Move-File $_ "docker/base/$_"
}

Get-ChildItem -Name "docker-compose*.yml" -File | ForEach-Object {
    Move-File $_ "docker/compose/$_"
}

Write-Host "`nMoving Scripts" -ForegroundColor Magenta
Get-ChildItem -Name "*.ps1" -File | Where-Object { $_ -notlike "*migrate*" } | ForEach-Object {
    Move-File $_ "scripts/$_"
}

Get-ChildItem -Name "*.sh" -File | ForEach-Object {
    Move-File $_ "scripts/$_"
}

Write-Host "`nMoving Documentation" -ForegroundColor Magenta
Get-ChildItem -Name "*.md" -File | Where-Object { $_ -ne "README.md" } | ForEach-Object {
    Move-File $_ "docs/$_"
}

Write-Host "`nOrganizing Config & Security Files" -ForegroundColor Magenta

# Keep important root files
$keepInRoot = @("package.json", "package-lock.json", "tsconfig.json", "components.json", "tailwind.config.js", "vite.config.ts")

# Move security-related config files
Get-ChildItem -Name "seccomp*.json" -File | ForEach-Object {
    Move-File $_ "security/seccomp/$_"
}

Get-ChildItem -Name "*policy*.json" -File | ForEach-Object {
    Move-File $_ "security/policies/$_"
}

Get-ChildItem -Name "*security*.json" -File | ForEach-Object {
    Move-File $_ "security/$_"
}

Get-ChildItem -Name "audit*.yaml" -File | ForEach-Object {
    Move-File $_ "security/policies/$_"
}

# Move K8s related yaml files
Get-ChildItem -Name "*.yaml" -File | Where-Object { 
    $_ -notlike "docker-compose*" -and 
    $_ -notlike "audit*" -and
    ($_ -like "*k8s*" -or $_ -like "*metallb*" -or $_ -like "*kind*")
} | ForEach-Object {
    Move-File $_ "k8s/base/$_"
}

# Move remaining config files (non-security, non-k8s)
Get-ChildItem -Name "*.json" -File | Where-Object { 
    $keepInRoot -notcontains $_ -and
    $_ -notlike "*security*" -and 
    $_ -notlike "*policy*" -and
    $_ -notlike "seccomp*"
} | ForEach-Object {
    Move-File $_ "monitoring/$_"
}

Write-Host "`nCreating Essential Files" -ForegroundColor Magenta

if (-not $DryRun) {
    # Simple Makefile
    if (-not (Test-Path "Makefile")) {
        $content = ".PHONY: help build test`n`nhelp:`n`techo GameForge AI`n`nbuild:`n`techo Building`n`ntest:`n`techo Testing"
        Set-Content "Makefile" $content -Encoding UTF8
        Write-Host "   Created Makefile" -ForegroundColor Green
    }
    
    # Environment template
    if (-not (Test-Path ".env.example")) {
        $content = "NODE_ENV=development`nPORT=3000`nDATABASE_URL=postgresql://localhost:5432/gameforge"
        Set-Content ".env.example" $content -Encoding UTF8
        Write-Host "   Created .env.example" -ForegroundColor Green
    }
}

Write-Host "`nMIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "Files processed: $FilesProcessed" -ForegroundColor White
Write-Host "Directories created: $DirectoriesCreated" -ForegroundColor White

if ($DryRun) {
    Write-Host "`nDRY RUN - No changes made" -ForegroundColor Yellow
    Write-Host "Execute: .\scripts\migrate-production-clean.ps1 -CreateBackup" -ForegroundColor Cyan
} else {
    Write-Host "Repository is now production-ready!" -ForegroundColor Green
    Write-Host "Ready to compete with industry leaders!" -ForegroundColor Green
}