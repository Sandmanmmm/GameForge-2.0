# GameForge Security Services Testing Script
# ==========================================

Write-Host "GameForge Security Services Testing" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

# Define security services to test
$securityServices = @(
    @{
        Name = "Trivy Scanner"
        Container = "trivy-scanner"
        Port = "8082"
        HealthEndpoint = "/health"
        Description = "Vulnerability scanner"
    },
    @{
        Name = "SBOM Generator"
        Container = "sbom-generator" 
        Port = "8083"
        HealthEndpoint = "/health"
        Description = "Software Bill of Materials generator"
    },
    @{
        Name = "Harbor Registry"
        Container = "harbor-core"
        Port = "8084"
        HealthEndpoint = "/api/v2.0/health"
        Description = "Enterprise container registry"
    },
    @{
        Name = "Security Metrics"
        Container = "security-metrics"
        Port = "9091"
        HealthEndpoint = "/metrics"
        Description = "Prometheus metrics collector"
    },
    @{
        Name = "Security Dashboard"
        Container = "security-dashboard"
        Port = "3001"
        HealthEndpoint = "/api/health"
        Description = "Grafana security dashboard"
    }
)

# Function to test individual service
function Test-SecurityService {
    param(
        [string]$ServiceName,
        [string]$ContainerName,
        [string]$Port,
        [string]$HealthEndpoint,
        [string]$Description
    )
    
    Write-Host ""
    Write-Host "Testing $ServiceName..." -ForegroundColor Yellow
    Write-Host "Description: $Description" -ForegroundColor Gray
    
    # Check if container is running
    try {
        $containerStatus = docker ps --filter "name=$ContainerName" --format "table {{.Names}}\t{{.Status}}"
        if ($containerStatus -match $ContainerName) {
            Write-Host "✅ Container '$ContainerName' is running" -ForegroundColor Green
            
            # Test port accessibility
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$Port$HealthEndpoint" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Host "✅ Health endpoint responding (HTTP $($response.StatusCode))" -ForegroundColor Green
                    return $true
                } else {
                    Write-Host "⚠️ Health endpoint returned HTTP $($response.StatusCode)" -ForegroundColor Yellow
                    return $false
                }
            } catch {
                Write-Host "❌ Health endpoint not accessible: $_" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "❌ Container '$ContainerName' is not running" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Error checking container status: $_" -ForegroundColor Red
        return $false
    }
}

# Function to test all services
function Test-AllSecurityServices {
    Write-Host ""
    Write-Host "🧪 Testing All Security Services" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    
    $passedTests = 0
    $totalTests = $securityServices.Count
    
    foreach ($service in $securityServices) {
        $result = Test-SecurityService -ServiceName $service.Name -ContainerName $service.Container -Port $service.Port -HealthEndpoint $service.HealthEndpoint -Description $service.Description
        if ($result) {
            $passedTests++
        }
    }
    
    Write-Host ""
    Write-Host "📊 Test Results Summary:" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    Write-Host "Passed: $passedTests/$totalTests services" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })
    
    if ($passedTests -eq $totalTests) {
        Write-Host "🎉 All security services are healthy!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Some services need attention" -ForegroundColor Yellow
    }
    
    return ($passedTests -eq $totalTests)
}

# Main execution
Write-Host ""
Write-Host "Available Test Options:" -ForegroundColor Cyan
Write-Host "1. Test all services" -ForegroundColor White
Write-Host "2. Test individual service" -ForegroundColor White
Write-Host "3. Quick container status check" -ForegroundColor White

$choice = Read-Host "Select option (1-3)"

switch ($choice) {
    "1" {
        Test-AllSecurityServices
    }
    "2" {
        Write-Host ""
        Write-Host "Available Services:" -ForegroundColor Cyan
        for ($i = 0; $i -lt $securityServices.Count; $i++) {
            Write-Host "$($i + 1). $($securityServices[$i].Name)" -ForegroundColor White
        }
        
        $serviceChoice = Read-Host "Select service (1-$($securityServices.Count))"
        $selectedIndex = [int]$serviceChoice - 1
        
        if ($selectedIndex -ge 0 -and $selectedIndex -lt $securityServices.Count) {
            $service = $securityServices[$selectedIndex]
            Test-SecurityService -ServiceName $service.Name -ContainerName $service.Container -Port $service.Port -HealthEndpoint $service.HealthEndpoint -Description $service.Description
        } else {
            Write-Host "❌ Invalid selection" -ForegroundColor Red
        }
    }
    "3" {
        Write-Host ""
        Write-Host "🔍 Quick Container Status Check" -ForegroundColor Cyan
        Write-Host "===============================" -ForegroundColor Cyan
        
        foreach ($service in $securityServices) {
            try {
                $containerStatus = docker ps --filter "name=$($service.Container)" --format "{{.Names}}\t{{.Status}}"
                if ($containerStatus) {
                    Write-Host "✅ $($service.Name): Running" -ForegroundColor Green
                } else {
                    Write-Host "❌ $($service.Name): Not running" -ForegroundColor Red
                }
            } catch {
                Write-Host "❌ $($service.Name): Error checking status" -ForegroundColor Red
            }
        }
    }
    default {
        Write-Host "❌ Invalid choice. Running full test suite..." -ForegroundColor Yellow
        Test-AllSecurityServices
    }
}

Write-Host ""
Write-Host "🔐 Security Testing Complete" -ForegroundColor Green
