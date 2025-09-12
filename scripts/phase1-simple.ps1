# GameForge Production Phase 1 - Simple Pre-Build Hygiene Script

param(
    [switch]$Fix = $false,
    [switch]$Verbose = $false
)

Write-Host "GameForge Production Phase 1 - Pre-Build Hygiene" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$script:issuesFound = 0
$script:issuesFixed = 0

# Simple secrets scan function
function Test-Secrets {
    Write-Host "`nRunning Secrets Scan..." -ForegroundColor Yellow
    
    $secretsFound = $false
    $patterns = @(
        "api_key",
        "secret_key", 
        "password\s*=",
        "token\s*=",
        "AWS_ACCESS_KEY",
        "private_key"
    )
    
    # Get files to scan (limited to prevent hanging)
    $files = Get-ChildItem -Include "*.py", "*.js", "*.json", "*.yml", "*.yaml" -Recurse -File -ErrorAction SilentlyContinue | 
             Where-Object { $_.Length -lt 1MB -and $_.Name -notmatch "lock|node_modules|.git" } |
             Select-Object -First 50
    
    Write-Host "  Scanning $($files.Count) files..." -ForegroundColor Gray
    
    foreach ($file in $files) {
        try {
            $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
            if ($content) {
                foreach ($pattern in $patterns) {
                    if ($content -match $pattern) {
                        Write-Host "  Warning: Potential secret pattern '$pattern' in $($file.Name)" -ForegroundColor Yellow
                        $secretsFound = $true
                        $script:issuesFound++
                        break
                    }
                }
            }
        } catch {
            # Skip files that can't be read
            continue
        }
    }
    
    if (-not $secretsFound) {
        Write-Host "  No obvious secrets found" -ForegroundColor Green
    }
    
    return -not $secretsFound
}

# Check dependencies
function Test-Dependencies {
    Write-Host "`nChecking Dependencies..." -ForegroundColor Yellow
    
    $depIssues = 0
    
    # Check Python requirements
    if (Test-Path "requirements.txt") {
        $content = Get-Content "requirements.txt"
        $unpinned = $content | Where-Object { $_ -match "^[a-zA-Z]" -and $_ -notmatch "==" }
        if ($unpinned) {
            Write-Host "  Found $($unpinned.Count) unpinned Python dependencies" -ForegroundColor Yellow
            $depIssues++
            $script:issuesFound++
        } else {
            Write-Host "  Python dependencies are pinned" -ForegroundColor Green
        }
    }
    
    # Check Node package-lock
    if ((Test-Path "package.json") -and (-not (Test-Path "package-lock.json"))) {
        Write-Host "  Missing package-lock.json" -ForegroundColor Yellow
        $depIssues++
        $script:issuesFound++
        
        if ($Fix) {
            Write-Host "  Creating package-lock.json..." -ForegroundColor Cyan
            try {
                npm install --package-lock-only 2>$null
                Write-Host "  Created package-lock.json" -ForegroundColor Green
                $script:issuesFixed++
            } catch {
                Write-Host "  Failed to create package-lock.json" -ForegroundColor Red
            }
        }
    }
    
    return $depIssues -eq 0
}

# Check Dockerfiles for build args
function Test-ReproducibleBuild {
    Write-Host "`nChecking Reproducible Build..." -ForegroundColor Yellow
    
    $dockerfiles = Get-ChildItem -Filter "Dockerfile*" -File
    $issues = 0
    
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw
        
        $hasBuildArgs = ($content -match "ARG BUILD_DATE") -and 
                       ($content -match "ARG VCS_REF") -and 
                       ($content -match "ARG BUILD_VERSION")
        
        if (-not $hasBuildArgs) {
            Write-Host "  $($dockerfile.Name) missing build args" -ForegroundColor Yellow
            $issues++
            $script:issuesFound++
            
            if ($Fix) {
                Write-Host "  Adding build args to $($dockerfile.Name)..." -ForegroundColor Cyan
                $buildArgs = @"
# Reproducible build arguments
ARG BUILD_DATE
ARG VCS_REF  
ARG BUILD_VERSION

"@
                $newContent = $buildArgs + $content
                $newContent | Out-File -FilePath $dockerfile.FullName -Encoding UTF8
                Write-Host "  Added build args to $($dockerfile.Name)" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  $($dockerfile.Name) has build args" -ForegroundColor Green
        }
    }
    
    return $issues -eq 0
}

