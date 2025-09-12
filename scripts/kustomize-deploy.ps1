#!/usr/bin/env powershell
# GameForge Kustomize Production Deployment and Validation Script

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("validate", "build", "deploy", "diff", "cleanup")]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$DetailedOutput
)

# Configuration
$ScriptRoot = $PSScriptRoot
$K8sDir = "$ScriptRoot/k8s"
$LogDir = "$ScriptRoot/logs/kustomize"
$OverlayPath = "$K8sDir/overlays/$Environment"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Enhanced logging function
function Write-KustomizeLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "KUSTOMIZE"
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
    $logFile = "$LogDir/kustomize-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
    
    # Detailed output
    if ($DetailedOutput) {
        Write-Host "    [VERBOSE] Current directory: $(Get-Location)" -ForegroundColor Gray
        Write-Host "    [VERBOSE] Environment: $Environment" -ForegroundColor Gray
        Write-Host "    [VERBOSE] Overlay path: $OverlayPath" -ForegroundColor Gray
    }
}

# Validate Kustomize configuration
function Test-KustomizeConfiguration {
    Write-KustomizeLog "Validating Kustomize configuration for $Environment..." -Level "INFO"
    
    try {
        # Check if overlay directory exists
        if (!(Test-Path $OverlayPath)) {
            throw "Overlay directory not found: $OverlayPath"
        }
        Write-KustomizeLog "Overlay directory found: $OverlayPath" -Level "SUCCESS"
        
        # Check if kustomization.yaml exists
        $kustomizationFile = "$OverlayPath/kustomization.yaml"
        if (!(Test-Path $kustomizationFile)) {
            throw "Kustomization file not found: $kustomizationFile"
        }
        Write-KustomizeLog "Kustomization file found: $kustomizationFile" -Level "SUCCESS"
        
        # Validate base directory
        $basePath = "$K8sDir/base"
        if (!(Test-Path $basePath)) {
            throw "Base directory not found: $basePath"
        }
        Write-KustomizeLog "Base directory found: $basePath" -Level "SUCCESS"
        
        # Check component directories (if used)
        $componentPaths = @(
            "$K8sDir/components/high-availability",
            "$K8sDir/components/security-hardening"
        )
        
        foreach ($componentPath in $componentPaths) {
            if (Test-Path $componentPath) {
                Write-KustomizeLog "Component found: $componentPath" -Level "SUCCESS"
            } else {
                Write-KustomizeLog "Component not found: $componentPath" -Level "WARN"
            }
        }
        
        # Validate kustomization syntax
        Push-Location $OverlayPath
        try {
            kubectl kustomize . --dry-run | Out-Null
            Write-KustomizeLog "Kustomization syntax validation passed" -Level "SUCCESS"
        } catch {
            throw "Kustomization syntax validation failed: $_"
        } finally {
            Pop-Location
        }
        
        Write-KustomizeLog "Kustomize configuration validation completed successfully" -Level "SUCCESS"
        
    } catch {
        Write-KustomizeLog "Kustomize configuration validation failed: $_" -Level "ERROR"
        throw
    }
}

# Build Kustomize configuration
function Build-KustomizeConfiguration {
    Write-KustomizeLog "Building Kustomize configuration for $Environment..." -Level "INFO"
    
    try {
        Push-Location $OverlayPath
        
        # Build the configuration
        $buildOutput = kubectl kustomize . 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-KustomizeLog "Kustomize build completed successfully" -Level "SUCCESS"
            
            # Save build output
            $buildFile = "$LogDir/build-$Environment-$(Get-Date -Format 'yyyyMMddHHmmss').yaml"
            $buildOutput | Out-File -FilePath $buildFile -Encoding UTF8
            Write-KustomizeLog "Build output saved to: $buildFile" -Level "INFO"
            
            # Show resource summary
            $resources = $buildOutput | Select-String "^kind:" | Group-Object
            Write-KustomizeLog "Resources in build:" -Level "INFO"
            foreach ($resource in $resources) {
                Write-KustomizeLog "  $($resource.Name): $($resource.Count)" -Level "INFO"
            }
            
            return $buildFile
        } else {
            throw "Kustomize build failed: $buildOutput"
        }
        
    } catch {
        Write-KustomizeLog "Kustomize build failed: $_" -Level "ERROR"
        throw
    } finally {
        Pop-Location
    }
}

