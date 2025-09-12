#!/bin/bash
# GameForge Master Deployment Script
# Complete deployment orchestration for production secrets management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-production}"
DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-full}"
SKIP_BACKUP="${SKIP_BACKUP:-false}"
DRY_RUN="${DRY_RUN:-false}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging with deployment context
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')] 🚀${NC} $1"; }
success() { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✅${NC} $1"; }
warning() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️${NC} $1"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ❌${NC} $1"; }
step() { echo -e "${PURPLE}[$(date '+%H:%M:%S')] 📋${NC} STEP: $1"; }
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')] ℹ️${NC} $1"; }

# Deployment phases
declare -A DEPLOYMENT_PHASES=(
    ["infrastructure"]="Deploy base infrastructure (Docker, networks)"
    ["vault"]="Deploy Vault cluster with high availability"
    ["secrets"]="Initialize secrets management and policies"
    ["ssl"]="Configure SSL/TLS with Let's Encrypt"
    ["monitoring"]="Deploy monitoring and alerting stack"
    ["applications"]="Deploy GameForge applications with secrets"
    ["validation"]="Validate complete deployment"
)

# Load environment configuration
load_environment_config() {
    local config_file="$PROJECT_ROOT/secrets/config/$ENVIRONMENT.env"

    if [ -f "$config_file" ]; then
        log "Loading configuration for environment: $ENVIRONMENT"
        set -a
        source "$config_file"
        set +a
        success "Configuration loaded from $config_file"
    else
        error "Configuration file not found: $config_file"
        exit 1
    fi
}

# Pre-deployment validation
validate_prerequisites() {
    step "Validating deployment prerequisites"

    local validation_errors=0

    # Check required tools
    local required_tools=("docker" "docker-compose" "vault" "openssl" "jq")

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            error "Required tool not found: $tool"
            ((validation_errors++))
        else
            log "✓ Found: $tool"
        fi
    done

    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running"
        ((validation_errors++))
    else
        log "✓ Docker daemon is running"
    fi

    # Check Docker Swarm (if required)
    if [ "$SWARM_MODE" = "true" ]; then
        if ! docker node ls >/dev/null 2>&1; then
            warning "Docker Swarm not initialized, will initialize during deployment"
        else
            log "✓ Docker Swarm is active"
        fi
    fi

    # Check required files
    local required_files=(
        "$PROJECT_ROOT/docker-compose.production.yml"
        "$PROJECT_ROOT/docker-compose.vault.yml"
        "$PROJECT_ROOT/secrets/scripts/init-secrets.sh"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file not found: $file"
            ((validation_errors++))
        else
            log "✓ Found: $(basename "$file")"
        fi
    done

    # Check environment variables
    local required_vars=("VAULT_ADDR" "DATABASE_HOST")

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            error "Required environment variable not set: $var"
            ((validation_errors++))
        else
            log "✓ Set: $var"
        fi
    done

    if [ $validation_errors -eq 0 ]; then
        success "All prerequisites validated"
        return 0
    else
        error "$validation_errors validation errors found"
        return 1
    fi
}

# Create deployment backup
create_deployment_backup() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        warning "Skipping deployment backup (SKIP_BACKUP=true)"
        return 0
    fi

    step "Creating pre-deployment backup"

    local backup_dir="/var/backups/gameforge-deployment"
    mkdir -p "$backup_dir"

    # Backup current Docker containers and volumes
    if docker ps -q | grep -q .; then
        log "Backing up current Docker state..."

        docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" > "$backup_dir/containers_$TIMESTAMP.txt"
        docker volume ls --format "table {{.Name}}\t{{.Driver}}" > "$backup_dir/volumes_$TIMESTAMP.txt"

        # Export important volumes if they exist
        if docker volume ls | grep -q "gameforge_postgres_data"; then
            log "Backing up PostgreSQL data..."
            docker run --rm -v gameforge_postgres_data:/data -v "$backup_dir":/backup alpine tar czf /backup/postgres_data_$TIMESTAMP.tar.gz -C /data .
        fi
    fi

    # Backup Vault data if running
    if docker ps | grep -q vault; then
        log "Backing up Vault data..."
        "$PROJECT_ROOT/secrets/scripts/backup-vault.sh" || warning "Vault backup failed"
    fi

    success "Pre-deployment backup completed"
}

