# GameForge AI - Production Repository Migration Script
# This script reorganizes the repository into production-ready structure
# Version: 1.0 - Production Ready

param(
    [switch]$DryRun,
    [switch]$CreateBackup,
    [string]$BackupPath = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "🚀 GameForge AI - Production Repository Migration" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Get the repository root
$RepoRoot = Get-Location
Write-Host "📁 Repository Root: $RepoRoot" -ForegroundColor Green

# Initialize counters
$FilesProcessed = 0
$DirectoriesCreated = 0
$Errors = @()

# Create backup if requested
if ($CreateBackup -and -not $DryRun) {
    Write-Host "📦 Creating backup at: $BackupPath" -ForegroundColor Yellow
    if (Test-Path $BackupPath) {
        Remove-Item $BackupPath -Recurse -Force
    }
    
    try {
        # Create backup directory
        New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
        
        # Copy important files and directories
        $backupItems = @("src", "backend", "scripts", "k8s", "monitoring", "security", ".github", "*.md", "*.json", "*.yml", "*.yaml", "*.ps1", "*.sh", "Dockerfile*", "docker-compose*")
        
        foreach ($item in $backupItems) {
            $files = Get-ChildItem -Path $item -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                $relativePath = $file.Name
                $targetPath = Join-Path $BackupPath $relativePath
                
                if ($file.PSIsContainer) {
                    Copy-Item $file.FullName $targetPath -Recurse -Force -ErrorAction SilentlyContinue
                } else {
                    Copy-Item $file.FullName $targetPath -Force -ErrorAction SilentlyContinue
                }
            }
        }
        Write-Host "✅ Backup created successfully" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Backup creation failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Function to create directory safely
function New-DirectorySafe {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would create directory: $Path" -ForegroundColor Gray
        } else {
            try {
                New-Item -ItemType Directory -Path $Path -Force | Out-Null
                Write-Host "   ✅ Created: $Path" -ForegroundColor Green
                $script:DirectoriesCreated++
            } catch {
                Write-Host "   ❌ Failed to create: $Path - $($_.Exception.Message)" -ForegroundColor Red
                $script:Errors += "Failed to create directory: $Path"
            }
        }
    }
}

# Function to move file safely
function Move-FileSafe {
    param(
        [string]$Source,
        [string]$Destination
    )
    
    if (Test-Path $Source) {
        $destDir = Split-Path $Destination -Parent
        New-DirectorySafe $destDir
        
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would move: $Source → $Destination" -ForegroundColor Gray
        } else {
            try {
                Move-Item $Source $Destination -Force
                Write-Host "   ✅ Moved: $(Split-Path $Source -Leaf) → $destDir" -ForegroundColor Green
                $script:FilesProcessed++
            } catch {
                Write-Host "   ❌ Failed to move $Source : $($_.Exception.Message)" -ForegroundColor Red
                $script:Errors += "Failed to move: $Source → $Destination"
            }
        }
    }
}

Write-Host "`n🏗️  PHASE 1: Creating New Directory Structure" -ForegroundColor Magenta

# Create the production directory structure
$newDirs = @(
    "docker",
    "docker/base",
    "docker/services", 
    "docker/compose",
    "k8s/base",
    "k8s/overlays",
    "k8s/overlays/dev",
    "k8s/overlays/staging", 
    "k8s/overlays/prod",
    "k8s/templates",
    "src/frontend",
    "src/frontend/web",
    "src/frontend/mobile",
    "src/backend/api",
    "src/backend/worker", 
    "src/backend/services",
    "src/ai",
    "src/ai/inference",
    "src/ai/training",
    "src/ai/datasets", 
    "src/ai/evaluation",
    "src/common",
    "src/common/logging",
    "src/common/monitoring",
    "src/common/security",
    "src/common/utils",
    "tests",
    "tests/unit",
    "tests/integration", 
    "tests/load",
    "docs",
    "docs/api-specs",
    "docs/runbooks",
    "config"
)

