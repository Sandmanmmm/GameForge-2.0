#!/usr/bin/env powershell
# Simple Kustomize Validation Script

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "production"
)

$K8sDir = "$PSScriptRoot/k8s"
$OverlayPath = "$K8sDir/overlays/$Environment"

Write-Host "=== GameForge Kustomize Validation ===" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Overlay Path: $OverlayPath" -ForegroundColor Yellow
Write-Host ""

# Test 1: Check if directories exist
Write-Host "[TEST 1] Checking directory structure..." -ForegroundColor Cyan

if (Test-Path "$K8sDir/base") {
    Write-Host "[PASS] Base directory exists" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Base directory missing" -ForegroundColor Red
    exit 1
}

if (Test-Path $OverlayPath) {
    Write-Host "[PASS] Overlay directory exists: $Environment" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Overlay directory missing: $Environment" -ForegroundColor Red
    exit 1
}

# Test 2: Check kustomization files
Write-Host "`n[TEST 2] Checking kustomization files..." -ForegroundColor Cyan

if (Test-Path "$K8sDir/base/kustomization.yaml") {
    Write-Host "[PASS] Base kustomization.yaml exists" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Base kustomization.yaml missing" -ForegroundColor Red
}

if (Test-Path "$OverlayPath/kustomization.yaml") {
    Write-Host "[PASS] Overlay kustomization.yaml exists" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Overlay kustomization.yaml missing" -ForegroundColor Red
}

# Test 3: Test kustomize build
Write-Host "`n[TEST 3] Testing kustomize build..." -ForegroundColor Cyan

try {
    Push-Location $OverlayPath
    $buildOutput = kubectl kustomize . 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Kustomize build successful" -ForegroundColor Green
        
        # Count resources
        $resourceSeparators = $buildOutput | Select-String "^---"
        $resourceCount = $resourceSeparators.Count + 1  # Add 1 for first resource
        Write-Host "       Resources: $resourceCount" -ForegroundColor Gray
        
        # Show resource types
        $resourceTypes = $buildOutput | Select-String "^kind:" | ForEach-Object { ($_ -split ":")[1].Trim() } | Group-Object | Sort-Object Name
        Write-Host "       Resource Types:" -ForegroundColor Gray
        foreach ($type in $resourceTypes) {
            Write-Host "         $($type.Name): $($type.Count)" -ForegroundColor Gray
        }
        
    } else {
        Write-Host "[FAIL] Kustomize build failed" -ForegroundColor Red
        Write-Host "Error output:" -ForegroundColor Red
        Write-Host $buildOutput -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Kustomize build failed with exception: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# Test 4: Check components
Write-Host "`n[TEST 4] Checking components..." -ForegroundColor Cyan

$componentDir = "$K8sDir/components"
if (Test-Path $componentDir) {
    $components = Get-ChildItem $componentDir -Directory
    foreach ($component in $components) {
        if (Test-Path "$($component.FullName)/kustomization.yaml") {
            Write-Host "[PASS] Component exists: $($component.Name)" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Component missing kustomization: $($component.Name)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[WARN] No components directory found" -ForegroundColor Yellow
}

# Test 5: Dry run validation
Write-Host "`n[TEST 5] Testing deployment dry-run..." -ForegroundColor Cyan

try {
    Push-Location $OverlayPath
    $dryRunOutput = kubectl apply --dry-run=client -k . 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Dry-run deployment successful" -ForegroundColor Green
        
        # Count resources to be applied
        $applyCount = ($dryRunOutput | Select-String "(created|configured|unchanged) \(dry run\)").Count
        Write-Host "       Resources to apply: $applyCount" -ForegroundColor Gray
        
    } else {
        Write-Host "[FAIL] Dry-run deployment failed" -ForegroundColor Red
        Write-Host "Error output:" -ForegroundColor Red
        Write-Host $dryRunOutput -ForegroundColor Red
    }
} catch {
    Write-Host "[FAIL] Dry-run failed with exception: $_" -ForegroundColor Red
} finally {
    Pop-Location
}

Write-Host "`n=== Validation Complete ===" -ForegroundColor Cyan

# Summary
Write-Host "`nUsage Examples:" -ForegroundColor Yellow
Write-Host "  Build:  kubectl kustomize k8s/overlays/$Environment" -ForegroundColor White
Write-Host "  Deploy: kubectl apply -k k8s/overlays/$Environment" -ForegroundColor White
Write-Host "  Delete: kubectl delete -k k8s/overlays/$Environment" -ForegroundColor White

Write-Host "`nAlternative Commands:" -ForegroundColor Yellow
Write-Host "  .\kustomize-deploy.ps1 -Action build -Environment $Environment" -ForegroundColor White
Write-Host "  .\kustomize-deploy.ps1 -Action deploy -Environment $Environment" -ForegroundColor White
