#!/usr/bin/env powershell
# GameForge Kubernetes Cluster Setup Script

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("local", "docker-desktop", "minikube", "kind", "azure", "aws", "gcp", "existing")]
    [string]$ClusterType,
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterName = "gameforge-production",
    
    [Parameter(Mandatory=$false)]
    [string]$KubeConfig = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation,
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateNamespaces
)

# Configuration
$ScriptRoot = $PSScriptRoot
$LogDir = "$ScriptRoot/logs/cluster-setup"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-ClusterLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "CLUSTER"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] [$Component] $Message"
    
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN" { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        default { Write-Host $logMessage -ForegroundColor White }
    }
    
    $logFile = "$LogDir/cluster-setup-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

function Test-Prerequisites {
    Write-ClusterLog "Checking prerequisites..." -Level "INFO"
    
    # Check kubectl
    try {
        $kubectlVersion = kubectl version --client=true --output=json 2>$null | ConvertFrom-Json
        Write-ClusterLog "kubectl found: $($kubectlVersion.clientVersion.gitVersion)" -Level "SUCCESS"
    } catch {
        Write-ClusterLog "kubectl not found. Please install kubectl." -Level "ERROR"
        return $false
    }
    
    # Check Docker (for local clusters)
    if ($ClusterType -in @("docker-desktop", "kind", "minikube")) {
        try {
            $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
            if ($dockerVersion) {
                Write-ClusterLog "Docker found: $dockerVersion" -Level "SUCCESS"
            } else {
                Write-ClusterLog "Docker not running. Please start Docker." -Level "ERROR"
                return $false
            }
        } catch {
            Write-ClusterLog "Docker not found. Please install Docker." -Level "ERROR"
            return $false
        }
    }
    
    return $true
}

function Set-DockerDesktopCluster {
    Write-ClusterLog "Setting up Docker Desktop Kubernetes cluster..." -Level "INFO"
    
    # Check if Docker Desktop Kubernetes is enabled
    try {
        kubectl config use-context docker-desktop 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ClusterLog "Docker Desktop Kubernetes context set" -Level "SUCCESS"
            return $true
        } else {
            Write-ClusterLog "Docker Desktop Kubernetes not enabled. Please enable in Docker Desktop settings." -Level "ERROR"
            Write-ClusterLog "Go to Docker Desktop > Settings > Kubernetes > Enable Kubernetes" -Level "INFO"
            return $false
        }
    } catch {
        Write-ClusterLog "Failed to set Docker Desktop context: $_" -Level "ERROR"
        return $false
    }
}

function New-MinikubeCluster {
    Write-ClusterLog "Creating Minikube cluster..." -Level "INFO"
    
    # Check if minikube is installed
    try {
        $minikubeVersion = minikube version --short 2>$null
        Write-ClusterLog "Minikube found: $minikubeVersion" -Level "SUCCESS"
    } catch {
        Write-ClusterLog "Minikube not found. Installing..." -Level "INFO"
        # Install minikube using chocolatey or scoop if available
        try {
            if (Get-Command choco -ErrorAction SilentlyContinue) {
                choco install minikube -y
            } elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
                scoop install minikube
            } else {
                Write-ClusterLog "Please install minikube manually from https://minikube.sigs.k8s.io/docs/start/" -Level "ERROR"
                return $false
            }
        } catch {
            Write-ClusterLog "Failed to install minikube: $_" -Level "ERROR"
            return $false
        }
    }
    
    # Start minikube cluster
    try {
        Write-ClusterLog "Starting minikube cluster with production-like settings..." -Level "INFO"
        minikube start --profile=$ClusterName --cpus=4 --memory=8192 --disk-size=50g --kubernetes-version=stable
        
        if ($LASTEXITCODE -eq 0) {
            Write-ClusterLog "Minikube cluster started successfully" -Level "SUCCESS"
            kubectl config use-context $ClusterName
            return $true
        } else {
            Write-ClusterLog "Failed to start minikube cluster" -Level "ERROR"
            return $false
        }
    } catch {
        Write-ClusterLog "Failed to create minikube cluster: $_" -Level "ERROR"
        return $false
    }
}

function New-KindCluster {
    Write-ClusterLog "Creating KIND cluster..." -Level "INFO"
    
    # Check if kind is installed
    try {
        $kindVersion = kind version 2>$null
        Write-ClusterLog "KIND found: $kindVersion" -Level "SUCCESS"
    } catch {
        Write-ClusterLog "KIND not found. Installing..." -Level "INFO"
        try {
            if (Get-Command choco -ErrorAction SilentlyContinue) {
                choco install kind -y
            } elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
                scoop install kind
            } else {
                # Download KIND binary
                $kindUrl = "https://kind.sigs.k8s.io/dl/v0.20.0/kind-windows-amd64"
                $kindPath = "$env:TEMP\kind.exe"
                Invoke-WebRequest -Uri $kindUrl -OutFile $kindPath
                Move-Item $kindPath "$env:ProgramFiles\kind.exe" -Force
                $env:PATH += ";$env:ProgramFiles"
            }
        } catch {
            Write-ClusterLog "Failed to install KIND: $_" -Level "ERROR"
            return $false
        }
    }
    
    # Create KIND cluster configuration
    $kindConfig = @"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $ClusterName
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
- role: worker
networking:
  apiServerAddress: "127.0.0.1"
  apiServerPort: 6443