foreach ($dir in $newDirs) {
    New-DirectorySafe $dir
}

Write-Host "`n🐳 PHASE 2: Organizing Docker Assets" -ForegroundColor Magenta

# Move Docker files
$dockerFiles = Get-ChildItem -Path . -Name "Dockerfile*" -File
foreach ($file in $dockerFiles) {
    Move-FileSafe $file "docker/services/$file"
}

$composeFiles = Get-ChildItem -Path . -Name "docker-compose*.yml" -File
foreach ($file in $composeFiles) {
    Move-FileSafe $file "docker/compose/$file"
}

Write-Host "`n📂 PHASE 3: Organizing Source Code" -ForegroundColor Magenta

# Handle src directory reorganization
if (Test-Path "src" -and -not (Test-Path "src/frontend")) {
    if ($DryRun) {
        Write-Host "   [DRY RUN] Would reorganize src/ directory structure" -ForegroundColor Gray
    } else {
        try {
            # Create a temporary directory
            $tempDir = "temp_src_$(Get-Random)"
            Move-Item "src" $tempDir
            
            # Create new src structure
            New-DirectorySafe "src/frontend/web"
            
            # Move contents to frontend/web
            $srcContents = Get-ChildItem $tempDir
            foreach ($item in $srcContents) {
                Move-Item $item.FullName "src/frontend/web/" -Force
            }
            
            # Clean up temp directory
            Remove-Item $tempDir -Force -ErrorAction SilentlyContinue
            
            Write-Host "   ✅ Reorganized src/ directory" -ForegroundColor Green
        } catch {
            Write-Host "   ❌ Failed to reorganize src/: $($_.Exception.Message)" -ForegroundColor Red
            $script:Errors += "Failed to reorganize src/ directory"
        }
    }
}

