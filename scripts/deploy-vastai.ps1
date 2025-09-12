# GameForge Vast.ai Deployment Script
# ========================================================================
# Deploy GameForge GPU workloads to Vast.ai cloud GPU instances
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("deploy", "start", "stop", "restart", "status", "logs", "clean", "connect")]
    [string]$Action = "deploy",
    
    [Parameter(Mandatory=$false)]
    [string]$VastaiInstanceId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VastaiInstanceType = "rtx4090",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxPrice = 50,  # cents per hour
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# Script configuration
$ErrorActionPreference = "Stop"
$VerbosePreference = if ($Verbose) { "Continue" } else { "SilentlyContinue" }

# Color output functions
function Write-ColorOutput($Message, $Color = "White") {
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success($Message) { Write-ColorOutput "✓ $Message" "Green" }
function Write-Warning($Message) { Write-ColorOutput "⚠ $Message" "Yellow" }
function Write-Error($Message) { Write-ColorOutput "✗ $Message" "Red" }
function Write-Info($Message) { Write-ColorOutput "ℹ $Message" "Cyan" }

# Header
Write-ColorOutput @"
========================================================================
GameForge Vast.ai GPU Deployment
========================================================================
Action: $Action
Instance Type: $VastaiInstanceType
Max Price: $MaxPrice cents/hour
Instance ID: $VastaiInstanceId
Dry Run: $DryRun
========================================================================
"@ "Magenta"

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check if vast.ai CLI is available
    try {
        $vastaiVersion = vastai --version 2>$null
        Write-Success "Vast.ai CLI found: $vastaiVersion"
    }
    catch {
        Write-Warning "Vast.ai CLI not found. Installing..."
        Install-VastaiCLI
    }
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker found: $dockerVersion"
    }
    catch {
        Write-Error "Docker not found. Please install Docker Desktop."
        exit 1
    }
    
    # Check required files
    $requiredFiles = @(
        "docker-compose.vastai.yml",
        "Dockerfile.vastai-gpu",
        "requirements-vastai.txt",
        ".env.vastai"
    )
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "Found required file: $file"
        } else {
            Write-Error "Missing required file: $file"
            exit 1
        }
    }
}

function Install-VastaiCLI {
    Write-Info "Installing Vast.ai CLI..."
    try {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            # Windows installation
            Invoke-WebRequest -Uri "https://raw.githubusercontent.com/vast-ai/vast-python/master/vast.py" -OutFile "vastai.py"
            Write-Success "Vast.ai CLI downloaded. Use 'python vastai.py' to run commands."
            
            # Create wrapper script
            @"
@echo off
python "$PWD\vastai.py" %*
"@ | Out-File -FilePath "vastai.bat" -Encoding ascii
            
            Write-Success "Created vastai.bat wrapper"
        } else {
            # Linux/macOS installation
            pip install vastai
        }
    }
    catch {
        Write-Error "Failed to install Vast.ai CLI: $_"
        exit 1
    }
}

function Search-VastaiInstances {
    Write-Info "Searching for available Vast.ai instances..."
    
    try {
        # Search for instances with specified GPU type
        $searchQuery = "gpu_name:$VastaiInstanceType reliability>0.95 num_gpus=1 inet_down>100 inet_up>100"
        
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            $instances = python vastai.py search offers $searchQuery --raw | ConvertFrom-Json
        } else {
            $instances = vastai search offers $searchQuery --raw | ConvertFrom-Json
        }
        
        # Filter by price and sort
        $availableInstances = $instances | Where-Object { $_.dph_total -le ($MaxPrice / 100) } | Sort-Object dph_total | Select-Object -First 5
        
        if ($availableInstances.Count -eq 0) {
            Write-Warning "No suitable instances found within price range"
            return $null
        }
        
        Write-Success "Found $($availableInstances.Count) suitable instances:"
        foreach ($instance in $availableInstances) {
            Write-Host "  ID: $($instance.id) | GPU: $($instance.gpu_name) | Price: $([math]::Round($instance.dph_total * 100, 2)) cents/hour | Location: $($instance.geolocation)"
        }
        
        return $availableInstances[0]  # Return cheapest option
    }
    catch {
        Write-Error "Failed to search Vast.ai instances: $_"
        return $null
    }
}

