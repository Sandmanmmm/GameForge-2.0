# GameForge Cosign Key Generation Script - Fixed Version
# ====================================================

Write-Host "GameForge Cosign Key Generation" -ForegroundColor Green
Write-Host "===============================" -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Error "❌ Docker is not running. Please start Docker first."
    exit 1
}

# Create keys directory
$keysDir = "volumes/security/cosign-keys"
if (-not (Test-Path $keysDir)) {
    New-Item -ItemType Directory -Path $keysDir -Force | Out-Null
    Write-Host "📁 Created keys directory: $keysDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔐 Generating Cosign key pair for image signing..." -ForegroundColor Yellow
Write-Host ""

# Generate secure random password for key
$cosignPassword = -join ((33..126) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# Define key paths
$privateKey = Join-Path $keysDir "cosign.key"
$publicKey = Join-Path $keysDir "cosign.pub"

# Create temporary directory for key generation
$tempDir = "temp-cosign-keys"
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host "🔧 Running Cosign key generation container..." -ForegroundColor Yellow
    
    # Generate keys using Cosign Docker container
    $dockerArgs = @(
        "run", "--rm",
        "-v", "${PWD}/${tempDir}:/keys",
        "-e", "COSIGN_PASSWORD=$cosignPassword",
        "gcr.io/projectsigstore/cosign:latest",
        "generate-key-pair", "/keys/cosign"
    )
    
    $result = docker @dockerArgs 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Cosign key generation failed: $result"
        exit 1
    }
    
    Write-Host "✅ Cosign keys generated successfully" -ForegroundColor Green
    
    # Move keys to permanent location
    Move-Item -Path (Join-Path $tempDir "cosign.key") -Destination $privateKey -Force
    Move-Item -Path (Join-Path $tempDir "cosign.pub") -Destination $publicKey -Force
    
    Write-Host "📁 Keys moved to: $keysDir" -ForegroundColor Green
    
    # Verify key files exist
    if ((Test-Path $privateKey) -and (Test-Path $publicKey)) {
        Write-Host "✅ Key files created:" -ForegroundColor Green
        Write-Host "  * Private key: $privateKey" -ForegroundColor White
        Write-Host "  * Public key: $publicKey" -ForegroundColor White
    } else {
        Write-Host "❌ Key files not found after generation" -ForegroundColor Red
        exit 1
    }
    
    # Set secure permissions on private key (Windows)
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Write-Host "🔒 Setting secure permissions on private key..." -ForegroundColor Yellow
        try {
            # Remove inheritance and set owner-only permissions
            icacls $privateKey /inheritance:r /grant:r "${env:USERNAME}:F" | Out-Null
            Write-Host "✅ Secure permissions set on private key" -ForegroundColor Green
        } catch {
            Write-Warning "⚠️ Could not set secure permissions: $_"
        }
    }
    
} catch {
    Write-Error "❌ Key generation failed: $_"
    exit 1
} finally {
    # Clean up temporary directory
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force
    }
}

# Create environment scripts for using the keys
Write-Host ""
Write-Host "📝 Creating environment scripts..." -ForegroundColor Yellow

# Create Bash environment script
$bashScript = @"
#!/bin/bash
# Cosign Environment Variables for GameForge
export COSIGN_PRIVATE_KEY_PATH="`$(pwd)/$($keysDir.Replace('\', '/'))/cosign.key"
export COSIGN_PUBLIC_KEY_PATH="`$(pwd)/$($keysDir.Replace('\', '/'))/cosign.pub"
export COSIGN_PASSWORD="$cosignPassword"

echo "🔐 Cosign environment loaded"
echo "Private Key: `$COSIGN_PRIVATE_KEY_PATH"
echo "Public Key: `$COSIGN_PUBLIC_KEY_PATH"
"@

$bashScript | Out-File -FilePath (Join-Path $keysDir "cosign-env.sh") -Encoding UTF8

