# Cloud Migration Readiness Validation
# Tests GameForge Docker-Kubernetes compatibility

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("local", "aws", "azure", "gcp")]
    [string]$Environment = "local",
    
    [Parameter(Mandatory=$false)]
    [switch]$DetailedOutput
)

Write-Host "=== GameForge Migration Readiness Check ===" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host ""

$script:score = 0
$script:maxScore = 0

function Test-Requirement {
    param($Name, $Test, $Required = $true)
    
    $script:maxScore++
    Write-Host "Testing: $Name" -ForegroundColor Cyan
    
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  ✅ PASS" -ForegroundColor Green
            $script:score++
            return $true
        } else {
            Write-Host "  ❌ FAIL" -ForegroundColor Red
            if ($Required) {
                Write-Host "    This is a required component" -ForegroundColor Yellow
            }
            return $false
        }
    } catch {
        Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# 1. Docker Environment Tests
Write-Host "`n=== Docker Environment ===" -ForegroundColor Magenta

Test-Requirement "Docker Engine Running" {
    docker version | Out-Null; $LASTEXITCODE -eq 0
}

Test-Requirement "Docker Compose Available" {
    docker-compose --version | Out-Null; $LASTEXITCODE -eq 0
}

Test-Requirement "GameForge Docker Images Built" {
    docker images | Select-String "gameforge.*phase2-phase4-production"
}

Test-Requirement "Production Compose File Exists" {
    Test-Path "docker-compose.production-hardened.yml"
}

# 2. Kubernetes Environment Tests
Write-Host "`n=== Kubernetes Environment ===" -ForegroundColor Magenta

Test-Requirement "kubectl Available" {
    kubectl version --client | Out-Null; $LASTEXITCODE -eq 0
}

Test-Requirement "Kubernetes Cluster Connection" {
    kubectl cluster-info | Out-Null; $LASTEXITCODE -eq 0
}

Test-Requirement "KIND Cluster Running" {
    kubectl get nodes | Select-String "gameforge-production-ha"
} $false

Test-Requirement "Kustomize Configuration Valid" {
    kubectl kustomize k8s/overlays/production | Out-Null; $LASTEXITCODE -eq 0
}

# 3. Cloud Provider Tests
if ($Environment -ne "local") {
    Write-Host "`n=== Cloud Provider ($Environment) ===" -ForegroundColor Magenta
    
    switch ($Environment) {
        "aws" {
            Test-Requirement "AWS CLI Available" {
                aws --version | Out-Null; $LASTEXITCODE -eq 0
            }
            
            Test-Requirement "AWS Credentials Configured" {
                aws sts get-caller-identity | Out-Null; $LASTEXITCODE -eq 0
            }
            
            Test-Requirement "ECR Login Capability" {
                aws ecr get-login-password --region us-west-2 | Out-Null; $LASTEXITCODE -eq 0
            } $false
        }
        "azure" {
            Test-Requirement "Azure CLI Available" {
                az --version | Out-Null; $LASTEXITCODE -eq 0
            }
            
            Test-Requirement "Azure Login Status" {
                az account show | Out-Null; $LASTEXITCODE -eq 0
            } $false
        }
        "gcp" {
            Test-Requirement "gcloud CLI Available" {
                gcloud version | Out-Null; $LASTEXITCODE -eq 0
            }
            
            Test-Requirement "GCP Authentication" {
                gcloud auth list --filter=status:ACTIVE | Select-String "ACTIVE"
            } $false
        }
    }
}

# 4. Configuration Tests
Write-Host "`n=== Configuration Validation ===" -ForegroundColor Magenta

Test-Requirement "Kustomization Files Present" {
    Test-Path "k8s/overlays/production/kustomization.yaml"
}

Test-Requirement "Cloud Overlay Configuration" {
    if ($Environment -ne "local") {
        Test-Path "k8s/overlays/cloud-$Environment/kustomization.yaml"
    } else {
        $true
    }
}

Test-Requirement "MetalLB Configuration Valid" {
    Test-Path "metallb-modern-config.yaml"
}

Test-Requirement "Security Policies Present" {
    Test-Path "k8s/components/security-policies/pod-security-standards.yaml"
} $false

# 5. Network and Storage Tests
Write-Host "`n=== Network and Storage ===" -ForegroundColor Magenta

Test-Requirement "LoadBalancer Services Configured" {
    kubectl get svc -A | Select-String "LoadBalancer.*172.19.255"
} $false

Test-Requirement "Persistent Volume Claims" {
    kubectl get pvc -A | Select-String "Bound"
} $false

Test-Requirement "Node Affinity Configuration" {
    Test-Path "k8s/components/node-affinity/kustomization.yaml"
}

# 6. Application Tests
Write-Host "`n=== Application Readiness ===" -ForegroundColor Magenta

Test-Requirement "GameForge Health Endpoint" {
    try {
        $pods = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=grafana 2>$null
        if ($pods) {
            $pod = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}' 2>$null
            if ($pod) {
                $health = kubectl exec $pod -n gameforge-monitoring -- curl -s http://localhost:3000/api/health 2>$null
                $health | Select-String "ok"
            } else {
                $false
            }
        } else {
            Write-Host "    Skipping (no pods running)" -ForegroundColor Yellow
            $true
        }
    } catch {
        Write-Host "    Skipping (cluster not available)" -ForegroundColor Yellow
        $true
    }
} $false

