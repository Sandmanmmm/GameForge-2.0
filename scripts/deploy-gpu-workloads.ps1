# GPU Workload Scheduling Deployment Script
# Deploys GPU workloads using Docker Compose with Kubernetes resource policies

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("deploy", "start", "stop", "restart", "status", "logs", "clean", "k8s-deploy")]
    [string]$Action = "deploy",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("docker", "kubernetes", "hybrid")]
    [string]$Platform = "docker",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("gpu", "cpu", "hybrid")]
    [string]$Mode = "gpu",
    
    [Parameter(Mandatory=$false)]
    [int]$GpuCount = 1,
    
    [string]$Environment = "production",
    [string]$Namespace = "gameforge",
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

# Set error handling
$ErrorActionPreference = "Stop"

# Set verbose preference
if ($Verbose) {
    $VerbosePreference = "Continue"
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Test-Prerequisites {
    Write-Log "Checking prerequisites..." -Level "INFO"
    
    if ($Platform -eq "kubernetes" -or $Platform -eq "hybrid") {
        # Check kubectl
        try {
            $kubectlVersion = kubectl version --client -o json | ConvertFrom-Json
            Write-Log "kubectl version: $($kubectlVersion.clientVersion.gitVersion)" -Level "SUCCESS"
        }
        catch {
            Write-Log "kubectl not found or not configured" -Level "ERROR"
            throw "kubectl is required for Kubernetes deployment"
        }
        
        # Check cluster connectivity
        try {
            kubectl cluster-info | Out-Null
            Write-Log "Kubernetes cluster connectivity verified" -Level "SUCCESS"
        }
        catch {
            Write-Log "Cannot connect to Kubernetes cluster" -Level "ERROR"
            throw "Kubernetes cluster connection failed"
        }
    }
    
    if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
        # Check Docker
        try {
            $dockerVersion = docker --version
            Write-Log "Docker found: $dockerVersion" -Level "SUCCESS"
        }
        catch {
            Write-Log "Docker not found or not running" -Level "ERROR"
            throw "Docker is required for Docker deployment"
        }
        
        # Check Docker Compose
        try {
            $composeVersion = docker compose version
            Write-Log "Docker Compose found: $composeVersion" -Level "SUCCESS"
        }
        catch {
            Write-Log "Docker Compose not found" -Level "ERROR"
            throw "Docker Compose is required"
        }
        
        # Check NVIDIA Docker runtime (for GPU mode)
        if ($Mode -eq "gpu" -or $Mode -eq "hybrid") {
            try {
                $nvidiaVersion = nvidia-smi --query-gpu=name --format=csv,noheader
                Write-Log "NVIDIA GPU found: $nvidiaVersion" -Level "SUCCESS"
                
                # Check NVIDIA Container Runtime
                $dockerInfo = docker info --format json | ConvertFrom-Json
                $runtimes = $dockerInfo.Runtimes
                if ($runtimes.nvidia) {
                    Write-Log "NVIDIA Container Runtime detected" -Level "SUCCESS"
                } else {
                    Write-Log "NVIDIA Container Runtime not detected - GPU mode may not work" -Level "WARN"
                }
            }
            catch {
                Write-Log "NVIDIA GPU or drivers not found - GPU mode may not work" -Level "WARN"
                if ($Mode -eq "gpu") {
                    Write-Log "GPU mode requires NVIDIA GPU and drivers" -Level "ERROR"
                    throw "GPU requirements not met"
                }
            }
        }
    }
        $nodes = kubectl get nodes --no-headers 2>$null
        if (-not $nodes) {
            throw "No nodes found"
        }
        Write-Log "Cluster connectivity verified" -Level "SUCCESS"
    }
    catch {
        Write-Log "Cannot connect to Kubernetes cluster" -Level "ERROR"
        throw "Cluster connectivity required"
    }
    
    # Check for GPU nodes
    try {
        $gpuNodes = kubectl get nodes -l accelerator=nvidia --no-headers 2>$null
        if (-not $gpuNodes) {
            Write-Log "Warning: No GPU nodes found with label 'accelerator=nvidia'" -Level "WARN"
            Write-Log "Make sure to label your GPU nodes: kubectl label nodes <node-name> accelerator=nvidia" -Level "WARN"
        } else {
            $gpuNodeCount = ($gpuNodes | Measure-Object).Count
            Write-Log "Found $gpuNodeCount GPU nodes" -Level "SUCCESS"
        }
    }
    catch {
        Write-Log "Could not check for GPU nodes" -Level "WARN"
    }
}

