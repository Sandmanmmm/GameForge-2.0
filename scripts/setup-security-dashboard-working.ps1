# GameForge Security Dashboard Setup and Configuration
# ==================================================

Write-Host "GameForge Security Dashboard Setup" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Create Grafana dashboards directory structure
$dashboardsDir = "monitoring/grafana/dashboards"
$provisioningDir = "monitoring/grafana/provisioning"
$datasourcesDir = "$provisioningDir/datasources"

Write-Host "📁 Creating dashboard directories..." -ForegroundColor Yellow

foreach ($dir in @($dashboardsDir, $datasourcesDir, "$provisioningDir/dashboards")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Green
    }
}

# Create Grafana datasources configuration using array approach
$datasourcesLines = @(
    "apiVersion: 1",
    "",
    "datasources:",
    "  - name: Security-Prometheus",
    "    type: prometheus",
    "    access: proxy", 
    "    url: http://security-metrics:9091",
    "    isDefault: true",
    "    editable: true",
    "    uid: security-prometheus",
    "    jsonData:",
    "      httpMethod: POST",
    "      manageAlerts: true",
    "      prometheusType: Prometheus",
    "      prometheusVersion: 2.47.0",
    "      cacheLevel: 'High'",
    "      disableRecordingRules: false",
    "      incrementalQueryOverlapWindow: 10m",
    "",
    "  - name: Elasticsearch-Security", 
    "    type: elasticsearch",
    "    access: proxy",
    "    url: http://elasticsearch:9200",
    "    database: security-logs-*",
    "    editable: true",
    "    uid: elasticsearch-security",
    "    basicAuth: true",
    "    basicAuthUser: elastic",
    "    secureJsonData:",
    "      basicAuthPassword: `${ELASTIC_PASSWORD}",
    "    jsonData:",
    "      interval: Daily",
    "      timeField: '@timestamp'",
    "      esVersion: 8.9.0",
    "      maxConcurrentShardRequests: 5",
    "      logMessageField: message",
    "      logLevelField: level"
)

$datasourcesLines | Out-File -FilePath "$datasourcesDir/security-datasources.yml" -Encoding UTF8

# Create dashboard provisioning configuration
$dashboardProvisioningLines = @(
    "apiVersion: 1",
    "",
    "providers:",
    "  - name: security-dashboards",
    "    orgId: 1",
    "    folder: Security",
    "    type: file", 
    "    disableDeletion: false",
    "    updateIntervalSeconds: 10",
    "    allowUiUpdates: true",
    "    options:",
    "      path: /var/lib/grafana/dashboards/security"
)

$dashboardProvisioningLines | Out-File -FilePath "$provisioningDir/dashboards/security-dashboards.yml" -Encoding UTF8

# Create Security Overview Dashboard JSON
$securityOverviewJson = @'
{
  "dashboard": {
    "id": null,
    "title": "GameForge Security Overview",
    "tags": ["security", "overview", "gameforge"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Vulnerability Scan Results",
        "type": "stat",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "trivy_vulnerabilities_total",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 10},
                {"color": "red", "value": 50}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "SBOM Generation Status",
        "type": "stat", 
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "sbom_generation_total",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "Image Signing Activity",
        "type": "graph",
        "targets": [
          {
            "datasource": "Security-Prometheus", 
            "expr": "rate(cosign_signatures_total[5m])",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s",
    "version": 1
  }
}
'@

$securityOverviewJson | Out-File -FilePath "$dashboardsDir/security-overview.json" -Encoding UTF8

# Create simplified dashboard access script
$accessScriptContent = @'
Write-Host "GameForge Security Dashboard Access" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

Write-Host ""
Write-Host "Dashboard Access Information:" -ForegroundColor Cyan
Write-Host "URL: http://localhost:3001" -ForegroundColor Yellow
Write-Host "Username: admin" -ForegroundColor White

if (Test-Path ".env.security") {
    $envContent = Get-Content ".env.security"
    $grafanaPassword = ($envContent | Where-Object { $_ -match "^GRAFANA_ADMIN_PASSWORD=(.+)" }) -replace "GRAFANA_ADMIN_PASSWORD=", ""
    if ($grafanaPassword) {
        Write-Host "Password: $grafanaPassword" -ForegroundColor White
    } else {
        Write-Host "Password: Check .env.security file" -ForegroundColor Yellow
    }
} else {
    Write-Host "Password: Check environment configuration" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Available Dashboards:" -ForegroundColor Cyan
Write-Host "* Security Overview - Main security metrics and status" -ForegroundColor White
Write-Host "* Vulnerability Management - Detailed vulnerability analysis" -ForegroundColor White 
Write-Host "* Harbor Registry - Container registry monitoring" -ForegroundColor White

$openBrowser = Read-Host "Open dashboard in browser? (y/N)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    try {
        Start-Process "http://localhost:3001"
        Write-Host "Dashboard opened in browser" -ForegroundColor Green
    } catch {
        Write-Host "Could not open browser: $_" -ForegroundColor Red
    }
}
'@

$accessScriptContent | Out-File -FilePath "access-security-dashboard.ps1" -Encoding UTF8

Write-Host ""
Write-Host "✅ Security Dashboard Setup Complete!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Created Files:" -ForegroundColor Cyan
Write-Host "* $datasourcesDir/security-datasources.yml" -ForegroundColor White
Write-Host "* $provisioningDir/dashboards/security-dashboards.yml" -ForegroundColor White
Write-Host "* $dashboardsDir/security-overview.json" -ForegroundColor White
Write-Host "* access-security-dashboard.ps1" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Start security dashboard: docker-compose up -d security-dashboard" -ForegroundColor White
Write-Host "2. Access dashboard: .\access-security-dashboard.ps1" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Access URL: http://localhost:3001" -ForegroundColor Green
