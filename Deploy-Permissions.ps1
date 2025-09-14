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
