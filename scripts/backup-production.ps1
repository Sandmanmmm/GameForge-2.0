# ========================================================================
# GameForge AI Production Platform - Backup Script
# Comprehensive backup of all production data before testing
# ========================================================================

param(
    [string]$BackupDir = ".\backups\$(Get-Date -Format 'yyyy-MM-dd-HH-mm-ss')",
    [switch]$SkipVolumeBackup = $false,
    [switch]$SkipDatabaseBackup = $false
)

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Blue"

function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $BLUE
}

function Write-LogSuccess {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $GREEN
}

function Write-LogWarning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $YELLOW
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $RED
}

function Write-LogSection {
    param([string]$Message)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $BLUE
    Write-Host $Message -ForegroundColor $BLUE
    Write-Host "========================================" -ForegroundColor $BLUE
    Write-Host ""
}

Write-LogSection "GameForge Production Backup - $(Get-Date)"

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-LogSuccess "Created backup directory: $BackupDir"
}

# ========================================================================
# 1. Export Docker Inventory
# ========================================================================
Write-LogSection "Exporting Docker Inventory"

try {
    docker ps -a --format "{{.ID}} {{.Image}} {{.Names}}" > "$BackupDir\docker-containers.txt"
    docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" > "$BackupDir\docker-images.txt"
    docker volume ls > "$BackupDir\docker-volumes.txt"
    docker network ls > "$BackupDir\docker-networks.txt"
    docker system df > "$BackupDir\docker-system-usage.txt"
    
    Write-LogSuccess "Docker inventory exported to $BackupDir"
} catch {
    Write-LogError "Failed to export Docker inventory: $($_.Exception.Message)"
}

# ========================================================================
# 2. Backup Critical Volumes
# ========================================================================
if (-not $SkipVolumeBackup) {
    Write-LogSection "Backing Up Critical Volumes"
    
    # Define critical volumes to backup
    $criticalVolumes = @(
        "ai-game-production-p_postgres-data",
        "ai-game-production-p_postgres-logs", 
        "ai-game-production-p_redis-data",
        "ai-game-production-p_vault-data",
        "ai-game-production-p_vault-logs",
        "ai-game-production-p_security-shared",
        "ai-game-production-p_vastai-postgres-data",
        "ai-game-production-p_vastai-postgres-logs",
        "ai-game-production-p_vastai-redis-data",
        "monitoring_grafana_data",
        "monitoring_prometheus_data"
    )
    
    foreach ($volume in $criticalVolumes) {
        Write-LogInfo "Backing up volume: $volume"
        
        try {
            # Check if volume exists
            $volumeExists = docker volume ls --format "{{.Name}}" | Where-Object { $_ -eq $volume }
            
            if ($volumeExists) {
                # Create backup using Alpine container
                $backupFile = "$BackupDir\$volume`_$(Get-Date -Format 'yyyy-MM-dd').tar.gz"
                
                docker run --rm -v "${volume}:/data" -v "${PWD}:/backup" alpine sh -c "cd /data && tar czf /backup/$($volume)_$(Get-Date -Format 'yyyy-MM-dd').tar.gz . 2>/dev/null || echo 'Backup completed with warnings'"
                
                if (Test-Path $backupFile) {
                    $size = (Get-Item $backupFile).Length / 1MB
                    Write-LogSuccess "✓ $volume backed up ($([math]::Round($size, 2)) MB)"
                } else {
                    Write-LogWarning "⚠ Backup file not found for $volume"
                }
            } else {
                Write-LogWarning "⚠ Volume $volume does not exist - skipping"
            }
        } catch {
            Write-LogError "✗ Failed to backup $volume : $($_.Exception.Message)"
        }
    }
}

# ========================================================================
# 3. Database Backups (if containers are running)
# ========================================================================
if (-not $SkipDatabaseBackup) {
    Write-LogSection "Creating Database Backups"
    
    # PostgreSQL Backup
    try {
        $postgresContainer = docker ps --format "{{.Names}}" | Where-Object { $_ -match "postgres" }
        
        if ($postgresContainer) {
            Write-LogInfo "Found PostgreSQL container: $postgresContainer"
            
            # Create SQL dump
            $sqlDumpFile = "$BackupDir\postgres_gameforge_$(Get-Date -Format 'yyyy-MM-dd').sql"
            docker exec $postgresContainer pg_dump -U gameforge -d gameforge_prod > $sqlDumpFile
            
            if (Test-Path $sqlDumpFile) {
                $size = (Get-Item $sqlDumpFile).Length / 1MB
                Write-LogSuccess "✓ PostgreSQL database backed up ($([math]::Round($size, 2)) MB)"
            }
        } else {
            Write-LogWarning "⚠ No running PostgreSQL container found"
        }
    } catch {
        Write-LogError "✗ Failed to backup PostgreSQL: $($_.Exception.Message)"
    }
    
    # Redis Backup
    try {
        $redisContainer = docker ps --format "{{.Names}}" | Where-Object { $_ -match "redis" }
        
        if ($redisContainer) {
            Write-LogInfo "Found Redis container: $redisContainer"
            
            # Create Redis dump
            docker exec $redisContainer redis-cli --rdb /tmp/dump.rdb
            docker cp "${redisContainer}:/tmp/dump.rdb" "$BackupDir\redis_$(Get-Date -Format 'yyyy-MM-dd').rdb"
            
            if (Test-Path "$BackupDir\redis_$(Get-Date -Format 'yyyy-MM-dd').rdb") {
                Write-LogSuccess "✓ Redis database backed up"
            }
        } else {
            Write-LogWarning "⚠ No running Redis container found"
        }
    } catch {
        Write-LogError "✗ Failed to backup Redis: $($_.Exception.Message)"
    }
}

