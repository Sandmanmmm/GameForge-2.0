# GameForge Cosign Key Generation Script
Write-Host "GameForge Cosign Key Generation" -ForegroundColor Green
Write-Host "===============================" -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Error "Docker is not running. Please start Docker first."
    exit 1
}

# Create keys directory
$keysDir = "volumes/security/cosign-keys"
if (-not (Test-Path $keysDir)) {
    New-Item -ItemType Directory -Path $keysDir -Force | Out-Null
    Write-Host "Created keys directory: $keysDir" -ForegroundColor Green
}

# Generate secure random password
$cosignPassword = -join ((33..126) | Get-Random -Count 32 | ForEach-Object {[char]$_})

Write-Host "Generating Cosign key pair..." -ForegroundColor Yellow

# Define key paths
$privateKey = Join-Path $keysDir "cosign.key"
$publicKey = Join-Path $keysDir "cosign.pub"

# Create temp directory
$tempDir = "temp-cosign-keys"
if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force }
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    # Generate keys using Docker with simpler approach
    $currentPath = (Get-Location).Path
    $tempPath = Join-Path $currentPath $tempDir
    
    # Convert Windows path to Docker Desktop format
    $dockerPath = $tempPath -replace '^([A-Z]):', '/$1' -replace '\\', '/' | ForEach-Object { $_.ToLower() }
    
    Write-Host "Temp path: $tempPath" -ForegroundColor Gray
    Write-Host "Docker path: $dockerPath" -ForegroundColor Gray
    
    # Set environment variable and generate keys
    $env:COSIGN_PASSWORD = $cosignPassword
    & docker run --rm -v "${dockerPath}:/keys" -e "COSIGN_PASSWORD=$cosignPassword" -w /keys gcr.io/projectsigstore/cosign:latest generate-key-pair
    
    if ($LASTEXITCODE -eq 0) {
        # Move keys to permanent location
        Move-Item -Path (Join-Path $tempDir "cosign.key") -Destination $privateKey -Force
        Move-Item -Path (Join-Path $tempDir "cosign.pub") -Destination $publicKey -Force
        Write-Host "Keys generated successfully" -ForegroundColor Green
        Write-Host "Password: $cosignPassword" -ForegroundColor Yellow
    } else {
        Write-Error "Key generation failed"
        exit 1
    }
} finally {
    if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force }
}

Write-Host "Cosign key generation complete!" -ForegroundColor Green
