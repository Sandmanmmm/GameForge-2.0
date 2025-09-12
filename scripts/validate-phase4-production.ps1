# GameForge Phase 4 - Production Validation Script
# Validates that Phase 4 Model Asset Security is properly integrated into production docker-compose

[CmdletBinding()]
param(
    [Parameter()]
    [switch]$VerboseOutput,
    
    [Parameter()]
    [switch]$QuickValidation
)

$ErrorActionPreference = "Stop"

# Colors
$Colors = @{
    Red = [System.ConsoleColor]::Red
    Green = [System.ConsoleColor]::Green
    Yellow = [System.ConsoleColor]::Yellow
    Blue = [System.ConsoleColor]::Blue
    Cyan = [System.ConsoleColor]::Cyan
    White = [System.ConsoleColor]::White
}

function Write-ColoredOutput {
    param([string]$Message, [System.ConsoleColor]$Color = [System.ConsoleColor]::White)
    $previousColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Output $Message
    $Host.UI.RawUI.ForegroundColor = $previousColor
}

function Write-Header { 
    param([string]$Title)
    Write-ColoredOutput "`n$('=' * 70)" -Color $Colors.Blue
    Write-ColoredOutput "🔍 $Title" -Color $Colors.Blue
    Write-ColoredOutput "$('=' * 70)" -Color $Colors.Blue
}

function Write-ValidationSuccess { 
    param([string]$Message) 
    Write-ColoredOutput "✅ $Message" -Color $Colors.Green 
}

function Write-ValidationWarning { 
    param([string]$Message) 
    Write-ColoredOutput "⚠️  $Message" -Color $Colors.Yellow 
}

function Write-ValidationError { 
    param([string]$Message) 
    Write-ColoredOutput "❌ $Message" -Color $Colors.Red 
}

function Write-ValidationInfo { 
    param([string]$Message) 
    Write-ColoredOutput "ℹ️  $Message" -Color $Colors.Cyan 
}

