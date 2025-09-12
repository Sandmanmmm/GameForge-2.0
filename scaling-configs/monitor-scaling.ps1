# ========================================================================
# GameForge AI - Scaling Monitoring and Alert Script
# ========================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Platform = "swarm",  # swarm or kubernetes
    
    [Parameter(Mandatory=$false)]
    [int]$IntervalSeconds = 60,
    
    [Parameter(Mandatory=$false)]
    [string]$LogFile = "scaling-monitor.log"
)

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

function Monitor-SwarmScaling {
    Write-Log "=== Docker Swarm Scaling Monitor ==="
    
    $services = docker service ls --format "{{.Name}}" | Where-Object { $_ -like "gameforge*" }
    
    foreach ($service in $services) {
        $replicas = docker service ls --filter "name=$service" --format "{{.Replicas}}"
        $desired = ($replicas -split "/")[1]
        $actual = ($replicas -split "/")[0]
        
        Write-Log "Service: $service, Desired: $desired, Actual: $actual"
        
        if ($actual -ne $desired) {
            Write-Log "⚠️  WARNING: Service $service has replica mismatch!"
        }
        
        # Check service health
        $unhealthy = docker service ps $service --filter "desired-state=running" --format "{{.CurrentState}}" | Where-Object { $_ -notlike "*Running*" }
        if ($unhealthy) {
            Write-Log "❌ ERROR: Service $service has unhealthy replicas!"
        }
    }
}

function Monitor-K8sScaling {
    Write-Log "=== Kubernetes Scaling Monitor ==="
    
    $deployments = kubectl get deployments -n gameforge -o jsonpath='{.items[*].metadata.name}'
    
    foreach ($deployment in $deployments.Split(' ')) {
        if ([string]::IsNullOrWhiteSpace($deployment)) { continue }
        
        $status = kubectl get deployment $deployment -n gameforge -o jsonpath='{.status.replicas}/{.status.readyReplicas}/{.spec.replicas}'
        $parts = $status.Split('/')
        $total = $parts[0]
        $ready = $parts[1]
        $desired = $parts[2]
        
        Write-Log "Deployment: $deployment, Total: $total, Ready: $ready, Desired: $desired"
        
        if ($ready -ne $desired) {
            Write-Log "⚠️  WARNING: Deployment $deployment not fully ready!"
        }
        
        # Check HPA status
        $hpaName = $deployment.Replace("-deployment", "-hpa")
        $hpaStatus = kubectl get hpa $hpaName -n gameforge -o jsonpath='{.status.currentReplicas}/{.spec.minReplicas}/{.spec.maxReplicas}' 2>$null
        if ($hpaStatus) {
            Write-Log "HPA: $hpaName, Status: $hpaStatus"
        }
    }
}

function Monitor-ResourceUsage {
    if ($Platform -eq "kubernetes") {
        Write-Log "=== Resource Usage Monitoring ==="
        
        # Get node resource usage
        $nodeUsage = kubectl top nodes --no-headers 2>$null
        if ($nodeUsage) {
            Write-Log "Node resource usage:"
            $nodeUsage | ForEach-Object { Write-Log "  $_" }
        }
        
        # Get pod resource usage
        $podUsage = kubectl top pods -n gameforge --no-headers 2>$null
        if ($podUsage) {
            Write-Log "Pod resource usage:"
            $podUsage | ForEach-Object { Write-Log "  $_" }
        }
    }
}

function Check-ScalingAlerts {
    Write-Log "=== Scaling Alert Check ==="
    
    # Define alert thresholds
    $alerts = @()
    
    if ($Platform -eq "swarm") {
        # Check for services with 0 replicas
        $services = docker service ls --format "{{.Name}} {{.Replicas}}"
        foreach ($service in $services) {
            $parts = $service.Split(' ')
            $name = $parts[0]
            $replicas = $parts[1]
            
            if ($replicas -like "0/*") {
                $alerts += "CRITICAL: Service $name has 0 running replicas!"
            }
        }
    } elseif ($Platform -eq "kubernetes") {
        # Check for deployments with 0 ready replicas
        $deployments = kubectl get deployments -n gameforge -o jsonpath='{range .items[*]}{.metadata.name} {.status.readyReplicas}{"
"}{end}'
        foreach ($deployment in $deployments.Split("`n")) {
            if ([string]::IsNullOrWhiteSpace($deployment)) { continue }
            $parts = $deployment.Trim().Split(' ')
            $name = $parts[0]
            $ready = $parts[1]
            
            if ($ready -eq "0" -or [string]::IsNullOrWhiteSpace($ready)) {
                $alerts += "CRITICAL: Deployment $name has 0 ready replicas!"
            }
        }
    }
    
    if ($alerts.Count -gt 0) {
        Write-Log "🚨 SCALING ALERTS DETECTED:"
        foreach ($alert in $alerts) {
            Write-Log "  $alert"
        }
    } else {
        Write-Log "✅ No scaling alerts detected"
    }
}

# Main monitoring loop
Write-Log "Starting GameForge AI Scaling Monitor (Platform: $Platform, Interval: ${IntervalSeconds}s)"

while ($true) {
    try {
        if ($Platform -eq "swarm") {
            Monitor-SwarmScaling
        } elseif ($Platform -eq "kubernetes") {
            Monitor-K8sScaling
            Monitor-ResourceUsage
        }
        
        Check-ScalingAlerts
        Write-Log "--- Monitor cycle completed ---"
        
    } catch {
        Write-Log "❌ ERROR in monitoring cycle: $($_.Exception.Message)"
    }
    
    Start-Sleep -Seconds $IntervalSeconds
}