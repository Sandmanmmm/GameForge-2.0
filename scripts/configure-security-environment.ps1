# GameForge Phase 3 Security Environment Configuration
# =================================================

Write-Host "GameForge Phase 3 Security Environment Setup" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Create secure environment file for Phase 3 security services
$securityEnvFile = ".env.security"

Write-Host "Creating Phase 3 security environment configuration..." -ForegroundColor Yellow

# Generate secure random passwords and secrets
function New-SecurePassword {
    param([int]$Length = 32)
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    $password = ""
    for ($i = 0; $i -lt $Length; $i++) {
        $password += $chars[(Get-Random -Maximum $chars.Length)]
    }
    return $password
}

function New-SecureKey {
    param([int]$Length = 64)
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $key = ""
    for ($i = 0; $i -lt $Length; $i++) {
        $key += $chars[(Get-Random -Maximum $chars.Length)]
    }
    return $key
}

Write-Host "Generating secure credentials..." -ForegroundColor Green

$harborAdminPassword = New-SecurePassword -Length 24
$harborCoreSecret = New-SecureKey -Length 32
$harborJobserviceSecret = New-SecureKey -Length 32
$grafanaAdminPassword = New-SecurePassword -Length 20
$grafanaSecretKey = New-SecureKey -Length 32
$elasticPassword = New-SecurePassword -Length 20
$logstashPassword = New-SecurePassword -Length 20
$filebeatPassword = New-SecurePassword -Length 20

$securityEnvContent = @"
# ========================================================================
# GameForge Phase 3 Security Pipeline Environment Variables
# ========================================================================
# Generated on: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# WARNING: Keep this file secure and do not commit to version control
# ========================================================================

# Harbor Registry Configuration
HARBOR_ADMIN_PASSWORD=$harborAdminPassword
HARBOR_CORE_SECRET=$harborCoreSecret
HARBOR_JOBSERVICE_SECRET=$harborJobserviceSecret
HARBOR_DB_PASSWORD=${harborAdminPassword}
HARBOR_DOMAIN=harbor.gameforge.local

# Grafana Security Dashboard Configuration
GRAFANA_ADMIN_PASSWORD=$grafanaAdminPassword
GRAFANA_SECRET_KEY=$grafanaSecretKey

# Elastic Stack Security Configuration
ELASTIC_PASSWORD=$elasticPassword
LOGSTASH_SYSTEM_PASSWORD=$logstashPassword
FILEBEAT_SYSTEM_PASSWORD=$filebeatPassword

# Domain Configuration
DOMAIN=gameforge.local

# Backup Configuration
BACKUP_S3_BUCKET=gameforge-backups
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# GitHub Token for Trivy (optional - for rate limiting)
GITHUB_TOKEN=your-github-token

# Security Scanner Configuration
TRIVY_AUTH_URL=
TRIVY_REGISTRY_TOKEN=
CLAIR_SCANNER_LOG_LEVEL=info

# OPA Policy Engine Configuration
OPA_LOG_LEVEL=info
OPA_DECISION_LOGS_ENABLED=true

# Cosign Configuration
COSIGN_PASSWORD=$grafanaSecretKey
COSIGN_REPOSITORY=harbor.gameforge.local/gameforge/signatures

# Notary Configuration
NOTARY_ROOT_PASSPHRASE=$harborCoreSecret
NOTARY_TARGETS_PASSPHRASE=$harborJobserviceSecret

# Monitoring Configuration
PROMETHEUS_RETENTION_TIME=30d
GRAFANA_INSTALL_PLUGINS=grafana-piechart-panel,grafana-worldmap-panel

# ========================================================================
# Security-specific Environment Variables
# ========================================================================

# Enable security features
SECURITY_SCAN_ENABLED=true
VULNERABILITY_SCAN_ENABLED=true
SBOM_GENERATION_ENABLED=true
IMAGE_SIGNING_ENABLED=true
POLICY_ENFORCEMENT_ENABLED=true

