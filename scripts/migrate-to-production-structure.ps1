# GameForge AI - Production Repository Migration Script
# This script automates the complete repository restructuring to production-ready layout

param(
    [switch]$DryRun = $false,
    [switch]$CreateBackup = $true,
    [string]$BackupPath = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "🚀 GameForge AI - Production Repository Migration" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Get the repository root
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

Write-Host "📁 Repository Root: $RepoRoot" -ForegroundColor Green

# Create backup if requested
if ($CreateBackup -and -not $DryRun) {
    Write-Host "📦 Creating backup at: $BackupPath" -ForegroundColor Yellow
    if (Test-Path $BackupPath) {
        Remove-Item $BackupPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    
    # Copy all files except .git, node_modules, .venv
    $excludePatterns = @('.git', 'node_modules', '.venv', '__pycache__', '*.pyc', 'dist', 'build')
    Get-ChildItem -Path . -Recurse | Where-Object {
        $exclude = $false
        foreach ($pattern in $excludePatterns) {
            if ($_.FullName -like "*$pattern*") {
                $exclude = $true
                break
            }
        }
        return -not $exclude
    } | ForEach-Object {
        $relativePath = $_.FullName.Substring($RepoRoot.Length + 1)
        $targetPath = Join-Path $BackupPath $relativePath
        $targetDir = Split-Path $targetPath -Parent
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        if (-not $_.PSIsContainer) {
            Copy-Item $_.FullName $targetPath -Force
        }
    }
    Write-Host "✅ Backup created successfully" -ForegroundColor Green
}

# Function to create directory if it doesn't exist
function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would create directory: $Path" -ForegroundColor Gray
        } else {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
            Write-Host "   ✅ Created: $Path" -ForegroundColor Green
        }
    }
}