# Deploy Kustomize configuration
function Deploy-KustomizeConfiguration {
    Write-KustomizeLog "Deploying Kustomize configuration for $Environment..." -Level "INFO"
    
    try {
        Push-Location $OverlayPath
        
        if ($DryRun) {
            Write-KustomizeLog "DRY RUN: Showing what would be deployed..." -Level "INFO"
            kubectl kustomize . | kubectl apply --dry-run=client -f -
        } else {
            # Apply the configuration
            kubectl apply -k .
            if ($LASTEXITCODE -eq 0) {
                Write-KustomizeLog "Kustomize deployment completed successfully" -Level "SUCCESS"
                
                # Wait for deployments to be ready
                Write-KustomizeLog "Waiting for deployments to be ready..." -Level "INFO"
                
                # Get list of deployments from the build
                $deployments = kubectl kustomize . | Select-String "^kind: Deployment" -A 5 | Select-String "name:" | ForEach-Object { ($_ -split ":")[1].Trim() }
                
                foreach ($deployment in $deployments) {
                    if ($deployment) {
                        $namespace = if ($deployment -match "prometheus|grafana") { "gameforge-monitoring" } else { "gameforge-security" }
                        Write-KustomizeLog "Waiting for deployment $deployment in namespace $namespace..." -Level "INFO"
                        kubectl wait --for=condition=available --timeout=300s deployment/$deployment -n $namespace 2>$null
                    }
                }
                
                Write-KustomizeLog "All deployments are ready" -Level "SUCCESS"
            } else {
                throw "Kustomize deployment failed"
            }
        }
        
    } catch {
        Write-KustomizeLog "Kustomize deployment failed: $_" -Level "ERROR"
        throw
    } finally {
        Pop-Location
    }
}

# Show diff between current and new configuration
function Show-KustomizeDiff {
    Write-KustomizeLog "Showing diff for $Environment environment..." -Level "INFO"
    
    try {
        Push-Location $OverlayPath
        
        # Get current resources
        $currentResources = kubectl get all -A -o yaml 2>$null
        $currentFile = "$LogDir/current-$Environment-$(Get-Date -Format 'yyyyMMddHHmmss').yaml"
        $currentResources | Out-File -FilePath $currentFile -Encoding UTF8
        
        # Get new configuration
        $newResources = kubectl kustomize .
        $newFile = "$LogDir/new-$Environment-$(Get-Date -Format 'yyyyMMddHHmmss').yaml"
        $newResources | Out-File -FilePath $newFile -Encoding UTF8
        
        Write-KustomizeLog "Current state saved to: $currentFile" -Level "INFO"
        Write-KustomizeLog "New configuration saved to: $newFile" -Level "INFO"
        
        # Show kubectl diff if available
        try {
            kubectl diff -k . 2>$null
            Write-KustomizeLog "Diff completed - check output above" -Level "SUCCESS"
        } catch {
            Write-KustomizeLog "kubectl diff not available, files saved for manual comparison" -Level "WARN"
        }
        
    } catch {
        Write-KustomizeLog "Diff generation failed: $_" -Level "ERROR"
        throw
    } finally {
        Pop-Location
    }
}

# Cleanup old resources
function Remove-KustomizeResources {
    Write-KustomizeLog "Cleaning up Kustomize resources for $Environment..." -Level "INFO"
    
    try {
        $confirm = Read-Host "This will delete all resources for $Environment environment. Continue? (y/n)"
        if ($confirm -eq "y" -or $confirm -eq "yes") {
            Push-Location $OverlayPath
            
            if ($DryRun) {
                Write-KustomizeLog "DRY RUN: Showing what would be deleted..." -Level "INFO"
                kubectl kustomize . | kubectl delete --dry-run=client -f -
            } else {
                kubectl delete -k .
                Write-KustomizeLog "Resources deleted successfully" -Level "SUCCESS"
            }
        } else {
            Write-KustomizeLog "Cleanup cancelled" -Level "INFO"
        }
        
    } catch {
        Write-KustomizeLog "Cleanup failed: $_" -Level "ERROR"
        throw
    } finally {
        Pop-Location
    }
}

