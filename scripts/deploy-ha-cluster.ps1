#!/usr/bin/env powershell
# GameForge High-Availability Cluster Deployment Script

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$DeleteExisting,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipLoadBalancer,
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterName = "gameforge-production-ha",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Configuration
$ScriptRoot = $PSScriptRoot
$LogDir = "$ScriptRoot/logs/ha-deployment"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-HALog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "HA-DEPLOY"
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
    
    $logFile = "$LogDir/ha-deployment-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage
}

function Test-Prerequisites {
    Write-HALog "Checking prerequisites..." "INFO"
    
    # Check if KIND is installed
    try {
        $kindVersion = kind version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "KIND found: $kindVersion" "SUCCESS"
        } else {
            throw "KIND not found"
        }
    } catch {
        Write-HALog "KIND is not installed. Please install KIND first." "ERROR"
        return $false
    }
    
    # Check if kubectl is installed
    try {
        $kubectlVersion = kubectl version --client --short 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "kubectl found: $kubectlVersion" "SUCCESS"
        } else {
            throw "kubectl not found"
        }
    } catch {
        Write-HALog "kubectl is not installed. Please install kubectl first." "ERROR"
        return $false
    }
    
    # Check if Docker is running
    try {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "Docker is running" "SUCCESS"
        } else {
            throw "Docker not running"
        }
    } catch {
        Write-HALog "Docker is not running. Please start Docker first." "ERROR"
        return $false
    }
    
    return $true
}

function Remove-ExistingCluster {
    param([string]$ClusterName)
    
    Write-HALog "Checking for existing cluster: $ClusterName" "INFO"
    
    try {
        $clusters = kind get clusters 2>$null
        if ($clusters -contains $ClusterName) {
            Write-HALog "Deleting existing cluster: $ClusterName" "WARN"
            kind delete cluster --name $ClusterName
            if ($LASTEXITCODE -eq 0) {
                Write-HALog "Successfully deleted existing cluster" "SUCCESS"
            } else {
                Write-HALog "Failed to delete existing cluster" "ERROR"
                return $false
            }
        } else {
            Write-HALog "No existing cluster found" "INFO"
        }
    } catch {
        Write-HALog "Error checking existing clusters: $_" "ERROR"
        return $false
    }
    
    return $true
}

function Deploy-HACluster {
    param([string]$ClusterName)
    
    Write-HALog "Creating high-availability cluster: $ClusterName" "INFO"
    
    try {
        # Create cluster with config
        $configPath = "$ScriptRoot/kind-config-ha.yaml"
        if (!(Test-Path $configPath)) {
            Write-HALog "KIND config file not found: $configPath" "ERROR"
            return $false
        }
        
        Write-HALog "Using config file: $configPath" "INFO"
        kind create cluster --name $ClusterName --config $configPath
        
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "Cluster created successfully" "SUCCESS"
        } else {
            Write-HALog "Failed to create cluster" "ERROR"
            return $false
        }
        
        # Wait for cluster to be ready
        Write-HALog "Waiting for cluster to be ready..." "INFO"
        Start-Sleep -Seconds 30
        
        # Verify cluster
        kubectl cluster-info --context "kind-$ClusterName"
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "Cluster is ready and responsive" "SUCCESS"
        } else {
            Write-HALog "Cluster is not responsive" "ERROR"
            return $false
        }
        
    } catch {
        Write-HALog "Error creating cluster: $_" "ERROR"
        return $false
    }
    
    return $true
}

function Deploy-LoadBalancer {
    Write-HALog "Deploying MetalLB LoadBalancer..." "INFO"
    
    try {
        $metallbPath = "$ScriptRoot/metallb-config.yaml"
        if (!(Test-Path $metallbPath)) {
            Write-HALog "MetalLB config file not found: $metallbPath" "ERROR"
            return $false
        }
        
        # Apply MetalLB configuration
        kubectl apply -f $metallbPath
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "MetalLB configuration applied" "SUCCESS"
        } else {
            Write-HALog "Failed to apply MetalLB configuration" "ERROR"
            return $false
        }
        
        # Wait for MetalLB to be ready
        Write-HALog "Waiting for MetalLB to be ready..." "INFO"
        kubectl wait --namespace metallb-system --for=condition=ready pod --selector=app=metallb --timeout=300s
        
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "MetalLB is ready" "SUCCESS"
        } else {
            Write-HALog "MetalLB failed to become ready" "WARN"
        }
        
    } catch {
        Write-HALog "Error deploying LoadBalancer: $_" "ERROR"
        return $false
    }
    
    return $true
}

