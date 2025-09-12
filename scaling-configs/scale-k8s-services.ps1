# ========================================================================
# GameForge AI - Kubernetes Scaling Management Script
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "status",
    
    [Parameter(Mandatory=$false)]
    [string]$Service = "all",
    
    [Parameter(Mandatory=$false)]
    [int]$Replicas = 0,
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "gameforge"
)

function Show-K8sStatus {
    Write-Host "=== Kubernetes Deployment Status ===" -ForegroundColor Green
    kubectl get deployments -n $Namespace
    Write-Host ""
    
    Write-Host "=== Pod Status ===" -ForegroundColor Green
    kubectl get pods -n $Namespace -o wide
    Write-Host ""
    
    Write-Host "=== HPA Status ===" -ForegroundColor Green
    kubectl get hpa -n $Namespace
}

function Scale-K8sDeployment {
    param([string]$ServiceName, [int]$ReplicaCount)
    
    $deploymentName = "$ServiceName-deployment"
    Write-Host "Scaling deployment '$deploymentName' to $ReplicaCount replicas..." -ForegroundColor Yellow
    
    kubectl scale deployment $deploymentName --replicas=$ReplicaCount -n $Namespace
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Deployment '$deploymentName' scaled successfully" -ForegroundColor Green
        
        # Wait for rollout to complete
        Write-Host "Waiting for rollout to complete..." -ForegroundColor Yellow
        kubectl rollout status deployment/$deploymentName -n $Namespace
    } else {
        Write-Host "❌ Failed to scale deployment '$deploymentName'" -ForegroundColor Red
    }
}

function Update-HPA-Settings {
    param([string]$ServiceName, [int]$MinReplicas, [int]$MaxReplicas, [int]$CpuThreshold)
    
    $hpaName = "$ServiceName-hpa"
    Write-Host "Updating HPA '$hpaName'..." -ForegroundColor Cyan
    
    # Update HPA with new settings
    kubectl patch hpa $hpaName -n $Namespace --type='merge' -p="{
        \`"spec\`": {
            \`"minReplicas\`": $MinReplicas,
            \`"maxReplicas\`": $MaxReplicas,
            \`"metrics\`": [{
                \`"type\`": \`"Resource\`",
                \`"resource\`": {
                    \`"name\`": \`"cpu\`",
                    \`"target\`": {
                        \`"type\`": \`"Utilization\`",
                        \`"averageUtilization\`": $CpuThreshold
                    }
                }
            }]
        }
    }"
}

function Show-ResourceUsage {
    Write-Host "=== Resource Usage ===" -ForegroundColor Cyan
    kubectl top nodes
    Write-Host ""
    kubectl top pods -n $Namespace --containers
}

function Deploy-All-Configs {
    Write-Host "=== Deploying all Kubernetes configurations ===" -ForegroundColor Green
    
    $configFiles = Get-ChildItem -Path "." -Filter "k8s-*.yaml"
    
    foreach ($file in $configFiles) {
        Write-Host "Applying $($file.Name)..." -ForegroundColor Yellow
        kubectl apply -f $file.FullName
    }
    
    Write-Host "✅ All configurations applied" -ForegroundColor Green
}

# Main execution
switch ($Action.ToLower()) {
    "status" {
        Show-K8sStatus
    }
    "scale" {
        if ($Service -eq "all") {
            Write-Host "Please specify a service name for scaling" -ForegroundColor Red
            exit 1
        }
        if ($Replicas -eq 0) {
            Write-Host "Please specify number of replicas" -ForegroundColor Red
            exit 1
        }
        Scale-K8sDeployment $Service $Replicas
    }
    "deploy" {
        Deploy-All-Configs
    }
    "resources" {
        Show-ResourceUsage
    }
    "hpa" {
        Show-K8sStatus
        Write-Host ""
        Write-Host "=== HPA Events ===" -ForegroundColor Cyan
        kubectl get events -n $Namespace --field-selector involvedObject.kind=HorizontalPodAutoscaler
    }
    default {
        Write-Host "Usage: .\scale-k8s-services.ps1 -Action [status|scale|deploy|resources|hpa] -Service [service-name] -Replicas [count]"
        Write-Host "Examples:"
        Write-Host "  .\scale-k8s-services.ps1 -Action status"
        Write-Host "  .\scale-k8s-services.ps1 -Action scale -Service gameforge-app -Replicas 5"
        Write-Host "  .\scale-k8s-services.ps1 -Action deploy"
        Write-Host "  .\scale-k8s-services.ps1 -Action resources"
    }
}