# Generate basic SBOM
function New-BasicSBOM {
    Write-Host "`nGenerating SBOM..." -ForegroundColor Yellow
    
    if (-not (Test-Path "sbom")) {
        New-Item -ItemType Directory -Path "sbom" -Force | Out-Null
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd-HHmm"
    $sbomFile = "sbom/sbom-basic-$timestamp.json"
    
    # Create basic SBOM structure
    $sbom = @{
        timestamp = (Get-Date -Format "o")
        repository = Split-Path -Leaf (Get-Location)
        scan_type = "basic"
        python_packages = @()
        node_packages = @()
    }
    
    # Add Python packages if requirements.txt exists
    if (Test-Path "requirements.txt") {
        $pythonPackages = Get-Content "requirements.txt" | 
                         Where-Object { $_ -match "^[a-zA-Z]" } |
                         ForEach-Object { 
                             $parts = $_ -split "=="
                             @{ name = $parts[0]; version = if ($parts.Length -gt 1) { $parts[1] } else { "unknown" } }
                         }
        $sbom.python_packages = $pythonPackages
    }
    
    # Add Node packages if package.json exists
    if (Test-Path "package.json") {
        try {
            $packageJson = Get-Content "package.json" | ConvertFrom-Json
            if ($packageJson.dependencies) {
                $sbom.node_packages = $packageJson.dependencies.PSObject.Properties | 
                                     ForEach-Object { @{ name = $_.Name; version = $_.Value } }
            }
        } catch {
            Write-Host "  Could not parse package.json" -ForegroundColor Yellow
        }
    }
    
    $sbom | ConvertTo-Json -Depth 3 | Out-File -FilePath $sbomFile -Encoding UTF8
    Write-Host "  Basic SBOM created: $sbomFile" -ForegroundColor Green
    
    return $true
}

# Create gitignore security additions
function Add-SecurityGitignore {
    if ($Fix) {
        Write-Host "`nAdding security patterns to .gitignore..." -ForegroundColor Yellow
        
        $securityPatterns = @"

# Security-specific additions
*.key
*.pem
*.p12
.env
.env.*
!.env.example
*_api_key*
*_secret*
*token*
!*token*.py
!*token*.js
*.backup
*.dump
.vault-token
secrets/
credentials/
"@
        
        if (Test-Path ".gitignore") {
            Add-Content -Path ".gitignore" -Value $securityPatterns
        } else {
            $securityPatterns | Out-File -FilePath ".gitignore" -Encoding UTF8
        }
        
        Write-Host "  Security patterns added to .gitignore" -ForegroundColor Green
        $script:issuesFixed++
    }
}

# Main execution
Write-Host "`nStarting Pre-Build Hygiene Check..." -ForegroundColor Cyan

# Run all checks
$secretsOk = Test-Secrets
$depsOk = Test-Dependencies  
$buildOk = Test-ReproducibleBuild
$sbomOk = New-BasicSBOM

if ($Fix) {
    Add-SecurityGitignore
}

# Summary
Write-Host "`nPre-Build Hygiene Summary" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host "Issues Found: $script:issuesFound" -ForegroundColor $(if ($script:issuesFound -eq 0) { "Green" } else { "Yellow" })

if ($Fix) {
    Write-Host "Issues Fixed: $script:issuesFixed" -ForegroundColor Green
}

$allOk = $secretsOk -and $depsOk -and $buildOk -and $sbomOk

if ($allOk -and $script:issuesFound -eq 0) {
    Write-Host "`nRepository is ready for production build!" -ForegroundColor Green
    exit 0
} elseif ($script:issuesFound -gt 0 -and -not $Fix) {
    Write-Host "`nRun with -Fix flag to automatically fix issues:" -ForegroundColor Yellow
    Write-Host "  .\phase1-simple.ps1 -Fix" -ForegroundColor Cyan
    exit 1
} else {
    Write-Host "`nPhase 1 pre-build hygiene completed" -ForegroundColor Green
    exit 0
}
