#!/bin/bash
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
    LATEST_BACKUP=$(find /backups -name "*.tar.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2)
    
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
            test_results+=("{\"test\": \"$test\", \"status\": \"PASSED\", \"timestamp\": \"$(date -Iseconds)\"}")
        else
            test_results+=("{\"test\": \"$test\", \"status\": \"FAILED\", \"timestamp\": \"$(date -Iseconds)\"}")
        fi
    done
    
    # Generate report
    results_json="[$(IFS=,; echo "${test_results[*]}")]"
    generate_dr_report "$results_json"
    
    # Send notification
    failed_count=$(echo "$results_json" | jq 'map(select(.status == "FAILED")) | length')
    
    if [ "$failed_count" -eq 0 ]; then
        curl -X POST "$WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{\"text\": \"🎉 All disaster recovery tests PASSED\"}"
    else
        curl -X POST "$WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{\"text\": \"⚠️ $failed_count disaster recovery tests FAILED - immediate attention required\"}"
    fi
    
    log "Disaster recovery test completed"
}

main "$@"
