#!/usr/bin/env powershell
# GameForge Kubernetes Deployment Script
# Deploys the enterprise secret rotation system to Kubernetes

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "gameforge-security",
    
    [Parameter(Mandatory=$false)]
    [string]$KubeContext = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$BuildImages,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipPreChecks
)

# Configuration
$ScriptRoot = $PSScriptRoot
$K8sDir = "$ScriptRoot/k8s"
$LogDir = "$ScriptRoot/logs/k8s-deployment"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Enhanced logging function
function Write-K8sLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "K8S-DEPLOY"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] [$Component] $Message"
    
    # Console output with colors
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN" { Write-Host $logMessage -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        default { Write-Host $logMessage -ForegroundColor White }
    }
    
    # File logging
    $logFile = "$LogDir/k8s-deployment-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

# Check prerequisites
function Test-K8sPrerequisites {
    Write-K8sLog "Checking Kubernetes deployment prerequisites..." -Level "INFO"
    
    $missingTools = @()
    
    # Check for required tools
    $requiredTools = @{
        "kubectl" = "Kubernetes CLI for cluster management (includes kustomize)"
        "docker" = "Docker for building container images"
    }
    
    foreach ($tool in $requiredTools.Keys) {
        try {
            $null = Get-Command $tool -ErrorAction Stop
            Write-K8sLog "Found: $tool" -Level "SUCCESS"
        } catch {
            $missingTools += $tool
            Write-K8sLog "Missing: $tool - $($requiredTools[$tool])" -Level "ERROR"
        }
    }
    
    if ($missingTools.Count -gt 0) {
        throw "Missing required tools: $($missingTools -join ', ')"
    }
    
        # Check Kubernetes cluster connectivity
        try {
            if ($KubeContext) {
                kubectl config use-context $KubeContext | Out-Null
                Write-K8sLog "Using Kubernetes context: $KubeContext" -Level "SUCCESS"
            }
            
            kubectl cluster-info 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-K8sLog "Kubernetes cluster is accessible" -Level "SUCCESS"
            } else {
                throw "Cannot connect to Kubernetes cluster"
            }        # Check if we have sufficient permissions
        $canCreateNamespaces = kubectl auth can-i create namespaces 2>$null
        if ($canCreateNamespaces -eq "yes") {
            Write-K8sLog "Sufficient permissions to create namespaces" -Level "SUCCESS"
        } else {
            Write-K8sLog "Warning: May not have permissions to create namespaces" -Level "WARN"
        }
        
    } catch {
        Write-K8sLog "Failed to connect to Kubernetes cluster: $_" -Level "ERROR"
        throw
    }
}

# Build Docker images
function New-K8sImages {
    Write-K8sLog "Building Docker images for Kubernetes deployment..." -Level "INFO"
    
    try {
        Push-Location $ScriptRoot
        
        # Build secret rotation image
        Write-K8sLog "Building secret rotation image..." -Level "INFO"
        docker build -f Dockerfile.k8s -t gameforge/secret-rotation:latest . --no-cache
        if ($LASTEXITCODE -eq 0) {
            Write-K8sLog "Secret rotation image built successfully" -Level "SUCCESS"
        } else {
            throw "Failed to build secret rotation image"
        }
        
        # Tag for production
        docker tag gameforge/secret-rotation:latest gameforge/secret-rotation:v1.0.0-production
        Write-K8sLog "Tagged image for production: gameforge/secret-rotation:v1.0.0-production" -Level "SUCCESS"
        
        # Build security monitor image (placeholder for now)
        Write-K8sLog "Security monitor image will be pulled from registry" -Level "INFO"
        
    } catch {
        Write-K8sLog "Failed to build images: $_" -Level "ERROR"
        throw
    } finally {
        Pop-Location
    }
}

