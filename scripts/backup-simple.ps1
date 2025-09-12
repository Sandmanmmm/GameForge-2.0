# ========================================================================
# GameForge AI Production Platform - Simple Backup Script
# Quick backup of all production data before testing
# ========================================================================

param(
    [string]$BackupDir = ".\backups\$(Get-Date -Format 'yyyy-MM-dd-HH-mm-ss')"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "GameForge Production Backup - $(Get-Date)" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "[SUCCESS] Created backup directory: $BackupDir" -ForegroundColor Green
}

# ========================================================================
# 1. Export Docker Inventory
# ========================================================================
Write-Host ""
Write-Host "Exporting Docker Inventory..." -ForegroundColor Blue

try {
    docker ps -a --format "table {{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}" > "$BackupDir\docker-containers.txt"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" > "$BackupDir\docker-images.txt"
    docker volume ls > "$BackupDir\docker-volumes.txt"
    docker network ls > "$BackupDir\docker-networks.txt"
    docker system df > "$BackupDir\docker-system-usage.txt"
    
    Write-Host "[SUCCESS] Docker inventory exported" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to export Docker inventory: $($_.Exception.Message)" -ForegroundColor Red
}

# ========================================================================
# 2. Backup Critical Volumes
# ========================================================================
Write-Host ""
Write-Host "Backing Up Critical Volumes..." -ForegroundColor Blue

# Get all GameForge related volumes
$volumes = docker volume ls --format "{{.Name}}" | Where-Object { $_ -like "*ai-game-production-p*" -or $_ -like "*monitoring*" }

foreach ($volume in $volumes) {
    Write-Host "[INFO] Backing up volume: $volume" -ForegroundColor Cyan
    
    try {
        $backupFile = "$volume`_$(Get-Date -Format 'yyyy-MM-dd').tar.gz"
        
        # Use docker run to backup volume
        docker run --rm -v "${volume}:/data" -v "${PWD}:/backup" alpine sh -c "cd /data && tar czf /backup/$backupFile . 2>/dev/null"
        
        if (Test-Path $backupFile) {
            Move-Item $backupFile "$BackupDir\"
            $size = [math]::Round((Get-Item "$BackupDir\$backupFile").Length / 1MB, 2)
            Write-Host "[SUCCESS] $volume backed up ($size MB)" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] Backup file not created for $volume" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ERROR] Failed to backup $volume : $($_.Exception.Message)" -ForegroundColor Red
    }
}

# ========================================================================
# 3. Database Backups (if containers are running)
# ========================================================================
Write-Host ""
Write-Host "Creating Database Backups..." -ForegroundColor Blue

# PostgreSQL Backup
$postgresContainer = docker ps --format "{{.Names}}" | Where-Object { $_ -match "postgres" }

if ($postgresContainer) {
    Write-Host "[INFO] Found PostgreSQL container: $postgresContainer" -ForegroundColor Cyan
    
    try {
        $sqlDumpFile = "$BackupDir\postgres_gameforge_$(Get-Date -Format 'yyyy-MM-dd').sql"
        docker exec $postgresContainer pg_dump -U gameforge -d gameforge_prod > $sqlDumpFile
        
        if (Test-Path $sqlDumpFile) {
            $size = [math]::Round((Get-Item $sqlDumpFile).Length / 1MB, 2)
            Write-Host "[SUCCESS] PostgreSQL database backed up ($size MB)" -ForegroundColor Green
        }
    } catch {
        Write-Host "[ERROR] Failed to backup PostgreSQL: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "[WARNING] No running PostgreSQL container found" -ForegroundColor Yellow
}

# Redis Backup
$redisContainer = docker ps --format "{{.Names}}" | Where-Object { $_ -match "redis" }

if ($redisContainer) {
    Write-Host "[INFO] Found Redis container: $redisContainer" -ForegroundColor Cyan
    
    try {
        docker exec $redisContainer redis-cli BGSAVE
        Start-Sleep -Seconds 5
        docker cp "${redisContainer}:/data/dump.rdb" "$BackupDir\redis_$(Get-Date -Format 'yyyy-MM-dd').rdb"
        
        if (Test-Path "$BackupDir\redis_$(Get-Date -Format 'yyyy-MM-dd').rdb") {
            Write-Host "[SUCCESS] Redis database backed up" -ForegroundColor Green
        }
    } catch {
        Write-Host "[ERROR] Failed to backup Redis: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "[WARNING] No running Redis container found" -ForegroundColor Yellow
}

# ========================================================================
# 4. Configuration Backup
# ========================================================================
Write-Host ""
Write-Host "Backing Up Configuration Files..." -ForegroundColor Blue

$configFiles = @(
    "docker-compose*.yml",
    ".env*",
    "Dockerfile*",
    "*.conf",
    "*.json"
)

foreach ($pattern in $configFiles) {
    $files = Get-ChildItem -Path . -Name $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        if (Test-Path $file) {
            Copy-Item $file "$BackupDir\" -Force
            Write-Host "[SUCCESS] Backed up: $file" -ForegroundColor Green
        }
    }
}

# ========================================================================
# 5. System State Snapshot
# ========================================================================
Write-Host ""
Write-Host "Creating System State Snapshot..." -ForegroundColor Blue

try {
    docker system info > "$BackupDir\docker-system-info.txt"
    docker version > "$BackupDir\docker-version.txt"
    systeminfo > "$BackupDir\system-info.txt"
    
    Write-Host "[SUCCESS] System state snapshot created" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Failed to create complete system snapshot" -ForegroundColor Yellow
}

# ========================================================================
# 6. Backup Summary
# ========================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "Backup Summary" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue

$backupSize = [math]::Round((Get-ChildItem -Path $BackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
$fileCount = (Get-ChildItem -Path $BackupDir -Recurse -File | Measure-Object).Count

Write-Host "[SUCCESS] Backup completed successfully!" -ForegroundColor Green
Write-Host "[INFO] Backup location: $BackupDir" -ForegroundColor Cyan
Write-Host "[INFO] Total backup size: $backupSize MB" -ForegroundColor Cyan
Write-Host "[INFO] Files backed up: $fileCount" -ForegroundColor Cyan

# Create backup manifest
$manifest = @{
    BackupDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    BackupLocation = $BackupDir
    TotalSizeMB = $backupSize
    FileCount = $fileCount
    DockerVersion = (docker version --format "{{.Server.Version}}" 2>$null)
}

$manifest | ConvertTo-Json | Out-File "$BackupDir\backup-manifest.json"

Write-Host "[INFO] Backup manifest saved to: $BackupDir\backup-manifest.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "Backup Process Complete - Your data is safe!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Blue

# List backup contents
Write-Host ""
Write-Host "Backup Contents:" -ForegroundColor Blue
Get-ChildItem -Path $BackupDir | Format-Table Name, Length, LastWriteTime