function Deploy-GPUDevicePlugin {
    Write-Log "Deploying NVIDIA Device Plugin..." -Level "INFO"
    
    $command = "kubectl apply -f k8s/gpu-device-plugin.yaml"
    if ($DryRun) {
        $command += " --dry-run=client"
    }
    
    try {
        Invoke-Expression $command
        Write-Log "NVIDIA Device Plugin deployed successfully" -Level "SUCCESS"
        
        if (-not $DryRun) {
            # Wait for device plugin to be ready
            Write-Log "Waiting for device plugin to be ready..." -Level "INFO"
            Start-Sleep -Seconds 30
            
            $devicePluginStatus = kubectl get daemonset nvidia-device-plugin-daemonset -n kube-system -o jsonpath='{.status.numberReady}/{.status.desiredNumberScheduled}' 2>$null
            if ($devicePluginStatus) {
                Write-Log "Device plugin status: $devicePluginStatus" -Level "INFO"
            }
        }
    }
    catch {
        Write-Log "Failed to deploy NVIDIA Device Plugin: $_" -Level "ERROR"
        throw
    }
}

function Deploy-GPUPolicies {
    Write-Log "Deploying GPU workload policies..." -Level "INFO"
    
    $command = "kubectl apply -f k8s/gpu-workload-policies.yaml"
    if ($DryRun) {
        $command += " --dry-run=client"
    }
    
    try {
        Invoke-Expression $command
        Write-Log "GPU workload policies deployed successfully" -Level "SUCCESS"
    }
    catch {
        Write-Log "Failed to deploy GPU workload policies: $_" -Level "ERROR"
        throw
    }
}

function Deploy-GPUStorage {
    Write-Log "Deploying GPU storage resources..." -Level "INFO"
    
    $command = "kubectl apply -f k8s/gpu-storage.yaml"
    if ($DryRun) {
        $command += " --dry-run=client"
    }
    
    try {
        Invoke-Expression $command
        Write-Log "GPU storage resources deployed successfully" -Level "SUCCESS"
        
        if (-not $DryRun) {
            # Wait for PVCs to be bound
            Write-Log "Waiting for PVCs to be bound..." -Level "INFO"
            Start-Sleep -Seconds 10
            
            $pvcStatus = kubectl get pvc -n $Namespace --no-headers 2>$null
            if ($pvcStatus) {
                Write-Log "PVC Status:" -Level "INFO"
                $pvcStatus | ForEach-Object { Write-Log "  $_" -Level "INFO" }
            }
        }
    }
    catch {
        Write-Log "Failed to deploy GPU storage: $_" -Level "ERROR"
        throw
    }
}

function Deploy-GPUWorkloads {
    Write-Log "Deploying GPU AI workloads..." -Level "INFO"
    
    $command = "kubectl apply -f k8s/gpu-ai-workloads.yaml"
    if ($DryRun) {
        $command += " --dry-run=client"
    }
    
    try {
        Invoke-Expression $command
        Write-Log "GPU AI workloads deployed successfully" -Level "SUCCESS"
        
        if (-not $DryRun) {
            # Wait for deployments to be ready
            Write-Log "Waiting for deployments to be ready..." -Level "INFO"
            Start-Sleep -Seconds 30
            
            $deployments = @("gameforge-training", "gameforge-inference", "gameforge-asset-generation")
            foreach ($deployment in $deployments) {
                try {
                    $status = kubectl get deployment $deployment -n $Namespace -o jsonpath='{.status.readyReplicas}/{.status.replicas}' 2>$null
                    if ($status) {
                        Write-Log "Deployment $deployment status: $status" -Level "INFO"
                    }
                }
                catch {
                    Write-Log "Could not get status for deployment $deployment" -Level "WARN"
                }
            }
        }
    }
    catch {
        Write-Log "Failed to deploy GPU AI workloads: $_" -Level "ERROR"
        throw
    }
}

