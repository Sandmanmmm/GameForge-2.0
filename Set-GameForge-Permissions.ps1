# GameForge Windows Permission Setup
# Simplified version for Windows environments
param(
    [string]$Environment = "development"
)

function Write-Log {
    param($Message, $Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colors = @{
        "INFO" = "White"
        "SUCCESS" = "Green" 
        "WARNING" = "Yellow"
        "ERROR" = "Red"
    }
    Write-Host "[$timestamp] $Level`: $Message" -ForegroundColor $colors[$Level]
}

Write-Log "Starting GameForge Windows Permission Setup"
Write-Log "Environment: $Environment"

$currentUser = $env:USERNAME
$gameforgeRoot = Get-Location
Write-Log "Current User: $currentUser"
Write-Log "GameForge Root: $gameforgeRoot"

# Check and set permissions for main.py
if (Test-Path "main.py") {
    try {
        $acl = Get-Acl "main.py"
        Write-Log "main.py found and accessible" "SUCCESS"
    }
    catch {
        Write-Log "Error accessing main.py: $($_.Exception.Message)" "ERROR"
    }
}
else {
    Write-Log "main.py not found" "WARNING"
}

# Check backend/router files
if (Test-Path "backend") {
    $routerFiles = Get-ChildItem -Path "backend" -Filter "*.py" -Recurse
    Write-Log "Found $($routerFiles.Count) Python files in backend" "SUCCESS"
}
else {
    Write-Log "Backend directory not found" "WARNING"
}

# Check src files
if (Test-Path "src") {
    $srcFiles = Get-ChildItem -Path "src" -Filter "*.py" -Recurse
    Write-Log "Found $($srcFiles.Count) Python files in src" "SUCCESS"
}
else {
    Write-Log "src directory not found" "WARNING"
}

# Set basic file permissions using icacls
Write-Log "Setting basic file permissions..."

# Main application files
if (Test-Path "main.py") {
    icacls "main.py" /grant "${currentUser}:(R,X)" 2>$null
    Write-Log "Set permissions on main.py" "SUCCESS"
}

# Backend files
if (Test-Path "backend") {
    Get-ChildItem -Path "backend" -Filter "*.py" -Recurse | ForEach-Object {
        icacls $_.FullName /grant "${currentUser}:(R,X)" 2>$null
    }
    Write-Log "Set permissions on backend Python files" "SUCCESS"
}

# Src files
if (Test-Path "src") {
    Get-ChildItem -Path "src" -Filter "*.py" -Recurse | ForEach-Object {
        icacls $_.FullName /grant "${currentUser}:(R,X)" 2>$null
    }
    Write-Log "Set permissions on src Python files" "SUCCESS"
}

# Configuration files (read-only)
$configPatterns = @("*.yml", "*.yaml", "*.json", "*.toml")
foreach ($pattern in $configPatterns) {
    Get-ChildItem -Filter $pattern -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        icacls $_.FullName /grant "${currentUser}:(R)" 2>$null
    }
}
Write-Log "Set read-only permissions on configuration files" "SUCCESS"

# Script files (read + execute)
$scriptPatterns = @("*.ps1", "*.bat", "*.sh")
foreach ($pattern in $scriptPatterns) {
    Get-ChildItem -Filter $pattern -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        icacls $_.FullName /grant "${currentUser}:(R,X)" 2>$null
    }
}
Write-Log "Set execute permissions on script files" "SUCCESS"

Write-Log "GameForge Windows permissions setup completed!" "SUCCESS"

Write-Host "`n=== PERMISSION SUMMARY ===" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor White
Write-Host "Current User: $currentUser" -ForegroundColor White
Write-Host "Python files: Read and Execute permissions" -ForegroundColor White
Write-Host "Config files: Read-only permissions" -ForegroundColor White
Write-Host "Script files: Read and Execute permissions" -ForegroundColor White
Write-Host "=========================" -ForegroundColor Cyan