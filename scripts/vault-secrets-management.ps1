#!/usr/bin/env powershell
# ========================================================================
# GameForge AI Docker Secrets Management with Vault Integration
# Creates Docker secrets and integrates with Vault for production security
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Remove = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Validate = $false
)

$ErrorActionPreference = "Stop"

# ========================================================================
# Configuration
# ========================================================================

$SecretPrefix = "gameforge"
$VaultAddr = "http://localhost:8200"

$SecretsConfig = @{
    "postgres_password" = @{
        "length" = 32
        "type" = "alphanumeric"
        "description" = "PostgreSQL database password"
    }
    "redis_password" = @{
        "length" = 32  
        "type" = "alphanumeric"
        "description" = "Redis cache password"
    }
    "minio_access_key" = @{
        "length" = 20
        "type" = "alphanumeric" 
        "description" = "MinIO access key"
    }
    "minio_secret_key" = @{
        "length" = 40
        "type" = "base64"
        "description" = "MinIO secret key"
    }
    "elastic_password" = @{
        "length" = 32
        "type" = "alphanumeric"
        "description" = "Elasticsearch password"
    }
    "grafana_password" = @{
        "length" = 24
        "type" = "alphanumeric"
        "description" = "Grafana admin password"
    }
    "app_secret_key" = @{
        "length" = 64
        "type" = "base64"
        "description" = "Application secret key"
    }
    "jwt_secret" = @{
        "length" = 64
        "type" = "base64"
        "description" = "JWT signing secret"
    }
    "vault_root_token" = @{
        "length" = 32
        "type" = "uuid"
        "description" = "Vault root token"
    }
    "vault_app_token" = @{
        "length" = 32
        "type" = "uuid" 
        "description" = "Vault application token"
    }
}

# ========================================================================
# Utility Functions
# ========================================================================

