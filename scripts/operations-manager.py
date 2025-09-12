#!/usr/bin/env python3
"""
========================================================================
GameForge AI - Operations Automation & Management System
Comprehensive production operations with automated scheduling, secret rotation, 
disaster recovery, and monitoring
========================================================================
"""

import os
import yaml
import json
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OperationsManager:
    """Comprehensive production operations management"""
    
    def __init__(self):
        self.ops_dir = "ops"
        self.schedules_dir = f"{self.ops_dir}/schedules"
        self.backups_dir = f"{self.ops_dir}/backups"
        self.secrets_dir = f"{self.ops_dir}/secrets"
        self.dr_dir = f"{self.ops_dir}/disaster-recovery"
        
        for directory in [self.ops_dir, self.schedules_dir, self.backups_dir, 
                         self.secrets_dir, self.dr_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def create_automated_scheduling_system(self):
        """Create comprehensive automated scheduling for all operations"""
        
        # Cron configuration for production schedules
        cron_config = '''
# GameForge AI Production Cron Schedule
# Comprehensive automation for production operations

# Database backups - Every 6 hours
0 */6 * * * /opt/gameforge/scripts/backup-database.sh >> /var/log/gameforge/backup.log 2>&1

# Application backups - Daily at 2 AM
0 2 * * * /opt/gameforge/scripts/backup-application.sh >> /var/log/gameforge/backup.log 2>&1

# Secret rotation - Weekly on Sunday at 3 AM
0 3 * * 0 /opt/gameforge/scripts/rotate-secrets.sh >> /var/log/gameforge/secrets.log 2>&1

# Health checks - Every 5 minutes
*/5 * * * * /opt/gameforge/scripts/health-check.sh >> /var/log/gameforge/health.log 2>&1

# Performance monitoring - Every 15 minutes
*/15 * * * * /opt/gameforge/scripts/performance-monitor.sh >> /var/log/gameforge/performance.log 2>&1

# Log rotation - Daily at 4 AM
0 4 * * * /opt/gameforge/scripts/rotate-logs.sh >> /var/log/gameforge/maintenance.log 2>&1

# Disk cleanup - Weekly on Monday at 1 AM
0 1 * * 1 /opt/gameforge/scripts/cleanup-disk.sh >> /var/log/gameforge/maintenance.log 2>&1

# Certificate renewal - Monthly on 1st at 5 AM
0 5 1 * * /opt/gameforge/scripts/renew-certificates.sh >> /var/log/gameforge/certificates.log 2>&1

# Disaster recovery test - Monthly on 15th at 6 AM
0 6 15 * * /opt/gameforge/scripts/test-disaster-recovery.sh >> /var/log/gameforge/dr-test.log 2>&1

# Security scan - Weekly on Wednesday at 7 AM
0 7 * * 3 /opt/gameforge/scripts/security-scan.sh >> /var/log/gameforge/security.log 2>&1
'''
        
        with open(f'{self.schedules_dir}/gameforge-cron.conf', 'w', encoding='utf-8') as f:
            f.write(cron_config)
        
        # Kubernetes CronJob configurations
        cronjobs = [
            {
                'name': 'database-backup',
                'schedule': '0 */6 * * *',
                'image': 'gameforge/backup:latest',
                'command': ['/scripts/backup-database.sh'],
                'resources': {'requests': {'memory': '256Mi', 'cpu': '100m'}}
            },
            {
                'name': 'secret-rotation',
                'schedule': '0 3 * * 0',
                'image': 'gameforge/secrets:latest',
                'command': ['/scripts/rotate-secrets.sh'],
                'resources': {'requests': {'memory': '128Mi', 'cpu': '50m'}}
            },
            {
                'name': 'health-monitoring',
                'schedule': '*/5 * * * *',
                'image': 'gameforge/monitoring:latest',
                'command': ['/scripts/health-check.sh'],
                'resources': {'requests': {'memory': '64Mi', 'cpu': '25m'}}
            },
            {
                'name': 'disaster-recovery-test',
                'schedule': '0 6 15 * *',
                'image': 'gameforge/dr-test:latest',
                'command': ['/scripts/test-disaster-recovery.sh'],
                'resources': {'requests': {'memory': '512Mi', 'cpu': '200m'}}
            }
        ]
        
        for job in cronjobs:
            k8s_cronjob = {
                'apiVersion': 'batch/v1',
                'kind': 'CronJob',
                'metadata': {
                    'name': job['name'],
                    'namespace': 'gameforge',
                    'labels': {
                        'app': 'gameforge',
                        'component': 'operations',
                        'type': 'cronjob'
                    }
                },
                'spec': {
                    'schedule': job['schedule'],
                    'jobTemplate': {
                        'spec': {
                            'template': {
                                'spec': {
                                    'containers': [{
                                        'name': job['name'],
                                        'image': job['image'],
                                        'command': job['command'],
                                        'resources': job['resources'],
                                        'volumeMounts': [
                                            {
                                                'name': 'logs',
                                                'mountPath': '/var/log/gameforge'
                                            },
                                            {
                                                'name': 'config',
                                                'mountPath': '/etc/gameforge'
                                            }
                                        ]
                                    }],
                                    'volumes': [
                                        {
                                            'name': 'logs',
                                            'persistentVolumeClaim': {
                                                'claimName': 'gameforge-logs'
                                            }
                                        },
                                        {
                                            'name': 'config',
                                            'configMap': {
                                                'name': 'gameforge-config'
                                            }
                                        }
                                    ],
                                    'restartPolicy': 'OnFailure'
                                }
                            }
                        }
                    }
                }
            }
            
            filename = f'{self.schedules_dir}/k8s-cronjob-{job["name"]}.yaml'
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(k8s_cronjob, f, default_flow_style=False, indent=2)
        
        logger.info("Automated scheduling system created")
    
    def create_secret_rotation_system(self):
        """Create comprehensive secret rotation system"""
        
        # Secret rotation configuration
        rotation_config = {
            'rotation_schedule': {
                'database_passwords': {'frequency': 'weekly', 'retention': 3},
                'api_keys': {'frequency': 'monthly', 'retention': 2},
                'jwt_secrets': {'frequency': 'daily', 'retention': 7},
                'ssl_certificates': {'frequency': 'monthly', 'retention': 2},
                'encryption_keys': {'frequency': 'quarterly', 'retention': 4}
            },
            'vault_config': {
                'address': 'https://vault.gameforge.local:8200',
                'auth_method': 'kubernetes',
                'mount_point': 'gameforge'
            },
            'notification': {
                'webhook_url': 'https://hooks.slack.com/services/...',
                'email_alerts': ['ops@gameforge.com'],
                'success_notifications': True,
                'failure_notifications': True
            }
        }
        
        with open(f'{self.secrets_dir}/rotation-config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(rotation_config, f, default_flow_style=False, indent=2)
        
        # Secret rotation script
        rotation_script = '''#!/bin/bash
# GameForge AI Secret Rotation System
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../secrets/rotation-config.yaml"
LOG_FILE="/var/log/gameforge/secret-rotation.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Vault functions
vault_login() {
    if [ "$VAULT_AUTH_METHOD" = "kubernetes" ]; then
        vault auth -method=kubernetes role=gameforge-operations
    else
        vault auth -method=userpass username="$VAULT_USERNAME" password="$VAULT_PASSWORD"
    fi
}

rotate_database_password() {
    log "Rotating database password..."
    
    # Generate new password
    NEW_PASSWORD=$(openssl rand -base64 32)
    
    # Update in Vault
    vault kv put secret/gameforge/database password="$NEW_PASSWORD"
    
    # Update database user
    PGPASSWORD="$OLD_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "ALTER USER $DB_USER WITH PASSWORD '$NEW_PASSWORD';"
    
    # Restart services with new password
    kubectl rollout restart deployment/gameforge-app -n gameforge
    
    log "Database password rotated successfully"
}

rotate_api_keys() {
    log "Rotating API keys..."
    
    # Generate new API key
    NEW_API_KEY=$(uuidgen)
    
    # Update in Vault
    vault kv put secret/gameforge/api-keys main="$NEW_API_KEY"
    
    # Update external service configurations
    curl -X PUT "https://external-api.com/keys" \\
         -H "Authorization: Bearer $OLD_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d "{\\"key\\": \\"$NEW_API_KEY\\"}"
    
    log "API keys rotated successfully"
}

rotate_jwt_secrets() {
    log "Rotating JWT secrets..."
    
    # Generate new JWT secret
    NEW_JWT_SECRET=$(openssl rand -hex 64)
    
    # Update in Vault
    vault kv put secret/gameforge/jwt secret="$NEW_JWT_SECRET"
    
    # Graceful restart to allow token validation overlap
    kubectl patch deployment gameforge-app -n gameforge -p '{"spec":{"template":{"metadata":{"annotations":{"deployment.kubernetes.io/restartedAt":"'"$(date -Iseconds)"'"}}}}}'
    
    log "JWT secrets rotated successfully"
}

rotate_ssl_certificates() {
    log "Rotating SSL certificates..."
    
    # Generate new certificates
    ./generate-mtls-certs.sh
    
    # Update Kubernetes secrets
    kubectl create secret tls gameforge-tls \\
        --cert=certs/server-cert.pem \\
        --key=certs/server-key.pem \\
        --namespace=gameforge \\
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Restart nginx
    kubectl rollout restart deployment/nginx -n gameforge
    
    log "SSL certificates rotated successfully"
}

send_notification() {
    local status="$1"
    local message="$2"
    
    # Send Slack notification
    curl -X POST "$WEBHOOK_URL" \\
         -H "Content-Type: application/json" \\
         -d "{\\"text\\": \\"Secret Rotation $status: $message\\"}"
    
    # Send email notification
    echo "$message" | mail -s "GameForge Secret Rotation $status" "$EMAIL_ALERTS"
}

main() {
    log "Starting secret rotation process..."
    
    # Load configuration
    source /etc/gameforge/vault.env
    
    # Login to Vault
    vault_login
    
    # Get current secrets for backup
    OLD_DB_PASSWORD=$(vault kv get -field=password secret/gameforge/database)
    OLD_API_KEY=$(vault kv get -field=main secret/gameforge/api-keys)
    OLD_JWT_SECRET=$(vault kv get -field=secret secret/gameforge/jwt)
    
    # Perform rotations based on schedule
    case "${1:-all}" in
        "database")
            rotate_database_password
            ;;
        "api")
            rotate_api_keys
            ;;
        "jwt")
            rotate_jwt_secrets
            ;;
        "ssl")
            rotate_ssl_certificates
            ;;
        "all")
            rotate_database_password
            rotate_api_keys
            rotate_jwt_secrets
            rotate_ssl_certificates
            ;;
        *)
            log "Unknown rotation type: $1"
            exit 1
            ;;
    esac
    
    send_notification "SUCCESS" "Secret rotation completed successfully"
    log "Secret rotation process completed"
}

# Error handling
trap 'send_notification "FAILED" "Secret rotation failed: $BASH_COMMAND"; exit 1' ERR

main "$@"
'''
        
        with open(f'{self.secrets_dir}/rotate-secrets.sh', 'w', encoding='utf-8') as f:
            f.write(rotation_script)
        
        os.chmod(f'{self.secrets_dir}/rotate-secrets.sh', 0o755)
        
        logger.info("Secret rotation system created")
    
    def create_disaster_recovery_system(self):
        """Create comprehensive disaster recovery system"""
        
        # Disaster recovery plan
        dr_plan = {
            'recovery_objectives': {
                'rto': '1 hour',  # Recovery Time Objective
                'rpo': '15 minutes'  # Recovery Point Objective
            },
            'backup_strategy': {
                'database': {
                    'frequency': 'every 6 hours',
                    'retention': '30 days',
                    'location': ['local', 's3', 'azure-blob']
                },
                'application_data': {
                    'frequency': 'daily',
                    'retention': '90 days',
                    'location': ['local', 's3']
                },
                'models': {
                    'frequency': 'weekly',
                    'retention': '1 year',
                    'location': ['s3', 'azure-blob']
                }
            },
            'failover_procedures': {
                'primary_region': 'us-west-2',
                'secondary_region': 'us-east-1',
                'auto_failover': True,
                'manual_approval_required': False
            }
        }
        
        with open(f'{self.dr_dir}/disaster-recovery-plan.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(dr_plan, f, default_flow_style=False, indent=2)
        
        # Disaster recovery test script
        dr_test_script = '''#!/bin/bash
# GameForge AI Disaster Recovery Testing System
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DR_DIR="$SCRIPT_DIR/../disaster-recovery"
LOG_FILE="/var/log/gameforge/dr-test.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Test database backup and restore
test_database_recovery() {
    log "Testing database recovery..."
    
    # Create test backup
    TEST_BACKUP="test_backup_$(date +%Y%m%d_%H%M%S)"
    pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "/tmp/${TEST_BACKUP}.sql"
    
    # Create test database
    createdb -h "$DB_HOST" -U "$DB_USER" "test_${DB_NAME}"
    
    # Restore from backup
    psql -h "$DB_HOST" -U "$DB_USER" -d "test_${DB_NAME}" < "/tmp/${TEST_BACKUP}.sql"
    
    # Verify data integrity
    ORIGINAL_COUNT=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;")
    TEST_COUNT=$(psql -h "$DB_HOST" -U "$DB_USER" -d "test_${DB_NAME}" -t -c "SELECT COUNT(*) FROM users;")
    
    if [ "$ORIGINAL_COUNT" = "$TEST_COUNT" ]; then
        log "✅ Database recovery test PASSED"
    else
        log "❌ Database recovery test FAILED"
        return 1
    fi
    
    # Cleanup
    dropdb -h "$DB_HOST" -U "$DB_USER" "test_${DB_NAME}"
    rm "/tmp/${TEST_BACKUP}.sql"
}

# Test application failover
test_application_failover() {
    log "Testing application failover..."
    
    # Scale down primary instance
    kubectl scale deployment gameforge-app --replicas=0 -n gameforge
    
    # Wait for failover
    sleep 30
    
    # Test health endpoint
    for i in {1..12}; do
        if curl -f "https://gameforge.local/health" > /dev/null 2>&1; then
            log "✅ Application failover test PASSED"
            break
        fi
        
        if [ $i -eq 12 ]; then
            log "❌ Application failover test FAILED"
            return 1
        fi
        
        sleep 10
    done
    
    # Restore primary instance
    kubectl scale deployment gameforge-app --replicas=3 -n gameforge
}

# Test backup integrity
test_backup_integrity() {
    log "Testing backup integrity..."
    
    # List recent backups
    LATEST_BACKUP=$(find /backups -name "*.tar.gz" -type f -printf '%T@ %p\\n' | sort -n | tail -1 | cut -d' ' -f2)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log "❌ No backups found"
        return 1
    fi
    
    # Verify backup file integrity
    if tar -tzf "$LATEST_BACKUP" > /dev/null 2>&1; then
        log "✅ Backup integrity test PASSED: $LATEST_BACKUP"
    else
        log "❌ Backup integrity test FAILED: $LATEST_BACKUP"
        return 1
    fi
}

# Test network connectivity to secondary region
test_network_connectivity() {
    log "Testing network connectivity..."
    
    # Test connectivity to secondary region endpoints
    ENDPOINTS=(
        "secondary.gameforge.com:443"
        "s3.us-east-1.amazonaws.com:443"
        "backup.gameforge.com:22"
    )
    
    for endpoint in "${ENDPOINTS[@]}"; do
        if timeout 10 bash -c "cat < /dev/null > /dev/tcp/${endpoint/:/ }"; then
            log "✅ Connectivity test PASSED: $endpoint"
        else
            log "❌ Connectivity test FAILED: $endpoint"
            return 1
        fi
    done
}

# Test secrets recovery
test_secrets_recovery() {
    log "Testing secrets recovery..."
    
    # Test Vault connectivity
    if vault status > /dev/null 2>&1; then
        log "✅ Vault connectivity test PASSED"
    else
        log "❌ Vault connectivity test FAILED"
        return 1
    fi
    
    # Test secret retrieval
    if vault kv get secret/gameforge/database > /dev/null 2>&1; then
        log "✅ Secret retrieval test PASSED"
    else
        log "❌ Secret retrieval test FAILED"
        return 1
    fi
}

# Generate DR test report
generate_dr_report() {
    local test_results="$1"
    
    cat > "$DR_DIR/dr-test-report-$(date +%Y%m%d).json" << EOF
{
    "test_date": "$(date -Iseconds)",
    "test_results": $test_results,
    "summary": {
        "total_tests": $(echo "$test_results" | jq 'length'),
        "passed_tests": $(echo "$test_results" | jq 'map(select(.status == "PASSED")) | length'),
        "failed_tests": $(echo "$test_results" | jq 'map(select(.status == "FAILED")) | length')
    },
    "next_test_date": "$(date -d '+1 month' -Iseconds)"
}
EOF
}

main() {
    log "Starting disaster recovery test..."
    
    declare -a test_results=()
    
    # Run all DR tests
    tests=(
        "test_database_recovery"
        "test_application_failover"
        "test_backup_integrity"
        "test_network_connectivity"
        "test_secrets_recovery"
    )
    
    for test in "${tests[@]}"; do
        log "Running $test..."
        
        if $test; then
            test_results+=("{\\"test\\": \\"$test\\", \\"status\\": \\"PASSED\\", \\"timestamp\\": \\"$(date -Iseconds)\\"}")
        else
            test_results+=("{\\"test\\": \\"$test\\", \\"status\\": \\"FAILED\\", \\"timestamp\\": \\"$(date -Iseconds)\\"}")
        fi
    done
    
    # Generate report
    results_json="[$(IFS=,; echo "${test_results[*]}")]"
    generate_dr_report "$results_json"
    
    # Send notification
    failed_count=$(echo "$results_json" | jq 'map(select(.status == "FAILED")) | length')
    
    if [ "$failed_count" -eq 0 ]; then
        curl -X POST "$WEBHOOK_URL" \\
             -H "Content-Type: application/json" \\
             -d "{\\"text\\": \\"🎉 All disaster recovery tests PASSED\\"}"
    else
        curl -X POST "$WEBHOOK_URL" \\
             -H "Content-Type: application/json" \\
             -d "{\\"text\\": \\"⚠️ $failed_count disaster recovery tests FAILED - immediate attention required\\"}"
    fi
    
    log "Disaster recovery test completed"
}

main "$@"
'''
        
        with open(f'{self.dr_dir}/test-disaster-recovery.sh', 'w', encoding='utf-8') as f:
            f.write(dr_test_script)
        
        os.chmod(f'{self.dr_dir}/test-disaster-recovery.sh', 0o755)
        
        logger.info("Disaster recovery system created")
    
    def create_automated_backup_system(self):
        """Create comprehensive automated backup system"""
        
        # Enhanced backup script
        backup_script = '''#!/bin/bash
# GameForge AI Enhanced Production Backup System
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="/backups"
LOG_FILE="/var/log/gameforge/backup.log"
RETENTION_DAYS=30

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create backup directory with timestamp
create_backup_dir() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    CURRENT_BACKUP_DIR="$BACKUP_DIR/backup_$TIMESTAMP"
    mkdir -p "$CURRENT_BACKUP_DIR"
    echo "$CURRENT_BACKUP_DIR"
}

# Database backup with compression
backup_database() {
    local backup_dir="$1"
    log "Starting database backup..."
    
    # PostgreSQL backup
    pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$backup_dir/database.sql.gz"
    
    # Redis backup
    redis-cli -h "$REDIS_HOST" BGSAVE
    sleep 5
    cp /var/lib/redis/dump.rdb "$backup_dir/redis.rdb"
    
    # Calculate checksums
    cd "$backup_dir"
    sha256sum database.sql.gz redis.rdb > checksums.txt
    
    log "Database backup completed"
}

# Application data backup
backup_application_data() {
    local backup_dir="$1"
    log "Starting application data backup..."
    
    # User uploads
    if [ -d "/app/uploads" ]; then
        tar -czf "$backup_dir/uploads.tar.gz" -C /app uploads/
    fi
    
    # Configuration files
    tar -czf "$backup_dir/config.tar.gz" -C /etc gameforge/
    
    # Logs (recent only)
    find /var/log/gameforge -name "*.log" -mtime -7 | tar -czf "$backup_dir/logs.tar.gz" -T -
    
    log "Application data backup completed"
}

# Model artifacts backup
backup_models() {
    local backup_dir="$1"
    log "Starting model backup..."
    
    # Model files
    if [ -d "/models" ]; then
        tar -czf "$backup_dir/models.tar.gz" -C /models .
    fi
    
    # Model metadata
    if [ -f "/app/model_registry.json" ]; then
        cp /app/model_registry.json "$backup_dir/"
    fi
    
    log "Model backup completed"
}

# Upload to cloud storage
upload_to_cloud() {
    local backup_dir="$1"
    log "Uploading backup to cloud storage..."
    
    # Create archive
    cd "$(dirname "$backup_dir")"
    tar -czf "$(basename "$backup_dir").tar.gz" "$(basename "$backup_dir")"
    
    # Upload to S3
    if [ -n "$AWS_S3_BUCKET" ]; then
        aws s3 cp "$(basename "$backup_dir").tar.gz" "s3://$AWS_S3_BUCKET/backups/"
        log "Backup uploaded to S3"
    fi
    
    # Upload to Azure Blob
    if [ -n "$AZURE_STORAGE_ACCOUNT" ]; then
        az storage blob upload \\
            --account-name "$AZURE_STORAGE_ACCOUNT" \\
            --container-name backups \\
            --name "$(basename "$backup_dir").tar.gz" \\
            --file "$(basename "$backup_dir").tar.gz"
        log "Backup uploaded to Azure Blob"
    fi
    
    # Clean up local archive
    rm "$(basename "$backup_dir").tar.gz"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Local cleanup
    find "$BACKUP_DIR" -type d -name "backup_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \\;
    
    # S3 cleanup
    if [ -n "$AWS_S3_BUCKET" ]; then
        aws s3 ls "s3://$AWS_S3_BUCKET/backups/" | awk '{print $4}' | while read -r file; do
            file_date=$(echo "$file" | grep -o '[0-9]\\{8\\}')
            if [ -n "$file_date" ] && [ "$file_date" -lt "$(date -d "-$RETENTION_DAYS days" +%Y%m%d)" ]; then
                aws s3 rm "s3://$AWS_S3_BUCKET/backups/$file"
            fi
        done
    fi
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    local backup_dir="$1"
    log "Verifying backup integrity..."
    
    cd "$backup_dir"
    
    # Verify checksums
    if sha256sum -c checksums.txt; then
        log "✅ Backup integrity verified"
        return 0
    else
        log "❌ Backup integrity check failed"
        return 1
    fi
}

# Send backup notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Slack notification
    curl -X POST "$WEBHOOK_URL" \\
         -H "Content-Type: application/json" \\
         -d "{\\"text\\": \\"Backup $status: $message\\"}"
    
    # Email notification
    echo "$message" | mail -s "GameForge Backup $status" "$EMAIL_ALERTS"
}

main() {
    log "Starting enhanced backup process..."
    
    # Create backup directory
    BACKUP_DIR_CURRENT=$(create_backup_dir)
    
    # Perform backups
    backup_database "$BACKUP_DIR_CURRENT"
    backup_application_data "$BACKUP_DIR_CURRENT"
    backup_models "$BACKUP_DIR_CURRENT"
    
    # Verify backup
    if verify_backup "$BACKUP_DIR_CURRENT"; then
        # Upload to cloud
        upload_to_cloud "$BACKUP_DIR_CURRENT"
        
        # Cleanup old backups
        cleanup_old_backups
        
        send_notification "SUCCESS" "Backup completed successfully: $(basename "$BACKUP_DIR_CURRENT")"
        log "Backup process completed successfully"
    else
        send_notification "FAILED" "Backup integrity check failed: $(basename "$BACKUP_DIR_CURRENT")"
        log "Backup process failed - integrity check failed"
        exit 1
    fi
}

# Error handling
trap 'send_notification "FAILED" "Backup process failed: $BASH_COMMAND"; exit 1' ERR

main "$@"
'''
        
        with open(f'{self.backups_dir}/enhanced-backup.sh', 'w', encoding='utf-8') as f:
            f.write(backup_script)
        
        os.chmod(f'{self.backups_dir}/enhanced-backup.sh', 0o755)
        
        logger.info("Automated backup system created")
    
    def create_operations_dashboard_config(self):
        """Create operations monitoring dashboard"""
        
        # Grafana dashboard for operations
        dashboard_config = {
            'dashboard': {
                'id': None,
                'title': 'GameForge AI - Operations Dashboard',
                'description': 'Comprehensive operations monitoring and alerting',
                'tags': ['gameforge', 'operations', 'production'],
                'timezone': 'browser',
                'time': {
                    'from': 'now-1h',
                    'to': 'now'
                },
                'refresh': '30s',
                'panels': [
                    {
                        'id': 1,
                        'title': 'System Health Overview',
                        'type': 'stat',
                        'targets': [
                            {
                                'expr': 'up{job="gameforge"}',
                                'legendFormat': 'Services Up'
                            }
                        ],
                        'gridPos': {'h': 4, 'w': 6, 'x': 0, 'y': 0}
                    },
                    {
                        'id': 2,
                        'title': 'Backup Status',
                        'type': 'table',
                        'targets': [
                            {
                                'expr': 'backup_last_success_timestamp',
                                'legendFormat': 'Last Backup'
                            }
                        ],
                        'gridPos': {'h': 4, 'w': 6, 'x': 6, 'y': 0}
                    },
                    {
                        'id': 3,
                        'title': 'Secret Rotation Status',
                        'type': 'stat',
                        'targets': [
                            {
                                'expr': 'secret_rotation_last_success_timestamp',
                                'legendFormat': 'Last Rotation'
                            }
                        ],
                        'gridPos': {'h': 4, 'w': 6, 'x': 12, 'y': 0}
                    },
                    {
                        'id': 4,
                        'title': 'Disaster Recovery Test Status',
                        'type': 'stat',
                        'targets': [
                            {
                                'expr': 'dr_test_last_success_timestamp',
                                'legendFormat': 'Last DR Test'
                            }
                        ],
                        'gridPos': {'h': 4, 'w': 6, 'x': 18, 'y': 0}
                    }
                ]
            }
        }
        
        with open(f'{self.ops_dir}/operations-dashboard.json', 'w', encoding='utf-8') as f:
            json.dump(dashboard_config, f, indent=2)
        
        logger.info("Operations dashboard configuration created")

def main():
    """Create all operations management configurations"""
    logger.info("Creating comprehensive operations management system...")
    
    ops_manager = OperationsManager()
    
    ops_manager.create_automated_scheduling_system()
    ops_manager.create_secret_rotation_system()
    ops_manager.create_disaster_recovery_system()
    ops_manager.create_automated_backup_system()
    ops_manager.create_operations_dashboard_config()
    
    logger.info("\nALL OPERATIONS SYSTEMS CREATED")
    logger.info("Key components:")
    logger.info("1. Automated scheduling: ops/schedules/ (cron + K8s CronJobs)")
    logger.info("2. Secret rotation: ops/secrets/rotate-secrets.sh")
    logger.info("3. Disaster recovery: ops/disaster-recovery/test-disaster-recovery.sh")
    logger.info("4. Enhanced backups: ops/backups/enhanced-backup.sh")
    logger.info("5. Operations dashboard: ops/operations-dashboard.json")

if __name__ == "__main__":
    main()