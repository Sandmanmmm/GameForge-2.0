#!/bin/bash
# GameForge Audit System Management Script
# Provides comprehensive management of the audit logging infrastructure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$AUDIT_DIR")"

# Configuration
ELASTICSEARCH_URL="http://localhost:9201"
KIBANA_URL="http://localhost:5602"
KAFKA_BROKERS="localhost:9092"
GRAFANA_URL="http://localhost:3001"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are available
check_dependencies() {
    log_info "Checking dependencies..."

    local deps=("docker" "docker-compose" "curl" "jq")
    local missing_deps=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again"
        exit 1
    fi

    log_success "All dependencies are available"
}

# Deploy audit infrastructure
deploy_infrastructure() {
    log_info "Deploying audit infrastructure..."

    cd "$PROJECT_ROOT"

    # Start audit services
    docker-compose -f docker-compose.audit.yml up -d

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30

    # Check service health
    check_service_health

    # Initialize audit indices and configurations
    initialize_audit_system

    log_success "Audit infrastructure deployed successfully"
}

# Check health of audit services
check_service_health() {
    log_info "Checking service health..."

    # Check Elasticsearch
    if curl -sf "$ELASTICSEARCH_URL/_cluster/health" > /dev/null; then
        log_success "Elasticsearch is healthy"
    else
        log_error "Elasticsearch is not responding"
        return 1
    fi

    # Check Kibana
    if curl -sf "$KIBANA_URL/api/status" > /dev/null; then
        log_success "Kibana is healthy"
    else
        log_warning "Kibana is not yet ready"
    fi

    # Check Kafka
    if docker exec kafka-audit kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
        log_success "Kafka is healthy"
    else
        log_error "Kafka is not responding"
        return 1
    fi

    # Check Grafana
    if curl -sf "$GRAFANA_URL/api/health" > /dev/null; then
        log_success "Grafana is healthy"
    else
        log_warning "Grafana is not yet ready"
    fi
}

# Initialize audit system configuration
initialize_audit_system() {
    log_info "Initializing audit system configuration..."

    # Create Elasticsearch index template
    curl -X PUT "$ELASTICSEARCH_URL/_index_template/gameforge-audit" \
        -H "Content-Type: application/json" \
        -H "Authorization: Basic ZWxhc3RpYzphdWRpdF9zZWN1cmVfcGFzc3dvcmRfMjAyNA==" \
        -d @"$AUDIT_DIR/configs/audit-mapping.json"

    # Create Kafka topics
    docker exec kafka-audit kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic audit-events \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists

    docker exec kafka-audit kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic security-alerts \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists

    # Import Grafana dashboard
    if [ -f "$AUDIT_DIR/dashboards/audit-dashboard.json" ]; then
        log_info "Importing Grafana dashboard..."
        # Dashboard import would be done via Grafana API
        # This is a placeholder for the actual implementation
    fi

    log_success "Audit system initialized"
}

# Generate test audit data
generate_test_data() {
    log_info "Generating test audit data..."

    # Use the audit logger to generate sample events
    python3 - << 'PYTHON'
import sys
sys.path.append('/audit/scripts')

from audit_logger import AuditLogger, AuditEventType, SeverityLevel
import time
import random

audit = AuditLogger("test-service")

# Generate various types of audit events
for i in range(100):
    # Authentication events
    audit.log_authentication(
        user_id=f"user{random.randint(1, 20)}",
        success=random.choice([True, True, True, False]),  # 75% success rate
        ip_address=f"192.168.1.{random.randint(1, 255)}",
        method=random.choice(["password", "oauth2", "mfa"])
    )

    # Data access events
    audit.log_data_access(
        user_id=f"user{random.randint(1, 20)}",
        resource=random.choice(["player_profile", "game_data", "billing_info", "admin_panel"]),
        action=random.choice(["read", "write", "delete"])
    )

    # Game events
    audit.log_game_event(
        user_id=f"user{random.randint(1, 20)}",
        action=random.choice(["level_up", "purchase", "chat_message", "trade"]),
        resource="game_world"
    )

    # Occasional security events
    if random.random() < 0.05:  # 5% chance
        audit.log_security_event(
            event_description="Suspicious activity detected",
            severity=random.choice([SeverityLevel.MEDIUM, SeverityLevel.HIGH]),
            user_id=f"user{random.randint(1, 20)}",
            ip_address=f"192.168.1.{random.randint(1, 255)}"
        )

    time.sleep(0.1)  # Small delay between events

print("Generated 100+ test audit events")
PYTHON

    log_success "Test audit data generated"
}

# Run audit analytics
run_analytics() {
    log_info "Running audit analytics..."

    # Execute Spark analytics job
    docker exec spark-master-audit spark-submit \
        --master local[*] \
        --packages org.elasticsearch:elasticsearch-hadoop:8.10.0 \
        /opt/bitnami/spark/analytics/audit_analytics.py

    log_success "Audit analytics completed"
}