"@
    
    $configPath = "$env:TEMP\kind-config.yaml"
    $kindConfig | Out-File -FilePath $configPath -Encoding UTF8
    
    try {
        kind create cluster --config $configPath --name $ClusterName
        if ($LASTEXITCODE -eq 0) {
            Write-ClusterLog "KIND cluster created successfully" -Level "SUCCESS"
            kubectl config use-context "kind-$ClusterName"
            return $true
        } else {
            Write-ClusterLog "Failed to create KIND cluster" -Level "ERROR"
            return $false
        }
    } catch {
        Write-ClusterLog "Failed to create KIND cluster: $_" -Level "ERROR"
        return $false
    }
}

function Set-ExistingCluster {
    Write-ClusterLog "Connecting to existing cluster..." -Level "INFO"
    
    if ($KubeConfig) {
        Write-ClusterLog "Using provided kubeconfig: $KubeConfig" -Level "INFO"
        $env:KUBECONFIG = $KubeConfig
    }
    
    # List available contexts
    $contexts = kubectl config get-contexts -o name 2>$null
    if ($contexts) {
        Write-ClusterLog "Available contexts:" -Level "INFO"
        foreach ($context in $contexts) {
            Write-ClusterLog "  - $context" -Level "INFO"
        }
        
        # If specific cluster name provided, try to use it
        if ($ClusterName -ne "gameforge-production") {
            if ($ClusterName -in $contexts) {
                kubectl config use-context $ClusterName
                Write-ClusterLog "Switched to context: $ClusterName" -Level "SUCCESS"
                return $true
            } else {
                Write-ClusterLog "Context $ClusterName not found" -Level "ERROR"
                return $false
            }
        } else {
            # Use first available context
            kubectl config use-context $contexts[0]
            Write-ClusterLog "Using context: $($contexts[0])" -Level "SUCCESS"
            return $true
        }
    } else {
        Write-ClusterLog "No kubectl contexts found. Please configure your kubeconfig." -Level "ERROR"
        return $false
    }
}

function Set-CloudCluster {
    param([string]$Provider)
    
    Write-ClusterLog "Setting up $Provider cluster connection..." -Level "INFO"
    
    switch ($Provider) {
        "azure" {
            # Check if Azure CLI is installed
            try {
                $azVersion = az version --output tsv --query '"azure-cli"' 2>$null
                Write-ClusterLog "Azure CLI found: $azVersion" -Level "SUCCESS"
                
                Write-ClusterLog "Please run the following commands to connect to your AKS cluster:" -Level "INFO"
                Write-ClusterLog "  az login" -Level "INFO"
                Write-ClusterLog "  az aks get-credentials --resource-group <resource-group> --name <cluster-name>" -Level "INFO"
                
            } catch {
                Write-ClusterLog "Azure CLI not found. Please install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -Level "ERROR"
                return $false
            }
        }
        "aws" {
            # Check if AWS CLI is installed
            try {
                $awsVersion = aws --version 2>$null
                Write-ClusterLog "AWS CLI found: $awsVersion" -Level "SUCCESS"
                
                Write-ClusterLog "Please run the following commands to connect to your EKS cluster:" -Level "INFO"
                Write-ClusterLog "  aws configure" -Level "INFO"
                Write-ClusterLog "  aws eks update-kubeconfig --region <region> --name <cluster-name>" -Level "INFO"
                
            } catch {
                Write-ClusterLog "AWS CLI not found. Please install from https://aws.amazon.com/cli/" -Level "ERROR"
                return $false
            }
        }
        "gcp" {
            # Check if Google Cloud CLI is installed
            try {
                $gcloudVersion = gcloud version --format="value(Google Cloud SDK)" 2>$null
                Write-ClusterLog "Google Cloud CLI found: $gcloudVersion" -Level "SUCCESS"
                
                Write-ClusterLog "Please run the following commands to connect to your GKE cluster:" -Level "INFO"
                Write-ClusterLog "  gcloud auth login" -Level "INFO"
                Write-ClusterLog "  gcloud container clusters get-credentials <cluster-name> --zone <zone> --project <project-id>" -Level "INFO"
                
            } catch {
                Write-ClusterLog "Google Cloud CLI not found. Please install from https://cloud.google.com/sdk/docs/install" -Level "ERROR"
                return $false
            }
        }
    }
    
    Write-ClusterLog "After running the cloud provider commands, run this script again with -ClusterType existing" -Level "INFO"
    return $false
}

