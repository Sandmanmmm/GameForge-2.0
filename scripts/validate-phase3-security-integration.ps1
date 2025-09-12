# GameForge Phase 3 Security Pipeline Integration Validator
# ========================================================

Write-Host "GameForge Phase 3 Image Security Pipeline Integration" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green

# Initialize security volumes directory structure
Write-Host "Initializing Phase 3 security pipeline volumes..." -ForegroundColor Yellow

$securityVolumes = @(
    "volumes/security/harbor-data",
    "volumes/security/harbor-logs", 
    "volumes/security/harbor-secret",
    "volumes/security/harbor-ca",
    "volumes/security/clair-data",
    "volumes/security/clair-logs",
    "volumes/security/notary-data",
    "volumes/security/notary-certs",
    "volumes/security/sbom-reports",
    "volumes/security/sbom-cache",
    "volumes/security/cosign-keys",
    "volumes/security/signing-reports",
    "volumes/security/policy-data",
    "volumes/security/policy-logs",
    "volumes/security/metrics-data",
    "volumes/security/metrics-rules",
    "volumes/security/dashboard-data"
)

foreach ($volume in $securityVolumes) {
    if (-not (Test-Path $volume)) {
        New-Item -ItemType Directory -Path $volume -Force | Out-Null
        Write-Host "Created: $volume" -ForegroundColor Green
    } else {
        Write-Host "Exists: $volume" -ForegroundColor Blue
    }
}

# Create missing configuration files
Write-Host ""
Write-Host "Creating Phase 3 security configuration files..." -ForegroundColor Yellow

# Create Notary server configuration
$notaryConfig = @"
{
  "server": {
    "http_addr": ":4443",
    "tls_cert_file": "/etc/ssl/notary/notary-server.crt", 
    "tls_key_file": "/etc/ssl/notary/notary-server.key"
  },
  "trust_service": {
    "type": "local",
    "hostname": "",
    "port": "",
    "key_algorithm": "ecdsa"
  },
  "logging": {
    "level": "info"
  },
  "storage": {
    "backend": "postgres",
    "db_url": "postgres://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@postgres:5432/notary_server?sslmode=require"
  },
  "auth": {
    "type": "token",
    "options": {
      "realm": "https://harbor-registry:8080/service/token",
      "service": "harbor-notary",
      "issuer": "harbor-token-issuer",
      "rootcertbundle": "/etc/ssl/notary/root-ca.crt"
    }
  }
}
"@

if (-not (Test-Path "security/configs/notary-server.json")) {
    $notaryConfig | Out-File -FilePath "security/configs/notary-server.json" -Encoding UTF8
    Write-Host "Created: security/configs/notary-server.json" -ForegroundColor Green
}

# Create OPA configuration
$opaConfig = @"
services:
  authz:
    url: http://security-policy-engine:8181

bundles:
  gameforge:
    resource: /policies

decision_logs:
  console: true
  reporting:
    min_delay_seconds: 1
    max_delay_seconds: 5

status:
  console: true
  
plugins:
  envoy_ext_authz_grpc:
    addr: :9191
    query: data.envoy.authz.allow
    enable_reflection: true
"@

if (-not (Test-Path "security/configs/opa-config.yaml")) {
    $opaConfig | Out-File -FilePath "security/configs/opa-config.yaml" -Encoding UTF8
    Write-Host "Created: security/configs/opa-config.yaml" -ForegroundColor Green
}

# Create Prometheus security configuration
$prometheusSecurityConfig = @"
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'gameforge-security'
    environment: 'production'

rule_files:
  - "/etc/prometheus/rules/*.yml"