function Verify-GPUScheduling {
    Write-Log "Verifying GPU workload scheduling..." -Level "INFO"
    
    # Check device plugin
    Write-Log "Checking NVIDIA Device Plugin..." -Level "INFO"
    try {
        $devicePlugin = kubectl get daemonset nvidia-device-plugin-daemonset -n kube-system 2>$null
        if ($devicePlugin) {
            Write-Log "✓ NVIDIA Device Plugin found" -Level "SUCCESS"
        } else {
            Write-Log "✗ NVIDIA Device Plugin not found" -Level "ERROR"
        }
    }
    catch {
        Write-Log "✗ Could not check NVIDIA Device Plugin" -Level "ERROR"
    }
    
    # Check GPU resource quota
    Write-Log "Checking GPU resource quota..." -Level "INFO"
    try {
        $quota = kubectl get resourcequota gpu-resource-quota -n $Namespace 2>$null
        if ($quota) {
            Write-Log "✓ GPU resource quota found" -Level "SUCCESS"
            kubectl describe resourcequota gpu-resource-quota -n $Namespace
        } else {
            Write-Log "✗ GPU resource quota not found" -Level "ERROR"
        }
    }
    catch {
        Write-Log "✗ Could not check GPU resource quota" -Level "ERROR"
    }
    
    # Check GPU nodes
    Write-Log "Checking GPU node allocations..." -Level "INFO"
    try {
        $gpuNodes = kubectl get nodes -l accelerator=nvidia -o custom-columns="NAME:.metadata.name,GPU-CAPACITY:.status.allocatable.nvidia\.com/gpu,GPU-ALLOCATED:.status.capacity.nvidia\.com/gpu" --no-headers 2>$null
        if ($gpuNodes) {
            Write-Log "GPU Node Status:" -Level "INFO"
            $gpuNodes | ForEach-Object { Write-Log "  $_" -Level "INFO" }
        } else {
            Write-Log "No GPU nodes found" -Level "WARN"
        }
    }
    catch {
        Write-Log "Could not check GPU nodes" -Level "WARN"
    }
    
    # Check workload scheduling
    Write-Log "Checking GPU workload pod scheduling..." -Level "INFO"
    try {
        $gpuPods = kubectl get pods -n $Namespace -l gpu-enabled=true -o custom-columns="NAME:.metadata.name,NODE:.spec.nodeName,STATUS:.status.phase,GPU-REQUEST:.spec.containers[*].resources.requests.nvidia\.com/gpu" --no-headers 2>$null
        if ($gpuPods) {
            Write-Log "GPU Pod Status:" -Level "INFO"
            $gpuPods | ForEach-Object { Write-Log "  $_" -Level "INFO" }
        } else {
            Write-Log "No GPU pods found" -Level "INFO"
        }
    }
    catch {
        Write-Log "Could not check GPU pods" -Level "WARN"
    }
}

function Remove-GPUWorkloads {
    Write-Log "Removing GPU workload scheduling..." -Level "INFO"
    
    $files = @(
        "k8s/gpu-ai-workloads.yaml",
        "k8s/gpu-storage.yaml",
        "k8s/gpu-workload-policies.yaml",
        "k8s/gpu-device-plugin.yaml"
    )
    
    foreach ($file in $files) {
        if (Test-Path $file) {
            try {
                $command = "kubectl delete -f $file --ignore-not-found=true"
                if ($DryRun) {
                    $command += " --dry-run=client"
                }
                Invoke-Expression $command
                Write-Log "Removed resources from $file" -Level "SUCCESS"
            }
            catch {
                Write-Log "Failed to remove resources from $file: $_" -Level "ERROR"
            }
        }
    }
}