# Validation Functions
function Test-DockerComposeStructure {
    Write-Header "Docker Compose Structure Validation"
    
    $composeFile = "docker-compose.production-hardened.yml"
    $validations = @()
    
    if (-not (Test-Path $composeFile)) {
        Write-ValidationError "Production docker-compose file not found: $composeFile"
        return $false
    }
    
    $content = Get-Content $composeFile -Raw
    
    # Check Phase 4 Security Templates
    if ($content -match 'x-vault-security:.*&vault-security') {
        Write-ValidationSuccess "Vault security template found"
        $validations += $true
    } else {
        Write-ValidationError "Vault security template missing"
        $validations += $false
    }
    
    # Check Phase 4 comments and labels
    $phase4Features = @(
        'Phase 4:.*Model Asset Security',
        'Phase 4:.*Vault Integration',
        'Phase 4:.*Model Storage Configuration',
        'Phase 4:.*Enhanced entrypoint',
        'Phase 4:.*Model Cache Volume',
        'Phase 4:.*Vault Network'
    )
    
    foreach ($feature in $phase4Features) {
        if ($content -match $feature) {
            Write-Success "Found: $($feature -replace 'Phase 4:', '')"
            $validations += $true
        } else {
            Write-Warning "Missing: $($feature -replace 'Phase 4:', '')"
            $validations += $false
        }
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Test-GameForgeAppConfiguration {
    Write-Header "GameForge App Phase 4 Configuration"
    
    $composeFile = "docker-compose.production-hardened.yml"
    $content = Get-Content $composeFile -Raw
    $validations = @()
    
    # Check build configuration
    if ($content -match 'BUILD_ENV:.*phase4-production') {
        Write-Success "Build environment set to phase4-production"
        $validations += $true
    } else {
        Write-Error "Build environment not set to phase4-production"
        $validations += $false
    }
    
    # Check Phase 4 environment variables
    $requiredEnvVars = @(
        'MODEL_SECURITY_ENABLED.*true',
        'SECURITY_SCAN_ENABLED.*true',
        'STRICT_MODEL_SECURITY.*true',
        'VAULT_HEALTH_CHECK_ENABLED.*true',
        'PERFORMANCE_MONITORING_ENABLED.*true',
        'VAULT_ADDR.*vault:8200',
        'MODEL_STORAGE_BACKEND.*s3',
        'MODEL_CACHE_DIR.*/tmp/models'
    )
    
    foreach ($envVar in $requiredEnvVars) {
        if ($content -match $envVar) {
            $varName = ($envVar -split '.*')[0] -replace '\.\*', ''
            Write-Success "Environment variable configured: $varName"
            $validations += $true
        } else {
            Write-Error "Missing environment variable: $envVar"
            $validations += $false
        }
    }
    
    # Check entrypoint
    if ($content -match 'entrypoint:.*entrypoint-phase4\.sh') {
        Write-Success "Phase 4 enhanced entrypoint configured"
        $validations += $true
    } else {
        Write-Error "Phase 4 entrypoint not configured"
        $validations += $false
    }
    
    # Check volumes
    $requiredVolumes = @(
        '\./scripts:/app/scripts:ro',
        'model-cache:/tmp/models:rw',
        'monitoring-data:/tmp/monitoring:rw'
    )
    
    foreach ($volume in $requiredVolumes) {
        if ($content -match $volume) {
            Write-Success "Volume configured: $volume"
            $validations += $true
        } else {
            Write-Error "Missing volume: $volume"
            $validations += $false
        }
    }
    
    # Check networks
    if ($content -match 'vault-network.*Phase 4') {
        Write-Success "Vault network access configured"
        $validations += $true
    } else {
        Write-Error "Vault network access not configured"
        $validations += $false
    }
    
    # Check dependencies
    if ($content -match 'vault:.*condition: service_healthy') {
        Write-Success "Vault dependency configured"
        $validations += $true
    } else {
        Write-Error "Vault dependency not configured"
        $validations += $false
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Test-VaultService {
    Write-Header "Vault Service Configuration"
    
    $composeFile = "docker-compose.production-hardened.yml"
    $content = Get-Content $composeFile -Raw
    $validations = @()
    
    # Check Vault service exists
    if ($content -match 'vault:.*image:.*hashicorp/vault') {
        Write-Success "Vault service configured with HashiCorp image"
        $validations += $true
    } else {
        Write-Error "Vault service not configured properly"
        $validations += $false
    }
    
    # Check Vault security
    if ($content -match '<<:.*\*vault-security') {
        Write-Success "Vault security template applied"
        $validations += $true
    } else {
        Write-Error "Vault security template not applied"
        $validations += $false
    }
    
    # Check Vault configuration
    $vaultConfig = @(
        'VAULT_ADDR.*0\.0\.0\.0:8200',
        'VAULT_API_ADDR.*vault:8200',
        'VAULT_DEV_ROOT_TOKEN_ID'
    )
    
    foreach ($config in $vaultConfig) {
        if ($content -match $config) {
            Write-Success "Vault config found: $config"
            $validations += $true
        } else {
            Write-Warning "Vault config may be missing: $config"
            $validations += $false
        }
    }
    
    # Check Vault volumes
    $vaultVolumes = @(
        'vault-data:/vault/data',
        'vault-logs:/vault/logs'
    )
    
    foreach ($volume in $vaultVolumes) {
        if ($content -match $volume) {
            Write-Success "Vault volume configured: $volume"
            $validations += $true
        } else {
            Write-Error "Missing vault volume: $volume"
            $validations += $false
        }
    }
    
    # Check Vault networks
    if ($content -match 'vault-network') {
        Write-Success "Vault network configured"
        $validations += $true
    } else {
        Write-Error "Vault network not configured"
        $validations += $false
    }
    
    # Check health check
    if ($content -match 'vault.*status') {
        Write-Success "Vault health check configured"
        $validations += $true
    } else {
        Write-Error "Vault health check not configured"
        $validations += $false
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Test-Phase4Scripts {
    Write-Header "Phase 4 Scripts Validation"
    
    $validations = @()
    
    # Check required scripts exist
    $requiredScripts = @(
        "scripts/model-manager.sh",
        "scripts/entrypoint-phase4.sh"
    )
    
    foreach ($script in $requiredScripts) {
        if (Test-Path $script) {
            Write-Success "Script exists: $script"
            $validations += $true
            
            # Check script permissions (if on Unix-like system)
            $content = Get-Content $script -Raw
            if ($content -match '#!/bin/bash') {
                Write-Success "Script has proper shebang: $script"
                $validations += $true
            } else {
                Write-Warning "Script may not have proper shebang: $script"
                $validations += $false
            }
        } else {
            Write-Error "Missing script: $script"
            $validations += $false
        }
    }
    
    # Check model-manager.sh functions
    if (Test-Path "scripts/model-manager.sh") {
        $modelManagerContent = Get-Content "scripts/model-manager.sh" -Raw
        $requiredFunctions = @(
            'authenticate_vault\(\)',
            'get_model_credentials\(\)',
            'download_model\(\)',
            'cleanup_old_sessions\(\)'
        )
        
        foreach ($func in $requiredFunctions) {
            if ($modelManagerContent -match $func) {
                Write-Success "Model manager function: $($func -replace '\(\)', '')"
                $validations += $true
            } else {
                Write-Error "Missing model manager function: $($func -replace '\(\)', '')"
                $validations += $false
            }
        }
    }
    
    # Check entrypoint-phase4.sh functions
    if (Test-Path "scripts/entrypoint-phase4.sh") {
        $entrypointContent = Get-Content "scripts/entrypoint-phase4.sh" -Raw
        $requiredFunctions = @(
            'check_system_health\(\)',
            'check_vault_health\(\)',
            'validate_model_security\(\)',
            'perform_security_scan\(\)'
        )
        
        foreach ($func in $requiredFunctions) {
            if ($entrypointContent -match $func) {
                Write-Success "Entrypoint function: $($func -replace '\(\)', '')"
                $validations += $true
            } else {
                Write-Error "Missing entrypoint function: $($func -replace '\(\)', '')"
                $validations += $false
            }
        }
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Test-NetworksAndVolumes {
    Write-Header "Networks and Volumes Validation"
    
    $composeFile = "docker-compose.production-hardened.yml"
    $content = Get-Content $composeFile -Raw
    $validations = @()
    
    # Check Phase 4 volumes
    $phase4Volumes = @(
        'model-cache:.*tmpfs.*size=4G',
        'monitoring-data:.*monitoring',
        'vault-data:.*vault/data',
        'vault-logs:.*vault/logs'
    )
    
    foreach ($volume in $phase4Volumes) {
        if ($content -match $volume) {
            Write-Success "Phase 4 volume: $($volume -split ':')[0]"
            $validations += $true
        } else {
            Write-Error "Missing Phase 4 volume: $($volume -split ':')[0]"
            $validations += $false
        }
    }
    
    # Check vault-network
    if ($content -match 'vault-network:.*driver:.*bridge.*internal:.*true') {
        Write-Success "Vault network properly configured as internal"
        $validations += $true
    } else {
        Write-Error "Vault network not properly configured"
        $validations += $false
    }
    
    # Check network subnet
    if ($content -match '172\.23\.0\.0/24') {
        Write-Success "Vault network subnet configured"
        $validations += $true
    } else {
        Write-Warning "Vault network subnet may not be configured"
        $validations += $false
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Test-SecurityCompliance {
    Write-Header "Phase 4 Security Compliance"
    
    $composeFile = "docker-compose.production-hardened.yml"
    $content = Get-Content $composeFile -Raw
    $validations = @()
    
    # Check security labels
    $securityLabels = @(
        'phase4\.model-security=enabled',
        'phase4\.vault-integration=enabled',
        'security\.scan=enabled',
        'security\.profile=phase4-production'
    )
    
    foreach ($label in $securityLabels) {
        if ($content -match $label) {
            Write-Success "Security label: $($label -replace '\\', '')"
            $validations += $true
        } else {
            Write-Error "Missing security label: $($label -replace '\\', '')"
            $validations += $false
        }
    }
    
    # Check tmpfs configuration for security
    if ($content -match '/tmp:size=2G,mode=1777.*Phase 4.*Increased for model storage') {
        Write-Success "Secure tmpfs configured for model storage"
        $validations += $true
    } else {
        Write-Warning "Tmpfs may not be properly configured for Phase 4"
        $validations += $false
    }
    
    # Check read_only is properly set
    if ($content -match 'read_only:.*false.*Phase 4.*Allow model cache') {
        Write-Success "Read-only filesystem properly adjusted for Phase 4"
        $validations += $true
    } else {
        Write-Warning "Read-only filesystem configuration may need review"
        $validations += $false
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Test-DockerfileIntegration {
    Write-Header "Dockerfile Integration Check"
    
    $validations = @()
    
    # Check if Dockerfile.production.enhanced exists
    if (Test-Path "Dockerfile.production.enhanced") {
        Write-Success "Enhanced production Dockerfile exists"
        $validations += $true
        
        $dockerfileContent = Get-Content "Dockerfile.production.enhanced" -Raw
        
        # Check for multi-stage build
        $stages = [regex]::Matches($dockerfileContent, 'FROM .+ AS .+')
        if ($stages.Count -ge 5) {
            Write-Success "Multi-stage build with $($stages.Count) stages"
            $validations += $true
        } else {
            Write-Warning "May need more build stages for security"
            $validations += $false
        }
        
        # Check that no models are copied
        $modelExtensions = @('*.safetensors', '*.bin', '*.pt', '*.pth', '*.ckpt')
        $modelsFound = $false
        
        foreach ($ext in $modelExtensions) {
            if ($dockerfileContent -match "COPY.*$ext") {
                Write-Error "Model files being copied: $ext"
                $modelsFound = $true
            }
        }
        
        if (-not $modelsFound) {
            Write-Success "No model files copied into image - Phase 4 compliant"
            $validations += $true
        } else {
            $validations += $false
        }
    } else {
        Write-Error "Dockerfile.production.enhanced not found"
        $validations += $false
    }
    
    return ($validations | Where-Object { -not $_ }).Count -eq 0
}

function Show-ValidationSummary {
    param([hashtable]$Results)
    
    Write-Header "Phase 4 Production Validation Summary"
    
    $totalTests = $Results.Count
    $passedTests = ($Results.Values | Where-Object { $_ -eq $true }).Count
    $successRate = [math]::Round(($passedTests / $totalTests) * 100, 1)
    
    Write-Info "Total validation categories: $totalTests"
    Write-Info "Passed categories: $passedTests"
    Write-Info "Success rate: $successRate%"
    
    Write-Output "`nValidation Results:"
    foreach ($test in $Results.GetEnumerator()) {
        $status = if ($test.Value) { "✅ PASS" } else { "❌ FAIL" }
        $color = if ($test.Value) { $Colors.Green } else { $Colors.Red }
        Write-ColoredOutput "  $status - $($test.Key)" -Color $color
    }
    
    if ($successRate -ge 90) {
        Write-Success "`n🎉 Phase 4 is properly integrated and ready for production!"
    } elseif ($successRate -ge 75) {
        Write-Warning "`n⚠️  Phase 4 integration mostly complete with minor issues"
    } else {
        Write-Error "`n❌ Phase 4 integration needs significant improvements"
    }
    
    return $successRate -ge 75
}

# Main execution
function Main {
    Write-ColoredOutput @"
🔐 GameForge Phase 4 Production Integration Validation
======================================================
Validating Phase 4 Model Asset Security integration in:
docker-compose.production-hardened.yml

Verbose Output: $VerboseOutput
Quick Validation: $QuickValidation
"@ -Color $Colors.Blue
    
    $results = @{}
    
    # Run all validations
    $results["Docker Compose Structure"] = Test-DockerComposeStructure
    $results["GameForge App Configuration"] = Test-GameForgeAppConfiguration
    $results["Vault Service"] = Test-VaultService
    $results["Phase 4 Scripts"] = Test-Phase4Scripts
    $results["Networks and Volumes"] = Test-NetworksAndVolumes
    $results["Security Compliance"] = Test-SecurityCompliance
    
    if (-not $QuickValidation) {
        $results["Dockerfile Integration"] = Test-DockerfileIntegration
    }
    
    # Show summary
    $validationPassed = Show-ValidationSummary -Results $results
    
    if ($validationPassed) {
        Write-Success "`n🚀 Phase 4 production integration validation SUCCESSFUL!"
        exit 0
    } else {
        Write-Error "`n❌ Phase 4 production integration validation FAILED"
        exit 1
    }
}

# Execute
Main
