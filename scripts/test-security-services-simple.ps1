# GameForge Security Services Testing Script
# ==========================================

Write-Host "GameForge Security Services Testing" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

# Define security services to test  
$services = @(
    "trivy-scanner",
    "sbom-generator", 
    "harbor-core",
    "security-metrics",
    "security-dashboard"
)

Write-Host ""
Write-Host "Checking Security Service Status..." -ForegroundColor Yellow

foreach ($service in $services) {
    try {
        $status = docker ps --filter "name=$service" --format "{{.Names}} {{.Status}}"
        if ($status) {
            Write-Host "✅ $service : Running" -ForegroundColor Green
        } else {
            Write-Host "❌ $service : Not running" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ $service : Error checking status" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Security Testing Complete" -ForegroundColor Green
