Write-Host "GameForge Security Dashboard Access" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3001/api/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "Security Dashboard is running" -ForegroundColor Green
} catch {
    Write-Host "Starting security dashboard..." -ForegroundColor Yellow
    docker-compose -f docker-compose.production-hardened.yml up -d security-dashboard
    Start-Sleep -Seconds 15
}

Write-Host ""
Write-Host "Dashboard Access:" -ForegroundColor Cyan
Write-Host "URL: http://localhost:3001" -ForegroundColor Yellow  
Write-Host "Username: admin" -ForegroundColor White

if (Test-Path ".env.security") {
    $envContent = Get-Content ".env.security"
    $grafanaPassword = ($envContent | Where-Object { $_ -match "^GRAFANA_ADMIN_PASSWORD=(.+)" }) -replace "GRAFANA_ADMIN_PASSWORD=", ""
    if ($grafanaPassword) {
        Write-Host "Password: $grafanaPassword" -ForegroundColor White
    }
}

$openBrowser = Read-Host "Open dashboard in browser? (y/N)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    Start-Process "http://localhost:3001"
}