# Create PowerShell environment script
$psScript = @"
# Cosign Environment Variables for GameForge
`$env:COSIGN_PRIVATE_KEY_PATH = "`$(Get-Location)/$($keysDir.Replace('\', '/'))/cosign.key"
`$env:COSIGN_PUBLIC_KEY_PATH = "`$(Get-Location)/$($keysDir.Replace('\', '/'))/cosign.pub"
`$env:COSIGN_PASSWORD = "$cosignPassword"

Write-Host "🔐 Cosign environment loaded" -ForegroundColor Green
Write-Host "Private Key: `$env:COSIGN_PRIVATE_KEY_PATH" -ForegroundColor White
Write-Host "Public Key: `$env:COSIGN_PUBLIC_KEY_PATH" -ForegroundColor White
"@

$psScript | Out-File -FilePath (Join-Path $keysDir "cosign-env.ps1") -Encoding UTF8

# Create a test script for image signing
$testContent = @"
# GameForge Image Signing Test Script
# ==================================

Write-Host "GameForge Image Signing Test" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green

# Load Cosign environment
. ./volumes/security/cosign-keys/cosign-env.ps1

Write-Host ""
Write-Host "🧪 Testing image signing with Cosign..." -ForegroundColor Yellow

try {
    # Pull a test image
    Write-Host "📥 Pulling test image (hello-world)..." -ForegroundColor Yellow
    docker pull hello-world:latest
    
    # Sign the image
    Write-Host "✍️ Signing image..." -ForegroundColor Yellow
    `$signArgs = @(
        "run", "--rm", 
        "-v", "`$(`$env:COSIGN_PRIVATE_KEY_PATH):/cosign.key",
        "-v", "`$(`$env:COSIGN_PUBLIC_KEY_PATH):/cosign.pub",
        "-e", "COSIGN_PASSWORD=`$env:COSIGN_PASSWORD",
        "gcr.io/projectsigstore/cosign:latest",
        "sign", "--key", "/cosign.key", "hello-world:latest"
    )
    
    docker @signArgs
    
    if (`$LASTEXITCODE -eq 0) {
        Write-Host "✅ Image signing successful!" -ForegroundColor Green
        
        # Verify the signature
        Write-Host "🔍 Verifying signature..." -ForegroundColor Yellow
        `$verifyArgs = @(
            "run", "--rm",
            "-v", "`$(`$env:COSIGN_PUBLIC_KEY_PATH):/cosign.pub", 
            "gcr.io/projectsigstore/cosign:latest",
            "verify", "--key", "/cosign.pub", "hello-world:latest"
        )
        
        docker @verifyArgs
        
        if (`$LASTEXITCODE -eq 0) {
            Write-Host "✅ Signature verification successful!" -ForegroundColor Green
        } else {
            Write-Host "❌ Signature verification failed" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ Image signing failed" -ForegroundColor Red
    }
    
} catch {
    Write-Error "❌ Image signing test failed: `$_"
}

Write-Host ""
Write-Host "🔐 Image signing test completed" -ForegroundColor Green
"@

$testContent | Out-File -FilePath "test-image-signing.ps1" -Encoding UTF8

# Create README for the keys
$readmeText = @"
# GameForge Cosign Keys

This directory contains the Cosign key pair for signing GameForge container images.

## Files

- cosign.key - Private key for signing (keep secure!)
- cosign.pub - Public key for verification
- cosign-env.sh - Bash environment setup script
- cosign-env.ps1 - PowerShell environment setup script

## Usage

### PowerShell
```powershell
# Load environment
. ./cosign-env.ps1

# Sign an image  
docker run --rm -v `$env:COSIGN_PRIVATE_KEY_PATH:/cosign.key -e COSIGN_PASSWORD=`$env:COSIGN_PASSWORD gcr.io/projectsigstore/cosign:latest sign --key /cosign.key IMAGE_NAME
```

### Bash
```bash
# Load environment
source ./cosign-env.sh

# Sign an image
docker run --rm -v `$COSIGN_PRIVATE_KEY_PATH:/cosign.key -e COSIGN_PASSWORD=`$COSIGN_PASSWORD gcr.io/projectsigstore/cosign:latest sign --key /cosign.key IMAGE_NAME
```

## Security Notes

- The private key is password protected
- Keep the private key secure and never commit to version control
- The password is stored in the environment scripts - protect these files
- Use hardware security modules (HSM) for production deployments

## Generated

- Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- Password Length: 32 characters
- Key Type: ECDSA P-256
"@

$readmeText | Out-File -FilePath (Join-Path $keysDir "README.md") -Encoding UTF8

Write-Host "✅ Environment scripts created" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 Cosign Key Generation Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Generated Files:" -ForegroundColor Cyan
Write-Host "* cosign.key (private key)" -ForegroundColor White
Write-Host "* cosign.pub (public key)" -ForegroundColor White  
Write-Host "* README.md" -ForegroundColor White
Write-Host "* cosign-env.sh" -ForegroundColor White
Write-Host "* cosign-env.ps1" -ForegroundColor White
Write-Host "* test-image-signing.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Key Information:" -ForegroundColor Yellow
Write-Host "* Password: $cosignPassword" -ForegroundColor White
Write-Host "* Location: $keysDir" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test signing: .\test-image-signing.ps1" -ForegroundColor White
Write-Host "2. Load environment: . .\volumes\security\cosign-keys\cosign-env.ps1" -ForegroundColor White
Write-Host "3. Sign GameForge images before deployment" -ForegroundColor White
Write-Host ""
Write-Host "🔒 Security Reminder:" -ForegroundColor Red
Write-Host "* Keep the private key and password secure" -ForegroundColor White
Write-Host "* Never commit keys to version control" -ForegroundColor White
Write-Host "* Consider using HSM for production" -ForegroundColor White