function Create-Namespaces {
    Write-HALog "Creating GameForge namespaces..." "INFO"
    
    try {
        # Create namespaces with Pod Security Standards
        kubectl create namespace gameforge-security --dry-run=client -o yaml | `
            kubectl label --local -f - pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --dry-run=client -o yaml | `
            kubectl apply -f -
            
        kubectl create namespace gameforge-monitoring --dry-run=client -o yaml | `
            kubectl label --local -f - pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --dry-run=client -o yaml | `
            kubectl apply -f -
        
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "Namespaces created successfully" "SUCCESS"
        } else {
            Write-HALog "Failed to create namespaces" "ERROR"
            return $false
        }
        
    } catch {
        Write-HALog "Error creating namespaces: $_" "ERROR"
        return $false
    }
    
    return $true
}

function Deploy-GameForgeStack {
    Write-HALog "Deploying GameForge production stack..." "INFO"
    
    try {
        # Deploy using Kustomize
        kubectl apply -k k8s/overlays/production
        
        if ($LASTEXITCODE -eq 0) {
            Write-HALog "GameForge stack deployed successfully" "SUCCESS"
        } else {
            Write-HALog "Failed to deploy GameForge stack" "ERROR"
            return $false
        }
        
        # Wait for deployments to be ready
        Write-HALog "Waiting for deployments to be ready..." "INFO"
        kubectl wait --for=condition=available --timeout=600s deployment/gameforge-grafana-prod -n gameforge-monitoring
        kubectl wait --for=condition=available --timeout=600s deployment/gameforge-prometheus-prod -n gameforge-monitoring
        
    } catch {
        Write-HALog "Error deploying GameForge stack: $_" "ERROR"
        return $false
    }
    
    return $true
}

function Show-ClusterStatus {
    Write-HALog "Displaying cluster status..." "INFO"
    
    Write-Host "`n=== CLUSTER NODES ===" -ForegroundColor Yellow
    kubectl get nodes -o wide
    
    Write-Host "`n=== NAMESPACES ===" -ForegroundColor Yellow
    kubectl get namespaces | Select-String "gameforge|metallb"
    
    Write-Host "`n=== MONITORING NAMESPACE ===" -ForegroundColor Yellow
    kubectl get all -n gameforge-monitoring
    
    Write-Host "`n=== SECURITY NAMESPACE ===" -ForegroundColor Yellow
    kubectl get all -n gameforge-security
    
    Write-Host "`n=== LOADBALANCER SERVICES ===" -ForegroundColor Yellow
    kubectl get services --all-namespaces -o wide | Select-String "LoadBalancer"
    
    Write-Host "`n=== METALLB STATUS ===" -ForegroundColor Yellow
    kubectl get all -n metallb-system
}

# Main deployment process
Write-HALog "Starting GameForge HA Cluster Deployment" "INFO"
Write-HALog "Cluster Name: $ClusterName" "INFO"
Write-HALog "Delete Existing: $DeleteExisting" "INFO"
Write-HALog "Skip LoadBalancer: $SkipLoadBalancer" "INFO"
Write-HALog "Dry Run: $DryRun" "INFO"

if ($DryRun) {
    Write-HALog "DRY RUN MODE - No actual changes will be made" "WARN"
    exit 0
}

# Step 1: Check prerequisites
if (!(Test-Prerequisites)) {
    Write-HALog "Prerequisites check failed" "ERROR"
    exit 1
}

# Step 2: Remove existing cluster if requested
if ($DeleteExisting) {
    if (!(Remove-ExistingCluster -ClusterName $ClusterName)) {
        Write-HALog "Failed to remove existing cluster" "ERROR"
        exit 1
    }
}

# Step 3: Deploy HA cluster
if (!(Deploy-HACluster -ClusterName $ClusterName)) {
    Write-HALog "Failed to deploy HA cluster" "ERROR"
    exit 1
}

# Step 4: Deploy LoadBalancer
if (!$SkipLoadBalancer) {
    if (!(Deploy-LoadBalancer)) {
        Write-HALog "Failed to deploy LoadBalancer" "ERROR"
        exit 1
    }
}

# Step 5: Create namespaces
if (!(Create-Namespaces)) {
    Write-HALog "Failed to create namespaces" "ERROR"
    exit 1
}

# Step 6: Deploy GameForge stack
if (!(Deploy-GameForgeStack)) {
    Write-HALog "Failed to deploy GameForge stack" "ERROR"
    exit 1
}

# Step 7: Show status
Show-ClusterStatus

Write-HALog "GameForge HA Cluster deployment completed successfully!" "SUCCESS"
Write-HALog "Cluster: $ClusterName with $(kubectl get nodes --no-headers | wc -l) nodes" "SUCCESS"
Write-HALog "LoadBalancer: MetalLB configured for external access" "SUCCESS"
Write-HALog "Access Grafana via LoadBalancer IP when available" "INFO"
