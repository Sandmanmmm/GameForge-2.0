# ========================================================================
# GameForge AI - Docker Swarm Scaling Management Script
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "status",
    
    [Parameter(Mandatory=$false)]
    [string]$Service = "all",
    
    [Parameter(Mandatory=$false)]
    [int]$Replicas = 0
)

function Show-SwarmStatus {
    Write-Host "=== Docker Swarm Service Status ===" -ForegroundColor Green
    docker service ls
    Write-Host ""
    
    Write-Host "=== Service Replica Details ===" -ForegroundColor Green
    docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"
}

function Scale-SwarmService {
    param([string]$ServiceName, [int]$ReplicaCount)
    
    Write-Host "Scaling service '$ServiceName' to $ReplicaCount replicas..." -ForegroundColor Yellow
    docker service scale "${ServiceName}=$ReplicaCount"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Service '$ServiceName' scaled successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to scale service '$ServiceName'" -ForegroundColor Red
    }
}

function Auto-Scale-Based-On-Load {
    Write-Host "=== Auto-scaling based on resource usage ===" -ForegroundColor Cyan
    
    # Get service metrics (simplified example)
    $services = @("gameforge-app", "gpu-inference", "nginx", "redis")
    
    foreach ($svc in $services) {
        $stats = docker service ps $svc --format "{{.CurrentState}}" | Where-Object { $_ -like "*Running*" } | Measure-Object
        $runningReplicas = $stats.Count
        
        Write-Host "Service: $svc, Running replicas: $runningReplicas"
        
        # Simple scaling logic (extend with actual metrics)
        switch ($svc) {
            "gameforge-app" {
                if ($runningReplicas -lt 2) {
                    Scale-SwarmService $svc 2
                }
            }
            "gpu-inference" {
                if ($runningReplicas -lt 1) {
                    Scale-SwarmService $svc 1
                }
            }
        }
    }
}

# Main execution
switch ($Action.ToLower()) {
    "status" {
        Show-SwarmStatus
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
        Scale-SwarmService $Service $Replicas
    }
    "auto" {
        Auto-Scale-Based-On-Load
    }
    default {
        Write-Host "Usage: .\scale-swarm-services.ps1 -Action [status|scale|auto] -Service [service-name] -Replicas [count]"
        Write-Host "Examples:"
        Write-Host "  .\scale-swarm-services.ps1 -Action status"
        Write-Host "  .\scale-swarm-services.ps1 -Action scale -Service gameforge-app -Replicas 5"
        Write-Host "  .\scale-swarm-services.ps1 -Action auto"
    }
}