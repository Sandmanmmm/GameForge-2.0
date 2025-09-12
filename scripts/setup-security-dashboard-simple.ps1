# GameForge Security Dashboard Setup and Configuration
# ==================================================

Write-Host "GameForge Security Dashboard Setup" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Create Grafana dashboards directory structure
$dashboardsDir = "monitoring/grafana/dashboards"
$provisioningDir = "monitoring/grafana/provisioning"
$datasourcesDir = "$provisioningDir/datasources"

Write-Host "Creating dashboard directories..." -ForegroundColor Yellow

foreach ($dir in @($dashboardsDir, $datasourcesDir, "$provisioningDir/dashboards")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Green
    }
}

# Create basic Grafana configuration files
Write-Host "Creating Grafana configuration files..." -ForegroundColor Yellow

# Create a simple datasources configuration
$datasourcesYaml = @'
apiVersion: 1
datasources:
  - name: Security-Prometheus
    type: prometheus
    url: http://security-metrics:9091
    isDefault: true
  - name: Elasticsearch-Security  
    type: elasticsearch
    url: http://elasticsearch:9200
    database: security-logs-*
'@

$datasourcesYaml | Out-File -FilePath "$datasourcesDir/security-datasources.yml" -Encoding UTF8

# Create dashboard provisioning config
$dashboardProvision = @'
apiVersion: 1
providers:
  - name: security-dashboards
    orgId: 1
    folder: Security
    type: file
    options:
      path: /var/lib/grafana/dashboards/security
'@

$dashboardProvision | Out-File -FilePath "$provisioningDir/dashboards/security-dashboards.yml" -Encoding UTF8

# Create a basic security dashboard JSON
$securityDashboard = @'
{
  "dashboard": {
    "title": "GameForge Security Overview",
    "panels": [
      {
        "title": "Vulnerability Scan Results",
        "type": "stat",
        "targets": [{"expr": "trivy_vulnerabilities_total"}]
      },
      {
        "title": "Image Signing Activity", 
        "type": "graph",
        "targets": [{"expr": "cosign_signatures_total"}]
      }
    ]
  }
}
'@

$securityDashboard | Out-File -FilePath "$dashboardsDir/security-overview.json" -Encoding UTF8

# Create access script
$accessScript = @'
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
'@

$accessScript | Out-File -FilePath "access-security-dashboard.ps1" -Encoding UTF8

Write-Host ""
Write-Host "Security Dashboard Setup Complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created Files:" -ForegroundColor Cyan
Write-Host "* $datasourcesDir/security-datasources.yml" -ForegroundColor White
Write-Host "* $provisioningDir/dashboards/security-dashboards.yml" -ForegroundColor White  
Write-Host "* $dashboardsDir/security-overview.json" -ForegroundColor White
Write-Host "* access-security-dashboard.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Start security dashboard: docker-compose up -d security-dashboard" -ForegroundColor White
Write-Host "2. Access dashboard: .\access-security-dashboard.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Access URL: http://localhost:3001" -ForegroundColor Green