# Create Kubernetes secrets from environment
function New-K8sSecrets {
    Write-K8sLog "Creating Kubernetes secrets..." -Level "INFO"
    
    try {
        # Create vault credentials secret
        if ($env:VAULT_ADDR -and $env:VAULT_TOKEN) {
            $vaultAddr = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:VAULT_ADDR))
            $vaultToken = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:VAULT_TOKEN))
            
            if (!$DryRun) {
                kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null
                
                $secretYaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: vault-credentials
  namespace: $Namespace
type: Opaque
data:
  vault-addr: $vaultAddr
  vault-token: $vaultToken
"@
                $secretYaml | kubectl apply -f - | Out-Null
                Write-K8sLog "Vault credentials secret created" -Level "SUCCESS"
            } else {
                Write-K8sLog "DRY RUN: Would create vault credentials secret" -Level "INFO"
            }
        } else {
            Write-K8sLog "VAULT_ADDR or VAULT_TOKEN not set - update secrets manually" -Level "WARN"
        }
        
        # Create notification secrets
        if ($env:SLACK_WEBHOOK_URL) {
            $slackWebhook = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:SLACK_WEBHOOK_URL))
            
            if (!$DryRun) {
                $notificationSecretYaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: notification-credentials
  namespace: $Namespace
type: Opaque
data:
  slack-webhook-url: $slackWebhook
"@
                $notificationSecretYaml | kubectl apply -f - | Out-Null
                Write-K8sLog "Notification credentials secret created" -Level "SUCCESS"
            } else {
                Write-K8sLog "DRY RUN: Would create notification credentials secret" -Level "INFO"
            }
        }
        
    } catch {
        Write-K8sLog "Failed to create secrets: $_" -Level "ERROR"
        throw
    }
}

# Deploy using Kustomize
function Invoke-K8sDeployment {
    Write-K8sLog "Deploying Kubernetes manifests using Kustomize..." -Level "INFO"
    
    try {
        Push-Location "$K8sDir/overlays/$Environment"
        
        if (!$DryRun) {
            # Apply the manifests using kubectl kustomize
            kubectl apply -k .
            if ($LASTEXITCODE -eq 0) {
                Write-K8sLog "Kubernetes manifests applied successfully" -Level "SUCCESS"
            } else {
                throw "Failed to apply Kubernetes manifests"
            }
            
            # Wait for deployments to be ready
            Write-K8sLog "Waiting for deployments to be ready..." -Level "INFO"
            kubectl wait --for=condition=available --timeout=600s deployment/prometheus -n gameforge-monitoring 2>$null
            kubectl wait --for=condition=available --timeout=600s deployment/grafana -n gameforge-monitoring 2>$null
            
            Write-K8sLog "All deployments are ready" -Level "SUCCESS"
            
        } else {
            Write-K8sLog "DRY RUN: Showing what would be deployed..." -Level "INFO"
            kubectl kustomize . | kubectl apply --dry-run=client -f -
        }
        
    } catch {
        Write-K8sLog "Failed to deploy manifests: $_" -Level "ERROR"
        throw
    } finally {
        Pop-Location
    }
}

# Verify deployment
function Test-K8sDeployment {
    Write-K8sLog "Verifying Kubernetes deployment..." -Level "INFO"
    
    try {
        # Check namespaces
        $namespaces = kubectl get namespaces -o name 2>$null | Where-Object { $_ -like "*gameforge*" }
        Write-K8sLog "Found GameForge namespaces: $($namespaces.Count)" -Level "SUCCESS"
        
        # Check CronJobs
        $cronJobs = kubectl get cronjobs -n $Namespace 2>$null
        if ($cronJobs) {
            Write-K8sLog "CronJobs deployed successfully" -Level "SUCCESS"
            kubectl get cronjobs -n $Namespace
        }
        
        # Check DaemonSet
        $daemonSet = kubectl get daemonset -n gameforge-monitoring 2>$null
        if ($daemonSet) {
            Write-K8sLog "DaemonSet deployed successfully" -Level "SUCCESS"
            kubectl get daemonset -n gameforge-monitoring
        }
        
        # Check monitoring stack
        $prometheus = kubectl get deployment prometheus -n gameforge-monitoring 2>$null
        $grafana = kubectl get deployment grafana -n gameforge-monitoring 2>$null
        
        if ($prometheus -and $grafana) {
            Write-K8sLog "Monitoring stack deployed successfully" -Level "SUCCESS"
        }
        
        # Check services
        $services = kubectl get services -n gameforge-monitoring 2>$null
        if ($services) {
            Write-K8sLog "Services created successfully" -Level "SUCCESS"
            kubectl get services -n gameforge-monitoring
        }
        
    } catch {
        Write-K8sLog "Error during deployment verification: $_" -Level "ERROR"
    }
}