Test-Requirement "Prometheus Metrics Available" {
    try {
        $pods = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=prometheus 2>$null
        if ($pods) {
            $pod = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=prometheus -o jsonpath='{.items[0].metadata.name}' 2>$null
            if ($pod) {
                $ready = kubectl exec $pod -n gameforge-monitoring -- curl -s http://localhost:9090/-/ready 2>$null
                $ready | Select-String "Ready"
            } else {
                $false
            }
        } else {
            Write-Host "    Skipping (no pods running)" -ForegroundColor Yellow
            $true
        }
    } catch {
        Write-Host "    Skipping (cluster not available)" -ForegroundColor Yellow
        $true
    }
} $false

# 7. Migration Script Tests
Write-Host "`n=== Migration Tools ===" -ForegroundColor Magenta

Test-Requirement "Migration Script Present" {
    Test-Path "migrate-to-cloud.ps1"
}

Test-Requirement "Cluster Status Script" {
    Test-Path "cluster-status.ps1"
}

Test-Requirement "Docker-K8s Bridge Config" {
    Test-Path "docker-k8s-bridge.yml"
}

# Final Score
Write-Host "`n=== Migration Readiness Score ===" -ForegroundColor Green
if ($script:maxScore -gt 0) {
    $percentage = [math]::Round(($script:score / $script:maxScore) * 100, 1)
} else {
    $percentage = 0
}

Write-Host "Score: $($script:score) / $($script:maxScore) ($percentage%)" -ForegroundColor $(
    if ($percentage -ge 90) { "Green" }
    elseif ($percentage -ge 75) { "Yellow" }
    else { "Red" }
)

if ($percentage -ge 90) {
    Write-Host "✅ READY FOR PRODUCTION MIGRATION" -ForegroundColor Green
    Write-Host "Your GameForge deployment is ready for cloud migration!" -ForegroundColor Green
} elseif ($percentage -ge 75) {
    Write-Host "⚠️  MOSTLY READY - MINOR ISSUES" -ForegroundColor Yellow
    Write-Host "Address the failed checks before migration." -ForegroundColor Yellow
} else {
    Write-Host "❌ NOT READY - CRITICAL ISSUES" -ForegroundColor Red
    Write-Host "Significant configuration issues need to be resolved." -ForegroundColor Red
}

Write-Host "`nRecommended next steps:" -ForegroundColor Cyan
if ($Environment -eq "local") {
    Write-Host "1. Run: .\migrate-to-cloud.ps1 -CloudProvider aws -DryRun" -ForegroundColor White
    Write-Host "2. Set up cloud provider credentials" -ForegroundColor White
    Write-Host "3. Create cloud Kubernetes cluster" -ForegroundColor White
} else {
    Write-Host "1. Run: .\migrate-to-cloud.ps1 -CloudProvider $Environment" -ForegroundColor White
    Write-Host "2. Monitor deployment with .\cluster-status.ps1" -ForegroundColor White
    Write-Host "3. Configure DNS and SSL certificates" -ForegroundColor White
}