function Create-VastaiInstance {
    param($InstanceOffer)
    
    Write-Info "Creating Vast.ai instance..."
    
    if ($DryRun) {
        Write-Warning "DRY RUN: Would create instance ID $($InstanceOffer.id)"
        return "dry-run-instance-id"
    }
    
    try {
        # Create instance with Docker image
        $createCommand = @(
            "create", "instance", $InstanceOffer.id,
            "--image", "nvidia/cuda:12.1-devel-ubuntu22.04",
            "--disk", "50",
            "--args", "-p 22:22 -p 8080:8080 -p 8081:8081 -p 8082:8082 -p 3000:3000 -p 5432:5432 -p 6379:6379"
        )
        
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            $result = python vastai.py @createCommand --raw | ConvertFrom-Json
        } else {
            $result = vastai @createCommand --raw | ConvertFrom-Json
        }
        
        if ($result.success) {
            $instanceId = $result.new_contract
            Write-Success "Created Vast.ai instance: $instanceId"
            return $instanceId
        } else {
            Write-Error "Failed to create instance: $($result.msg)"
            return $null
        }
    }
    catch {
        Write-Error "Failed to create Vast.ai instance: $_"
        return $null
    }
}

function Wait-ForInstance {
    param($InstanceId)
    
    Write-Info "Waiting for instance $InstanceId to be ready..."
    
    $maxWaitTime = 300  # 5 minutes
    $waitInterval = 10
    $elapsed = 0
    
    while ($elapsed -lt $maxWaitTime) {
        try {
            if ($IsWindows -or $env:OS -eq "Windows_NT") {
                $status = python vastai.py show instance $InstanceId --raw | ConvertFrom-Json
            } else {
                $status = vastai show instance $InstanceId --raw | ConvertFrom-Json
            }
            
            if ($status.actual_status -eq "running") {
                Write-Success "Instance $InstanceId is running"
                return $status
            }
            
            Write-Verbose "Instance status: $($status.actual_status)"
            Start-Sleep $waitInterval
            $elapsed += $waitInterval
        }
        catch {
            Write-Verbose "Waiting for instance to respond..."
            Start-Sleep $waitInterval
            $elapsed += $waitInterval
        }
    }
    
    Write-Error "Instance $InstanceId did not start within $maxWaitTime seconds"
    return $null
}

function Deploy-ToVastai {
    param($InstanceId, $InstanceInfo)
    
    Write-Info "Deploying GameForge to Vast.ai instance $InstanceId..."
    
    $sshHost = "$($InstanceInfo.ssh_host)"
    $sshPort = $InstanceInfo.ssh_port
    $sshUser = "root"
    
    try {
        # Copy files to instance
        Write-Info "Copying files to Vast.ai instance..."
        
        $filesToCopy = @(
            "docker-compose.vastai.yml",
            "Dockerfile.vastai-gpu", 
            "requirements-vastai.txt",
            ".env.vastai"
        )
        
        foreach ($file in $filesToCopy) {
            scp -P $sshPort $file "${sshUser}@${sshHost}:/workspace/"
        }
        
        # Copy application code
        Write-Info "Copying application code..."
        scp -P $sshPort -r ./gameforge "${sshUser}@${sshHost}:/workspace/"
        
        # Connect and deploy
        Write-Info "Connecting to instance and deploying..."
        
        $deployScript = @"
cd /workspace
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
export BUILD_VERSION=$(git describe --tags --always 2>/dev/null || echo "dev")

# Load environment variables
source .env.vastai

# Install Docker Compose if needed
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Deploy services
docker-compose -f docker-compose.vastai.yml build
docker-compose -f docker-compose.vastai.yml up -d

echo "Deployment completed successfully!"
"@
        
        $deployScript | ssh -p $sshPort "${sshUser}@${sshHost}" 'bash -s'
        
        Write-Success "Deployment to Vast.ai completed successfully!"
        
        # Display access information
        Write-Info @"

========================================================================
Vast.ai Instance Access Information
========================================================================
Instance ID: $InstanceId
SSH Access: ssh -p $sshPort root@$sshHost
Web Interface: http://$sshHost:8080
GPU Inference API: http://$sshHost:8081
GPU Training API: http://$sshHost:8082
Grafana Dashboard: http://$sshHost:3000
========================================================================
"@
        
    }
    catch {
        Write-Error "Failed to deploy to Vast.ai: $_"
        throw
    }
}

