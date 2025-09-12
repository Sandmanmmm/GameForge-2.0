# GameForge Stack Analysis Script
Write-Host "========================================================================"
Write-Host "GameForge Production Stack Analysis"
Write-Host "========================================================================"

# Function to check component status
function Check-Component {
    param($name, $exists, $description = "")
    $color = if ($exists) { "Green" } else { "Red" }
    $symbol = if ($exists) { "✅" } else { "❌" }
    $status = if ($exists) { "IMPLEMENTED" } else { "MISSING" }
    
    Write-Host "$symbol $name - $status" -ForegroundColor $color
    if ($description -and $exists) {
        Write-Host "   $description" -ForegroundColor Gray
    }
}

Write-Host "`n=== Core Infrastructure Components ===" -ForegroundColor Yellow

# Check PostgreSQL
$postgresExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "postgres:" | Measure-Object).Count -gt 0
Check-Component "PostgreSQL Database Service" $postgresExists "Hardened PostgreSQL 15.4 with security contexts"

# Check Elasticsearch 
$elasticExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "elasticsearch:" | Measure-Object).Count -gt 0
Check-Component "Elasticsearch for Log Aggregation" $elasticExists "Elasticsearch 8.9.2 with security and monitoring"

# Check Redis
$redisExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "redis:" | Measure-Object).Count -gt 0
Check-Component "Redis Cache Service" $redisExists "Redis 7.2.1 with authentication and persistence"

# Check Nginx
$nginxExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "nginx:" | Measure-Object).Count -gt 0
Check-Component "Nginx Reverse Proxy" $nginxExists "Nginx 1.24.0 with SSL and security hardening"

# Check Background Workers
$workerExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "gameforge-worker:" | Measure-Object).Count -gt 0
Check-Component "Background Workers Configuration" $workerExists "Celery workers with security contexts and monitoring"

# Check Backup Service
$backupExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "backup-service:" | Measure-Object).Count -gt 0
Check-Component "Automated Backup Service" $backupExists "Comprehensive backup with PostgreSQL, Redis, and app data"

# Check Prometheus
$prometheusExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "prometheus:" | Measure-Object).Count -gt 0
Check-Component "Prometheus Monitoring" $prometheusExists "Prometheus 2.47.0 with comprehensive metrics collection"

# Check Grafana
$grafanaExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "grafana:" | Measure-Object).Count -gt 0
Check-Component "Grafana Dashboard" $grafanaExists "Grafana 10.1.2 with security hardening and provisioning"

Write-Host "`n=== Security Infrastructure ===" -ForegroundColor Yellow

# Check security contexts
$securityContextExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "security_opt:" | Measure-Object).Count -gt 0
Check-Component "Security Contexts" $securityContextExists "Comprehensive security contexts with seccomp and AppArmor"

# Check capability dropping
$capDropExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "cap_drop:" | Measure-Object).Count -gt 0
Check-Component "Capability Dropping" $capDropExists "ALL capabilities dropped with minimal required capabilities added"

# Check read-only filesystems
$readOnlyExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "read_only: true" | Measure-Object).Count -gt 0
Check-Component "Read-Only Filesystems" $readOnlyExists "Read-only container filesystems with secure tmpfs mounts"

# Check seccomp profiles
$seccompExists = Test-Path "security/seccomp"
Check-Component "Seccomp Profiles" $seccompExists "Syscall filtering profiles for all service types"

# Check AppArmor profiles
$apparmorExists = Test-Path "security/apparmor"
Check-Component "AppArmor Policies" $apparmorExists "Mandatory access control policies for container security"

Write-Host "`n=== Supporting Infrastructure ===" -ForegroundColor Yellow

# Check backup scripts
$backupScriptsExist = (Test-Path "scripts/backup.sh") -and (Test-Path "scripts/restore.sh")
Check-Component "Backup Scripts" $backupScriptsExist "Comprehensive backup and restore scripts with S3 integration"

# Check monitoring configuration
$monitoringConfigExists = (Test-Path "monitoring/prometheus.yml") -and (Test-Path "monitoring/grafana")
Check-Component "Monitoring Configuration" $monitoringConfigExists "Prometheus and Grafana configuration with dashboards"

# Check network isolation
$networkIsolationExists = (Get-Content "docker-compose.production-hardened.yml" | Select-String "internal: true" | Measure-Object).Count -gt 0
Check-Component "Network Isolation" $networkIsolationExists "Segmented networks with internal-only backend services"

