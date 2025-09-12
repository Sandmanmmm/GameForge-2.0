#!/usr/bin/env powershell
# GameForge Kubernetes Management Helper Script

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("deploy", "status", "logs", "rotate", "cleanup", "port-forward", "scale")]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "gameforge-security",
    
    [Parameter(Mandatory=$false)]
    [string]$SecretType = "application",
    
    [Parameter(Mandatory=$false)]
    [int]$Replicas = 1
)

function Write-MgmtLog {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    switch ($Level) {
        "ERROR" { Write-Host "[$timestamp] [ERROR] $Message" -ForegroundColor Red }
        "WARN" { Write-Host "[$timestamp] [WARN] $Message" -ForegroundColor Yellow }
        "SUCCESS" { Write-Host "[$timestamp] [SUCCESS] $Message" -ForegroundColor Green }
        default { Write-Host "[$timestamp] [INFO] $Message" -ForegroundColor Cyan }
    }
}

switch ($Action) {
    "deploy" {
        Write-MgmtLog "Deploying GameForge Secret Rotation to Kubernetes..."
        & "$PSScriptRoot/deploy-k8s.ps1" -Environment production -BuildImages
    }
    
    "status" {
        Write-MgmtLog "Checking GameForge Kubernetes deployment status..."
        
        Write-Host "`n=== NAMESPACES ===" -ForegroundColor Cyan
        kubectl get namespaces | Select-String "gameforge"
        
        Write-Host "`n=== CRONJOBS ===" -ForegroundColor Cyan
        kubectl get cronjobs -n $Namespace -o wide
        
        Write-Host "`n=== DAEMONSET ===" -ForegroundColor Cyan
        kubectl get daemonset -n gameforge-monitoring -o wide
        
        Write-Host "`n=== DEPLOYMENTS ===" -ForegroundColor Cyan
        kubectl get deployments -n gameforge-monitoring -o wide
        
        Write-Host "`n=== SERVICES ===" -ForegroundColor Cyan
        kubectl get services -n gameforge-monitoring -o wide
        
        Write-Host "`n=== PODS ===" -ForegroundColor Cyan
        kubectl get pods -n $Namespace -o wide
        kubectl get pods -n gameforge-monitoring -o wide
    }
    
    "logs" {
        Write-MgmtLog "Fetching logs from GameForge components..."
        
        Write-Host "`n=== RECENT CRONJOB EXECUTIONS ===" -ForegroundColor Cyan
        $jobs = kubectl get jobs -n $Namespace --sort-by='.metadata.creationTimestamp' -o name 2>$null | Select-Object -Last 5
        foreach ($job in $jobs) {
            if ($job) {
                Write-Host "`nLogs for ${job}:" -ForegroundColor Yellow
                kubectl logs $job -n $Namespace --tail=50
            }
        }
        
        Write-Host "`n=== DAEMONSET LOGS ===" -ForegroundColor Cyan
        $pods = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=gameforge-security-monitor -o name 2>$null | Select-Object -First 2
        foreach ($pod in $pods) {
            if ($pod) {
                Write-Host "`nLogs for ${pod}:" -ForegroundColor Yellow
                kubectl logs $pod -n gameforge-monitoring --tail=20 -c security-monitor
            }
        }
        
        Write-Host "`n=== EVENTS ===" -ForegroundColor Cyan
        kubectl get events -n $Namespace --sort-by='.lastTimestamp' | Select-Object -Last 10
    }
    
    "rotate" {
        Write-MgmtLog "Triggering manual secret rotation for $SecretType..."
        
        $jobName = "manual-rotation-$SecretType-$(Get-Date -Format 'yyyyMMddHHmmss')"
        $cronJobName = "secret-rotation-$SecretType"
        
        # Check if CronJob exists
        $cronJob = kubectl get cronjob $cronJobName -n $Namespace 2>$null
        if (!$cronJob) {
            Write-MgmtLog "CronJob $cronJobName not found in namespace $Namespace" -Level "ERROR"
            return
        }
        
        # Create manual job from CronJob
        kubectl create job $jobName --from=cronjob/$cronJobName -n $Namespace
        
        if ($LASTEXITCODE -eq 0) {
            Write-MgmtLog "Manual rotation job created: $jobName" -Level "SUCCESS"
            Write-MgmtLog "Monitor with: kubectl logs job/$jobName -n $Namespace -f" -Level "INFO"
            
            # Wait for job to start and show logs
            Start-Sleep 5
            kubectl logs job/$jobName -n $Namespace -f
        } else {
            Write-MgmtLog "Failed to create manual rotation job" -Level "ERROR"
        }
    }
    
    "cleanup" {
        Write-MgmtLog "Cleaning up GameForge Kubernetes resources..."
        
        $confirm = Read-Host "This will delete all GameForge resources. Continue? (y/n)"
        if ($confirm -eq "y" -or $confirm -eq "yes") {
            # Delete completed jobs (keep last 3)
            $jobs = kubectl get jobs -n $Namespace --sort-by='.metadata.creationTimestamp' -o name 2>$null
            if ($jobs.Count -gt 3) {
                $jobsToDelete = $jobs | Select-Object -SkipLast 3
                foreach ($job in $jobsToDelete) {
                    kubectl delete $job -n $Namespace
                    Write-MgmtLog "Deleted old job: $job" -Level "SUCCESS"
                }
            }
            
            # Clean up failed pods
            kubectl delete pods --field-selector=status.phase=Failed -n $Namespace 2>$null
            kubectl delete pods --field-selector=status.phase=Failed -n gameforge-monitoring 2>$null
            
            Write-MgmtLog "Cleanup completed" -Level "SUCCESS"
        } else {
            Write-MgmtLog "Cleanup cancelled" -Level "INFO"
        }
    }
    
    "port-forward" {
        Write-MgmtLog "Setting up port forwarding for GameForge services..."
        
        Write-Host "`nStarting port forwarding (press Ctrl+C to stop):" -ForegroundColor Cyan
        Write-Host "  • Grafana: http://localhost:3000" -ForegroundColor White
        Write-Host "  • Prometheus: http://localhost:9090" -ForegroundColor White
        
        # Start port forwarding in background
        Start-Job -ScriptBlock { kubectl port-forward svc/grafana 3000:3000 -n gameforge-monitoring } | Out-Null
        Start-Job -ScriptBlock { kubectl port-forward svc/prometheus 9090:9090 -n gameforge-monitoring } | Out-Null
        
        Write-MgmtLog "Port forwarding started. Services are available locally." -Level "SUCCESS"
        Write-MgmtLog "Stop with: Get-Job | Stop-Job; Get-Job | Remove-Job" -Level "INFO"
    }
    
    "scale" {
        Write-MgmtLog "Scaling GameForge deployments..."
        
        # Scale Prometheus
        kubectl scale deployment prometheus --replicas=$Replicas -n gameforge-monitoring
        Write-MgmtLog "Scaled Prometheus to $Replicas replicas" -Level "SUCCESS"
        
        # Scale Grafana (usually should stay at 1)
        if ($Replicas -gt 1) {
            Write-MgmtLog "Warning: Grafana scaling beyond 1 replica may cause issues" -Level "WARN"
        }
        kubectl scale deployment grafana --replicas=1 -n gameforge-monitoring
        
        # Show current status
        kubectl get deployments -n gameforge-monitoring
    }
    
    default {
        Write-MgmtLog "Unknown action: $Action" -Level "ERROR"
        Write-Host "`nAvailable actions:" -ForegroundColor Cyan
        Write-Host "  deploy      - Deploy the entire stack to Kubernetes" -ForegroundColor White
        Write-Host "  status      - Show status of all components" -ForegroundColor White
        Write-Host "  logs        - Fetch logs from components" -ForegroundColor White
        Write-Host "  rotate      - Trigger manual secret rotation" -ForegroundColor White
        Write-Host "  cleanup     - Clean up old jobs and failed pods" -ForegroundColor White
        Write-Host "  port-forward - Forward services to localhost" -ForegroundColor White
        Write-Host "  scale       - Scale deployments" -ForegroundColor White
    }
}