# Docker Compose Functions
function Set-DockerEnvironment {
    Write-Log "Setting up Docker environment variables..." -Level "INFO"
    
    # Generate build metadata
    $buildDate = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $vcsRef = try { git rev-parse HEAD } catch { "unknown" }
    $buildVersion = try { git describe --tags --always } catch { "dev" }
    
    # Set environment variables
    $env:BUILD_DATE = $buildDate
    $env:VCS_REF = $vcsRef
    $env:BUILD_VERSION = $buildVersion
    $env:GAMEFORGE_ENV = $Environment
    $env:GAMEFORGE_VARIANT = $Mode
    
    # GPU-specific configuration
    if ($Mode -eq "gpu" -or $Mode -eq "hybrid") {
        $env:ENABLE_GPU = "true"
        $env:DOCKER_RUNTIME = "nvidia"
        $env:GPU_COUNT = $GpuCount
        $env:NVIDIA_VISIBLE_DEVICES = "all"
        $env:NVIDIA_DRIVER_CAPABILITIES = "compute,utility"
        $env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:2048,garbage_collection_threshold:0.8,expandable_segments:True"
        
        # Training-specific GPU configuration
        $env:TRAINING_GPU_COUNT = [Math]::Max(1, $GpuCount - 1)
        $env:TRAINING_NVIDIA_VISIBLE_DEVICES = if ($GpuCount -gt 1) { "1,2,3" } else { "0" }
        
        # Resource limits based on GPU count
        $env:MEMORY_LIMIT = "$(16 * $GpuCount)G"
        $env:CPU_LIMIT = "$(8.0 * $GpuCount)"
        $env:MEMORY_RESERVATION = "$(8 * $GpuCount)G"
        $env:CPU_RESERVATION = "$(4.0 * $GpuCount)"
        
        Write-Log "GPU mode configured with $GpuCount GPU(s)" -Level "SUCCESS"
    } else {
        $env:ENABLE_GPU = "false"
        $env:DOCKER_RUNTIME = "runc"
        $env:MEMORY_LIMIT = "8G"
        $env:CPU_LIMIT = "4.0"
        $env:MEMORY_RESERVATION = "4G"
        $env:CPU_RESERVATION = "2.0"
        
        Write-Log "CPU mode configured" -Level "SUCCESS"
    }
    
    # Set paths for volumes
    $currentDir = Get-Location
    $env:TRAINING_DATA_PATH = "$currentDir\volumes\training-data"
    $env:CHECKPOINT_PATH = "$currentDir\volumes\model-checkpoints"
}

function Initialize-DockerDirectories {
    Write-Log "Creating required directories..." -Level "INFO"
    
    $directories = @(
        "volumes\training-data",
        "volumes\model-checkpoints",
        "volumes\security\harbor-secret",
        "volumes\security\harbor-ca",
        "volumes\security\clair-data",
        "volumes\security\clair-logs",
        "volumes\security\notary-data",
        "volumes\security\notary-certs",
        "logs\gpu-inference",
        "logs\gpu-training",
        "cache\gpu-models",
        "monitoring\gpu-metrics"
    )
    
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Log "Created directory: $dir" -Level "SUCCESS"
        } else {
            Write-Verbose "Directory already exists: $dir"
        }
    }
}

function Start-DockerServices {
    Write-Log "Deploying GameForge GPU workload services via Docker Compose..." -Level "INFO"
    
    $composeFile = "docker-compose.production-hardened.yml"
    $services = @()
    
    # Determine services to deploy based on mode
    switch ($Mode) {
        "gpu" {
            $services = @(
                "security-bootstrap",
                "security-monitor", 
                "postgres",
                "redis",
                "vault",
                "gameforge-app",
                "gameforge-gpu-inference",
                "gameforge-gpu-training",
                "nginx",
                "prometheus",
                "grafana"
            )
        }
        "cpu" {
            $services = @(
                "security-bootstrap",
                "security-monitor",
                "postgres", 
                "redis",
                "vault",
                "gameforge-app",
                "gameforge-worker",
                "nginx",
                "prometheus",
                "grafana"
            )
        }
        "hybrid" {
            $services = @(
                "security-bootstrap",
                "security-monitor",
                "postgres",
                "redis", 
                "vault",
                "gameforge-app",
                "gameforge-worker",
                "gameforge-gpu-inference",
                "gameforge-gpu-training",
                "nginx",
                "prometheus",
                "grafana"
            )
        }
    }
    
    if ($DryRun) {
        Write-Log "DRY RUN: Would deploy the following services:" -Level "WARN"
        $services | ForEach-Object { Write-Host "  - $_" }
        return
    }
    
    try {
        # Build images first
        Write-Log "Building container images..." -Level "INFO"
        docker compose -f $composeFile build $services
        Write-Log "Container images built successfully" -Level "SUCCESS"
        
        # Deploy services
        Write-Log "Starting services..." -Level "INFO"
        docker compose -f $composeFile up -d $services
        Write-Log "Services deployed successfully" -Level "SUCCESS"
        
        # Wait for services to be healthy
        Write-Log "Waiting for services to be healthy..." -Level "INFO"
        Start-Sleep -Seconds 30
        
        # Check service status
        Test-DockerServices
        
    }
    catch {
        Write-Log "Failed to deploy services: $_" -Level "ERROR"
        throw
    }
}

