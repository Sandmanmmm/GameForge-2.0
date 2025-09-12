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

# Create Grafana datasources configuration
$datasourcesConfig = @"
apiVersion: 1

datasources:
  - name: Security-Prometheus
    type: prometheus
    access: proxy
    url: http://security-metrics:9091
    isDefault: true
    editable: true
    uid: security-prometheus
    jsonData:
      httpMethod: POST
      manageAlerts: true
      prometheusType: Prometheus
      prometheusVersion: 2.47.0
      cacheLevel: 'High'
      disableRecordingRules: false
      incrementalQueryOverlapWindow: 10m

  - name: Elasticsearch-Security
    type: elasticsearch
    access: proxy
    url: http://elasticsearch:9200
    database: "security-logs-*"
    editable: true
    uid: elasticsearch-security
    basicAuth: true
    basicAuthUser: elastic
    secureJsonData:
      basicAuthPassword: ${'$'}{ELASTIC_PASSWORD}
    jsonData:
      interval: Daily
      timeField: "@timestamp"
      esVersion: "8.9.0"
      maxConcurrentShardRequests: 5
      logMessageField: message
      logLevelField: level
"@

$datasourcesConfig | Out-File -FilePath "$datasourcesDir/security-datasources.yml" -Encoding UTF8

# Create dashboard provisioning configuration
$dashboardProvisioningConfig = @"
apiVersion: 1

providers:
  - name: 'security-dashboards'
    orgId: 1
    folder: 'Security'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards/security
"@

$dashboardProvisioningConfig | Out-File -FilePath "$provisioningDir/dashboards/security-dashboards.yml" -Encoding UTF8

# Create Security Overview Dashboard
$securityOverviewDashboard = @"
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
      },
      {
        "id": 4,
        "title": "Security Policy Violations",
        "type": "table",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "opa_policy_violations_total",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 5,
        "title": "Harbor Registry Health",
        "type": "stat",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "harbor_health_status",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 8}
      },
      {
        "id": 6,
        "title": "Security Scan Timeline",
        "type": "graph",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "increase(trivy_scans_total[1h])",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 18, "x": 0, "y": 16}
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
"@

$securityOverviewDashboard | Out-File -FilePath "$dashboardsDir/security-overview.json" -Encoding UTF8

# Create Vulnerability Dashboard
$vulnerabilityDashboard = @"
{
  "dashboard": {
    "id": null,
    "title": "GameForge Vulnerability Management", 
    "tags": ["security", "vulnerabilities", "trivy"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Critical Vulnerabilities",
        "type": "stat",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "trivy_vulnerabilities_total{severity=\"CRITICAL\"}",
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
                {"color": "red", "value": 1}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 4, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "High Vulnerabilities",
        "type": "stat",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "trivy_vulnerabilities_total{severity=\"HIGH\"}",
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
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 10}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 4, "x": 4, "y": 0}
      },
      {
        "id": 3,
        "title": "Vulnerability Trends",
        "type": "graph",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "trivy_vulnerabilities_total",
            "refId": "A",
            "legendFormat": "{{severity}}"
          }
        ],
        "gridPos": {"h": 8, "w": 16, "x": 8, "y": 0}
      },
      {
        "id": 4,
        "title": "Recent Scan Results",
        "type": "table",
        "targets": [
          {
            "datasource": "Elasticsearch-Security",
            "query": "source:trivy AND level:INFO",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 10, "w": 24, "x": 0, "y": 8}
      }
    ],
    "time": {
      "from": "now-24h", 
      "to": "now"
    },
    "refresh": "1m",
    "version": 1
  }
}
"@

$vulnerabilityDashboard | Out-File -FilePath "$dashboardsDir/vulnerability-management.json" -Encoding UTF8