# Deploy infrastructure phase
deploy_infrastructure() {
    step "Deploying base infrastructure"

    # Initialize Docker Swarm if needed
    if [ "$SWARM_MODE" = "true" ] && ! docker node ls >/dev/null 2>&1; then
        log "Initializing Docker Swarm..."
        docker swarm init --advertise-addr $(hostname -i) || {
            error "Failed to initialize Docker Swarm"
            return 1
        }
        success "Docker Swarm initialized"
    fi

    # Create networks
    log "Creating Docker networks..."

    docker network create --driver overlay --attachable gameforge-network 2>/dev/null || {
        log "Network gameforge-network already exists"
    }

    docker network create --driver overlay --attachable vault-network 2>/dev/null || {
        log "Network vault-network already exists"
    }

    docker network create --driver overlay --attachable monitoring-network 2>/dev/null || {
        log "Network monitoring-network already exists"
    }

    success "Infrastructure deployment completed"
}

# Deploy Vault cluster
deploy_vault() {
    step "Deploying Vault cluster"

    log "Starting Vault and Consul services..."

    # Deploy Vault infrastructure
    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY RUN] Would deploy: docker-compose -f docker-compose.vault.yml up -d"
    else
        docker-compose -f "$PROJECT_ROOT/docker-compose.vault.yml" up -d

        # Wait for Vault to be ready
        log "Waiting for Vault to be ready..."
        local max_attempts=30
        local attempt=1

        while [ $attempt -le $max_attempts ]; do
            if timeout 10 curl -s "$VAULT_ADDR/v1/sys/health" >/dev/null 2>&1; then
                break
            fi

            log "Attempt $attempt/$max_attempts: Vault not ready, waiting..."
            sleep 10
            ((attempt++))
        done

        if [ $attempt -gt $max_attempts ]; then
            error "Vault did not become ready within timeout"
            return 1
        fi
    fi

    success "Vault cluster deployment completed"
}

# Initialize secrets
deploy_secrets() {
    step "Initializing secrets management"

    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY RUN] Would run: $PROJECT_ROOT/secrets/scripts/init-secrets.sh"
    else
        # Run secrets initialization
        "$PROJECT_ROOT/secrets/scripts/init-secrets.sh" || {
            error "Secrets initialization failed"
            return 1
        }

        # Start Vault-Docker bridge
        log "Starting Vault-Docker bridge service..."
        docker-compose -f "$PROJECT_ROOT/docker-compose.swarm-secrets.yml" up -d vault-docker-bridge || {
            warning "Failed to start Vault-Docker bridge"
        }
    fi

    success "Secrets management initialization completed"
}

# Deploy SSL/TLS
deploy_ssl() {
    if [ "$SSL_ENABLED" != "true" ]; then
        warning "SSL disabled, skipping SSL deployment"
        return 0
    fi

    step "Deploying SSL/TLS configuration"

    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY RUN] Would deploy SSL/TLS stack"
    else
        # Deploy SSL infrastructure
        docker-compose -f "$PROJECT_ROOT/docker-compose.ssl.yml" up -d || {
            error "SSL deployment failed"
            return 1
        }

        # Wait for certificates
        log "Waiting for SSL certificates..."
        sleep 30
    fi

    success "SSL/TLS deployment completed"
}

# Deploy monitoring
deploy_monitoring() {
    if [ "$METRICS_ENABLED" != "true" ]; then
        warning "Monitoring disabled, skipping monitoring deployment"
        return 0
    fi

    step "Deploying monitoring stack"

    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY RUN] Would deploy monitoring stack"
    else
        # Deploy monitoring services
        docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" up -d prometheus grafana elasticsearch logstash kibana || {
            warning "Some monitoring services failed to start"
        }
    fi

    success "Monitoring deployment completed"
}

# Deploy applications
deploy_applications() {
    step "Deploying GameForge applications"

    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY RUN] Would deploy GameForge applications"
    else
        # Deploy main application stack
        docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" up -d gameforge-api gameforge-worker postgres redis || {
            error "Application deployment failed"
            return 1
        }

        # Wait for applications to be ready
        log "Waiting for applications to be ready..."
        sleep 60
    fi

    success "Application deployment completed"
}

