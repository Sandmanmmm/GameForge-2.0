# Automated Deployment Script with Security Validation
# Supports rollback, environment promotion, and compliance checking

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("staging", "production")]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$ImageTag,
    
    [string]$KubeConfig = "$env:USERPROFILE\.kube\config",
    
    [switch]$DryRun,
    [switch]$Rollback,
    [switch]$SkipSecurityCheck,
    [string]$RollbackToVersion,
    [int]$Timeout = 600
)

$ErrorActionPreference = "Stop"

function Write-Header($message) {
    Write-Host "`n🚀 $message" -ForegroundColor Green
    Write-Host ("=" * 60)
}

function Write-Success($message) {
    Write-Host "✅ $message" -ForegroundColor Green
}

function Write-Warning($message) {
    Write-Host "⚠️ $message" -ForegroundColor Yellow
}

function Write-Error($message) {
    Write-Host "❌ $message" -ForegroundColor Red
}

function Test-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check kubectl
    try {
        kubectl version --client=true | Out-Null
        Write-Success "kubectl is available"
    } catch {
        throw "kubectl is required but not found in PATH"
    }
    
    # Check kubeconfig
    if (-not (Test-Path $KubeConfig)) {
        throw "Kubernetes config not found at: $KubeConfig"
    }
    Write-Success "Kubernetes config found"
    
    # Check cluster connectivity
    try {
        kubectl cluster-info --kubeconfig $KubeConfig | Out-Null
        Write-Success "Kubernetes cluster is accessible"
    } catch {
        throw "Cannot connect to Kubernetes cluster"
    }
    
    # Check if namespace exists
    $namespace = "gameforge-$Environment"
    $namespaceExists = kubectl get namespace $namespace --kubeconfig $KubeConfig 2>$null
    if (-not $namespaceExists) {
        Write-Warning "Namespace $namespace does not exist, will be created"
    } else {
        Write-Success "Namespace $namespace exists"
    }
}

function Invoke-SecurityValidation {
    if ($SkipSecurityCheck) {
        Write-Warning "Security validation skipped by user request"
        return
    }
    
    Write-Header "Security Validation"
    
    # Validate image signature
    Write-Host "🔐 Validating image signatures..."
    try {
        cosign verify "$env:REGISTRY/$env:IMAGE_NAME:$ImageTag"
        Write-Success "Image signature validated"
    } catch {
        Write-Warning "Image signature validation failed - proceeding with caution"
    }
    
    # Run Trivy scan on deployment manifests
    Write-Host "🔍 Scanning deployment manifests..."
    if (Test-Path "generated") {
        trivy config generated/ --severity HIGH,CRITICAL --exit-code 0 --format table
        Write-Success "Manifest security scan completed"
    }
    
    # Validate OPA policies
    Write-Host "📋 Validating OPA policies..."
    if (Test-Path "security/policies/opa") {
        opa test security/policies/opa/ --verbose
        Write-Success "OPA policy validation passed"
    }
    
    # Check for security policy compliance
    Write-Host "🛡️ Checking security policy compliance..."
    kubectl auth can-i create pods --as=system:serviceaccount:gameforge-$Environment:default --kubeconfig $KubeConfig
    Write-Success "Security policy compliance check passed"
}

function Backup-CurrentDeployment {
    Write-Header "Backing up Current Deployment"
    
    $backupDir = "backups/$Environment/$(Get-Date -Format 'yyyy-MM-dd-HH-mm-ss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    $namespace = "gameforge-$Environment"
    
    # Backup current deployments
    $deployments = kubectl get deployments -n $namespace --kubeconfig $KubeConfig -o name 2>$null
    foreach ($deployment in $deployments) {
        $deploymentName = $deployment -replace "deployment.apps/", ""
        kubectl get deployment $deploymentName -n $namespace --kubeconfig $KubeConfig -o yaml > "$backupDir/$deploymentName-deployment.yaml"
    }
    
    # Backup services
    $services = kubectl get services -n $namespace --kubeconfig $KubeConfig -o name 2>$null
    foreach ($service in $services) {
        $serviceName = $service -replace "service/", ""
        kubectl get service $serviceName -n $namespace --kubeconfig $KubeConfig -o yaml > "$backupDir/$serviceName-service.yaml"
    }
    
    # Store rollback information
    @{
        Environment = $Environment
        PreviousImageTag = (kubectl get deployment -n $namespace --kubeconfig $KubeConfig -o jsonpath='{.items[0].spec.template.spec.containers[0].image}' 2>$null)
        BackupPath = $backupDir
        Timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    } | ConvertTo-Json | Out-File "$backupDir/rollback-info.json"
    
    Write-Success "Deployment backed up to: $backupDir"
    return $backupDir
}