# Security thresholds
MAX_CRITICAL_VULNERABILITIES=0
MAX_HIGH_VULNERABILITIES=5
MAX_MEDIUM_VULNERABILITIES=50

# Scan schedules (cron format)
SECURITY_SCAN_SCHEDULE="0 2 * * *"  # Daily at 2 AM
SBOM_GENERATION_SCHEDULE="0 3 * * *"  # Daily at 3 AM
VULNERABILITY_UPDATE_SCHEDULE="0 1 * * *"  # Daily at 1 AM

"@

$securityEnvContent | Out-File -FilePath $securityEnvFile -Encoding UTF8

Write-Host "Security environment file created: $securityEnvFile" -ForegroundColor Green

# Create deployment script
$deployScript = @"
#!/bin/bash
# GameForge Phase 3 Security Pipeline Deployment Script
set -e

echo "🔐 Starting GameForge Phase 3 Security Pipeline Deployment"
echo "=========================================================="

# Load security environment variables
if [ -f .env.security ]; then
    export `$(cat .env.security | grep -v '^#' | xargs)`
    echo "✅ Loaded security environment variables"
else
    echo "❌ .env.security file not found. Run configure-security-environment.ps1 first."
    exit 1
fi

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Create network if it doesn't exist
docker network create security-pipeline 2>/dev/null || echo "Security pipeline network already exists"

echo "🚀 Deploying Phase 3 Security Services..."

# Deploy security services in dependency order
echo "📊 Starting Security Metrics Collector..."
docker-compose -f docker-compose.production-hardened.yml up -d security-metrics

echo "🔍 Starting Security Scanner..."
docker-compose -f docker-compose.production-hardened.yml up -d security-scanner

echo "📋 Starting SBOM Generator..."
docker-compose -f docker-compose.production-hardened.yml up -d sbom-generator

echo "✍️ Starting Image Signer..."
docker-compose -f docker-compose.production-hardened.yml up -d image-signer

echo "📊 Starting Security Dashboard..."
docker-compose -f docker-compose.production-hardened.yml up -d security-dashboard

echo "🏢 Starting Harbor Registry..."
docker-compose -f docker-compose.production-hardened.yml up -d harbor-registry

echo "⏳ Waiting for services to be healthy..."
sleep 30

echo "🔍 Checking service status..."
docker-compose -f docker-compose.production-hardened.yml ps security-scanner security-metrics sbom-generator image-signer security-dashboard

echo ""
echo "✅ Phase 3 Security Pipeline Deployment Complete!"
echo ""
echo "🌐 Access Points:"
echo "  • Security Scanner:  http://localhost:8082"
echo "  • SBOM Generator:    http://localhost:8083"
echo "  • Harbor Registry:   http://localhost:8084"
echo "  • Security Dashboard: http://localhost:3001"
echo ""
echo "📋 Next Steps:"
echo "  1. Generate signing keys: ./generate-cosign-keys.sh"
echo "  2. Configure Harbor: Access http://localhost:8084 (admin/$harborAdminPassword)"
echo "  3. Import security dashboards into Grafana"
echo ""
"@

$deployScript | Out-File -FilePath "deploy-security-pipeline.sh" -Encoding UTF8

Write-Host ""
Write-Host "Created deployment script: deploy-security-pipeline.sh" -ForegroundColor Green

Write-Host ""
Write-Host "Generated Credentials Summary:" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host "Harbor Admin Password: $harborAdminPassword" -ForegroundColor Yellow
Write-Host "Grafana Admin Password: $grafanaAdminPassword" -ForegroundColor Yellow
Write-Host "Elastic Password: $elasticPassword" -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Red
Write-Host "1. Save these credentials securely" -ForegroundColor White
Write-Host "2. Add .env.security to .gitignore" -ForegroundColor White
Write-Host "3. Use environment-specific values for production" -ForegroundColor White
Write-Host ""
Write-Host "Environment file created: $securityEnvFile" -ForegroundColor Green
Write-Host "Deployment script created: deploy-security-pipeline.sh" -ForegroundColor Green