# ========================================================================
# 4. Configuration Backup
# ========================================================================
Write-LogSection "Backing Up Configuration Files"

$configFiles = @(
    "docker-compose.yml",
    "docker-compose.production.yml", 
    "docker-compose.production-hardened.yml",
    "docker-compose.vastai-production.yml",
    ".env*",
    "Dockerfile*",
    "nginx.conf",
    "prometheus.yml"
)

foreach ($pattern in $configFiles) {
    $files = Get-ChildItem -Path . -Name $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        if (Test-Path $file) {
            Copy-Item $file "$BackupDir\" -Force
            Write-LogSuccess "✓ Backed up: $file"
        }
    }
}

# ========================================================================
# 5. Model and Asset Inventory
# ========================================================================
Write-LogSection "Creating Model and Asset Inventory"

try {
    # Look for model directories
    $modelDirs = @("models", "models_cache", "stable-diffusion", "checkpoints", "weights")
    
    foreach ($dir in $modelDirs) {
        if (Test-Path $dir) {
            $inventory = Get-ChildItem -Path $dir -Recurse -File | ForEach-Object {
                [PSCustomObject]@{
                    Path = $_.FullName
                    Size = $_.Length
                    LastModified = $_.LastWriteTime
                    Hash = (Get-FileHash $_.FullName -Algorithm MD5).Hash
                }
            }
            
            $inventory | Export-Csv -Path "$BackupDir\model_inventory_$dir.csv" -NoTypeInformation
            Write-LogSuccess "✓ Model inventory created for: $dir"
        }
    }
} catch {
    Write-LogWarning "⚠ Failed to create model inventory: $($_.Exception.Message)"
}

# ========================================================================
# 6. System State Snapshot
# ========================================================================
Write-LogSection "Creating System State Snapshot"

try {
    # Docker system info
    docker system info > "$BackupDir\docker-system-info.txt"
    docker version > "$BackupDir\docker-version.txt"
    
    # System resources
    Get-ComputerInfo | Out-File "$BackupDir\system-info.txt"
    Get-Process | Where-Object { $_.ProcessName -match "docker" } | Out-File "$BackupDir\docker-processes.txt"
    
    # Disk usage
    Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace | Out-File "$BackupDir\disk-usage.txt"
    
    Write-LogSuccess "✓ System state snapshot created"
} catch {
    Write-LogWarning "⚠ Failed to create complete system snapshot: $($_.Exception.Message)"
}

# ========================================================================
# 7. Backup Summary
# ========================================================================
Write-LogSection "Backup Summary"

$backupSize = (Get-ChildItem -Path $BackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
$fileCount = (Get-ChildItem -Path $BackupDir -Recurse -File | Measure-Object).Count

Write-LogSuccess "Backup completed successfully!"
Write-LogInfo "Backup location: $BackupDir"
Write-LogInfo "Total backup size: $([math]::Round($backupSize, 2)) MB"
Write-LogInfo "Files backed up: $fileCount"

# Create backup manifest
$manifest = @{
    BackupDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    BackupLocation = $BackupDir
    TotalSizeMB = [math]::Round($backupSize, 2)
    FileCount = $fileCount
    DockerVersion = (docker version --format "{{.Server.Version}}" 2>$null)
    SystemInfo = @{
        OS = (Get-CimInstance Win32_OperatingSystem).Caption
        Hostname = $env:COMPUTERNAME
        User = $env:USERNAME
    }
}

$manifest | ConvertTo-Json -Depth 3 | Out-File "$BackupDir\backup-manifest.json"

Write-LogInfo "Backup manifest saved to: $BackupDir\backup-manifest.json"
Write-LogSection "Backup Process Complete"

# Return backup directory for further use
return $BackupDir