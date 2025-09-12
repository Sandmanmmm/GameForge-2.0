#!/bin/bash
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
        az storage blob upload \
            --account-name "$AZURE_STORAGE_ACCOUNT" \
            --container-name backups \
            --name "$(basename "$backup_dir").tar.gz" \
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
    find "$BACKUP_DIR" -type d -name "backup_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;
    
    # S3 cleanup
    if [ -n "$AWS_S3_BUCKET" ]; then
        aws s3 ls "s3://$AWS_S3_BUCKET/backups/" | awk '{print $4}' | while read -r file; do
            file_date=$(echo "$file" | grep -o '[0-9]\{8\}')
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
    curl -X POST "$WEBHOOK_URL" \
         -H "Content-Type: application/json" \
         -d "{\"text\": \"Backup $status: $message\"}"
    
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
