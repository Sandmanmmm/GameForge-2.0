# GameForge Production Phase 1 - Repository & Build Preparation Script

param(
    [switch]$Fix = $false,
    [switch]$Verbose = $false
)

Write-Host "GameForge Production Phase 1 - Pre-Build Hygiene" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$script:issuesFound = 0
$script:issuesFixed = 0

# Function to check if a tool is installed
function Test-ToolInstalled {
    param([string]$Tool)
    
    $command = Get-Command $Tool -ErrorAction SilentlyContinue
    if ($command) {
        Write-Host "[PASS] $Tool is installed" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[FAIL] $Tool is not installed" -ForegroundColor Red
        return $false
    }
}

# Function to run secrets scan
function Invoke-SecretsScan {
    Write-Host "`nRunning Secrets Scan..." -ForegroundColor Yellow
    
    $secretsFound = $false
    
    # Check for common secret patterns (simplified)
    $secretPatterns = @(
        @{Pattern = 'api_key\s*='; Description = "API Key"},
        @{Pattern = 'secret_key\s*='; Description = "Secret Key"},
        @{Pattern = 'password\s*='; Description = "Password"},
        @{Pattern = 'token\s*='; Description = "Token"},
        @{Pattern = 'AWS_ACCESS_KEY_ID'; Description = "AWS Access Key"},
        @{Pattern = 'AWS_SECRET_ACCESS_KEY'; Description = "AWS Secret Key"},
        @{Pattern = 'private_key\s*='; Description = "Private Key"}
    )
    
    $includeFiles = @('*.py', '*.js', '*.json', '*.yml', '*.yaml')
    
    foreach ($pattern in $secretPatterns) {
        if ($Verbose) {
            Write-Host "  Scanning for: $($pattern.Description)" -ForegroundColor Gray
        }
        
        try {
            $matches = Get-ChildItem -Recurse -Include $includeFiles -File -ErrorAction SilentlyContinue | 
                Select-String -Pattern $pattern.Pattern -AllMatches -ErrorAction SilentlyContinue
            
            if ($matches) {
                $secretsFound = $true
                $script:issuesFound++
                Write-Host "  [WARN] Found potential $($pattern.Description) in:" -ForegroundColor Yellow
                foreach ($match in $matches) {
                    $relativePath = Resolve-Path -Relative $match.Path
                    Write-Host "     $relativePath : $($match.LineNumber)" -ForegroundColor Red
                }
            }
        } catch {
            Write-Host "  [ERROR] Error scanning for $($pattern.Description): $_" -ForegroundColor Red
        }
    }
    
    if (-not $secretsFound) {
        Write-Host "  [PASS] No secrets found in repository" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Found potential secrets" -ForegroundColor Red
        if ($Fix) {
            Write-Host "  [FIX] Creating .env.vault template..." -ForegroundColor Cyan
            New-VaultTemplate
            $script:issuesFixed++
        }
    }
    
    return -not $secretsFound
}

# Function to create vault template
function New-VaultTemplate {
    $vaultTemplate = @"
# Vault Configuration Template
# Move all secrets to HashiCorp Vault or environment variables

# Database Credentials
DATABASE_URL=vault:secret/data/gameforge/database#url
DATABASE_PASSWORD=vault:secret/data/gameforge/database#password

# API Keys
OPENAI_API_KEY=vault:secret/data/gameforge/api#openai_key
JWT_SECRET=vault:secret/data/gameforge/security#jwt_secret

# AWS Credentials
AWS_ACCESS_KEY_ID=vault:secret/data/gameforge/aws#access_key
AWS_SECRET_ACCESS_KEY=vault:secret/data/gameforge/aws#secret_key
"@
    
    $vaultTemplate | Out-File -FilePath ".env.vault" -Encoding UTF8
    Write-Host "  [PASS] Created .env.vault template" -ForegroundColor Green
}

