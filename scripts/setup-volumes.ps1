# GameForge Production Volume Setup Script
# ========================================
# Creates all required volume directories for production deployment

Write-Host "GameForge Production Volume Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

$baseDir = "volumes"
$volumeDirs = @(
    "postgres",
    "postgres-logs", 
    "redis",
    "vault/data",
    "vault/logs",
    "elasticsearch",
    "elasticsearch-logs",
    "grafana",
    "monitoring",
    "logs",
    "cache",
    "assets",
    "models",
    "nginx-logs",
    "static",
    "backups",
    "logstash",
    "prometheus"
)

Write-Host "Creating volume directories..." -ForegroundColor Yellow

foreach ($dir in $volumeDirs) {
    $fullPath = Join-Path $baseDir $dir
    
    if (-not (Test-Path $fullPath)) {
        try {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
            Write-Host "✅ Created: $fullPath" -ForegroundColor Green
        } catch {
            Write-Host "❌ Failed to create: $fullPath - $_" -ForegroundColor Red
        }
    } else {
        Write-Host "✅ Exists: $fullPath" -ForegroundColor Green
    }
}

# Set appropriate permissions (Windows)
Write-Host "`nSetting directory permissions..." -ForegroundColor Yellow

try {
    # Give full control to current user for all volume directories
    $acl = Get-Acl $baseDir
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
        "FullControl",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl.SetAccessRule($accessRule)
    Set-Acl -Path $baseDir -AclObject $acl -ErrorAction SilentlyContinue
    Write-Host "✅ Permissions set for volume directories" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not set permissions: $_" -ForegroundColor Yellow
}

Write-Host "`nVolume setup complete!" -ForegroundColor Green
Write-Host "Total directories created/verified: $($volumeDirs.Count)" -ForegroundColor Cyan