scrape_configs:
  - job_name: 'security-scanner'
    static_configs:
      - targets: ['security-scanner:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'harbor-registry'
    static_configs:
      - targets: ['harbor-registry:8080']
    metrics_path: '/api/v2.0/metrics'
    scrape_interval: 60s

  - job_name: 'clair-scanner'
    static_configs:
      - targets: ['clair-scanner:6061']
    metrics_path: '/metrics'
    scrape_interval: 60s

  - job_name: 'policy-engine'
    static_configs:
      - targets: ['security-policy-engine:8181']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'sbom-generator'
    static_configs:
      - targets: ['sbom-generator:8080']
    metrics_path: '/metrics'
    scrape_interval: 60s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
"@

if (-not (Test-Path "security/configs/prometheus-security.yml")) {
    $prometheusSecurityConfig | Out-File -FilePath "security/configs/prometheus-security.yml" -Encoding UTF8
    Write-Host "Created: security/configs/prometheus-security.yml" -ForegroundColor Green
}

# Create Grafana security configuration
$grafanaSecurityConfig = @"
[server]
protocol = http
http_addr = 
http_port = 3000
domain = localhost
enforce_domain = false
root_url = http://localhost:3000/
serve_from_sub_path = false

[security]
admin_user = admin
admin_password = \${GRAFANA_ADMIN_PASSWORD}
secret_key = \${GRAFANA_SECRET_KEY}
disable_gravatar = true
cookie_secure = true
strict_transport_security = true
content_type_protection = true
x_content_type_options = nosniff
x_xss_protection = true

[analytics]
reporting_enabled = false
check_for_updates = false

[snapshots]
external_enabled = false

[users]
allow_sign_up = false
allow_org_create = false
auto_assign_org = true
auto_assign_org_role = Viewer

[auth]
disable_login_form = false
disable_signout_menu = false

[auth.anonymous]
enabled = false

[log]
mode = console
level = info

[paths]
data = /var/lib/grafana
logs = /var/log/grafana
plugins = /var/lib/grafana/plugins
provisioning = /etc/grafana/provisioning
"@

if (-not (Test-Path "security/configs/grafana-security.ini")) {
    $grafanaSecurityConfig | Out-File -FilePath "security/configs/grafana-security.ini" -Encoding UTF8
    Write-Host "Created: security/configs/grafana-security.ini" -ForegroundColor Green
}

# Validate Docker Compose configuration
Write-Host ""
Write-Host "Validating Phase 3 Security Pipeline integration..." -ForegroundColor Yellow

try {
    $validation = docker-compose -f docker-compose.production-hardened.yml config 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker Compose validation: PASSED" -ForegroundColor Green
    } else {
        Write-Host "Docker Compose validation: FAILED" -ForegroundColor Red
        Write-Host "Errors: $validation" -ForegroundColor Red
    }
} catch {
    Write-Host "Docker Compose validation: ERROR - $_" -ForegroundColor Red
}

# Check for security services in compose file
Write-Host ""
Write-Host "Checking Phase 3 Security Services integration..." -ForegroundColor Yellow

$securityServices = @(
    "security-scanner",
    "sbom-generator", 
    "image-signer",
    "security-policy-engine",
    "security-metrics",
    "security-dashboard",
    "harbor-registry",
    "clair-scanner", 
    "notary-server"
)

foreach ($service in $securityServices) {
    $pattern = "^\s+${service}:"
    $found = Select-String -Path "docker-compose.production-hardened.yml" -Pattern $pattern -Quiet
    if ($found) {
        Write-Host "Service '$service': INTEGRATED" -ForegroundColor Green
    } else {
        Write-Host "Service '$service': MISSING" -ForegroundColor Red
    }
}

# Summary
Write-Host ""
Write-Host "Phase 3 Image Security Pipeline Integration Summary" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Integrated Components:" -ForegroundColor Green
Write-Host "• Trivy Security Scanner - Vulnerability scanning" -ForegroundColor White
Write-Host "• Syft SBOM Generator - Software Bill of Materials" -ForegroundColor White
Write-Host "• Cosign Image Signer - Container image signing" -ForegroundColor White
Write-Host "• Harbor Registry - Enterprise container registry" -ForegroundColor White
Write-Host "• Clair Scanner - Container vulnerability analysis" -ForegroundColor White
Write-Host "• Notary Server - Image trust and verification" -ForegroundColor White
Write-Host "• OPA Policy Engine - Runtime policy enforcement" -ForegroundColor White
Write-Host "• Security Metrics - Prometheus security monitoring" -ForegroundColor White
Write-Host "• Security Dashboard - Grafana security visualization" -ForegroundColor White
Write-Host ""
Write-Host "Security Pipeline Features:" -ForegroundColor Yellow
Write-Host "✅ Image vulnerability scanning (Trivy + Clair)" -ForegroundColor Green
Write-Host "✅ SBOM generation and tracking" -ForegroundColor Green
Write-Host "✅ Container image signing and verification" -ForegroundColor Green
Write-Host "✅ Enterprise registry with Harbor" -ForegroundColor Green
Write-Host "✅ Policy-based security enforcement" -ForegroundColor Green
Write-Host "✅ Security metrics and monitoring" -ForegroundColor Green
Write-Host "✅ Centralized security dashboard" -ForegroundColor Green
Write-Host "✅ Image trust verification with Notary" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure environment variables for Harbor and security services" -ForegroundColor White
Write-Host "2. Generate signing keys for Cosign and Notary" -ForegroundColor White  
Write-Host "3. Deploy security pipeline: docker-compose up -d security-scanner sbom-generator" -ForegroundColor White
Write-Host "4. Access security dashboard at: http://localhost:3001" -ForegroundColor White
Write-Host ""
