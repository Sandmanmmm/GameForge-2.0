# GameForge Phase 4 Production Deployment Script
# This PowerShell script deploys the Phase 4 Model Asset Security system

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("deploy", "start", "stop", "restart", "status", "logs", "cleanup")]
    [string]$Action = "deploy",
    
    [Parameter()]
    [string]$Environment = "production",
    
    [Parameter()]
    [switch]$SkipVaultInit,
    
    [Parameter()]
    [switch]$SkipVolumeSetup,
    
    [Parameter()]
    [switch]$VerboseOutput
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
$Colors = @{
    Red = [System.ConsoleColor]::Red
    Green = [System.ConsoleColor]::Green
    Yellow = [System.ConsoleColor]::Yellow
    Blue = [System.ConsoleColor]::Blue
    Cyan = [System.ConsoleColor]::Cyan
    White = [System.ConsoleColor]::White
}

function Write-ColoredOutput {
    param(
        [string]$Message,
        [System.ConsoleColor]$Color = [System.ConsoleColor]::White
    )
    
    $previousColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Output $Message
    $Host.UI.RawUI.ForegroundColor = $previousColor
}

function Write-Header {
    param([string]$Title)
    
    Write-ColoredOutput "`n$('=' * 70)" -Color $Colors.Blue
    Write-ColoredOutput "🚀 $Title" -Color $Colors.Blue
    Write-ColoredOutput "$('=' * 70)" -Color $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColoredOutput "✅ $Message" -Color $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-ColoredOutput "⚠️  $Message" -Color $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-ColoredOutput "❌ $Message" -Color $Colors.Red
}

function Write-Info {
    param([string]$Message)
    Write-ColoredOutput "ℹ️  $Message" -Color $Colors.Cyan
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Header "Prerequisites Check"
    
    $checks = @()
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker is available: $dockerVersion"
        $checks += $true
    }
    catch {
        Write-Error "Docker is not available or not working"
        $checks += $false
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Success "Docker Compose is available: $composeVersion"
        $checks += $true
    }
    catch {
        Write-Error "Docker Compose is not available"
        $checks += $false
    }
    
    # Check environment file
    if (Test-Path ".env.phase4.production") {
        Write-Success "Environment file found: .env.phase4.production"
        $checks += $true
    }
    else {
        Write-Warning "Environment file not found. Copy .env.phase4.production.template to .env.phase4.production and configure it"
        $checks += $false
    }
    
    # Check required files
    $requiredFiles = @(
        "docker-compose.production-hardened.yml",
        "Dockerfile.production.enhanced",
        "scripts/model-manager.sh",
        "scripts/entrypoint-phase4.sh"
    )
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "Required file exists: $file"
            $checks += $true
        }
        else {
            Write-Error "Missing required file: $file"
            $checks += $false
        }
    }
    
    return ($checks | Where-Object { -not $_ }).Count -eq 0
}

# Function to setup volumes
function Initialize-Volumes {
    Write-Header "Phase 4 Volume Initialization"
    
    if ($SkipVolumeSetup) {
        Write-Info "Skipping volume setup as requested"
        return $true
    }
    
    # Load environment variables
    if (Test-Path ".env.phase4.production") {
        Get-Content ".env.phase4.production" | ForEach-Object {
            if ($_ -match "^([^#][^=]*)=(.*)$") {
                Set-Variable -Name $matches[1] -Value $matches[2]
            }
        }
    }
    
    $basePath = $env:VOLUME_BASE_PATH
    if (-not $basePath) {
        $basePath = "$PWD/volumes"
        Write-Info "Using default volume base path: $basePath"
    }
    
    $volumePaths = @(
        "$basePath/logs",
        "$basePath/cache",
        "$basePath/assets",
        "$basePath/models",
        "$basePath/postgres",
        "$basePath/redis",
        "$basePath/elasticsearch",
        "$basePath/vault/data",
        "$basePath/vault/logs",
        "$basePath/monitoring"
    )
    
    foreach ($path in $volumePaths) {
        try {
            if (-not (Test-Path $path)) {
                New-Item -ItemType Directory -Path $path -Force | Out-Null
                Write-Success "Created volume directory: $path"
            }
            else {
                Write-Info "Volume directory exists: $path"
            }
            
            # Set appropriate permissions (Linux-style, adjust for Windows if needed)
            if ($IsLinux -or $IsMacOS) {
                chmod 755 $path
            }
        }
        catch {
            Write-Error "Failed to create volume directory: $path - $($_.Exception.Message)"
            return $false
        }
    }
    
    Write-Success "Volume initialization completed"
    return $true
}