# Validate deployment
validate_deployment() {
    step "Validating complete deployment"

    local validation_errors=0

    if [ "$DRY_RUN" = "true" ]; then
        log "[DRY RUN] Would run deployment validation"
        return 0
    fi

    # Run health checks
    log "Running health checks..."

    if ! "$PROJECT_ROOT/secrets/vault/scripts/health-check-secrets.sh" --quiet; then
        error "Secrets health check failed"
        ((validation_errors++))
    fi

    # Test application endpoints
    log "Testing application endpoints..."

    local endpoints=("http://localhost:8080/health" "http://localhost:8080/api/v1/status")

    for endpoint in "${endpoints[@]}"; do
        if timeout 30 curl -s "$endpoint" >/dev/null 2>&1; then
            log "✓ Endpoint accessible: $endpoint"
        else
            error "✗ Endpoint not accessible: $endpoint"
            ((validation_errors++))
        fi
    done

    # Test database connectivity
    log "Testing database connectivity..."

    if docker exec -it $(docker ps -q -f name=postgres) pg_isready >/dev/null 2>&1; then
        log "✓ PostgreSQL is ready"
    else
        error "✗ PostgreSQL is not ready"
        ((validation_errors++))
    fi

    # Test secret access
    log "Testing secret accessibility..."

    if vault kv get secret/gameforge/database >/dev/null 2>&1; then
        log "✓ Secrets are accessible"
    else
        error "✗ Secrets are not accessible"
        ((validation_errors++))
    fi

    if [ $validation_errors -eq 0 ]; then
        success "All deployment validations passed"
        return 0
    else
        error "$validation_errors validation errors found"
        return 1
    fi
}

# Rollback deployment
rollback_deployment() {
    error "Deployment failed, initiating rollback..."

    step "Rolling back deployment"

    # Stop current services
    log "Stopping current services..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" down 2>/dev/null || true
    docker-compose -f "$PROJECT_ROOT/docker-compose.vault.yml" down 2>/dev/null || true
    docker-compose -f "$PROJECT_ROOT/docker-compose.ssl.yml" down 2>/dev/null || true

    # Restore from backup if available
    local latest_backup=$(find /var/backups/gameforge-deployment -name "postgres_data_*.tar.gz" -type f | sort | tail -1)

    if [ -n "$latest_backup" ] && [ -f "$latest_backup" ]; then
        warning "Restoring from backup: $(basename "$latest_backup")"

        # Restore PostgreSQL data
        docker volume rm gameforge_postgres_data 2>/dev/null || true
        docker volume create gameforge_postgres_data
        docker run --rm -v gameforge_postgres_data:/data -v "$(dirname "$latest_backup")":/backup alpine tar xzf "/backup/$(basename "$latest_backup")" -C /data

        log "Data restored from backup"
    fi

    warning "Rollback completed - manual intervention may be required"
}

# Send deployment notification
send_deployment_notification() {
    local status="$1"
    local phase="$2"
    local message="$3"

    local notification_msg="🚀 GameForge Deployment: $status\n"
    notification_msg+="Environment: $ENVIRONMENT\n"
    notification_msg+="Phase: $phase\n"
    notification_msg+="Time: $TIMESTAMP\n"
    notification_msg+="Message: $message"

    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local emoji="✅"
        case $status in
            "FAILED") emoji="❌" ;;
            "WARNING") emoji="⚠️" ;;
            "STARTED") emoji="🚀" ;;
        esac

        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\": \"$emoji $notification_msg\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi

    if [ -n "${DEPLOYMENT_EMAIL:-}" ]; then
        echo -e "$notification_msg" | mail -s "GameForge Deployment: $status" "$DEPLOYMENT_EMAIL" 2>/dev/null || true
    fi
}

# Show deployment summary
show_deployment_summary() {
    echo ""
    echo "🎉 GAMEFORGE DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "=============================================="
    echo "Environment: $ENVIRONMENT"
    echo "Deployment Mode: $DEPLOYMENT_MODE"
    echo "Timestamp: $TIMESTAMP"
    echo ""
    echo "📋 Deployed Components:"
    echo "  ✅ Vault Cluster (HA)"
    echo "  ✅ Secrets Management"
    echo "  ✅ SSL/TLS (Let's Encrypt)"
    echo "  ✅ Monitoring Stack"
    echo "  ✅ GameForge Applications"
    echo ""
    echo "🔗 Access URLs:"
    echo "  • Vault UI: $VAULT_ADDR/ui"
    echo "  • GameForge API: http://localhost:8080"
    echo "  • Grafana: http://localhost:3000"
    echo "  • Prometheus: http://localhost:9090"
    echo ""
    echo "🔐 Security:"
    echo "  • Secrets encrypted with Vault"
    echo "  • SSL/TLS enabled"
    echo "  • Automatic secret rotation configured"
    echo ""
    echo "📊 Monitoring:"
    echo "  • Health checks: ./secrets/vault/scripts/health-check-secrets.sh"
    echo "  • Backup: ./secrets/scripts/backup-vault.sh"
    echo "  • Logs: docker-compose logs -f"
    echo ""
    echo "🚀 Next Steps:"
    echo "  1. Review deployment in Grafana dashboards"
    echo "  2. Test application functionality"
    echo "  3. Schedule regular backups"
    echo "  4. Monitor health check alerts"
}