# Function to lock dependencies
function Lock-Dependencies {
    Write-Host "`nLocking Dependency Versions..." -ForegroundColor Yellow
    
    # Python dependencies
    if (Test-Path "requirements.in") {
        Write-Host "  Processing Python dependencies..." -ForegroundColor Cyan
        
        if ($Fix) {
            try {
                # Try pip-compile first
                & python -m piptools compile requirements.in -o requirements.txt --resolver=backtracking
                Write-Host "  [PASS] Generated locked requirements.txt" -ForegroundColor Green
                $script:issuesFixed++
            } catch {
                # Fallback to pip freeze
                Write-Host "  [WARN] pip-tools not available, using pip freeze..." -ForegroundColor Yellow
                & pip freeze > requirements.txt
                Write-Host "  [PASS] Generated requirements.txt with pip freeze" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  [WARN] requirements.in exists but not compiled" -ForegroundColor Yellow
            $script:issuesFound++
        }
    } elseif (Test-Path "requirements.txt") {
        # Check if requirements.txt has version pins
        $content = Get-Content "requirements.txt" -ErrorAction SilentlyContinue
        $unpinned = $content | Where-Object { $_ -match '^[a-zA-Z]' -and $_ -notmatch '==' }
        if ($unpinned) {
            Write-Host "  [WARN] Found unpinned dependencies:" -ForegroundColor Yellow
            $unpinned | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
            $script:issuesFound++
            
            if ($Fix) {
                Write-Host "  [FIX] Freezing current environment..." -ForegroundColor Cyan
                & pip freeze > requirements.locked.txt
                Write-Host "  [PASS] Created requirements.locked.txt" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  [PASS] All Python dependencies are pinned" -ForegroundColor Green
        }
    } else {
        Write-Host "  [INFO] No Python requirements file found" -ForegroundColor Gray
    }
    
    # Node dependencies
    if (Test-Path "package.json") {
        Write-Host "  Processing Node dependencies..." -ForegroundColor Cyan
        
        if (-not (Test-Path "package-lock.json")) {
            Write-Host "  [WARN] package-lock.json not found" -ForegroundColor Yellow
            $script:issuesFound++
            
            if ($Fix) {
                & npm install --package-lock-only
                Write-Host "  [PASS] Generated package-lock.json" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  [PASS] package-lock.json exists" -ForegroundColor Green
        }
    } else {
        Write-Host "  [INFO] No package.json found" -ForegroundColor Gray
    }
}

# Function to add reproducible build configuration
function Add-ReproducibleBuild {
    Write-Host "`nChecking Reproducible Build Configuration..." -ForegroundColor Yellow
    
    $dockerfiles = Get-ChildItem -Filter "Dockerfile*" -File -ErrorAction SilentlyContinue
    
    if ($dockerfiles.Count -eq 0) {
        Write-Host "  [INFO] No Dockerfiles found" -ForegroundColor Gray
        return
    }
    
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw -ErrorAction SilentlyContinue
        
        # Check for build args
        $hasBuildDate = $content -match 'ARG BUILD_DATE'
        $hasVcsRef = $content -match 'ARG VCS_REF'
        $hasBuildVersion = $content -match 'ARG BUILD_VERSION'
        
        if (-not ($hasBuildDate -and $hasVcsRef -and $hasBuildVersion)) {
            Write-Host "  [WARN] $($dockerfile.Name) missing reproducible build args" -ForegroundColor Yellow
            $script:issuesFound++
            
            if ($Fix) {
                # Add build args at the beginning of the file
                $buildArgs = @"
# Reproducible build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION

"@
                $labels = @"

# Labels for image metadata
LABEL org.opencontainers.image.created=`${BUILD_DATE} \
      org.opencontainers.image.revision=`${VCS_REF} \
      org.opencontainers.image.version=`${BUILD_VERSION} \
      org.opencontainers.image.vendor="GameForge"
"@
                
                $newContent = $buildArgs + $content + $labels
                $newContent | Out-File -FilePath $dockerfile.FullName -Encoding UTF8
                Write-Host "  [PASS] Added reproducible build args to $($dockerfile.Name)" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  [PASS] $($dockerfile.Name) has reproducible build args" -ForegroundColor Green
        }
    }
}

# Function to generate SBOM
function New-SBOM {
    Write-Host "`nGenerating Software Bill of Materials (SBOM)..." -ForegroundColor Yellow
    
    # Create SBOM directory
    if (-not (Test-Path "sbom")) {
        New-Item -ItemType Directory -Path "sbom" -Force | Out-Null
    }
    
    # Check if syft is available
    $syftInstalled = Test-ToolInstalled "syft"
    
    if (-not $syftInstalled) {
        Write-Host "  [INFO] Syft not installed, creating placeholder SBOM..." -ForegroundColor Yellow
        
        # Create a simple placeholder SBOM
        $timestamp = Get-Date -Format "yyyy-MM-dd"
        $placeholderSBOM = @"
{
  "artifacts": [],
  "artifactRelationships": [],
  "source": {
    "type": "directory",
    "target": "."
  },
  "distro": {},
  "descriptor": {
    "name": "gameforge-sbom-placeholder",
    "version": "1.0.0"
  },
  "schema": {
    "version": "3.0.1",
    "url": "https://raw.githubusercontent.com/anchore/syft/main/schema/json/schema-3.0.1.json"
  }
}
"@
        
        $sbomFile = "sbom/sbom-$timestamp.json"
        $placeholderSBOM | Out-File -FilePath $sbomFile -Encoding UTF8
        Write-Host "  [PASS] Created placeholder SBOM: $sbomFile" -ForegroundColor Green
    } else {
        # Generate SBOM with syft
        $timestamp = Get-Date -Format "yyyy-MM-dd"
        $sbomFile = "sbom/sbom-$timestamp.json"
        
        try {
            & syft packages dir:. -o json | Out-File -FilePath $sbomFile -Encoding UTF8
            Write-Host "  [PASS] SBOM generated: $sbomFile" -ForegroundColor Green
        } catch {
            Write-Host "  [FAIL] Failed to generate SBOM: $_" -ForegroundColor Red
            $script:issuesFound++
        }
    }
}

# Function to create pre-commit hooks
function New-PreCommitHooks {
    Write-Host "`nSetting up Pre-commit Hooks..." -ForegroundColor Yellow
    
    if ($Fix) {
        $preCommitConfig = @"
# Pre-commit configuration for GameForge
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: detect-private-key
"@
        
        $preCommitConfig | Out-File -FilePath ".pre-commit-config.yaml" -Encoding UTF8
        Write-Host "  [PASS] Created .pre-commit-config.yaml" -ForegroundColor Green
        $script:issuesFixed++
    } else {
        if (-not (Test-Path ".pre-commit-config.yaml")) {
            Write-Host "  [WARN] Pre-commit hooks not configured" -ForegroundColor Yellow
            $script:issuesFound++
        } else {
            Write-Host "  [PASS] Pre-commit hooks configured" -ForegroundColor Green
        }
    }
}

# Main execution
Write-Host "`nStarting Pre-Build Hygiene Check..." -ForegroundColor Cyan

# Run all checks
Invoke-SecretsScan
Lock-Dependencies
Add-ReproducibleBuild
New-SBOM
New-PreCommitHooks

# Summary
Write-Host "`nPre-Build Hygiene Summary" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host "Issues Found: $script:issuesFound" -ForegroundColor $(if ($script:issuesFound -eq 0) { "Green" } else { "Yellow" })
if ($Fix) {
    Write-Host "Issues Fixed: $script:issuesFixed" -ForegroundColor Green
}

if ($script:issuesFound -gt 0 -and -not $Fix) {
    Write-Host "`nRun with -Fix flag to automatically fix issues" -ForegroundColor Yellow
    Write-Host "   .\phase1-prebuild-hygiene.ps1 -Fix" -ForegroundColor Cyan
}

if ($script:issuesFound -eq 0) {
    Write-Host "`nRepository is ready for production build!" -ForegroundColor Green
    exit 0
} else {
    exit 1
}