function Test-DockerServices {
    Write-Log "Checking Docker service status..." -Level "INFO"
    
    try {
        $status = docker compose -f docker-compose.production-hardened.yml ps --format json | ConvertFrom-Json
        foreach ($service in $status) {
            $serviceName = $service.Service
            $state = $service.State
            $health = $service.Health
            
            if ($state -eq "running") {
                if ($health -eq "healthy" -or $health -eq "") {
                    Write-Log "Service $serviceName is running and healthy" -Level "SUCCESS"
                } else {
                    Write-Log "Service $serviceName is running but not healthy: $health" -Level "WARN"
                }
            } else {
                Write-Log "Service $serviceName is not running: $state" -Level "ERROR"
            }
        }
        
        # GPU-specific checks
        if ($Mode -eq "gpu" -or $Mode -eq "hybrid") {
            Write-Log "Checking GPU service status..." -Level "INFO"
            
            # Check GPU inference service
            try {
                $gpuInferenceStatus = docker compose exec gameforge-gpu-inference python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}, GPU Count: {torch.cuda.device_count()}')" 2>$null
                Write-Log "GPU Inference Service: $gpuInferenceStatus" -Level "SUCCESS"
            }
            catch {
                Write-Log "GPU Inference Service: Not accessible" -Level "WARN"
            }
            
            # Check GPU training service
            try {
                $gpuTrainingStatus = docker compose exec gameforge-gpu-training python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}, GPU Count: {torch.cuda.device_count()}')" 2>$null
                Write-Log "GPU Training Service: $gpuTrainingStatus" -Level "SUCCESS"
            }
            catch {
                Write-Log "GPU Training Service: Not accessible" -Level "WARN"
            }
        }
    }
    catch {
        Write-Log "Failed to check service status: $_" -Level "ERROR"
    }
}

function Stop-DockerServices {
    Write-Log "Stopping GameForge Docker services..." -Level "INFO"
    
    if ($DryRun) {
        Write-Log "DRY RUN: Would stop all services" -Level "WARN"
        return
    }
    
    try {
        docker compose -f docker-compose.production-hardened.yml down
        Write-Log "Services stopped successfully" -Level "SUCCESS"
    }
    catch {
        Write-Log "Failed to stop services: $_" -Level "ERROR"
        throw
    }
}

function Show-Help {
    Write-Host @"
GPU Workload Scheduling Deployment Script

USAGE:
    .\deploy-gpu-workloads.ps1 [OPTIONS]

OPTIONS:
    -Action <deploy|remove|verify>  Action to perform (default: deploy)
    -Environment <env>              Environment name (default: production)
    -Namespace <ns>                 Kubernetes namespace (default: gameforge)
    -DryRun                        Perform dry run without making changes
    -Verbose                       Enable verbose output
    -Help                          Show this help message

EXAMPLES:
    # Deploy GPU workload scheduling
    .\deploy-gpu-workloads.ps1

    # Verify GPU scheduling setup
    .\deploy-gpu-workloads.ps1 -Action verify

    # Remove GPU workloads
    .\deploy-gpu-workloads.ps1 -Action remove

    # Dry run deployment
    .\deploy-gpu-workloads.ps1 -DryRun

REQUIREMENTS:
    - kubectl configured and connected to cluster
    - GPU nodes labeled with 'accelerator=nvidia'
    - Appropriate RBAC permissions
    - NVIDIA drivers installed on GPU nodes

"@
}