function Write-LogMessage {
    param(
        [string]$Message,
        [string]$Level = "Info"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colors = @{
        "Info" = "Green"
        "Warning" = "Yellow"  
        "Error" = "Red"
        "Success" = "Cyan"
    }
    
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $colors[$Level]
}

function Generate-SecureSecret {
    param(
        [int]$Length,
        [string]$Type
    )
    
    switch ($Type) {
        "alphanumeric" {
            $chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            $secret = -join ((1..$Length) | ForEach { $chars[(Get-Random -Maximum $chars.Length)] })
            return $secret
        }
        "base64" {
            $bytes = New-Object byte[] $Length
            [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
            return [Convert]::ToBase64String($bytes)
        }
        "uuid" {
            return [System.Guid]::NewGuid().ToString()
        }
        default {
            throw "Unknown secret type: $Type"
        }
    }
}

function Test-DockerSwarmMode {
    try {
        $swarmInfo = docker info --format "{{.Swarm.LocalNodeState}}" 2>$null
        return $swarmInfo -eq "active"
    }
    catch {
        return $false
    }
}

function Initialize-DockerSwarm {
    Write-LogMessage "Initializing Docker Swarm mode for secrets support..."
    
    try {
        docker swarm init 2>$null | Out-Null
        Write-LogMessage "Docker Swarm initialized successfully" -Level "Success"
    }
    catch {
        Write-LogMessage "Failed to initialize Docker Swarm: $($_.Exception.Message)" -Level "Error"
        throw
    }
}

# ========================================================================
# Secret Management Functions
# ========================================================================

function Test-DockerSecret {
    param([string]$SecretName)
    
    try {
        docker secret inspect $SecretName 2>$null | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function New-DockerSecret {
    param(
        [string]$SecretName,
        [string]$SecretValue,
        [string]$Description
    )
    
    try {
        $tempFile = [System.IO.Path]::GetTempFileName()
        $SecretValue | Out-File -FilePath $tempFile -Encoding UTF8 -NoNewline
        
        docker secret create $SecretName $tempFile --label "description=$Description" | Out-Null
        Remove-Item $tempFile
        
        Write-LogMessage "Created Docker secret: $SecretName" -Level "Success"
        return $true
    }
    catch {
        Write-LogMessage "Failed to create Docker secret ${SecretName}: $($_.Exception.Message)" -Level "Error"
        if (Test-Path $tempFile) { Remove-Item $tempFile }
        return $false
    }
}

function Remove-DockerSecret {
    param([string]$SecretName)
    
    try {
        docker secret rm $SecretName | Out-Null
        Write-LogMessage "Removed Docker secret: $SecretName" -Level "Success"
        return $true
    }
    catch {
        Write-LogMessage "Failed to remove Docker secret ${SecretName}: $($_.Exception.Message)" -Level "Warning"
        return $false
    }
}

# ========================================================================
# Composite Secret Generation
# ========================================================================

function New-CompositeSecrets {
    Write-LogMessage "Generating composite connection strings..."
    
    # Get individual secrets for composition
    $postgresPassword = docker secret inspect "${SecretPrefix}_postgres_password" --format "{{.CreatedAt}}" 2>$null
    $redisPassword = docker secret inspect "${SecretPrefix}_redis_password" --format "{{.CreatedAt}}" 2>$null
    $minioAccessKey = docker secret inspect "${SecretPrefix}_minio_access_key" --format "{{.CreatedAt}}" 2>$null
    $minioSecretKey = docker secret inspect "${SecretPrefix}_minio_secret_key" --format "{{.CreatedAt}}" 2>$null
    
    if ($postgresPassword -and $redisPassword -and $minioAccessKey -and $minioSecretKey) {
        # Create composite secrets (connection strings)
        $databaseUrl = "postgresql://gameforge:POSTGRES_PASSWORD_PLACEHOLDER@postgres:5432/gameforge_prod"
        $redisUrl = "redis://:REDIS_PASSWORD_PLACEHOLDER@redis:6379/0"
        
        # These will be resolved at runtime by the application
        if (-not (Test-DockerSecret "${SecretPrefix}_database_url")) {
            New-DockerSecret "${SecretPrefix}_database_url" $databaseUrl "PostgreSQL connection URL template"
        }
        
        if (-not (Test-DockerSecret "${SecretPrefix}_redis_url")) {
            New-DockerSecret "${SecretPrefix}_redis_url" $redisUrl "Redis connection URL template"
        }
    }
}

# ========================================================================
# Main Functions
# ========================================================================

function Initialize-Secrets {
    Write-LogMessage "Initializing GameForge production secrets..."
    
    # Check Docker Swarm mode
    if (-not (Test-DockerSwarmMode)) {
        Initialize-DockerSwarm
    }
    
    $createdSecrets = @()
    $skippedSecrets = @()
    
    foreach ($secretKey in $SecretsConfig.Keys) {
        $config = $SecretsConfig[$secretKey]
        $secretName = "${SecretPrefix}_$secretKey"
        
        if ((Test-DockerSecret $secretName) -and -not $Force) {
            Write-LogMessage "Secret already exists: $secretName" -Level "Warning"
            $skippedSecrets += $secretName
            continue
        }
        
        if ($Force -and (Test-DockerSecret $secretName)) {
            Write-LogMessage "Removing existing secret: $secretName"
            Remove-DockerSecret $secretName
        }
        
        # Generate secret value
        $secretValue = Generate-SecureSecret -Length $config.length -Type $config.type
        
        # Create Docker secret
        if (New-DockerSecret $secretName $secretValue $config.description) {
            $createdSecrets += $secretName
        }
    }
    
    # Create composite secrets
    New-CompositeSecrets
    
    Write-LogMessage "Secret initialization complete!" -Level "Success"
    Write-LogMessage "Created secrets: $($createdSecrets.Count)" -Level "Info"
    Write-LogMessage "Skipped secrets: $($skippedSecrets.Count)" -Level "Info"
    
    if ($createdSecrets.Count -gt 0) {
        Write-LogMessage "New secrets created:" -Level "Info"
        $createdSecrets | ForEach-Object { Write-LogMessage "  - $_" -Level "Info" }
    }
}

function Remove-AllSecrets {
    Write-LogMessage "Removing all GameForge secrets..." -Level "Warning"
    
    $removedSecrets = @()
    
    foreach ($secretKey in $SecretsConfig.Keys) {
        $secretName = "${SecretPrefix}_$secretKey"
        
        if (Test-DockerSecret $secretName) {
            if (Remove-DockerSecret $secretName) {
                $removedSecrets += $secretName
            }
        }
    }
    
    # Remove composite secrets
    $compositeSecrets = @("${SecretPrefix}_database_url", "${SecretPrefix}_redis_url")
    foreach ($secretName in $compositeSecrets) {
        if (Test-DockerSecret $secretName) {
            if (Remove-DockerSecret $secretName) {
                $removedSecrets += $secretName
            }
        }
    }
    
    Write-LogMessage "Removed $($removedSecrets.Count) secrets" -Level "Success"
}

function Test-SecretsValidation {
    Write-LogMessage "Validating GameForge secrets..."
    
    $validSecrets = @()
    $invalidSecrets = @()
    
    foreach ($secretKey in $SecretsConfig.Keys) {
        $secretName = "${SecretPrefix}_$secretKey"
        
        if (Test-DockerSecret $secretName) {
            $validSecrets += $secretName
            Write-LogMessage "✓ Secret exists: $secretName" -Level "Success"
        } else {
            $invalidSecrets += $secretName
            Write-LogMessage "✗ Secret missing: $secretName" -Level "Error"
        }
    }
    
    # Check composite secrets
    $compositeSecrets = @("${SecretPrefix}_database_url", "${SecretPrefix}_redis_url")
    foreach ($secretName in $compositeSecrets) {
        if (Test-DockerSecret $secretName) {
            $validSecrets += $secretName
            Write-LogMessage "✓ Composite secret exists: $secretName" -Level "Success"
        } else {
            $invalidSecrets += $secretName
            Write-LogMessage "✗ Composite secret missing: $secretName" -Level "Error"
        }
    }
    
    Write-LogMessage "Validation complete: $($validSecrets.Count) valid, $($invalidSecrets.Count) invalid" -Level "Info"
    
    if ($invalidSecrets.Count -gt 0) {
        Write-LogMessage "Run with -Force to recreate missing secrets" -Level "Warning"
        return $false
    }
    
    return $true
}

function Show-SecretsStatus {
    Write-LogMessage "GameForge Docker Secrets Status:"
    Write-Host ""
    
    Write-Host "Docker Swarm Status: " -NoNewline
    if (Test-DockerSwarmMode) {
        Write-Host "Active" -ForegroundColor Green
    } else {
        Write-Host "Inactive" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Secrets Status:" -ForegroundColor Cyan
    
    $totalSecrets = $SecretsConfig.Keys.Count + 2  # +2 for composite secrets
    $existingSecrets = 0
    
    foreach ($secretKey in $SecretsConfig.Keys) {
        $secretName = "${SecretPrefix}_$secretKey"
        $config = $SecretsConfig[$secretKey]
        
        if (Test-DockerSecret $secretName) {
            Write-Host "  ✓ $secretName" -ForegroundColor Green -NoNewline
            Write-Host " - $($config.description)" -ForegroundColor Gray
            $existingSecrets++
        } else {
            Write-Host "  ✗ $secretName" -ForegroundColor Red -NoNewline  
            Write-Host " - $($config.description)" -ForegroundColor Gray
        }
    }
    
    # Check composite secrets
    $compositeSecrets = @(
        @{ name = "${SecretPrefix}_database_url"; desc = "PostgreSQL connection URL" },
        @{ name = "${SecretPrefix}_redis_url"; desc = "Redis connection URL" }
    )
    
    foreach ($secret in $compositeSecrets) {
        if (Test-DockerSecret $secret.name) {
            Write-Host "  ✓ $($secret.name)" -ForegroundColor Green -NoNewline
            Write-Host " - $($secret.desc)" -ForegroundColor Gray
            $existingSecrets++
        } else {
            Write-Host "  ✗ $($secret.name)" -ForegroundColor Red -NoNewline
            Write-Host " - $($secret.desc)" -ForegroundColor Gray  
        }
    }
    
    Write-Host ""
    Write-Host "Summary: $existingSecrets/$totalSecrets secrets configured" -ForegroundColor Cyan
    
    if ($existingSecrets -eq $totalSecrets) {
        Write-Host "✅ All secrets ready for production deployment!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Missing secrets - run Initialize-Secrets to create them" -ForegroundColor Yellow
    }
}

# ========================================================================
# Main Execution
# ========================================================================

function Main {
    Write-Host "GameForge AI Docker Secrets Management" -ForegroundColor Magenta
    Write-Host "=====================================" -ForegroundColor Magenta
    
    try {
        if ($Remove) {
            Remove-AllSecrets
        }
        elseif ($Validate) {
            $isValid = Test-SecretsValidation
            if (-not $isValid) {
                exit 1
            }
        }
        else {
            Initialize-Secrets
        }
        
        Write-Host ""
        Show-SecretsStatus
        
        if (-not $Remove) {
            Write-Host ""
            Write-Host "Next Steps:" -ForegroundColor Cyan
            Write-Host "1. Deploy with vault secrets: docker-compose -f docker-compose.vastai-production.yml -f docker-compose.vault-secrets.yml up -d"
            Write-Host "2. Validate deployment: .\vault-secrets-management.ps1 -Validate"
            Write-Host "3. Check container logs: docker-compose logs -f"
        }
        
    }
    catch {
        Write-LogMessage "Script execution failed: $($_.Exception.Message)" -Level "Error"
        exit 1
    }
}

# Execute main function
Main