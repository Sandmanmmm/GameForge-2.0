#!/usr/bin/env powershell
# Quick HA Cluster Deployment Script

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$ForceRecreate,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseSimpleConfig,
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterName = "gameforge-production-ha"
)

function Write-Status {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = switch ($Level) {
        "SUCCESS" { "Green" }
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        default { "Cyan" }
    }
    Write-Host "[$timestamp] $Message" -ForegroundColor $color
}

Write-Status "GameForge HA Cluster Quick Deploy" "SUCCESS"
Write-Status "Cluster Name: $ClusterName"
Write-Status "Force Recreate: $ForceRecreate"
Write-Status "Use Simple Config: $UseSimpleConfig"

# Check if cluster creation is hanging
$existingClusters = .\kind.exe get clusters 2>$null
if ($existingClusters -contains $ClusterName -and !$ForceRecreate) {
    Write-Status "Cluster $ClusterName already exists!" "SUCCESS"
    kubectl cluster-info --context "kind-$ClusterName"
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Cluster is responsive, proceeding with deployment..." "SUCCESS"
        $skipClusterCreation = $true
    } else {
        Write-Status "Cluster exists but not responsive" "WARN"
        $ForceRecreate = $true
    }
}

if ($ForceRecreate) {
    Write-Status "Force recreating cluster..." "WARN"
    .\kind.exe delete cluster --name $ClusterName 2>$null
    Start-Sleep -Seconds 5
}

if (!$skipClusterCreation) {
    $configFile = if ($UseSimpleConfig) { "kind-config-simple.yaml" } else { "kind-config-ha.yaml" }
    Write-Status "Creating cluster with config: $configFile"
    
    # Start cluster creation in background and monitor
    $job = Start-Job -ScriptBlock {
        param($ClusterName, $ConfigFile)
        Set-Location $using:PWD
        .\kind.exe create cluster --name $ClusterName --config $ConfigFile
    } -ArgumentList $ClusterName, $configFile
    
    Write-Status "Cluster creation started... Monitoring progress (max 5 minutes)"
    $timeout = 300 # 5 minutes
    $elapsed = 0
    
    while ($job.State -eq "Running" -and $elapsed -lt $timeout) {
        Start-Sleep -Seconds 10
        $elapsed += 10
        Write-Status "Creating cluster... ($elapsed/$timeout seconds)"
        
        # Check if cluster is responding
        $clusters = .\kind.exe get clusters 2>$null
        if ($clusters -contains $ClusterName) {
            kubectl cluster-info --context "kind-$ClusterName" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Status "Cluster is now responsive!" "SUCCESS"
                break
            }
        }
    }
    
    if ($elapsed -ge $timeout) {
        Write-Status "Cluster creation timed out, stopping job..." "ERROR"
        Stop-Job $job
        Remove-Job $job
        return
    }
    
    Wait-Job $job | Out-Null
    $result = Receive-Job $job
    Remove-Job $job
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Cluster created successfully!" "SUCCESS"
    } else {
        Write-Status "Cluster creation failed" "ERROR"
        return
    }
}

# Verify cluster
Write-Status "Verifying cluster status..."
kubectl get nodes -o wide
if ($LASTEXITCODE -ne 0) {
    Write-Status "Failed to get cluster nodes" "ERROR"
    return
}

# Deploy MetalLB for LoadBalancer support
Write-Status "Deploying MetalLB LoadBalancer..."
kubectl apply -f metallb-config.yaml
if ($LASTEXITCODE -eq 0) {
    Write-Status "MetalLB deployed successfully" "SUCCESS"
} else {
    Write-Status "MetalLB deployment failed" "WARN"
}

# Create namespaces
Write-Status "Creating namespaces..."
kubectl create namespace gameforge-security --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace gameforge-monitoring --dry-run=client -o yaml | kubectl apply -f -

# Label namespaces for Pod Security Standards
kubectl label namespace gameforge-security pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite
kubectl label namespace gameforge-monitoring pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite

Write-Status "Namespaces created with Pod Security Standards" "SUCCESS"

# Deploy GameForge stack
Write-Status "Deploying GameForge production stack..."
kubectl apply -k k8s/overlays/production
if ($LASTEXITCODE -eq 0) {
    Write-Status "GameForge stack deployed successfully!" "SUCCESS"
} else {
    Write-Status "GameForge stack deployment had issues" "WARN"
}

# Show final status
Write-Status "=== FINAL CLUSTER STATUS ===" "SUCCESS"
Write-Host "`nNodes:" -ForegroundColor Yellow
kubectl get nodes -o wide

Write-Host "`nMonitoring Services:" -ForegroundColor Yellow
kubectl get svc -n gameforge-monitoring

Write-Host "`nPod Status:" -ForegroundColor Yellow
kubectl get pods -n gameforge-monitoring

Write-Status "HA Cluster deployment completed!" "SUCCESS"
Write-Status "Nodes: $(kubectl get nodes --no-headers | wc -l)" "SUCCESS"
Write-Status "Access via: kubectl port-forward -n gameforge-monitoring svc/gameforge-grafana-prod 3000:3000" "INFO"