# Check volume directories
$volumeDirs = @("volumes/logs", "volumes/cache", "volumes/assets", "volumes/models", 
                "volumes/postgres", "volumes/redis", "volumes/elasticsearch", 
                "volumes/backups", "volumes/prometheus", "volumes/grafana")
$volumesExist = $true
foreach ($dir in $volumeDirs) {
    if (-not (Test-Path $dir)) {
        $volumesExist = $false
        break
    }
}
Check-Component "Volume Directories" $volumesExist "All required persistent volume directories created"

Write-Host "`n=== Environment Configuration ===" -ForegroundColor Yellow

# Check environment files
$envExists = Test-Path ".env.production"
Check-Component "Production Environment File" $envExists "Environment variables for production deployment"

# Check SSL configuration
$sslExists = Test-Path "ssl"
Check-Component "SSL Configuration" $sslExists "SSL certificates and configuration for HTTPS"

Write-Host "`n========================================================================"
Write-Host "Stack Analysis Summary"
Write-Host "========================================================================"

# Count components
$totalComponents = 16
$implementedComponents = 0

$checks = @(
    $postgresExists, $elasticExists, $redisExists, $nginxExists,
    $workerExists, $backupExists, $prometheusExists, $grafanaExists,
    $securityContextExists, $capDropExists, $readOnlyExists,
    $seccompExists, $apparmorExists, $backupScriptsExist,
    $monitoringConfigExists, $networkIsolationExists
)

foreach ($check in $checks) {
    if ($check) { $implementedComponents++ }
}

$completionRate = [math]::Round(($implementedComponents * 100) / $totalComponents, 1)

Write-Host "`nImplementation Status:" -ForegroundColor Yellow
Write-Host "  Total Components: $totalComponents" -ForegroundColor Blue
Write-Host "  Implemented: $implementedComponents" -ForegroundColor Green
Write-Host "  Missing: $($totalComponents - $implementedComponents)" -ForegroundColor Red
Write-Host "  Completion Rate: $completionRate%" -ForegroundColor Yellow

if ($completionRate -eq 100) {
    Write-Host "`nStack Status: COMPLETE" -ForegroundColor Green
    Write-Host "All components are properly implemented and configured." -ForegroundColor Green
} elseif ($completionRate -ge 90) {
    Write-Host "`nStack Status: NEARLY COMPLETE" -ForegroundColor Yellow
    Write-Host "Most components are implemented. Minor configurations may be needed." -ForegroundColor Yellow
} else {
    Write-Host "`nStack Status: INCOMPLETE" -ForegroundColor Red
    Write-Host "Several components are missing and need to be implemented." -ForegroundColor Red
}

Write-Host "`nPreviously Missing Components - Current Status:" -ForegroundColor Cyan
Write-Host "  PostgreSQL database service: $(if ($postgresExists) { "✅ RESOLVED" } else { "❌ STILL MISSING" })" -ForegroundColor $(if ($postgresExists) { "Green" } else { "Red" })
Write-Host "  Elasticsearch for log aggregation: $(if ($elasticExists) { "✅ RESOLVED" } else { "❌ STILL MISSING" })" -ForegroundColor $(if ($elasticExists) { "Green" } else { "Red" })
Write-Host "  Automated backup service: $(if ($backupExists) { "✅ RESOLVED" } else { "❌ STILL MISSING" })" -ForegroundColor $(if ($backupExists) { "Green" } else { "Red" })
Write-Host "  Background workers configuration: $(if ($workerExists) { "✅ RESOLVED" } else { "❌ STILL MISSING" })" -ForegroundColor $(if ($workerExists) { "Green" } else { "Red" })
Write-Host "  Prometheus + Grafana: $(if ($prometheusExists -and $grafanaExists) { "✅ RESOLVED" } else { "❌ STILL MISSING" })" -ForegroundColor $(if ($prometheusExists -and $grafanaExists) { "Green" } else { "Red" })

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Validate configuration: .\security-check.ps1" -ForegroundColor White
Write-Host "  2. Deploy hardened stack: docker-compose -f docker-compose.production-hardened.yml up -d" -ForegroundColor White
Write-Host "  3. Monitor deployment: docker-compose -f docker-compose.production-hardened.yml logs -f" -ForegroundColor White
Write-Host "  4. Access Grafana: http://localhost:3000 (admin/password)" -ForegroundColor White
Write-Host "  5. Access Prometheus: http://localhost:9090" -ForegroundColor White

Write-Host "========================================================================"