# Main execution
try {
    Write-Log "🚀 GameForge GPU Workload Scheduling Deployment" -Level "INFO"
    Write-Log "Platform: $Platform" -Level "INFO"
    Write-Log "Mode: $Mode" -Level "INFO"
    Write-Log "Environment: $Environment" -Level "INFO"
    Write-Log "Action: $Action" -Level "INFO"
    
    if ($DryRun) {
        Write-Log "DRY RUN MODE - No changes will be made" -Level "WARN"
    }
    
    Test-Prerequisites
    
    switch ($Action.ToLower()) {
        "deploy" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Set-DockerEnvironment
                Initialize-DockerDirectories
                Start-DockerServices
            }
            if ($Platform -eq "kubernetes" -or $Platform -eq "hybrid") {
                Deploy-GPUDevicePlugin
                Deploy-GPUPolicies
                Deploy-GPUStorage
                Deploy-GPUWorkloads
                Verify-GPUScheduling
            }
            Write-Log "✅ GPU workload scheduling deployment completed successfully!" -Level "SUCCESS"
        }
        "start" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Set-DockerEnvironment
                Initialize-DockerDirectories
                Start-DockerServices
            }
            Write-Log "✅ Services started successfully!" -Level "SUCCESS"
        }
        "stop" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Stop-DockerServices
            }
            Write-Log "✅ Services stopped successfully!" -Level "SUCCESS"
        }
        "restart" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Stop-DockerServices
                Start-Sleep -Seconds 5
                Set-DockerEnvironment
                Start-DockerServices
            }
            Write-Log "✅ Services restarted successfully!" -Level "SUCCESS"
        }
        "status" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Test-DockerServices
            }
            if ($Platform -eq "kubernetes" -or $Platform -eq "hybrid") {
                Verify-GPUScheduling
            }
            Write-Log "✅ Status check completed!" -Level "SUCCESS"
        }
        "logs" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Write-Log "Showing Docker service logs..." -Level "INFO"
                docker compose -f docker-compose.production-hardened.yml logs -f
            }
        }
        "clean" {
            if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
                Write-Log "Cleaning up Docker resources..." -Level "INFO"
                docker compose -f docker-compose.production-hardened.yml down -v --remove-orphans
                $images = docker images --filter "reference=gameforge*" -q
                if ($images) {
                    docker rmi $images -f
                }
                docker builder prune -f
            }
            Write-Log "✅ Cleanup completed!" -Level "SUCCESS"
        }
        "k8s-deploy" {
            Deploy-GPUDevicePlugin
            Deploy-GPUPolicies
            Deploy-GPUStorage
            Deploy-GPUWorkloads
            Verify-GPUScheduling
            Write-Log "✅ Kubernetes GPU workload scheduling deployment completed successfully!" -Level "SUCCESS"
        }
        "remove" {
            Remove-GPUWorkloads
            Write-Log "✅ GPU workload scheduling removed successfully!" -Level "SUCCESS"
        }
        "verify" {
            Verify-GPUScheduling
            Write-Log "✅ GPU workload scheduling verification completed!" -Level "SUCCESS"
        }
        "help" {
            Show-Help
        }
        default {
            Write-Log "Invalid action: $Action" -Level "ERROR"
            Show-Help
            exit 1
        }
    }
}
catch {
    Write-Log "❌ Deployment failed: $($_.Exception.Message)" -Level "ERROR"
    exit 1
}

Write-Log "🎉 GPU workload scheduling is ready!" -Level "SUCCESS"

if ($Platform -eq "docker" -or $Platform -eq "hybrid") {
    if ($Action -eq "deploy" -or $Action -eq "start") {
        Write-Log "Next steps for Docker deployment:" -Level "INFO"
        Write-Log "  📊 Web Interface: http://localhost:8080" -Level "INFO"
        Write-Log "  🔧 GPU Inference API: http://localhost:8081" -Level "INFO"
        Write-Log "  🏋️ GPU Training API: http://localhost:8082" -Level "INFO"
        Write-Log "  📈 Grafana Dashboard: http://localhost:3000" -Level "INFO"
        Write-Log "  📊 Prometheus Metrics: http://localhost:9090" -Level "INFO"
        Write-Log "  " -Level "INFO"
        Write-Log "  🔍 Check status: .\deploy-gpu-workloads.ps1 -Action status -Platform docker" -Level "INFO"
        Write-Log "  📋 View logs: .\deploy-gpu-workloads.ps1 -Action logs -Platform docker" -Level "INFO"
    }
}

if ($Platform -eq "kubernetes" -or $Platform -eq "hybrid") {
    Write-Log "Next steps for Kubernetes deployment:" -Level "INFO"
    Write-Log "  1. Label your GPU nodes: kubectl label nodes <node-name> accelerator=nvidia" -Level "INFO"
    Write-Log "  2. Verify device plugin: kubectl get daemonset nvidia-device-plugin-daemonset -n kube-system" -Level "INFO"
    Write-Log "  3. Check GPU resources: kubectl describe nodes | grep -A 5 'Allocatable:'" -Level "INFO"
    Write-Log "  4. Monitor workloads: kubectl get pods -n $Namespace -l gpu-enabled=true" -Level "INFO"
}
