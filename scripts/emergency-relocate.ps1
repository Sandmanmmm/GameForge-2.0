# Emergency GameForge Relocation Script - C: to D: Drive
# Moves Docker data and project to D: drive due to full C: drive

param(
    [Parameter(Mandatory=$false)]
    [string]$TargetPath = "D:\GameForge"
)

Write-Host "=== EMERGENCY RELOCATION: C: TO D: DRIVE ===" -ForegroundColor Red
Write-Host ""

# Step 1: Stop Docker build if running
Write-Host "1. Stopping any running Docker builds..." -ForegroundColor Yellow
try {
    docker system prune -f --filter "until=1h" 2>$null
    Write-Host "   ✅ Docker build processes stopped" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Docker may still be running" -ForegroundColor Yellow
}

# Step 2: Check disk space
Write-Host "`n2. Checking disk space..." -ForegroundColor Yellow
$drives = Get-PSDrive -Name C,D | Select-Object Name, @{Name="Free(GB)";Expression={[math]::Round($_.Free/1GB,2)}}
$drives | ForEach-Object { 
    $color = if($_.Name -eq "C" -and $_."Free(GB)" -lt 1) {"Red"} else {"Green"}
    Write-Host "   $($_.Name): Free: $($_."Free(GB)")GB" -ForegroundColor $color
}

# Step 3: Create target directory
Write-Host "`n3. Creating target directory on D:..." -ForegroundColor Yellow
if (!(Test-Path $TargetPath)) {
    New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
    Write-Host "   ✅ Created: $TargetPath" -ForegroundColor Green
} else {
    Write-Host "   ✅ Directory exists: $TargetPath" -ForegroundColor Green
}

# Step 4: Copy critical files first (small size)
Write-Host "`n4. Copying critical configuration files..." -ForegroundColor Yellow
$criticalFiles = @(
    "docker-compose.production-hardened.yml",
    "Dockerfile.production",
    "Dockerfile.production.enhanced",
    "k8s\",
    "*.ps1",
    "*.md",
    "*.yaml",
    "*.yml"
)

foreach ($pattern in $criticalFiles) {
    try {
        if ($pattern.EndsWith("\")) {
            # Directory
            $source = $pattern
            if (Test-Path $source) {
                robocopy $source "$TargetPath\$source" /E /MT:4 /NJH /NJS | Out-Null
                Write-Host "   ✅ Copied directory: $source" -ForegroundColor Green
            }
        } else {
            # Files with pattern
            $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                Copy-Item $file.FullName "$TargetPath\$($file.Name)" -Force
            }
            if ($files.Count -gt 0) {
                Write-Host "   ✅ Copied $($files.Count) files matching: $pattern" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "   ⚠️  Could not copy: $pattern" -ForegroundColor Yellow
    }
}

# Step 5: Move Docker data directory
Write-Host "`n5. Relocating Docker data..." -ForegroundColor Yellow
$dockerDataPath = "$env:USERPROFILE\.docker"
$newDockerPath = "D:\Docker"

if (Test-Path $dockerDataPath) {
    Write-Host "   Moving Docker data from C: to D:..." -ForegroundColor Cyan
    
    # Stop Docker Desktop
    Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
    Start-Sleep 5
    
    # Move data
    if (!(Test-Path $newDockerPath)) {
        robocopy $dockerDataPath $newDockerPath /E /MOVE /MT:4
        Write-Host "   ✅ Docker data moved to D:\Docker" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠️  Docker data directory not found at expected location" -ForegroundColor Yellow
}

# Step 6: Update Docker Desktop settings
Write-Host "`n6. Creating Docker configuration update..." -ForegroundColor Yellow
$dockerConfig = @"
{
  "data-root": "D:\\Docker\\data",
  "storage-driver": "windowsfilter"
}
"@

$configPath = "$newDockerPath\daemon.json"
Set-Content -Path $configPath -Value $dockerConfig
Write-Host "   ✅ Docker daemon.json created" -ForegroundColor Green

# Step 7: Create startup script for new location
Write-Host "`n7. Creating startup script for D: drive..." -ForegroundColor Yellow
$startupScript = @"
# GameForge Startup Script - D: Drive Location
Set-Location "$TargetPath"
Write-Host "=== GameForge Relocated to D: Drive ===" -ForegroundColor Green
Write-Host "Location: $TargetPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart Docker Desktop" -ForegroundColor White
Write-Host "2. Run: docker system prune -a (cleanup C: drive)" -ForegroundColor White
Write-Host "3. Run: .\validate-migration.ps1" -ForegroundColor White
Write-Host "4. Resume build: docker-compose -f docker-compose.production-hardened.yml build gameforge-app" -ForegroundColor White
"@

Set-Content -Path "$TargetPath\start-gameforge.ps1" -Value $startupScript
Write-Host "   ✅ Startup script created: $TargetPath\start-gameforge.ps1" -ForegroundColor Green

# Step 8: Instructions
Write-Host "`n=== RELOCATION COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "IMMEDIATE ACTIONS REQUIRED:" -ForegroundColor Red
Write-Host "1. Close Docker Desktop completely" -ForegroundColor White
Write-Host "2. Go to Docker Desktop Settings > Resources > Advanced" -ForegroundColor White
Write-Host "3. Change 'Disk image location' to: D:\Docker" -ForegroundColor White
Write-Host "4. Restart Docker Desktop" -ForegroundColor White
Write-Host "5. Navigate to: $TargetPath" -ForegroundColor White
Write-Host "6. Run: .\start-gameforge.ps1" -ForegroundColor White
Write-Host ""
Write-Host "C: DRIVE CLEANUP:" -ForegroundColor Yellow
Write-Host "After Docker restart, run: docker system prune -a --volumes" -ForegroundColor White
Write-Host ""
Write-Host "NEW WORKING DIRECTORY: $TargetPath" -ForegroundColor Cyan