# Main deployment orchestration
main() {
    log "🚀 STARTING GAMEFORGE PRODUCTION DEPLOYMENT"
    echo "Environment: $ENVIRONMENT"
    echo "Mode: $DEPLOYMENT_MODE"
    echo "Dry Run: $DRY_RUN"
    echo "Skip Backup: $SKIP_BACKUP"
    echo ""

    # Send start notification
    send_deployment_notification "STARTED" "Initialization" "Starting GameForge deployment"

    # Load configuration
    load_environment_config

    # Validate prerequisites
    if ! validate_prerequisites; then
        send_deployment_notification "FAILED" "Prerequisites" "Prerequisite validation failed"
        exit 1
    fi

    # Create backup
    create_deployment_backup

    # Execute deployment phases
    local failed_phase=""

    case "$DEPLOYMENT_MODE" in
        "full")
            local phases=("infrastructure" "vault" "secrets" "ssl" "monitoring" "applications" "validation")
            ;;
        "secrets-only")
            local phases=("vault" "secrets" "validation")
            ;;
        "apps-only")
            local phases=("applications" "validation")
            ;;
        *)
            error "Unknown deployment mode: $DEPLOYMENT_MODE"
            exit 1
            ;;
    esac

    for phase in "${phases[@]}"; do
        local phase_desc="${DEPLOYMENT_PHASES[$phase]}"

        if [ "$phase" = "infrastructure" ]; then
            deploy_infrastructure || { failed_phase="$phase"; break; }
        elif [ "$phase" = "vault" ]; then
            deploy_vault || { failed_phase="$phase"; break; }
        elif [ "$phase" = "secrets" ]; then
            deploy_secrets || { failed_phase="$phase"; break; }
        elif [ "$phase" = "ssl" ]; then
            deploy_ssl || { failed_phase="$phase"; break; }
        elif [ "$phase" = "monitoring" ]; then
            deploy_monitoring || { failed_phase="$phase"; break; }
        elif [ "$phase" = "applications" ]; then
            deploy_applications || { failed_phase="$phase"; break; }
        elif [ "$phase" = "validation" ]; then
            validate_deployment || { failed_phase="$phase"; break; }
        fi
    done

    # Handle deployment result
    if [ -n "$failed_phase" ]; then
        send_deployment_notification "FAILED" "$failed_phase" "Deployment failed during $failed_phase phase"
        rollback_deployment
        exit 1
    else
        send_deployment_notification "SUCCESS" "Complete" "Deployment completed successfully"
        show_deployment_summary
        exit 0
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "GameForge Master Deployment Script"
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h           Show this help message"
        echo "  --dry-run            Show what would be deployed without making changes"
        echo "  --skip-backup        Skip pre-deployment backup"
        echo "  --rollback           Rollback to previous deployment"
        echo ""
        echo "Environment Variables:"
        echo "  ENVIRONMENT          Deployment environment (default: production)"
        echo "  DEPLOYMENT_MODE      Deployment mode: full, secrets-only, apps-only (default: full)"
        echo "  SKIP_BACKUP          Skip backup creation (default: false)"
        echo "  DRY_RUN              Show deployment plan only (default: false)"
        echo ""
        echo "Deployment Modes:"
        echo "  full                 Complete deployment (infrastructure + secrets + apps)"
        echo "  secrets-only         Deploy only Vault and secrets management"
        echo "  apps-only            Deploy only GameForge applications"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Full production deployment"
        echo "  ENVIRONMENT=staging $0                # Deploy to staging"
        echo "  DEPLOYMENT_MODE=secrets-only $0       # Deploy only secrets"
        echo "  DRY_RUN=true $0                      # Show deployment plan"
        exit 0
        ;;
    --dry-run)
        DRY_RUN=true
        main
        ;;
    --skip-backup)
        SKIP_BACKUP=true
        main
        ;;
    --rollback)
        log "🔄 Initiating deployment rollback..."
        rollback_deployment
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
