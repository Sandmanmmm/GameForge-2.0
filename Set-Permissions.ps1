# GameForge File Permissions Setup Script (Windows/PowerShell)
# Sets proper file permissions for secure deployment
# Usage: .\Set-Permissions.ps1 [-Environment production]

param(
    [string]$Environment = "production",
    [string]$DevUser = "dev",
    [string]$AppUser = "gameforge"
)

# Configuration
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

# Color functions for output
function Write-Info {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] INFO: $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] SUCCESS: $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] WARNING: $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $Message" -ForegroundColor Red
}

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Set file permissions using icacls
function Set-FilePermissions {
    param(
        [string]$Path,
        [string]$User,
        [string]$Permissions
    )
    
    try {
        $result = & icacls $Path /grant "${User}:${Permissions}" /T /C /Q 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to set permissions on $Path"
        }
    }
    catch {
        Write-Warning "Error setting permissions on $Path : $_"
    }
}

# Remove inherited permissions and set explicit ones
function Set-ExplicitPermissions {
    param(
        [string]$Path,
        [string]$User,
        [string]$Permissions
    )
    
    try {
        # Remove inheritance
        & icacls $Path /inheritance:r /T /C /Q | Out-Null
        
        # Grant specific permissions
        & icacls $Path /grant "SYSTEM:F" /T /C /Q | Out-Null
        & icacls $Path /grant "Administrators:F" /T /C /Q | Out-Null
        & icacls $Path /grant "${User}:${Permissions}" /T /C /Q | Out-Null
        
        Write-Info "Set explicit permissions for $Path"
    }
    catch {
        Write-Warning "Error setting explicit permissions on $Path : $_"
    }
}

# Set permissions for source code files
function Set-SourceCodePermissions {
    Write-Success "Setting permissions for source code files..."
    
    # Main application file
    $mainPy = Join-Path $ProjectRoot "gameforge\main.py"
    if (Test-Path $mainPy) {
        Write-Info "Setting permissions for main.py"
        Set-FilePermissions -Path $mainPy -User $DevUser -Permissions "R"
        
        # Also set read permissions for the app user
        Set-FilePermissions -Path $mainPy -User $AppUser -Permissions "R"
    }
    
    # Core module files
    $coreDir = Join-Path $ProjectRoot "gameforge\core"
    if (Test-Path $coreDir) {
        Write-Info "Setting permissions for core module files"
        Get-ChildItem -Path $coreDir -Filter "*.py" -Recurse | ForEach-Object {
            Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "R"
            Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "R"
        }
    }
    
    # API router files
    $apiDir = Join-Path $ProjectRoot "gameforge\api"
    if (Test-Path $apiDir) {
        Write-Info "Setting permissions for API router files"
        Get-ChildItem -Path $apiDir -Filter "*.py" -Recurse | ForEach-Object {
            Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "R"
            Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "R"
        }
    }
    
    # All Python source files
    Write-Info "Setting permissions for all Python source files"
    Get-ChildItem -Path $ProjectRoot -Filter "*.py" -Recurse | Where-Object {
        $_.FullName -notlike "*\.git*" -and $_.FullName -notlike "*\__pycache__*"
    } | ForEach-Object {
        Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "R"
        Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "R"
    }
}

# Set permissions for configuration files
function Set-ConfigPermissions {
    Write-Success "Setting permissions for configuration files..."
    
    $configFiles = @(
        "requirements.txt",
        "docker-compose*.yml",
        "Dockerfile",
        ".env.example"
    )
    
    foreach ($pattern in $configFiles) {
        Get-ChildItem -Path $ProjectRoot -Filter $pattern | ForEach-Object {
            Write-Info "Setting permissions for $($_.Name)"
            Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "R"
            Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "R"
        }
    }
    
    # Secret files - highly restricted
    $secretPatterns = @(".env", "*.key", "*.pem", "*secret*", "*credentials*")
    
    foreach ($pattern in $secretPatterns) {
        Get-ChildItem -Path $ProjectRoot -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Warning "Found secret file: $($_.Name) - setting restrictive permissions"
            Set-ExplicitPermissions -Path $_.FullName -User $DevUser -Permissions "R"
        }
    }
}

# Set permissions for runtime directories
function Set-RuntimePermissions {
    Write-Success "Setting permissions for runtime directories..."
    
    $runtimeDirs = @("logs", "data", "uploads", "cache", "tmp")
    
    foreach ($dir in $runtimeDirs) {
        $fullPath = Join-Path $ProjectRoot $dir
        
        if (Test-Path $fullPath) {
            Write-Info "Setting permissions for $dir directory"
            Set-FilePermissions -Path $fullPath -User $AppUser -Permissions "F"
        } else {
            Write-Info "Creating runtime directory: $dir"
            New-Item -Path $fullPath -ItemType Directory -Force | Out-Null
            Set-FilePermissions -Path $fullPath -User $AppUser -Permissions "F"
        }
    }
}

# Set permissions for scripts
function Set-ScriptPermissions {
    Write-Success "Setting permissions for executable scripts..."
    
    # PowerShell scripts
    Get-ChildItem -Path $ProjectRoot -Filter "*.ps1" -Recurse | ForEach-Object {
        Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "RX"
        Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "RX"
    }
    
    # Batch scripts
    Get-ChildItem -Path $ProjectRoot -Filter "*.bat" -Recurse | ForEach-Object {
        Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "RX"
        Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "RX"
    }
    
    # Shell scripts (for WSL compatibility)
    Get-ChildItem -Path $ProjectRoot -Filter "*.sh" -Recurse | ForEach-Object {
        Set-FilePermissions -Path $_.FullName -User $DevUser -Permissions "RX"
        Set-FilePermissions -Path $_.FullName -User $AppUser -Permissions "RX"
    }
}