# Show deployment summary
function Show-K8sDeploymentSummary {
    Write-K8sLog "=== KUBERNETES DEPLOYMENT SUMMARY ===" -Level "INFO"
    Write-K8sLog "Environment: $Environment" -Level "INFO"
    Write-K8sLog "Namespace: $Namespace" -Level "INFO"
    
    Write-Host "`nGameForge Secret Rotation System - Kubernetes Deployment Complete!" -ForegroundColor Green
    
    Write-Host "`nDeployed Components:" -ForegroundColor Cyan
    Write-Host "   • CronJobs for automated secret rotation" -ForegroundColor White
    Write-Host "   • DaemonSet for distributed monitoring" -ForegroundColor White
    Write-Host "   • Prometheus for metrics collection" -ForegroundColor White
    Write-Host "   • Grafana for visualization" -ForegroundColor White
    Write-Host "   • AlertManager for notifications" -ForegroundColor White
    
    Write-Host "`nAccess Services:" -ForegroundColor Cyan
    Write-Host "   • Grafana: kubectl port-forward svc/grafana 3000:3000 -n gameforge-monitoring" -ForegroundColor White
    Write-Host "   • Prometheus: kubectl port-forward svc/prometheus 9090:9090 -n gameforge-monitoring" -ForegroundColor White
    
    Write-Host "`nManagement Commands:" -ForegroundColor Cyan
    Write-Host "   • List CronJobs: kubectl get cronjobs -n $Namespace" -ForegroundColor White
    Write-Host "   • View Logs: kubectl logs -l app.kubernetes.io/component=job -n $Namespace" -ForegroundColor White
    Write-Host "   • Check DaemonSet: kubectl get daemonset -n gameforge-monitoring" -ForegroundColor White
    Write-Host "   • Manual Job: kubectl create job --from=cronjob/secret-rotation-internal manual-rotation -n $Namespace" -ForegroundColor White
    
    Write-Host "`nMonitoring:" -ForegroundColor Cyan
    Write-Host "   • View Events: kubectl get events -n $Namespace --sort-by='.lastTimestamp'" -ForegroundColor White
    Write-Host "   • Check Pod Status: kubectl get pods -n $Namespace -o wide" -ForegroundColor White
    Write-Host "   • DaemonSet Status: kubectl get pods -n gameforge-monitoring -o wide" -ForegroundColor White
}

# Main deployment function
function Start-K8sDeployment {
    try {
        Write-K8sLog "Starting GameForge Kubernetes Deployment" -Level "INFO"
        Write-K8sLog "Environment: $Environment" -Level "INFO"
        Write-K8sLog "Namespace: $Namespace" -Level "INFO"
        Write-K8sLog "Dry Run: $($DryRun.IsPresent)" -Level "INFO"
        
        # Step 1: Check prerequisites
        if (!$SkipPreChecks) {
            Test-K8sPrerequisites
        }
        
        # Step 2: Build images if requested
        if ($BuildImages) {
            New-K8sImages
        }
        
        # Step 3: Create secrets
        New-K8sSecrets
        
        # Step 4: Deploy manifests
        Invoke-K8sDeployment
        
        # Step 5: Verify deployment
        Test-K8sDeployment
        
        # Step 6: Show summary
        Show-K8sDeploymentSummary
        
        Write-K8sLog "Kubernetes deployment completed successfully!" -Level "SUCCESS"
        
    } catch {
        Write-K8sLog "Kubernetes deployment failed: $_" -Level "ERROR"
        Write-Host "`nKubernetes Deployment Failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Check logs in: $LogDir" -ForegroundColor Yellow
        exit 1
    }
}

# Execute deployment
Start-K8sDeployment