function Get-VastaiStatus {
    param($InstanceId)
    
    Write-Info "Checking Vast.ai instance status..."
    
    try {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            $status = python vastai.py show instance $InstanceId --raw | ConvertFrom-Json
        } else {
            $status = vastai show instance $InstanceId --raw | ConvertFrom-Json
        }
        
        Write-Host "Instance Status: $($status.actual_status)" -ForegroundColor Green
        Write-Host "GPU: $($status.gpu_name)" -ForegroundColor Cyan
        Write-Host "Cost: $([math]::Round($status.dph_total * 100, 2)) cents/hour" -ForegroundColor Yellow
        Write-Host "Runtime: $($status.duration)" -ForegroundColor Magenta
        Write-Host "SSH: ssh -p $($status.ssh_port) root@$($status.ssh_host)" -ForegroundColor Blue
        
        return $status
    }
    catch {
        Write-Error "Failed to get instance status: $_"
        return $null
    }
}

function Connect-ToVastai {
    param($InstanceId)
    
    Write-Info "Connecting to Vast.ai instance $InstanceId..."
    
    try {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            $status = python vastai.py show instance $InstanceId --raw | ConvertFrom-Json
        } else {
            $status = vastai show instance $InstanceId --raw | ConvertFrom-Json
        }
        
        $sshCommand = "ssh -p $($status.ssh_port) root@$($status.ssh_host)"
        Write-Info "SSH Command: $sshCommand"
        
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            Start-Process "cmd" -ArgumentList "/c", $sshCommand
        } else {
            Invoke-Expression $sshCommand
        }
    }
    catch {
        Write-Error "Failed to connect to instance: $_"
    }
}

function Stop-VastaiInstance {
    param($InstanceId)
    
    Write-Info "Stopping Vast.ai instance $InstanceId..."
    
    if ($DryRun) {
        Write-Warning "DRY RUN: Would stop instance $InstanceId"
        return
    }
    
    try {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            python vastai.py destroy instance $InstanceId
        } else {
            vastai destroy instance $InstanceId
        }
        
        Write-Success "Instance $InstanceId stopped successfully"
    }
    catch {
        Write-Error "Failed to stop instance: $_"
    }
}

# Main execution
try {
    Test-Prerequisites
    
    switch ($Action.ToLower()) {
        "deploy" {
            if (-not $VastaiInstanceId) {
                $bestInstance = Search-VastaiInstances
                if ($bestInstance) {
                    $instanceId = Create-VastaiInstance -InstanceOffer $bestInstance
                    if ($instanceId) {
                        $instanceInfo = Wait-ForInstance -InstanceId $instanceId
                        if ($instanceInfo) {
                            Deploy-ToVastai -InstanceId $instanceId -InstanceInfo $instanceInfo
                        }
                    }
                }
            } else {
                $instanceInfo = Get-VastaiStatus -InstanceId $VastaiInstanceId
                if ($instanceInfo -and $instanceInfo.actual_status -eq "running") {
                    Deploy-ToVastai -InstanceId $VastaiInstanceId -InstanceInfo $instanceInfo
                } else {
                    Write-Error "Instance $VastaiInstanceId is not running"
                }
            }
        }
        "status" {
            if ($VastaiInstanceId) {
                Get-VastaiStatus -InstanceId $VastaiInstanceId
            } else {
                Write-Error "Instance ID required for status check"
            }
        }
        "connect" {
            if ($VastaiInstanceId) {
                Connect-ToVastai -InstanceId $VastaiInstanceId
            } else {
                Write-Error "Instance ID required for connection"
            }
        }
        "stop" {
            if ($VastaiInstanceId) {
                Stop-VastaiInstance -InstanceId $VastaiInstanceId
            } else {
                Write-Error "Instance ID required to stop instance"
            }
        }
        default {
            Write-Error "Unknown action: $Action"
            exit 1
        }
    }
    
    Write-Success "Action '$Action' completed successfully!"
}
catch {
    Write-Error "Vast.ai deployment failed: $($_.Exception.Message)"
    exit 1
}