# Move backend directory
if (Test-Path "backend" -and -not (Test-Path "src/backend/api")) {
    if ($DryRun) {
        Write-Host "   [DRY RUN] Would move backend/ to src/backend/" -ForegroundColor Gray
    } else {
        try {
            if (Test-Path "src/backend") {
                # Merge with existing backend
                $backendContents = Get-ChildItem "backend"
                foreach ($item in $backendContents) {
                    $targetPath = Join-Path "src/backend" $item.Name
                    if (Test-Path $targetPath) {
                        # Handle conflicts by creating a backup
                        Move-Item $targetPath "$targetPath.backup" -Force
                    }
                    Move-Item $item.FullName $targetPath -Force
                }
                Remove-Item "backend" -Force -ErrorAction SilentlyContinue
            } else {
                Move-Item "backend" "src/backend" -Force
            }
            Write-Host "   ✅ Moved backend/ to src/backend/" -ForegroundColor Green
        } catch {
            Write-Host "   ❌ Failed to move backend/: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n📜 PHASE 4: Organizing Scripts" -ForegroundColor Magenta

# Move script files (but keep essential ones at root)
$scriptExtensions = @("*.ps1", "*.sh", "*.bat")
$keepAtRoot = @("Makefile")

foreach ($extension in $scriptExtensions) {
    $scriptFiles = Get-ChildItem -Path . -Name $extension -File
    foreach ($file in $scriptFiles) {
        if ($keepAtRoot -notcontains $file) {
            Move-FileSafe $file "scripts/$file"
        }
    }
}

Write-Host "`n📚 PHASE 5: Organizing Documentation" -ForegroundColor Magenta

# Move documentation files (except README.md and LICENSE)
$docFiles = Get-ChildItem -Path . -Name "*.md" -File | Where-Object { $_ -notin @("README.md") }
foreach ($file in $docFiles) {
    Move-FileSafe $file "docs/$file"
}

Write-Host "`n🧹 PHASE 6: Organizing Configuration Files" -ForegroundColor Magenta

# Move loose configuration files
$configExtensions = @("*.json", "*.yaml", "*.yml")
$keepAtRoot = @("package.json", "package-lock.json", "tsconfig.json", "components.json", "tailwind.config.js")

foreach ($extension in $configExtensions) {
    $configFiles = Get-ChildItem -Path . -Name $extension -File
    foreach ($file in $configFiles) {
        if ($keepAtRoot -notcontains $file -and $file -notlike ".env*" -and $file -notlike "docker-compose*") {
            Move-FileSafe $file "config/$file"
        }
    }
}

Write-Host "`n📊 PHASE 7: Creating Essential Files" -ForegroundColor Magenta

if (-not $DryRun) {
    # Create enhanced Makefile
    $makefileContent = @'
# GameForge AI - Production Makefile
.PHONY: help build test deploy clean

help:
	@echo "GameForge AI - Production Commands"
	@echo "=================================="
	@echo "build          - Build all containers"
	@echo "test           - Run test suite"
	@echo "deploy-dev     - Deploy to development"
	@echo "deploy-prod    - Deploy to production"
	@echo "clean          - Clean up resources"
	@echo "validate       - Validate structure"

build:
	@if exist "docker\compose\docker-compose.production.yml" (docker-compose -f docker/compose/docker-compose.production.yml build) else (echo "Production compose file not found")

test:
	@echo "Running tests..."
	@if exist "package.json" (npm test) else (echo "No package.json found")

deploy-dev:
	@echo "Deploying to development..."
	@if exist "k8s\overlays\dev" (kubectl apply -k k8s/overlays/dev) else (echo "Dev overlay not found")

clean:
	docker system prune -f

validate:
	@powershell -ExecutionPolicy Bypass -File "scripts\validate-production-structure.ps1"
'@

    if (-not (Test-Path "Makefile")) {
        Set-Content -Path "Makefile" -Value $makefileContent -Encoding UTF8
        Write-Host "   ✅ Created enhanced Makefile" -ForegroundColor Green
    }
    
    # Create basic Docker base files
    New-DirectorySafe "docker/base"
    
    if (-not (Test-Path "docker/base/node.Dockerfile")) {
        $nodeDockerfile = @'
FROM node:18-alpine
RUN apk add --no-cache python3 py3-pip make g++
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
'@
        Set-Content -Path "docker/base/node.Dockerfile" -Value $nodeDockerfile -Encoding UTF8
        Write-Host "   ✅ Created docker/base/node.Dockerfile" -ForegroundColor Green
    }
}

Write-Host "`n✅ MIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# Summary
Write-Host "`n📊 SUMMARY:" -ForegroundColor Cyan
Write-Host "Directories Created: $DirectoriesCreated" -ForegroundColor Green
Write-Host "Files Processed: $FilesProcessed" -ForegroundColor Green
Write-Host "Errors: $($Errors.Count)" -ForegroundColor $(if ($Errors.Count -eq 0) { "Green" } else { "Red" })

if ($Errors.Count -gt 0) {
    Write-Host "`n❌ Errors encountered:" -ForegroundColor Red
    foreach ($errorMsg in $Errors) {
        Write-Host "   • $errorMsg" -ForegroundColor Red
    }
}

if ($DryRun) {
    Write-Host "`n🔍 This was a DRY RUN - no files were actually moved" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to perform the actual migration" -ForegroundColor Yellow
} else {
    Write-Host "`n🎉 Repository successfully reorganized to production structure!" -ForegroundColor Green
    Write-Host "`n📋 Next steps:" -ForegroundColor Blue
    Write-Host "   1. Run: .\scripts\validate-production-structure.ps1" -ForegroundColor White
    Write-Host "   2. Update import paths in source code" -ForegroundColor White
    Write-Host "   3. Test builds: make build" -ForegroundColor White
    Write-Host "   4. Update CI/CD pipeline references" -ForegroundColor White
}

if ($CreateBackup -and -not $DryRun) {
    Write-Host "`n💾 Backup available at: $BackupPath" -ForegroundColor Blue
}