# Function to move file safely
function Move-FileSafely {
    param(
        [string]$Source,
        [string]$Destination
    )
    
    if (Test-Path $Source) {
        $destDir = Split-Path $Destination -Parent
        Ensure-Directory $destDir
        
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would move: $Source → $Destination" -ForegroundColor Gray
        } else {
            try {
                Move-Item $Source $Destination -Force
                Write-Host "   ✅ Moved: $(Split-Path $Source -Leaf) → $destDir" -ForegroundColor Green
            } catch {
                Write-Host "   ❌ Failed to move $Source : $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
}

# Function to move multiple files by pattern
function Move-FilesByPattern {
    param(
        [string]$Pattern,
        [string]$DestinationDir,
        [string]$Description
    )
    
    Write-Host "📋 $Description" -ForegroundColor Cyan
    Ensure-Directory $DestinationDir
    
    $files = Get-ChildItem -Path . -Name $Pattern -File
    foreach ($file in $files) {
        Move-FileSafely $file (Join-Path $DestinationDir $file)
    }
    
    if ($files.Count -eq 0) {
        Write-Host "   ℹ️  No files found matching pattern: $Pattern" -ForegroundColor Yellow
    } else {
        Write-Host "   📊 Processed $($files.Count) files" -ForegroundColor Blue
    }
}

Write-Host "`n🏗️  PHASE 1: Creating New Directory Structure" -ForegroundColor Magenta

# Create the complete new directory structure
$newDirs = @(
    "docker/base",
    "docker/services", 
    "docker/compose",
    "k8s/base",
    "k8s/overlays/dev",
    "k8s/overlays/staging", 
    "k8s/overlays/prod",
    "k8s/templates",
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
    "tests/unit",
    "tests/integration", 
    "tests/load",
    "docs/api-specs",
    "docs/runbooks"
)

foreach ($dir in $newDirs) {
    Ensure-Directory $dir
}

Write-Host "`n🐳 PHASE 2: Organizing Docker Assets" -ForegroundColor Magenta

# Move Docker files
Move-FilesByPattern "Dockerfile*" "docker/services" "Moving Dockerfiles to docker/services/"
Move-FilesByPattern "docker-compose*.yml" "docker/compose" "Moving docker-compose files to docker/compose/"

# Create base Dockerfiles (these will be optimized versions)
$baseDockerfiles = @{
    "docker/base/node.Dockerfile" = @"
FROM node:18-alpine
RUN apk add --no-cache python3 py3-pip make g++
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
"@
    "docker/base/python.Dockerfile" = @"
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
"@
    "docker/base/gpu.Dockerfile" = @"
FROM nvidia/cuda:11.8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-gpu.txt .
RUN pip3 install -r requirements-gpu.txt
"@
}

foreach ($dockerfile in $baseDockerfiles.Keys) {
    if ($DryRun) {
        Write-Host "   [DRY RUN] Would create: $dockerfile" -ForegroundColor Gray
    } else {
        Set-Content -Path $dockerfile -Value $baseDockerfiles[$dockerfile]
        Write-Host "   ✅ Created: $dockerfile" -ForegroundColor Green
    }
}

Write-Host "`n📂 PHASE 3: Organizing Source Code" -ForegroundColor Magenta

# Move existing src/ content to frontend/web/
if (Test-Path "src" -and -not (Test-Path "src/frontend")) {
    if ($DryRun) {
        Write-Host "   [DRY RUN] Would reorganize src/ directory" -ForegroundColor Gray
    } else {
        # Create temporary directory and move current src content
        $tempSrc = "temp_src_$(Get-Random)"
        Move-Item "src" $tempSrc
        Ensure-Directory "src/frontend/web"
        
        # Move web frontend files
        $webFiles = Get-ChildItem $tempSrc -File
        foreach ($file in $webFiles) {
            Move-Item $file.FullName "src/frontend/web/"
        }
        
        # Move web directories (except specific ones we want to reorganize)
        $webDirs = Get-ChildItem $tempSrc -Directory | Where-Object { $_.Name -notin @('backend', 'ai', 'common') }
        foreach ($dir in $webDirs) {
            Move-Item $dir.FullName "src/frontend/web/"
        }
        
        # Move backend if it exists in src
        if (Test-Path "$tempSrc/backend") {
            Move-Item "$tempSrc/backend" "src/"
        }
        
        # Clean up temp directory
        if (Test-Path $tempSrc) {
            Remove-Item $tempSrc -Recurse -Force
        }
        
        Write-Host "   ✅ Reorganized src/ directory structure" -ForegroundColor Green
    }
}

# Move backend/ to src/backend/ if it exists at root
if (Test-Path "backend" -and -not (Test-Path "src/backend")) {
    Move-FileSafely "backend" "src/backend"
}

Write-Host "`n📜 PHASE 4: Organizing Scripts" -ForegroundColor Magenta

# Move all script files to scripts directory
Move-FilesByPattern "*.ps1" "scripts" "Moving PowerShell scripts to scripts/"
Move-FilesByPattern "*.sh" "scripts" "Moving shell scripts to scripts/"
Move-FilesByPattern "*.bat" "scripts" "Moving batch files to scripts/"

# Keep certain scripts at root (they're essential for the build process)
$keepAtRoot = @("Makefile")
foreach ($file in $keepAtRoot) {
    if (Test-Path "scripts/$file") {
        Move-FileSafely "scripts/$file" $file
    }
}

Write-Host "`n🔒 PHASE 5: Organizing Security Assets" -ForegroundColor Magenta

# Security directory should already exist, but ensure it's properly organized
Move-FilesByPattern "*seccomp*" "security/seccomp" "Moving seccomp profiles"
Move-FilesByPattern "*security*.json" "security/configs" "Moving security configs"

Write-Host "`n📊 PHASE 6: Organizing Monitoring Assets" -ForegroundColor Magenta

# Monitoring directory exists, ensure loose monitoring files are moved
$monitoringFiles = Get-ChildItem -Name "*prometheus*", "*grafana*", "*alert*" -File
foreach ($file in $monitoringFiles) {
    $destPath = if ($file -like "*prometheus*") { "monitoring/prometheus" }
               elseif ($file -like "*grafana*") { "monitoring/grafana" }
               elseif ($file -like "*alert*") { "monitoring/alerting" }
               else { "monitoring/configs" }
    
    Move-FileSafely $file (Join-Path $destPath $file)
}

Write-Host "`n📚 PHASE 7: Organizing Documentation" -ForegroundColor Magenta

# Move documentation files
$docFiles = Get-ChildItem -Name "*.md" -File | Where-Object { $_ -notin @("README.md", "LICENSE") }
foreach ($file in $docFiles) {
    Move-FileSafely $file (Join-Path "docs" $file)
}

Write-Host "`n🧹 PHASE 8: Clean Up Root Directory" -ForegroundColor Magenta

# Move remaining loose files to appropriate locations
Move-FilesByPattern "*.json" "config" "Moving loose JSON config files"
Move-FilesByPattern "*.yaml" "config" "Moving loose YAML config files"
Move-FilesByPattern "*.yml" "config" "Moving loose YML config files"

# Keep essential files at root
$keepAtRootFiles = @(
    "package.json", "package-lock.json", "tsconfig.json", "components.json",
    "tailwind.config.js", "vite.config.ts", ".env*", ".gitignore", 
    "README.md", "LICENSE", "Makefile"
)

Write-Host "`n✅ MIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

if ($DryRun) {
    Write-Host "🔍 This was a DRY RUN - no files were actually moved" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to perform the actual migration" -ForegroundColor Yellow
} else {
    Write-Host "📁 Repository has been reorganized to production structure" -ForegroundColor Green
    Write-Host "🔄 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Update import paths in source code" -ForegroundColor White
    Write-Host "   2. Update CI/CD pipeline file references" -ForegroundColor White
    Write-Host "   3. Test all deployments and builds" -ForegroundColor White
    Write-Host "   4. Update documentation" -ForegroundColor White
}

if ($CreateBackup -and -not $DryRun) {
    Write-Host "💾 Backup saved at: $BackupPath" -ForegroundColor Blue
}

Write-Host "`n🎉 GameForge AI is now enterprise-ready!" -ForegroundColor Green