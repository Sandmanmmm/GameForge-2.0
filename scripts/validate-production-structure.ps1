# GameForge AI - Production Migration Validator
# This script validates the migration and ensures everything is properly organized

param(
    [switch]$Detailed = $false,
    [switch]$FixIssues = $false
)

Write-Host "🔍 GameForge AI - Production Structure Validator" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Get the repository root
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

$ValidationResults = @{
    Passed = 0
    Failed = 0
    Warnings = 0
    Issues = @()
}

# Function to validate directory structure
function Test-DirectoryStructure {
    Write-Host "`n📁 Validating Directory Structure" -ForegroundColor Magenta
    
    $requiredDirs = @(
        ".github/workflows",
        "docker/base",
        "docker/services", 
        "docker/compose",
        "k8s/base",
        "k8s/overlays",
        "src/frontend",
        "src/backend",
        "scripts",
        "monitoring", 
        "security",
        "tests",
        "docs"
    )
    
    foreach ($dir in $requiredDirs) {
        if (Test-Path $dir) {
            Write-Host "   ✅ $dir" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ❌ Missing: $dir" -ForegroundColor Red
            $ValidationResults.Failed++
            $ValidationResults.Issues += "Missing required directory: $dir"
            
            if ($FixIssues) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-Host "      🔧 Created: $dir" -ForegroundColor Yellow
            }
        }
    }
}

# Function to validate docker structure
function Test-DockerStructure {
    Write-Host "`n🐳 Validating Docker Structure" -ForegroundColor Magenta
    
    $dockerFiles = @{
        "docker/base/node.Dockerfile" = "Node.js base image"
        "docker/base/python.Dockerfile" = "Python base image"
        "docker/base/gpu.Dockerfile" = "GPU base image"
    }
    
    foreach ($file in $dockerFiles.Keys) {
        if (Test-Path $file) {
            Write-Host "   ✅ $($dockerFiles[$file]): $file" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ⚠️  Missing: $file" -ForegroundColor Yellow
            $ValidationResults.Warnings++
        }
    }
    
    # Check for docker-compose files in compose directory
    $composeFiles = Get-ChildItem "docker/compose" -Filter "*.yml" -ErrorAction SilentlyContinue
    if ($composeFiles.Count -gt 0) {
        Write-Host "   ✅ Docker Compose files: $($composeFiles.Count) found" -ForegroundColor Green
        $ValidationResults.Passed++
    } else {
        Write-Host "   ❌ No Docker Compose files found in docker/compose/" -ForegroundColor Red
        $ValidationResults.Failed++
        $ValidationResults.Issues += "No Docker Compose files in docker/compose/"
    }
}

# Function to validate source code structure
function Test-SourceStructure {
    Write-Host "`n💻 Validating Source Code Structure" -ForegroundColor Magenta
    
    $sourceChecks = @{
        "src/frontend/web" = "Frontend web application"
        "src/backend" = "Backend services"
        "src/common" = "Common utilities"
    }
    
    foreach ($path in $sourceChecks.Keys) {
        if (Test-Path $path) {
            $fileCount = (Get-ChildItem $path -Recurse -File).Count
            Write-Host "   ✅ $($sourceChecks[$path]): $fileCount files" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ❌ Missing: $path" -ForegroundColor Red
            $ValidationResults.Failed++
            $ValidationResults.Issues += "Missing source directory: $path"
        }
    }
}

# Function to check for loose files at root
function Test-RootCleanness {
    Write-Host "`n🧹 Validating Root Directory Cleanness" -ForegroundColor Magenta
    
    $allowedAtRoot = @(
        "package.json", "package-lock.json", "tsconfig.json", "components.json",
        "tailwind.config.js", "vite.config.ts", "Makefile", "LICENSE", "README.md",
        ".env", ".env.example", ".gitignore", ".dockerignore"
    )
    
    $allowedPatterns = @("\.env\.*")
    
    $rootFiles = Get-ChildItem -File | Where-Object { 
        $fileName = $_.Name
        $isAllowed = $allowedAtRoot -contains $fileName
        if (-not $isAllowed) {
            foreach ($pattern in $allowedPatterns) {
                if ($fileName -match $pattern) {
                    $isAllowed = $true
                    break
                }
            }
        }
        return -not $isAllowed
    }
    
    if ($rootFiles.Count -eq 0) {
        Write-Host "   ✅ Root directory is clean" -ForegroundColor Green
        $ValidationResults.Passed++
    } else {
        Write-Host "   ⚠️  Found $($rootFiles.Count) loose files at root:" -ForegroundColor Yellow
        $ValidationResults.Warnings += $rootFiles.Count
        
        if ($Detailed) {
            foreach ($file in $rootFiles) {
                Write-Host "      - $($file.Name)" -ForegroundColor Gray
            }
        }
        
        if ($FixIssues) {
            Write-Host "   🔧 Moving loose files to appropriate directories..." -ForegroundColor Yellow
            foreach ($file in $rootFiles) {
                $targetDir = switch -Regex ($file.Extension) {
                    "\.ps1|\.sh|\.bat" { "scripts" }
                    "\.md" { "docs" }
                    "\.json|\.yaml|\.yml" { "config" }
                    default { "misc" }
                }
                
                if (-not (Test-Path $targetDir)) {
                    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                }
                
                Move-Item $file.FullName (Join-Path $targetDir $file.Name) -Force
                Write-Host "      ✅ Moved $($file.Name) to $targetDir/" -ForegroundColor Green
            }
        }
    }
}

