# GameForge Windows Permission Management Script
# Optimized for Windows development environments
# Author: GameForge Security Team
# Date: 2025-01-13

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "production")]
    [string]$Environment = "development",
    
    [Parameter(Mandatory=$false)]
    [string]$Owner = $env:USERNAME,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose = $false
)

# Logging functions
function Write-Log {
    param($Message, $Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = @{
        "INFO" = "White"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR" = "Red"
    }[$Level]
    
    Write-Host "[$timestamp] $Level`: $Message" -ForegroundColor $color
}

function Write-Success { param($Message) Write-Log $Message "SUCCESS" }
function Write-Warning { param($Message) Write-Log $Message "WARNING" }
function Write-Error { param($Message) Write-Log $Message "ERROR" }

# Main execution
Write-Log "Starting GameForge Windows Permission Setup"
Write-Log "Environment: $Environment"
Write-Log "Owner: $Owner"
Write-Log "Dry Run: $DryRun"

# Get current directory
$GameForgeRoot = Get-Location
Write-Log "GameForge Root: $GameForgeRoot"

# Define file patterns and permissions
$FilePermissions = @{
    "SourceFiles" = @{
        "Pattern" = "*.py"
        "Description" = "Python source files"
        "Permission" = "Read,Execute"
    }
    "ConfigFiles" = @{
        "Pattern" = @("*.yml", "*.yaml", "*.json", "*.toml", "*.ini", "*.env*")
        "Description" = "Configuration files"
        "Permission" = "Read"
    }
    "Scripts" = @{
        "Pattern" = @("*.sh", "*.ps1", "*.bat")
        "Description" = "Executable scripts"
        "Permission" = "Read,Execute"
    }
    "Documentation" = @{
        "Pattern" = @("*.md", "*.txt", "*.rst")
        "Description" = "Documentation files"
        "Permission" = "Read"
    }
}

# Directory permissions
$DirectoryPermissions = @{
    "src" = "Read,Execute"
    "backend" = "Read,Execute"
    "scripts" = "Read,Execute"
    "config" = "Read"
    "logs" = "FullControl"
    "data" = "FullControl"
    "temp" = "FullControl"
}

function Set-WindowsFilePermissions {
    param(
        [string]$Path,
        [string]$Permission,
        [string]$Description,
        [bool]$IsDirectory = $false
    )
    
    if (-not (Test-Path $Path)) {
        Write-Warning "Path not found: $Path"
        return $false
    }
    
    try {
        if ($DryRun) {
            Write-Log "DRY RUN: Would set $Permission on $Description`: $Path"
            return $true
        }
        
        # Use Windows ACL approach for better compatibility
        $Acl = Get-Acl $Path
        $AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $Owner,
            $Permission,
            $(if ($IsDirectory) { "ContainerInherit,ObjectInherit" } else { "None" }),
            "None",
            "Allow"
        )
        
        # Remove existing permissions for the user first
        $Acl.SetAccessRuleProtection($false, $true)
        $Acl.SetAccessRule($AccessRule)
        Set-Acl -Path $Path -AclObject $Acl
        
        if ($Verbose) {
            Write-Log "Set $Permission on $Description`: $Path"
        }
        return $true
    }
    catch {
        Write-Error "Failed to set permissions on $Path`: $($_.Exception.Message)"
        return $false
    }
}

# Set permissions on core application files
Write-Log "Setting permissions on core application files..."

# Main application entry point
$MainPy = Join-Path $GameForgeRoot "main.py"
if (Test-Path $MainPy) {
    Set-WindowsFilePermissions -Path $MainPy -Permission "Read,Execute" -Description "Main application"
    Write-Success "main.py permissions set ✓"
} else {
    Write-Warning "main.py not found"
}

# Backend/API router files
$BackendPath = Join-Path $GameForgeRoot "backend"
if (Test-Path $BackendPath) {
    $RouterFiles = Get-ChildItem -Path $BackendPath -Filter "*.py" -Recurse | Where-Object { $_.Name -like "*router*" -or $_.Directory.Name -eq "routers" }
    foreach ($file in $RouterFiles) {
        Set-WindowsFilePermissions -Path $file.FullName -Permission "Read,Execute" -Description "API router"
    }
    Write-Success "API router files: $($RouterFiles.Count) files ✓"
} else {
    Write-Warning "Backend directory not found"
}

# Source code files
$SrcPath = Join-Path $GameForgeRoot "src"
if (Test-Path $SrcPath) {
    $PyFiles = Get-ChildItem -Path $SrcPath -Filter "*.py" -Recurse
    foreach ($file in $PyFiles) {
        Set-WindowsFilePermissions -Path $file.FullName -Permission "Read,Execute" -Description "Source file"
    }
    Write-Success "Source files: $($PyFiles.Count) files ✓"
} else {
    Write-Warning "src directory not found"
}

