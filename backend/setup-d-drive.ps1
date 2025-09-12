# GameForge Backend - D: Drive Configuration
# Run this script to configure environment for D: drive usage

Write-Host "🔧 Configuring GameForge Backend for D: drive..." -ForegroundColor Cyan

# Set environment variables for this session
$env:TMPDIR = "D:\tmp"
$env:TEMP = "D:\tmp" 
$env:TMP = "D:\tmp"
$env:npm_config_cache = "D:\npm-cache"
$env:PRISMA_QUERY_ENGINE_BINARY = "D:\prisma-engines"

# Create directories if they don't exist
$directories = @("D:\tmp", "D:\npm-cache", "D:\prisma-engines")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✅ Created directory: $dir" -ForegroundColor Green
    }
}

Write-Host "✅ Environment configured for D: drive usage" -ForegroundColor Green
Write-Host "💡 Run this script before working with npm or Prisma commands" -ForegroundColor Yellow