# Generate compliance report
generate_compliance_report() {
    log_info "Generating compliance report..."

    # Run compliance analysis
    python3 - << 'PYTHON'
import sys
sys.path.append('/audit/compliance')

from compliance_rules import ComplianceMonitor
import json

# Mock audit data for demonstration
audit_data = [
    {"action": "authentication", "success": True, "user_id": "user1"},
    {"action": "data_access", "success": True, "user_id": "user1", "resource": "personal_data"},
    {"action": "data_deletion", "success": True, "user_id": "user1"},
    {"security_event": True, "severity": "high"},
]

monitor = ComplianceMonitor()
report = monitor.generate_compliance_report(audit_data)

print(json.dumps(report, indent=2))
PYTHON

    log_success "Compliance report generated"
}

# Backup audit data
backup_audit_data() {
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="/backup/audit/$backup_date"

    log_info "Backing up audit data to $backup_dir..."

    mkdir -p "$backup_dir"

    # Backup Elasticsearch indices
    curl -X POST "$ELASTICSEARCH_URL/_snapshot/audit_backup/$backup_date" \
        -H "Content-Type: application/json" \
        -H "Authorization: Basic ZWxhc3RpYzphdWRpdF9zZWN1cmVfcGFzc3dvcmRfMjAyNA==" \
        -d '{
            "indices": "gameforge-audit-*",
            "ignore_unavailable": true,
            "include_global_state": false
        }'

    # Backup configuration files
    cp -r "$AUDIT_DIR/configs" "$backup_dir/"
    cp -r "$AUDIT_DIR/dashboards" "$backup_dir/"

    log_success "Audit data backed up to $backup_dir"
}

# Cleanup old audit data
cleanup_old_data() {
    local retention_days=${1:-90}

    log_info "Cleaning up audit data older than $retention_days days..."

    # Delete old Elasticsearch indices
    local cutoff_date=$(date -d "$retention_days days ago" +%Y.%m.%d)

    curl -X DELETE "$ELASTICSEARCH_URL/gameforge-audit-*" \
        -H "Authorization: Basic ZWxhc3RpYzphdWRpdF9zZWN1cmVfcGFzc3dvcmRfMjAyNA==" \
        --data-urlencode "q=@timestamp:<$cutoff_date"

    log_success "Old audit data cleaned up"
}

# Display system status
show_status() {
    log_info "Audit System Status"
    echo "===================="

    # Service status
    echo "Services:"
    docker-compose -f "$PROJECT_ROOT/docker-compose.audit.yml" ps

    echo ""
    echo "Elasticsearch Status:"
    curl -s "$ELASTICSEARCH_URL/_cluster/health" | jq '.'

    echo ""
    echo "Kafka Topics:"
    docker exec kafka-audit kafka-topics --bootstrap-server localhost:9092 --list

    echo ""
    echo "Recent Audit Events:"
    curl -s "$ELASTICSEARCH_URL/gameforge-audit-*/_search?size=5&sort=@timestamp:desc" \
        -H "Authorization: Basic ZWxhc3RpYzphdWRpdF9zZWN1cmVfcGFzc3dvcmRfMjAyNA==" | \
        jq '.hits.hits[]._source | {timestamp: .timestamp, action: .action, user_id: .user_id}'
}

# Main command handling
case "${1:-}" in
    "deploy")
        check_dependencies
        deploy_infrastructure
        ;;
    "status")
        show_status
        ;;
    "health")
        check_service_health
        ;;
    "test-data")
        generate_test_data
        ;;
    "analytics")
        run_analytics
        ;;
    "compliance")
        generate_compliance_report
        ;;
    "backup")
        backup_audit_data "${2:-}"
        ;;
    "cleanup")
        cleanup_old_data "${2:-90}"
        ;;
    "stop")
        docker-compose -f "$PROJECT_ROOT/docker-compose.audit.yml" down
        ;;
    "restart")
        docker-compose -f "$PROJECT_ROOT/docker-compose.audit.yml" restart
        ;;
    "logs")
        docker-compose -f "$PROJECT_ROOT/docker-compose.audit.yml" logs -f "${2:-}"
        ;;
    *)
        echo "Usage: $0 {deploy|status|health|test-data|analytics|compliance|backup|cleanup|stop|restart|logs}"
        echo ""
        echo "Commands:"
        echo "  deploy     - Deploy audit infrastructure"
        echo "  status     - Show system status"
        echo "  health     - Check service health"
        echo "  test-data  - Generate test audit data"
        echo "  analytics  - Run audit analytics"
        echo "  compliance - Generate compliance report"
        echo "  backup     - Backup audit data"
        echo "  cleanup    - Clean up old audit data"
        echo "  stop       - Stop audit services"
        echo "  restart    - Restart audit services"
        echo "  logs       - Show service logs"
        exit 1
        ;;
esac