# Function to initialize Vault
function Initialize-Vault {
    Write-Header "Phase 4 Vault Initialization"
    
    if ($SkipVaultInit) {
        Write-Info "Skipping Vault initialization as requested"
        return $true
    }
    
    Write-Info "Starting Vault service for initialization..."
    
    try {
        # Start only Vault service
        docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production up vault -d
        
        # Wait for Vault to be ready
        Write-Info "Waiting for Vault to be ready..."
        Start-Sleep -Seconds 30
        
        # Check Vault status
        docker exec gameforge-vault-secure vault status 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Vault is initialized and ready"
        }
        else {
            Write-Warning "Vault may need manual initialization"
            Write-Info "Run: docker exec -it gameforge-vault-secure vault operator init"
        }
        
        # Configure Vault secrets engines
        Write-Info "Configuring Vault secrets engines..."
        
        $vaultToken = $env:VAULT_ROOT_TOKEN
        if (-not $vaultToken) {
            Write-Warning "VAULT_ROOT_TOKEN not found in environment"
            return $false
        }
        
        # Enable KV secrets engine
        docker exec -e VAULT_TOKEN=$vaultToken gameforge-vault-secure vault secrets enable -version=2 -path=gameforge kv
        
        # Enable AWS secrets engine
        docker exec -e VAULT_TOKEN=$vaultToken gameforge-vault-secure vault secrets enable aws
        
        Write-Success "Vault initialization completed"
        return $true
    }
    catch {
        Write-Error "Vault initialization failed: $($_.Exception.Message)"
        return $false
    }
}

# Function to deploy Phase 4
function Invoke-Deploy {
    Write-Header "Phase 4 Production Deployment"
    
    try {
        Write-Info "Starting Phase 4 production deployment..."
        
        # Build and start all services
        docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production up -d --build
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Deployment failed"
            return $false
        }
        
        Write-Success "Phase 4 services started successfully"
        
        # Wait for services to be ready
        Write-Info "Waiting for services to initialize..."
        Start-Sleep -Seconds 60
        
        # Check service health
        Write-Info "Checking service health..."
        $services = docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production ps --services
        
        foreach ($service in $services) {
            $health = docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production ps $service --format "{{.Health}}"
            if ($health -eq "healthy" -or $health -eq "running") {
                Write-Success "Service healthy: $service"
            }
            else {
                Write-Warning "Service not healthy: $service ($health)"
            }
        }
        
        Write-Success "Phase 4 deployment completed successfully"
        return $true
    }
    catch {
        Write-Error "Deployment failed: $($_.Exception.Message)"
        return $false
    }
}

# Function to show status
function Show-Status {
    Write-Header "Phase 4 System Status"
    
    Write-Info "Service Status:"
    docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production ps
    
    Write-Info "`nNetwork Status:"
    docker network ls | Where-Object { $_ -match "gameforge" }
    
    Write-Info "`nVolume Status:"
    docker volume ls | Where-Object { $_ -match "gameforge" }
}

# Function to show logs
function Show-Logs {
    param([string]$Service = "")
    
    Write-Header "Phase 4 Service Logs"
    
    if ($Service) {
        docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production logs -f $Service
    }
    else {
        docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production logs -f
    }
}

# Function to stop services
function Stop-Services {
    Write-Header "Stopping Phase 4 Services"
    
    docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production down
    Write-Success "Phase 4 services stopped"
}

# Function to restart services
function Restart-Services {
    Write-Header "Restarting Phase 4 Services"
    
    Stop-Services
    Start-Sleep -Seconds 10
    Invoke-Deploy
}

# Function to cleanup
function Invoke-Cleanup {
    Write-Header "Phase 4 Cleanup"
    
    Write-Warning "This will remove all Phase 4 containers, networks, and volumes"
    $confirm = Read-Host "Are you sure? (y/N)"
    
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        docker-compose -f docker-compose.production-hardened.yml --env-file .env.phase4.production down -v --remove-orphans
        docker system prune -f
        Write-Success "Phase 4 cleanup completed"
    }
    else {
        Write-Info "Cleanup cancelled"
    }
}

# Main execution
function Main {
    Write-ColoredOutput @"
🔐 GameForge Phase 4 - Production Deployment
===========================================
Action: $Action
Environment: $Environment
Skip Vault Init: $SkipVaultInit
Skip Volume Setup: $SkipVolumeSetup
Verbose Output: $VerboseOutput
"@ -Color $Colors.Blue
    
    # Check prerequisites first
    if (-not (Test-Prerequisites)) {
        Write-Error "Prerequisites check failed"
        exit 1
    }
    
    switch ($Action) {
        "deploy" {
            if (-not (Initialize-Volumes)) { exit 1 }
            if (-not (Initialize-Vault)) { exit 1 }
            if (-not (Invoke-Deploy)) { exit 1 }
        }
        "start" {
            Invoke-Deploy
        }
        "stop" {
            Stop-Services
        }
        "restart" {
            Restart-Services
        }
        "status" {
            Show-Status
        }
        "logs" {
            Show-Logs
        }
        "cleanup" {
            Invoke-Cleanup
        }
        default {
            Write-Error "Unknown action: $Action"
            exit 1
        }
    }
    
    Write-Success "Phase 4 operation completed: $Action"
}

# Execute main function
Main