function Test-ClusterConnection {
    Write-ClusterLog "Testing cluster connection..." -Level "INFO"
    
    try {
        # Test basic connectivity
        $clusterInfo = kubectl cluster-info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ClusterLog "Cluster connection successful" -Level "SUCCESS"
            Write-ClusterLog "Cluster info: $($clusterInfo[0])" -Level "INFO"
        } else {
            Write-ClusterLog "Cluster connection failed: $clusterInfo" -Level "ERROR"
            return $false
        }
        
        # Test permissions
        $namespaces = kubectl get namespaces -o name 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ClusterLog "Cluster permissions verified" -Level "SUCCESS"
            Write-ClusterLog "Found $($namespaces.Count) namespaces" -Level "INFO"
        } else {
            Write-ClusterLog "Insufficient cluster permissions" -Level "ERROR"
            return $false
        }
        
        # Get cluster version
        $version = kubectl version --output=json 2>$null | ConvertFrom-Json
        if ($version.serverVersion) {
            Write-ClusterLog "Kubernetes server version: $($version.serverVersion.gitVersion)" -Level "INFO"
        }
        
        return $true
        
    } catch {
        Write-ClusterLog "Cluster connection test failed: $_" -Level "ERROR"
        return $false
    }
}

function New-GameForgeNamespaces {
    Write-ClusterLog "Creating GameForge namespaces..." -Level "INFO"
    
    $namespaces = @("gameforge-security", "gameforge-monitoring")
    
    foreach ($namespace in $namespaces) {
        try {
            # Check if namespace exists
            kubectl get namespace $namespace 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-ClusterLog "Namespace $namespace already exists" -Level "INFO"
            } else {
                # Create namespace
                kubectl create namespace $namespace
                if ($LASTEXITCODE -eq 0) {
                    Write-ClusterLog "Created namespace: $namespace" -Level "SUCCESS"
                } else {
                    Write-ClusterLog "Failed to create namespace: $namespace" -Level "ERROR"
                }
            }
        } catch {
            Write-ClusterLog "Error with namespace $namespace`: $_" -Level "ERROR"
        }
    }
}

function Show-ClusterSummary {
    Write-ClusterLog "=== CLUSTER SETUP SUMMARY ===" -Level "INFO"
    
    # Current context
    $currentContext = kubectl config current-context 2>$null
    if ($currentContext) {
        Write-ClusterLog "Current Context: $currentContext" -Level "INFO"
    }
    
    # Cluster info
    Write-Host "`nCluster Information:" -ForegroundColor Cyan
    kubectl cluster-info 2>$null | ForEach-Object { 
        Write-Host "  $_" -ForegroundColor White 
    }
    
    # Node status
    Write-Host "`nNode Status:" -ForegroundColor Cyan
    kubectl get nodes -o wide 2>$null | ForEach-Object { 
        Write-Host "  $_" -ForegroundColor White 
    }
    
    # Namespaces
    Write-Host "`nNamespaces:" -ForegroundColor Cyan
    kubectl get namespaces 2>$null | ForEach-Object { 
        Write-Host "  $_" -ForegroundColor White 
    }
    
    Write-Host "`nNext Steps:" -ForegroundColor Yellow
    Write-Host "  1. Test deployment: .\kustomize-deploy.ps1 -Action validate -Environment production" -ForegroundColor White
    Write-Host "  2. Deploy to cluster: .\kustomize-deploy.ps1 -Action deploy -Environment production" -ForegroundColor White
    Write-Host "  3. Check status: kubectl get all -n gameforge-security" -ForegroundColor White
}

# Main execution
function Start-ClusterSetup {
    Write-ClusterLog "Starting Kubernetes cluster setup for GameForge production" -Level "INFO"
    Write-ClusterLog "Cluster Type: $ClusterType" -Level "INFO"
    
    try {
        # Check prerequisites
        if (-not (Test-Prerequisites)) {
            Write-ClusterLog "Prerequisites check failed" -Level "ERROR"
            exit 1
        }
        
        # Setup cluster based on type
        $success = $false
        switch ($ClusterType) {
            "docker-desktop" { $success = Set-DockerDesktopCluster }
            "minikube" { $success = New-MinikubeCluster }
            "kind" { $success = New-KindCluster }
            "existing" { $success = Set-ExistingCluster }
            "azure" { $success = Set-CloudCluster -Provider "azure" }
            "aws" { $success = Set-CloudCluster -Provider "aws" }
            "gcp" { $success = Set-CloudCluster -Provider "gcp" }
            "local" { 
                Write-ClusterLog "Local cluster setup - trying Docker Desktop first, then minikube" -Level "INFO"
                $success = Set-DockerDesktopCluster
                if (-not $success) {
                    $success = New-MinikubeCluster
                }
            }
        }
        
        if (-not $success) {
            Write-ClusterLog "Cluster setup failed" -Level "ERROR"
            exit 1
        }
        
        # Test connection
        if (-not $SkipValidation) {
            if (-not (Test-ClusterConnection)) {
                Write-ClusterLog "Cluster connection test failed" -Level "ERROR"
                exit 1
            }
        }
        
        # Create namespaces if requested
        if ($CreateNamespaces) {
            New-GameForgeNamespaces
        }
        
        # Show summary
        Show-ClusterSummary
        
        Write-ClusterLog "Cluster setup completed successfully!" -Level "SUCCESS"
        
    } catch {
        Write-ClusterLog "Cluster setup failed: $_" -Level "ERROR"
        exit 1
    }
}

# Execute setup
Start-ClusterSetup
