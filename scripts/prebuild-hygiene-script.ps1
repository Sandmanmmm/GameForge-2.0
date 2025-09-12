# GameForge Production Phase 1 - Repository & Build Preparation Script

param(
    [switch]$Fix = $false,
    [switch]$Verbose = $false
)

Write-Host "🔧 GameForge Production Phase 1 - Pre-Build Hygiene" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$script:issuesFound = 0
$script:issuesFixed = 0

# Function to check if a tool is installed
function Test-ToolInstalled {
    param([string]$Tool)
    
    $command = Get-Command $Tool -ErrorAction SilentlyContinue
    if ($command) {
        Write-Host "✅ $Tool is installed" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ $Tool is not installed" -ForegroundColor Red
        return $false
    }
}

# Function to run secrets scan
function Invoke-SecretsScan {
    Write-Host "`n📋 Running Secrets Scan..." -ForegroundColor Yellow
    
    $secretsFound = $false
    
    # Check for common secret patterns
    $secretPatterns = @(
        @{Pattern = 'api_key\s*='; Description = "API Key"},
        @{Pattern = 'secret_key\s*='; Description = "Secret Key"},
        @{Pattern = 'password\s*='; Description = "Password"},
        @{Pattern = 'token\s*='; Description = "Token"},
        @{Pattern = 'AWS_ACCESS_KEY_ID'; Description = "AWS Access Key"},
        @{Pattern = 'AWS_SECRET_ACCESS_KEY'; Description = "AWS Secret Key"},
        @{Pattern = 'private_key\s*='; Description = "Private Key"},
        @{Pattern = 'mongodb\+srv://'; Description = "MongoDB Connection"},
        @{Pattern = 'postgres://.*@'; Description = "PostgreSQL Connection"}
    )
    
    $excludeFiles = @('*.lock', '*.md', '*.txt', '.env.example', '.env.template')
    $includeFiles = @('*.py', '*.js', '*.ts', '*.jsx', '*.tsx', '*.json', '*.yml', '*.yaml', '*.sh', '*.ps1')
    
    foreach ($pattern in $secretPatterns) {
        if ($Verbose) {
            Write-Host "  Scanning for: $($pattern.Description)" -ForegroundColor Gray
        }
        
        $secretMatches = Get-ChildItem -Recurse -Include $includeFiles -Exclude $excludeFiles -File | 
            Select-String -Pattern $pattern.Pattern -AllMatches
        
        if ($secretMatches) {
            $secretsFound = $true
            $script:issuesFound++
            Write-Host "  ⚠️ Found potential $($pattern.Description) in:" -ForegroundColor Yellow
            foreach ($match in $secretMatches) {
                $relativePath = Resolve-Path -Relative $match.Path
                Write-Host "     $relativePath`:$($match.LineNumber)" -ForegroundColor Red
                if ($Verbose) {
                    Write-Host "       $($match.Line.Trim())" -ForegroundColor DarkGray
                }
            }
        }
    }
    
    if (-not $secretsFound) {
        Write-Host "  ✅ No secrets found in repository" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Found potential secrets" -ForegroundColor Red
        if ($Fix) {
            Write-Host "  🔧 Creating .env.vault template..." -ForegroundColor Cyan
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
HUGGINGFACE_TOKEN=vault:secret/data/gameforge/api#huggingface_token
STRIPE_API_KEY=vault:secret/data/gameforge/api#stripe_key

# AWS Credentials
AWS_ACCESS_KEY_ID=vault:secret/data/gameforge/aws#access_key
AWS_SECRET_ACCESS_KEY=vault:secret/data/gameforge/aws#secret_key

# Security Keys
JWT_SECRET=vault:secret/data/gameforge/security#jwt_secret
ENCRYPTION_KEY=vault:secret/data/gameforge/security#encryption_key

# External Services
REDIS_PASSWORD=vault:secret/data/gameforge/redis#password
ELASTICSEARCH_PASSWORD=vault:secret/data/gameforge/elasticsearch#password
"@
    
    $vaultTemplate | Out-File -FilePath ".env.vault" -Encoding UTF8
    Write-Host "  Created .env.vault template" -ForegroundColor Green
}

# Function to lock dependencies
function Lock-Dependencies {
    Write-Host "`n📋 Locking Dependency Versions..." -ForegroundColor Yellow
    
    # Python dependencies
    if (Test-Path "requirements.in") {
        Write-Host "  Processing Python dependencies..." -ForegroundColor Cyan
        
        if ($Fix) {
            # Generate locked requirements
            try {
                & python -m piptools compile requirements.in -o requirements.txt --resolver=backtracking
                Write-Host "  ✅ Generated locked requirements.txt" -ForegroundColor Green
                $script:issuesFixed++
            } catch {
                Write-Host "  ⚠️ pip-tools not available, using pip freeze..." -ForegroundColor Yellow
                & pip freeze > requirements.txt
                Write-Host "  ✅ Generated requirements.txt with pip freeze" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  ⚠️ requirements.in exists but not compiled" -ForegroundColor Yellow
            $script:issuesFound++
        }
    } elseif (Test-Path "requirements.txt") {
        # Check if requirements.txt has version pins
        $unpinned = Get-Content "requirements.txt" | Where-Object { $_ -match '^[a-zA-Z]' -and $_ -notmatch '==' }
        if ($unpinned) {
            Write-Host "  ⚠️ Found unpinned dependencies:" -ForegroundColor Yellow
            $unpinned | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
            $script:issuesFound++
            
            if ($Fix) {
                Write-Host "  🔧 Freezing current environment..." -ForegroundColor Cyan
                & pip freeze > requirements.locked.txt
                Write-Host "  ✅ Created requirements.locked.txt" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  ✅ All Python dependencies are pinned" -ForegroundColor Green
        }
    }
    
    # Node dependencies
    if (Test-Path "package.json") {
        Write-Host "  Processing Node dependencies..." -ForegroundColor Cyan
        
        if (-not (Test-Path "package-lock.json")) {
            Write-Host "  ⚠️ package-lock.json not found" -ForegroundColor Yellow
            $script:issuesFound++
            
            if ($Fix) {
                & npm install --package-lock-only
                Write-Host "  ✅ Generated package-lock.json" -ForegroundColor Green
                $script:issuesFixed++
            }
        } else {
            Write-Host "  ✅ package-lock.json exists" -ForegroundColor Green
        }
    }
}

# Function to add reproducible build configuration
function Add-ReproducibleBuild {
    Write-Host "`n📋 Checking Reproducible Build Configuration..." -ForegroundColor Yellow
    
    $dockerfiles = Get-ChildItem -Filter "Dockerfile*" -File
    
    foreach ($dockerfile in $dockerfiles) {
        $content = Get-Content $dockerfile.FullName -Raw
        
        # Check for build args
        $hasBuildDate = $content -match 'ARG BUILD_DATE'
        $hasVcsRef = $content -match 'ARG VCS_REF'
        $hasBuildVersion = $content -match 'ARG BUILD_VERSION'
        
        if (-not ($hasBuildDate -and $hasVcsRef -and $hasBuildVersion)) {
            Write-Host "  ⚠️ $($dockerfile.Name) missing reproducible build args" -ForegroundColor Yellow
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
      org.opencontainers.image.vendor="GameForge" \
      org.opencontainers.image.title="GameForge Production" \
      org.opencontainers.image.description="AI-powered game production platform"
"@
                
                if (-not $hasBuildDate) {
                    $content = $buildArgs + $content + $labels
                    $content | Out-File -FilePath $dockerfile.FullName -Encoding UTF8
                    Write-Host "  ✅ Added reproducible build args to $($dockerfile.Name)" -ForegroundColor Green
                    $script:issuesFixed++
                }
            }
        } else {
            Write-Host "  ✅ $($dockerfile.Name) has reproducible build args" -ForegroundColor Green
        }
    }
}

# Function to generate SBOM
function New-SBOM {
    Write-Host "`n📋 Generating Software Bill of Materials (SBOM)..." -ForegroundColor Yellow
    
    # Check if syft is available
    $syftInstalled = Test-ToolInstalled "syft"
    
    if (-not $syftInstalled) {
        Write-Host "  Syft not found, creating simple dependency list..." -ForegroundColor Cyan
        
        # Create SBOM directory
        if (-not (Test-Path "sbom")) {
            New-Item -ItemType Directory -Path "sbom" -Force | Out-Null
        }
        
        # Generate simple SBOM
        $timestamp = Get-Date -Format "yyyy-MM-dd"
        $sbomFile = "sbom/sbom-simple-$timestamp.json"
        
        $simpleSBOM = @{
            created = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            tool = "GameForge Phase 1"
            python_packages = @()
            docker_images = @()
        }
        
        # Add Python packages if available
        if (Test-Path "requirements.txt") {
            $packages = Get-Content "requirements.txt" | Where-Object { $_ -notmatch '^#' -and $_ -notmatch '^\s*$' }
            $simpleSBOM.python_packages = $packages
        }
        
        # Add Docker images
        $dockerfiles = Get-ChildItem -Filter "Dockerfile*" -File
        foreach ($dockerfile in $dockerfiles) {
            $content = Get-Content $dockerfile.FullName
            $fromLines = $content | Where-Object { $_ -match '^FROM\s+(.+)' }
            foreach ($from in $fromLines) {
                $image = ($from -split '\s+')[1]
                $simpleSBOM.docker_images += $image
            }
        }
        
        $simpleSBOM | ConvertTo-Json -Depth 3 | Out-File -FilePath $sbomFile -Encoding UTF8
        Write-Host "  ✅ Simple SBOM generated: $sbomFile" -ForegroundColor Green
    }
}

# Function to create pre-commit hooks
function New-PreCommitHooks {
    Write-Host "`n📋 Setting up Pre-commit Hooks..." -ForegroundColor Yellow
    
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
      - id: check-merge-conflict
      - id: detect-private-key
      
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.10
        
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100']
        
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
"@
    
    if ($Fix) {
        $preCommitConfig | Out-File -FilePath ".pre-commit-config.yaml" -Encoding UTF8
        Write-Host "  ✅ Created .pre-commit-config.yaml" -ForegroundColor Green
        $script:issuesFixed++
        
        # Install pre-commit if available
        if (Get-Command "pre-commit" -ErrorAction SilentlyContinue) {
            & pre-commit install
            Write-Host "  ✅ Pre-commit hooks installed" -ForegroundColor Green
        }
    } else {
        if (-not (Test-Path ".pre-commit-config.yaml")) {
            Write-Host "  ⚠️ Pre-commit hooks not configured" -ForegroundColor Yellow
            $script:issuesFound++
        } else {
            Write-Host "  ✅ Pre-commit hooks configured" -ForegroundColor Green
        }
    }
}

# Main execution
Write-Host "`n🔍 Starting Pre-Build Hygiene Check..." -ForegroundColor Cyan

# Run all checks
Invoke-SecretsScan
Lock-Dependencies
Add-ReproducibleBuild
New-SBOM
New-PreCommitHooks

# Summary
Write-Host "`n📊 Pre-Build Hygiene Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Issues Found: $script:issuesFound" -ForegroundColor $(if ($script:issuesFound -eq 0) { "Green" } else { "Yellow" })
if ($Fix) {
    Write-Host "Issues Fixed: $script:issuesFixed" -ForegroundColor Green
}

if ($script:issuesFound -gt 0 -and -not $Fix) {
    Write-Host "`n💡 Run with -Fix flag to automatically fix issues" -ForegroundColor Yellow
    Write-Host "   .\phase1-prebuild-hygiene.ps1 -Fix" -ForegroundColor Cyan
}

if ($script:issuesFound -eq 0) {
    Write-Host "`n✅ Repository is ready for production build!" -ForegroundColor Green
    exit 0
} else {
    exit 1
}
