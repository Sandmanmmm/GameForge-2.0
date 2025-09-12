#!/bin/bash
# ========================================================================
# GameForge Production Deployment Validation Script
# Validates complete production environment and infrastructure
# ========================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to log with colors and timestamp
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[${timestamp}] ✓ ${message}${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}[${timestamp}] ⚠ ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ✗ ${message}${NC}"
            ;;
        "HEADER")
            echo -e "${CYAN}[${timestamp}] ${message}${NC}"
            ;;
        *)
            echo -e "${BLUE}[${timestamp}] ${message}${NC}"
            ;;
    esac
}

echo -e "${CYAN}========================================================================${NC}"
echo -e "${CYAN}GameForge Production Deployment Validation${NC}"
echo -e "${CYAN}========================================================================${NC}"

# Validation counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Function to run a check
run_check() {
    local check_name="$1"
    local check_command="$2"
    local required=${3:-true}
    
    ((TOTAL_CHECKS++))
    log "HEADER" "Checking: $check_name"
    
    if eval "$check_command"; then
        ((PASSED_CHECKS++))
        log "INFO" "$check_name: PASSED"
        return 0
    else
        if [ "$required" = "true" ]; then
            ((FAILED_CHECKS++))
            log "ERROR" "$check_name: FAILED"
            return 1
        else
            ((WARNING_CHECKS++))
            log "WARN" "$check_name: WARNING"
            return 0
        fi
    fi
}

# ========================================================================
# Phase 0-6 Infrastructure Validation
# ========================================================================

log "HEADER" "=== Phase 0-6 Infrastructure Validation ==="

# Phase 0: Docker Infrastructure
run_check "Docker Engine" "docker --version >/dev/null 2>&1"
run_check "Docker Compose" "docker-compose --version >/dev/null 2>&1"
run_check "Docker Service Running" "docker info >/dev/null 2>&1"

# Phase 1: SSL/TLS Infrastructure
run_check "SSL Certificate Directory" "[ -d './ssl/certs' ]"
run_check "SSL Private Key Directory" "[ -d './ssl/private' ]"
run_check "Nginx Configuration" "[ -f './nginx/nginx.conf' ]"
run_check "Nginx Site Configuration" "[ -f './nginx/conf.d/gameforge.conf' ]"

# Phase 2: Secrets Management (Vault)
run_check "Vault Docker Compose" "[ -f './docker-compose.vault.yml' ]"
run_check "Vault Configuration" "[ -f './vault/config/vault.hcl' ]" false

# Phase 3: Elasticsearch Infrastructure
run_check "Elasticsearch Docker Compose" "[ -f './docker-compose.elasticsearch.yml' ]"
run_check "Elasticsearch Configuration" "[ -d './elasticsearch/config' ]"

# Phase 4: Security Scanning Infrastructure
run_check "Security Docker Compose" "[ -f './docker-compose.security.yml' ]"

# Phase 5: Audit Logging Infrastructure
run_check "Audit Docker Compose" "[ -f './docker-compose.audit.yml' ]"

# Phase 6: Advanced Monitoring Infrastructure
run_check "GPU Monitoring Docker Compose" "[ -f './docker-compose.gpu-monitoring.yml' ]"
run_check "AlertManager Docker Compose" "[ -f './docker-compose.alertmanager.yml' ]"
run_check "Log Pipeline Docker Compose" "[ -f './docker-compose.log-pipeline.yml' ]"
run_check "Monitoring Configuration Directory" "[ -d './monitoring/configs' ]"
run_check "Monitoring Dashboards" "[ -d './monitoring/dashboards' ]"
run_check "Monitoring Alerting" "[ -d './monitoring/alerting' ]"

# ========================================================================
# Production Files Validation
# ========================================================================

log "HEADER" "=== Production Files Validation ==="

run_check "Production Dockerfile" "[ -f './Dockerfile.production' ]"
run_check "Production Docker Compose" "[ -f './docker-compose.production-secure.yml' ]"
run_check "Production Environment" "[ -f '.env.production' ]"
run_check "Production Setup Script" "[ -f './setup-production.sh' ] && [ -x './setup-production.sh' ]"
run_check "Windows Setup Script" "[ -f './setup-production.ps1' ]"

# ========================================================================
# Backup Infrastructure Validation
# ========================================================================

log "HEADER" "=== Backup Infrastructure Validation ==="

run_check "Backup Directory" "[ -d './backup' ]"
run_check "Backup Dockerfile" "[ -f './backup/Dockerfile.backup' ]"
run_check "Backup Scripts Directory" "[ -d './backup/scripts' ]"
run_check "Backup Main Script" "[ -f './backup/scripts/backup.sh' ] && [ -x './backup/scripts/backup.sh' ]"
run_check "Backup Maintenance Script" "[ -f './backup/scripts/maintenance.sh' ] && [ -x './backup/scripts/maintenance.sh' ]"
run_check "Backup Crontab" "[ -f './backup/crontab' ]"

# ========================================================================
# Application Files Validation
# ========================================================================

log "HEADER" "=== Application Files Validation ==="

run_check "Production Server Script" "[ -f './gameforge_production_server.py' ]"
run_check "RTX4090 Optimized Server" "[ -f './gameforge_rtx4090_server.py' ]"
run_check "Custom SDXL Pipeline" "[ -f './custom_sdxl_pipeline.py' ]"
run_check "Backend GPU Integration" "[ -f './backend_gpu_integration.py' ]"
run_check "Requirements File" "[ -f './requirements.txt' ]"
run_check "Package.json" "[ -f './package.json' ]"

# ========================================================================
# Configuration Files Validation
# ========================================================================

log "HEADER" "=== Configuration Files Validation ==="