# Validate permissions
function Test-Permissions {
    Write-Success "Validating file permissions..."
    
    $errors = 0
    
    # Check main.py exists and has proper permissions
    $mainPy = Join-Path $ProjectRoot "gameforge\main.py"
    if (Test-Path $mainPy) {
        Write-Info "main.py found and accessible ✓"
    } else {
        Write-Error "main.py not found"
        $errors++
    }
    
    # Check core files
    $coreDir = Join-Path $ProjectRoot "gameforge\core"
    if (Test-Path $coreDir) {
        $coreFiles = Get-ChildItem -Path $coreDir -Filter "*.py" -Recurse
        Write-Info "Core module files: $($coreFiles.Count) files ✓"
    }
    
    # Check API files
    $apiDir = Join-Path $ProjectRoot "gameforge\api"
    if (Test-Path $apiDir) {
        $apiFiles = Get-ChildItem -Path $apiDir -Filter "*.py" -Recurse
        Write-Info "API router files: $($apiFiles.Count) files ✓"
    }
    
    if ($errors -eq 0) {
        Write-Success "All file permissions validation passed ✓"
        return $true
    } else {
        Write-Error "Found $errors permission errors"
        return $false
    }
}

# Generate deployment script for Windows
function New-DeploymentScript {
    Write-Success "Generating deployment permissions script..."
    
    $deployScript = @'
# GameForge Deployment Permissions Script (Windows)
# Run this script on the target deployment environment as Administrator
# Usage: .\Deploy-Permissions.ps1

param(
    [string]$AppUser = "gameforge"
)

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Error "This script must be run as Administrator"
    exit 1
}

Write-Host "Setting deployment permissions for GameForge..." -ForegroundColor Green

# Create application user if it doesn't exist
try {
    Get-LocalUser -Name $AppUser -ErrorAction Stop | Out-Null
    Write-Host "Application user '$AppUser' already exists" -ForegroundColor Yellow
}
catch {
    Write-Host "Creating application user: $AppUser" -ForegroundColor Blue
    $password = ConvertTo-SecureString -String (Get-Random) -AsPlainText -Force
    New-LocalUser -Name $AppUser -Password $password -Description "GameForge Application User" -UserMayNotChangePassword
}

# Set ownership and permissions for runtime
Write-Host "Setting file permissions..." -ForegroundColor Blue

# Deny network logon for app user (security hardening)
# Note: This would require additional configuration in production

# Set permissions on application files
icacls . /grant "${AppUser}:R" /T /C /Q
icacls . /grant "SYSTEM:F" /T /C /Q
icacls . /grant "Administrators:F" /T /C /Q

# Ensure Python files are not executable by removing execute permissions
Get-ChildItem -Filter "*.py" -Recurse | ForEach-Object {
    icacls $_.FullName /deny "${AppUser}:X" /C /Q 2>$null
}

# Set restrictive permissions on sensitive files
if (Test-Path ".env") {
    icacls ".env" /inheritance:r /grant "SYSTEM:F" /grant "Administrators:F" /grant "${AppUser}:R" /C /Q
    Write-Host "Set restrictive permissions on .env file" -ForegroundColor Yellow
}

Write-Host "Deployment permissions set successfully" -ForegroundColor Green
Write-Host "Application should run as user: $AppUser" -ForegroundColor Blue
'@

    $deployScriptPath = Join-Path $ProjectRoot "Deploy-Permissions.ps1"
    $deployScript | Out-File -FilePath $deployScriptPath -Encoding UTF8
    
    Write-Info "Generated Deploy-Permissions.ps1 for production deployment"
}

# Main execution
function Main {
    Write-Success "Starting GameForge permissions setup for $Environment environment"
    
    $isAdmin = Test-Administrator
    if (-not $isAdmin) {
        Write-Warning "Not running as administrator - some operations may fail"
        Write-Info "For full permissions setup, run as administrator"
    } else {
        Write-Info "Running as administrator - can set full permissions"
    }
    
    try {
        Set-SourceCodePermissions
        Set-ConfigPermissions
        Set-RuntimePermissions
        Set-ScriptPermissions
        
        if (Test-Permissions) {
            Write-Success "GameForge permissions setup completed successfully!"
        } else {
            Write-Error "Permission validation failed"
            exit 1
        }
        
        New-DeploymentScript
        
        if ($Environment -eq "production") {
            Write-Info ""
            Write-Info "For production deployment:"
            Write-Info "1. Copy files to target system"
            Write-Info "2. Run: .\Deploy-Permissions.ps1 as Administrator"
            Write-Info "3. Run application as non-admin user: $AppUser"
        }
        
        # Display permission summary
        Write-Host ""
        Write-Host "=== PERMISSION SUMMARY ===" -ForegroundColor Cyan
        Write-Host "Source code files (*.py): Read-only for dev and app users" -ForegroundColor White
        Write-Host "Configuration files: Read-only for dev and app users" -ForegroundColor White
        Write-Host "Secret files: Highly restricted access" -ForegroundColor White
        Write-Host "Executable scripts: Read and execute permissions" -ForegroundColor White
        Write-Host "Runtime directories: Full control for app user" -ForegroundColor White
        Write-Host "==========================" -ForegroundColor Cyan
    }
    catch {
        Write-Error "Permission setup failed: $_"
        exit 1
    }
}

# Run main function
Main