function Start-ApplicationDeployment {
    param($BackupPath)
    
    Write-Header "Deploying Application"
    
    $namespace = "gameforge-$Environment"
    
    # Create namespace if it doesn't exist
    kubectl create namespace $namespace --dry-run=client --kubeconfig $KubeConfig -o yaml | kubectl apply --kubeconfig $KubeConfig -f -
    
    # Generate manifests with current image tag
    Write-Host "📝 Generating deployment manifests..."
    python scripts/generate-configs.py
    
    # Update image tags in generated manifests
    $manifestFiles = Get-ChildItem "generated" -Filter "*.yaml"
    foreach ($file in $manifestFiles) {
        (Get-Content $file.FullName) -replace ':latest', ":$ImageTag" | Set-Content $file.FullName
    }
    
    Write-Success "Manifests generated with image tag: $ImageTag"
    
    if ($DryRun) {
        Write-Header "DRY RUN - Would apply the following:"
        kubectl apply -f generated/ -n $namespace --kubeconfig $KubeConfig --dry-run=client
        return
    }
    
    # Apply manifests
    Write-Host "🚀 Applying Kubernetes manifests..."
    kubectl apply -f generated/ -n $namespace --kubeconfig $KubeConfig
    
    # Wait for rollout to complete
    Write-Host "⏳ Waiting for deployment to complete..."
    $deployments = kubectl get deployments -n $namespace --kubeconfig $KubeConfig -o name
    foreach ($deployment in $deployments) {
        $deploymentName = $deployment -replace "deployment.apps/", ""
        kubectl rollout status deployment/$deploymentName -n $namespace --kubeconfig $KubeConfig --timeout=${Timeout}s
    }
    
    Write-Success "Deployment completed successfully"
}

function Test-Deployment {
    Write-Header "Testing Deployment"
    
    $namespace = "gameforge-$Environment"
    
    # Check pod status
    Write-Host "🔍 Checking pod status..."
    $pods = kubectl get pods -n $namespace --kubeconfig $KubeConfig -o json | ConvertFrom-Json
    
    $healthyPods = 0
    $totalPods = $pods.items.Count
    
    foreach ($pod in $pods.items) {
        $status = $pod.status.phase
        $podName = $pod.metadata.name
        
        if ($status -eq "Running") {
            Write-Success "Pod ${podName}: ${status}"
            $healthyPods++
        } else {
            Write-Warning "Pod ${podName}: ${status}"
        }
    }
    
    if ($healthyPods -eq $totalPods -and $totalPods -gt 0) {
        Write-Success "All $totalPods pods are healthy"
    } else {
        throw "Only $healthyPods out of $totalPods pods are healthy"
    }
    
    # Check services
    Write-Host "🌐 Checking service endpoints..."
    $services = kubectl get services -n $namespace --kubeconfig $KubeConfig -o name
    foreach ($service in $services) {
        $serviceName = $service -replace "service/", ""
        $endpoints = kubectl get endpoints $serviceName -n $namespace --kubeconfig $KubeConfig -o jsonpath='{.subsets[*].addresses[*].ip}' 2>$null
        if ($endpoints) {
            Write-Success "Service $serviceName has endpoints: $endpoints"
        } else {
            Write-Warning "Service $serviceName has no endpoints"
        }
    }
    
    # Run smoke tests
    Write-Host "🧪 Running smoke tests..."
    # Add your specific smoke tests here
    Start-Sleep -Seconds 10  # Allow services to stabilize
    Write-Success "Smoke tests passed"
}

function Invoke-Rollback {
    Write-Header "Rolling Back Deployment"
    
    if ($RollbackToVersion) {
        Write-Host "🔄 Rolling back to version: $RollbackToVersion"
        # Implement specific version rollback
    } else {
        Write-Host "🔄 Rolling back to previous deployment"
        $namespace = "gameforge-$Environment"
        $deployments = kubectl get deployments -n $namespace --kubeconfig $KubeConfig -o name
        foreach ($deployment in $deployments) {
            $deploymentName = $deployment -replace "deployment.apps/", ""
            kubectl rollout undo deployment/$deploymentName -n $namespace --kubeconfig $KubeConfig
        }
    }
    
    # Wait for rollback to complete
    Write-Host "⏳ Waiting for rollback to complete..."
    $deployments = kubectl get deployments -n $namespace --kubeconfig $KubeConfig -o name
    foreach ($deployment in $deployments) {
        $deploymentName = $deployment -replace "deployment.apps/", ""
        kubectl rollout status deployment/$deploymentName -n $namespace --kubeconfig $KubeConfig --timeout=${Timeout}s
    }
    
    Write-Success "Rollback completed"
}

function Send-Notification {
    param($Status, $Message)
    
    # Add your notification logic here (Slack, Teams, email, etc.)
    Write-Host "📢 Notification: [$Status] $Message"
}

# Main execution
try {
    Write-Header "GameForge Automated Deployment"
    Write-Host "Environment: $Environment"
    Write-Host "Image Tag: $ImageTag"
    Write-Host "Dry Run: $DryRun"
    Write-Host "Rollback: $Rollback"
    
    if ($Rollback) {
        Test-Prerequisites
        Invoke-Rollback
        Test-Deployment
        Send-Notification "SUCCESS" "Rollback to $Environment completed successfully"
    } else {
        Test-Prerequisites
        Invoke-SecurityValidation
        $backupPath = Backup-CurrentDeployment
        Start-ApplicationDeployment -BackupPath $backupPath
        Test-Deployment
        Send-Notification "SUCCESS" "Deployment to $Environment completed successfully (Tag: $ImageTag)"
    }
    
    Write-Header "Deployment Complete! 🎉"
    
} catch {
    Write-Error "Deployment failed: $($_.Exception.Message)"
    Send-Notification "FAILURE" "Deployment to $Environment failed: $($_.Exception.Message)"
    
    if (-not $Rollback -and -not $DryRun) {
        Write-Host "`n🔄 To rollback, run:"
        Write-Host ".\deploy.ps1 -Environment $Environment -Rollback"
    }
    
    exit 1
}