# Configuration files
Write-Log "Setting permissions on configuration files..."
$ConfigPatterns = @("*.yml", "*.yaml", "*.json", "*.toml", "*.ini")
foreach ($pattern in $ConfigPatterns) {
    $ConfigFiles = Get-ChildItem -Path $GameForgeRoot -Filter $pattern -Recurse | Where-Object { $_.Name -notlike ".*" }
    foreach ($file in $ConfigFiles) {
        Set-WindowsFilePermissions -Path $file.FullName -Permission "Read" -Description "Configuration file"
    }
}
Write-Success "Configuration files processed ✓"

# Script files
Write-Log "Setting permissions on executable scripts..."
$ScriptPatterns = @("*.sh", "*.ps1", "*.bat")
foreach ($pattern in $ScriptPatterns) {
    $ScriptFiles = Get-ChildItem -Path $GameForgeRoot -Filter $pattern -Recurse
    foreach ($file in $ScriptFiles) {
        Set-WindowsFilePermissions -Path $file.FullName -Permission "Read,Execute" -Description "Script file"
    }
}
Write-Success "Script files processed ✓"

# Directory permissions
Write-Log "Setting directory permissions..."
foreach ($dirName in $DirectoryPermissions.Keys) {
    $dirPath = Join-Path $GameForgeRoot $dirName
    if (Test-Path $dirPath) {
        $permission = $DirectoryPermissions[$dirName]
        Set-WindowsFilePermissions -Path $dirPath -Permission $permission -Description "Directory ($dirName)" -IsDirectory $true
    }
}
Write-Success "Directory permissions set ✓"

# Special handling for sensitive files
Write-Log "Securing sensitive files..."
$SensitivePatterns = @("*.env", "*.key", "*.pem", "*.p12", "*secret*", "*password*")
foreach ($pattern in $SensitivePatterns) {
    $SensitiveFiles = Get-ChildItem -Path $GameForgeRoot -Filter $pattern -Recurse -Force
    foreach ($file in $SensitiveFiles) {
        # Only owner can read sensitive files
        Set-WindowsFilePermissions -Path $file.FullName -Permission "Read" -Description "Sensitive file"
        
        # Additional security: hide file and set as system file
        if (-not $DryRun) {
            $file.Attributes = $file.Attributes -bor [System.IO.FileAttributes]::Hidden
        }
    }
}
Write-Success "Sensitive files secured ✓"

# Generate runtime permission summary
Write-Log "Generating permission summary..."

# Create deployment script
$DeployScript = @"
# GameForge Windows Deployment Permissions
# Generated: $(Get-Date)
# Environment: $Environment
# Owner: $Owner

# Core application files
Write-Host "Setting GameForge deployment permissions..." -ForegroundColor Green

# Main application
if (Test-Path "main.py") {
    icacls "main.py" /grant "${Owner}:(R,X)" /inheritance:r
    Write-Host "✓ main.py permissions set" -ForegroundColor Green
}

# Backend files
if (Test-Path "backend") {
    Get-ChildItem -Path "backend" -Filter "*.py" -Recurse | ForEach-Object {
        icacls $_.FullName /grant "${Owner}:(R,X)" /inheritance:r
    }
    Write-Host "✓ Backend files permissions set" -ForegroundColor Green
}

# Configuration files (read-only)
@("*.yml", "*.yaml", "*.json") | ForEach-Object {
    Get-ChildItem -Filter $_ -Recurse | ForEach-Object {
        icacls $_.FullName /grant "${Owner}:(R)" /inheritance:r
    }
}
Write-Host "✓ Configuration files secured" -ForegroundColor Green

Write-Host "GameForge deployment permissions completed!" -ForegroundColor Green
"@

$DeployScriptPath = Join-Path $GameForgeRoot "Deploy-Permissions-Windows.ps1"
if (-not $DryRun) {
    $DeployScript | Out-File -FilePath $DeployScriptPath -Encoding UTF8
    Write-Success "Generated Deploy-Permissions-Windows.ps1 for production deployment"
}

# Final validation
Write-Log "Validating file permissions..."

# Check main.py
if (Test-Path $MainPy) {
    Write-Log "main.py found and accessible ✓"
} else {
    Write-Warning "main.py validation failed"
}

# Check backend files
$BackendCount = 0
if (Test-Path $BackendPath) {
    $BackendCount = (Get-ChildItem -Path $BackendPath -Filter "*.py" -Recurse).Count
}
Write-Log "Backend Python files: $BackendCount files ✓"

Write-Success "GameForge Windows permissions setup completed successfully!"

# Summary report
Write-Host "`n=== WINDOWS PERMISSION SUMMARY ===" -ForegroundColor Cyan
Write-Host "Owner: $Owner" -ForegroundColor White
Write-Host "Environment: $Environment" -ForegroundColor White
Write-Host "Python files: Read and Execute permissions" -ForegroundColor White
Write-Host "Configuration files: Read-only permissions" -ForegroundColor White
Write-Host "Scripts: Read and Execute permissions" -ForegroundColor White
Write-Host "Sensitive files: Hidden and restricted access" -ForegroundColor White
Write-Host "===============================" -ForegroundColor Cyan

if (-not $DryRun) {
    Write-Log "Deployment script created: Deploy-Permissions-Windows.ps1"
    Write-Log "Run this script in production environment for consistent permissions"
}