run_check "Database Setup SQL" "[ -f './database_setup.sql' ]"
run_check "Redis Configuration" "[ -f './redis/redis.conf' ]"
run_check "Auth Middleware" "[ -f './auth_middleware.py' ]"

# ========================================================================
# Docker Compose Syntax Validation
# ========================================================================

log "HEADER" "=== Docker Compose Syntax Validation ==="

# Main production compose file
if [ -f "docker-compose.production-secure.yml" ]; then
    run_check "Production Compose Syntax" "docker-compose -f docker-compose.production-secure.yml config >/dev/null 2>&1"
fi

# Infrastructure compose files
for compose_file in docker-compose.*.yml; do
    if [ -f "$compose_file" ]; then
        filename=$(basename "$compose_file" .yml)
        run_check "$filename Syntax" "docker-compose -f $compose_file config >/dev/null 2>&1" false
    fi
done

# ========================================================================
# Monitoring Configuration Validation
# ========================================================================

log "HEADER" "=== Monitoring Configuration Validation ==="

# GPU monitoring configurations
if [ -d "monitoring/configs" ]; then
    run_check "GPU Prometheus Config" "[ -f './monitoring/configs/gpu-prometheus.yml' ]"
    run_check "GPU Exporter Config" "[ -f './monitoring/configs/gpu-exporter.yml' ]"
    run_check "Prometheus Rules" "[ -f './monitoring/configs/prometheus-rules.yml' ]"
fi

# Dashboard configurations
if [ -d "monitoring/dashboards" ]; then
    run_check "GPU Dashboard" "[ -f './monitoring/dashboards/gpu-monitoring.json' ]"
    run_check "Game Analytics Dashboard" "[ -f './monitoring/dashboards/game-analytics.json' ]"
    run_check "Business Intelligence Dashboard" "[ -f './monitoring/dashboards/business-intelligence.json' ]"
    run_check "System Overview Dashboard" "[ -f './monitoring/dashboards/system-overview.json' ]"
fi

# AlertManager configurations
if [ -d "monitoring/alerting" ]; then
    run_check "AlertManager Config" "[ -f './monitoring/alerting/alertmanager.yml' ]"
    run_check "Alert Rules" "[ -f './monitoring/alerting/alert-rules.yml' ]"
    run_check "Notification Templates" "[ -f './monitoring/alerting/templates.tmpl' ]"
fi

# ========================================================================
# Security Configuration Validation
# ========================================================================

log "HEADER" "=== Security Configuration Validation ==="

# Check for default passwords (should be changed)
if [ -f ".env.production" ]; then
    if grep -q "change-this" .env.production; then
        run_check "Production Passwords Updated" "false"
        log "ERROR" "Default passwords found in .env.production - MUST be changed before deployment!"
    else
        run_check "Production Passwords Updated" "true"
    fi
fi

# Check file permissions
run_check "SSL Private Key Permissions" "[ ! -f './ssl/private/gameforge.key' ] || [ \$(stat -c '%a' './ssl/private/gameforge.key' 2>/dev/null || echo '000') = '600' ]" false
run_check "Environment File Permissions" "[ ! -f '.env.production' ] || [ \$(stat -c '%a' '.env.production' 2>/dev/null || echo '000') = '600' ]" false

# ========================================================================
# Volume Directory Structure Validation
# ========================================================================

log "HEADER" "=== Volume Directory Structure Validation ==="

volumes=(
    "volumes/logs"
    "volumes/cache"
    "volumes/assets"
    "volumes/models"
    "volumes/postgres"
    "volumes/redis"
    "volumes/elasticsearch"
    "volumes/nginx-logs"
    "volumes/backup-logs"
)

for volume in "${volumes[@]}"; do
    run_check "Volume Directory: $volume" "[ -d './$volume' ]" false
done

# ========================================================================
# Integration Test Preparation
# ========================================================================

log "HEADER" "=== Integration Test Preparation ==="

# Check if we can build the production image
if [ -f "Dockerfile.production" ]; then
    run_check "Production Docker Build Test" "docker build -f Dockerfile.production -t gameforge:validation-test . --no-cache --target production >/dev/null 2>&1" false
fi

# ========================================================================
# Final Validation Summary
# ========================================================================

echo ""
echo -e "${CYAN}========================================================================${NC}"
echo -e "${CYAN}Validation Summary${NC}"
echo -e "${CYAN}========================================================================${NC}"

log "INFO" "Total Checks: $TOTAL_CHECKS"
log "INFO" "Passed: $PASSED_CHECKS"

if [ $WARNING_CHECKS -gt 0 ]; then
    log "WARN" "Warnings: $WARNING_CHECKS"
fi

if [ $FAILED_CHECKS -gt 0 ]; then
    log "ERROR" "Failed: $FAILED_CHECKS"
else
    log "INFO" "Failed: 0"
fi

echo ""

# Calculate success rate
success_rate=$(echo "scale=1; $PASSED_CHECKS * 100 / $TOTAL_CHECKS" | bc -l)

if [ $FAILED_CHECKS -eq 0 ]; then
    log "INFO" "✓ ALL CRITICAL CHECKS PASSED - Production environment ready!"
    log "INFO" "Success Rate: ${success_rate}%"
    echo ""
    log "INFO" "Next steps:"
    log "INFO" "1. Update passwords in .env.production"
    log "INFO" "2. Configure OAuth and AWS credentials"
    log "INFO" "3. Run: ./setup-production.sh"
    log "INFO" "4. Deploy: docker-compose -f docker-compose.production-secure.yml up -d"
    exit 0
else
    log "ERROR" "✗ CRITICAL ISSUES FOUND - Fix before deployment!"
    log "ERROR" "Success Rate: ${success_rate}%"
    echo ""
    log "ERROR" "Please address the failed checks above before proceeding with deployment."
    exit 1
fi