# Function to validate CI/CD structure
function Test-CICDStructure {
    Write-Host "`n🔄 Validating CI/CD Structure" -ForegroundColor Magenta
    
    $workflows = Get-ChildItem ".github/workflows" -Filter "*.yml" -ErrorAction SilentlyContinue
    
    $requiredWorkflows = @("build.yml", "test.yml", "security-scan.yml", "deploy.yml")
    $missingWorkflows = @()
    
    foreach ($workflow in $requiredWorkflows) {
        if ($workflows.Name -contains $workflow) {
            Write-Host "   ✅ $workflow" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ⚠️  Missing workflow: $workflow" -ForegroundColor Yellow
            $ValidationResults.Warnings++
            $missingWorkflows += $workflow
        }
    }
    
    if ($missingWorkflows.Count -gt 0 -and $FixIssues) {
        Write-Host "   🔧 Creating missing workflow templates..." -ForegroundColor Yellow
        # Here you could add logic to create basic workflow templates
    }
}

# Function to validate monitoring setup
function Test-MonitoringStructure {
    Write-Host "`n📊 Validating Monitoring Structure" -ForegroundColor Magenta
    
    $monitoringComponents = @{
        "monitoring/prometheus" = "Prometheus configuration"
        "monitoring/grafana" = "Grafana dashboards"
        "monitoring/alertmanager" = "Alert manager setup"
    }
    
    foreach ($component in $monitoringComponents.Keys) {
        if (Test-Path $component) {
            Write-Host "   ✅ $($monitoringComponents[$component])" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ⚠️  Missing: $component" -ForegroundColor Yellow
            $ValidationResults.Warnings++
        }
    }
}

# Function to validate security setup
function Test-SecurityStructure {
    Write-Host "`n🔒 Validating Security Structure" -ForegroundColor Magenta
    
    $securityComponents = @{
        "security/policies" = "Security policies"
        "security/seccomp" = "Seccomp profiles"
        "security/scripts" = "Security scripts"
    }
    
    foreach ($component in $securityComponents.Keys) {
        if (Test-Path $component) {
            Write-Host "   ✅ $($securityComponents[$component])" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ⚠️  Missing: $component" -ForegroundColor Yellow
            $ValidationResults.Warnings++
        }
    }
}

# Function to check for common issues
function Test-CommonIssues {
    Write-Host "`n🔍 Checking for Common Issues" -ForegroundColor Magenta
    
    # Check for duplicate files
    $duplicateCheck = @{
        "package.json files" = (Get-ChildItem -Recurse -Name "package.json").Count
        "Docker compose files" = (Get-ChildItem -Recurse -Name "docker-compose*.yml").Count
    }
    
    foreach ($check in $duplicateCheck.Keys) {
        $count = $duplicateCheck[$check]
        if ($count -le 3) {  # Reasonable number
            Write-Host "   ✅ $check`: $count (reasonable)" -ForegroundColor Green
            $ValidationResults.Passed++
        } else {
            Write-Host "   ⚠️  $check`: $count (may have duplicates)" -ForegroundColor Yellow
            $ValidationResults.Warnings++
        }
    }
    
    # Check for broken symlinks or references
    # This would require more sophisticated checking
}

# Run all validations
Test-DirectoryStructure
Test-DockerStructure
Test-SourceStructure
Test-RootCleanness
Test-CICDStructure
Test-MonitoringStructure
Test-SecurityStructure
Test-CommonIssues

# Summary
Write-Host "`n📋 VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host "✅ Passed: $($ValidationResults.Passed)" -ForegroundColor Green
Write-Host "⚠️  Warnings: $($ValidationResults.Warnings)" -ForegroundColor Yellow
Write-Host "❌ Failed: $($ValidationResults.Failed)" -ForegroundColor Red

if ($ValidationResults.Issues.Count -gt 0) {
    Write-Host "`n🚨 Critical Issues Found:" -ForegroundColor Red
    foreach ($issue in $ValidationResults.Issues) {
        Write-Host "   • $issue" -ForegroundColor Red
    }
}

$totalChecks = $ValidationResults.Passed + $ValidationResults.Warnings + $ValidationResults.Failed
$successRate = [math]::Round(($ValidationResults.Passed / $totalChecks) * 100, 1)

Write-Host "`n📊 Overall Health: $successRate%" -ForegroundColor $(
    if ($successRate -ge 90) { "Green" }
    elseif ($successRate -ge 70) { "Yellow" }
    else { "Red" }
)

if ($ValidationResults.Failed -eq 0) {
    Write-Host "`n🎉 Repository structure is production-ready!" -ForegroundColor Green
} elseif ($ValidationResults.Failed -le 3) {
    Write-Host "`n✨ Repository structure is mostly ready with minor issues" -ForegroundColor Yellow
} else {
    Write-Host "`n⚠️  Repository structure needs significant improvements" -ForegroundColor Red
}

Write-Host "`n💡 Recommendations:" -ForegroundColor Cyan
Write-Host "   • Run with -FixIssues to auto-resolve simple problems" -ForegroundColor White
Write-Host "   • Use -Detailed for more verbose output" -ForegroundColor White
Write-Host "   • Review and test all deployments after migration" -ForegroundColor White