# Create Harbor Registry Dashboard
$harborDashboard = @"
{
  "dashboard": {
    "id": null,
    "title": "GameForge Harbor Registry",
    "tags": ["security", "registry", "harbor"],
    "timezone": "browser", 
    "panels": [
      {
        "id": 1,
        "title": "Registry Health",
        "type": "stat",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "harbor_health{component=\"core\"}",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 6, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Total Projects",
        "type": "stat",
        "targets": [
          {
            "datasource": "Security-Prometheus", 
            "expr": "harbor_project_total",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 6, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "Repository Activity",
        "type": "graph",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "rate(harbor_repository_pull_total[5m])",
            "refId": "A",
            "legendFormat": "Pulls"
          },
          {
            "datasource": "Security-Prometheus",
            "expr": "rate(harbor_repository_push_total[5m])",
            "refId": "B", 
            "legendFormat": "Pushes"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 4,
        "title": "Scan Results Summary",
        "type": "piechart",
        "targets": [
          {
            "datasource": "Security-Prometheus",
            "expr": "harbor_artifact_scanned_total",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 6}
      }
    ],
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "refresh": "30s",
    "version": 1
  }
}
"@

$harborDashboard | Out-File -FilePath "$dashboardsDir/harbor-registry.json" -Encoding UTF8

# Create dashboard access script
$dashboardAccessScript = @'
# GameForge Security Dashboard Access Guide
# ========================================

Write-Host "GameForge Security Dashboard Access" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

# Check if security dashboard is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3001/api/health" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Security Dashboard is running" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Dashboard responded with status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Security Dashboard is not accessible" -ForegroundColor Red
    Write-Host "Starting security dashboard..." -ForegroundColor Yellow
    
    try {
        docker-compose -f docker-compose.production-hardened.yml up -d security-dashboard
        Write-Host "⏳ Waiting for dashboard to start..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
    } catch {
        Write-Host "❌ Failed to start dashboard: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🌐 Dashboard Access Information:" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""
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
Write-Host "📊 Available Dashboards:" -ForegroundColor Cyan
Write-Host "• Security Overview - Main security metrics and status" -ForegroundColor White
Write-Host "• Vulnerability Management - Detailed vulnerability analysis" -ForegroundColor White 
Write-Host "• Harbor Registry - Container registry monitoring" -ForegroundColor White
Write-Host ""

Write-Host "🔧 Dashboard Features:" -ForegroundColor Yellow
Write-Host "• Real-time vulnerability scanning results" -ForegroundColor White
Write-Host "• SBOM generation tracking" -ForegroundColor White
Write-Host "• Image signing activity monitoring" -ForegroundColor White
Write-Host "• Security policy violation alerts" -ForegroundColor White
Write-Host "• Harbor registry health and usage" -ForegroundColor White
Write-Host ""

Write-Host "📱 Quick Actions:" -ForegroundColor Green
Write-Host "1. Open dashboard: Start-Process 'http://localhost:3001'" -ForegroundColor White
Write-Host "2. View logs: docker-compose -f docker-compose.production-hardened.yml logs security-dashboard" -ForegroundColor White
Write-Host "3. Restart dashboard: docker-compose -f docker-compose.production-hardened.yml restart security-dashboard" -ForegroundColor White
Write-Host ""

# Attempt to open dashboard in browser
$openBrowser = Read-Host "Open dashboard in browser? (y/N)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    try {
        Start-Process "http://localhost:3001"
        Write-Host "✅ Dashboard opened in browser" -ForegroundColor Green
    } catch {
        Write-Host "❌ Could not open browser: $_" -ForegroundColor Red
    }
}
'@

$dashboardAccessScript | Out-File -FilePath "access-security-dashboard.ps1" -Encoding UTF8

Write-Host ""
Write-Host "✅ Security Dashboard Setup Complete!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Created Files:" -ForegroundColor Cyan
Write-Host "• $datasourcesDir/security-datasources.yml" -ForegroundColor White
Write-Host "• $provisioningDir/dashboards/security-dashboards.yml" -ForegroundColor White
Write-Host "• $dashboardsDir/security-overview.json" -ForegroundColor White
Write-Host "• $dashboardsDir/vulnerability-management.json" -ForegroundColor White
Write-Host "• $dashboardsDir/harbor-registry.json" -ForegroundColor White
Write-Host "• access-security-dashboard.ps1" -ForegroundColor White
Write-Host ""
Write-Host "📊 Dashboard Features:" -ForegroundColor Yellow
Write-Host "• Security Overview - Main metrics and KPIs" -ForegroundColor White
Write-Host "• Vulnerability Management - Detailed CVE tracking" -ForegroundColor White
Write-Host "• Harbor Registry - Container registry monitoring" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Start security dashboard: docker-compose up -d security-dashboard" -ForegroundColor White
Write-Host "2. Access dashboard: .\access-security-dashboard.ps1" -ForegroundColor White
Write-Host "3. Import additional dashboards as needed" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Access URL: http://localhost:3001" -ForegroundColor Green