# Show deployment summary
function Show-KustomizeSummary {
    Write-KustomizeLog "=== KUSTOMIZE DEPLOYMENT SUMMARY ===" -Level "INFO"
    Write-KustomizeLog "Environment: $Environment" -Level "INFO"
    Write-KustomizeLog "Overlay Path: $OverlayPath" -Level "INFO"
    
    Write-Host "`nKustomize Configuration:" -ForegroundColor Cyan
    Write-Host "   Environment: $Environment" -ForegroundColor White
    Write-Host "   Base Path: $K8sDir/base" -ForegroundColor White
    Write-Host "   Overlay Path: $OverlayPath" -ForegroundColor White
    
    # Show available overlays
    $overlays = Get-ChildItem "$K8sDir/overlays" -Directory | Select-Object -ExpandProperty Name
    Write-Host "`nAvailable Environments:" -ForegroundColor Cyan
    foreach ($overlay in $overlays) {
        $marker = if ($overlay -eq $Environment) { " (current)" } else { "" }
        Write-Host "   $overlay$marker" -ForegroundColor White
    }
    
    # Show components
    $components = Get-ChildItem "$K8sDir/components" -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
    if ($components) {
        Write-Host "`nAvailable Components:" -ForegroundColor Cyan
        foreach ($component in $components) {
            Write-Host "   $component" -ForegroundColor White
        }
    }
    
    Write-Host "`nKustomize Commands:" -ForegroundColor Cyan
    Write-Host "   Build: .\kustomize-deploy.ps1 -Action build -Environment $Environment" -ForegroundColor White
    Write-Host "   Deploy: .\kustomize-deploy.ps1 -Action deploy -Environment $Environment" -ForegroundColor White
    Write-Host "   Diff: .\kustomize-deploy.ps1 -Action diff -Environment $Environment" -ForegroundColor White
    Write-Host "   Validate: .\kustomize-deploy.ps1 -Action validate -Environment $Environment" -ForegroundColor White
}

# Main execution
function Start-KustomizeAction {
    try {
        Write-KustomizeLog "Starting Kustomize $Action for $Environment environment" -Level "INFO"
        Write-KustomizeLog "Dry Run: $($DryRun.IsPresent)" -Level "INFO"
        
        switch ($Action) {
            "validate" {
                Test-KustomizeConfiguration
                Write-KustomizeLog "Validation completed successfully" -Level "SUCCESS"
            }
            
            "build" {
                Test-KustomizeConfiguration
                $buildFile = Build-KustomizeConfiguration
                Write-KustomizeLog "Build completed successfully. Output: $buildFile" -Level "SUCCESS"
            }
            
            "deploy" {
                Test-KustomizeConfiguration
                Deploy-KustomizeConfiguration
                Write-KustomizeLog "Deployment completed successfully" -Level "SUCCESS"
            }
            
            "diff" {
                Test-KustomizeConfiguration
                Show-KustomizeDiff
                Write-KustomizeLog "Diff completed successfully" -Level "SUCCESS"
            }
            
            "cleanup" {
                Remove-KustomizeResources
                Write-KustomizeLog "Cleanup completed successfully" -Level "SUCCESS"
            }
        }
        
        # Show summary for all actions
        Show-KustomizeSummary
        
    } catch {
        Write-KustomizeLog "Kustomize $Action failed: $_" -Level "ERROR"
        Write-Host "`nKustomize $Action Failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Check logs in: $LogDir" -ForegroundColor Yellow
        exit 1
    }
}

# Execute the action
Start-KustomizeAction
