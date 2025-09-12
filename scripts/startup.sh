#!/bin/bash
# ========================================================================
# GameForge AI Production Startup Script
# Handles model download, database migration, and application startup
# ========================================================================

set -euo pipefail

# Configuration
export LOG_FILE="/app/logs/startup.log"
export CORRELATION_ID="${REQUEST_ID:-startup-$(date +%Y%m%d-%H%M%S)}"
export STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-300}"  # 5 minutes

# Ensure log directory exists
mkdir -p /app/logs /app/temp

# Logging function with JSON format
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    echo "{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"module\":\"startup\",\"message\":\"$message\",\"correlation_id\":\"$CORRELATION_ID\"}" | tee -a "$LOG_FILE"
}

log "INFO" "🚀 GameForge AI Production Startup - BEGIN"
log "INFO" "Correlation ID: $CORRELATION_ID"

# ========================================================================
# Health Check Functions
# ========================================================================

check_dependencies() {
    log "INFO" "Checking external dependencies..."
    
    # Check MinIO connectivity
    if ! curl -f -s --max-time 10 "http://${MINIO_ENDPOINT}/minio/health/live" > /dev/null; then
        log "ERROR" "MinIO not accessible at ${MINIO_ENDPOINT}"
        return 1
    fi
    log "INFO" "✅ MinIO connectivity verified"
    
    # Check PostgreSQL connectivity
    if ! python3 -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); conn.close()" 2>/dev/null; then
        log "WARN" "PostgreSQL not immediately available, will retry during migration"
    else
        log "INFO" "✅ PostgreSQL connectivity verified"
    fi
    
    # Check Redis connectivity
    if ! python3 -c "import redis; r = redis.from_url('$REDIS_URL'); r.ping()" 2>/dev/null; then
        log "WARN" "Redis not immediately available"
    else
        log "INFO" "✅ Redis connectivity verified"
    fi
    
    return 0
}

# ========================================================================
# Model Download Phase
# ========================================================================

download_models() {
    log "INFO" "📦 Starting model download phase..."
    
    # Check if models are already cached and valid
    if python3 /app/scripts/download-models.py --validate 2>/dev/null | grep -q "✅ Valid"; then
        log "INFO" "Models already cached and valid, skipping download"
        return 0
    fi
    
    # Download required models
    log "INFO" "Downloading required models from MinIO..."
    if python3 /app/scripts/download-models.py --required-only; then
        log "INFO" "✅ Model download completed successfully"
        return 0
    else
        log "ERROR" "❌ Model download failed"
        return 1
    fi
}

# ========================================================================
# Database Migration Phase
# ========================================================================

run_database_migrations() {
    log "INFO" "🔄 Starting database migration phase..."
    
    # Wait for PostgreSQL to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python3 /app/scripts/migrate-database.py --check-connection; then
            log "INFO" "✅ Database connection established"
            break
        fi
        
        log "INFO" "Waiting for database... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log "ERROR" "❌ Database connection timeout"
        return 1
    fi
    
    # Run migrations
    if python3 /app/scripts/migrate-database.py --migrate; then
        log "INFO" "✅ Database migrations completed"
        return 0
    else
        log "ERROR" "❌ Database migrations failed"
        return 1
    fi
}

# ========================================================================
# Application Startup Phase
# ========================================================================

start_application() {
    log "INFO" "🎮 Starting GameForge application..."
    
    # Verify models are available
    if [ ! -d "/app/models" ] || [ -z "$(ls -A /app/models)" ]; then
        log "ERROR" "❌ Model directory is empty or missing"
        return 1
    fi
    
    # Set production environment variables
    export PROMETHEUS_MULTIPROC_DIR="/tmp/prometheus_multiproc"
    export GAMEFORGE_CONFIG_FILE="/app/config/production.yaml"
    export GAMEFORGE_LOG_CONFIG="/app/config/logging.json"
    
    # Create prometheus metrics directory
    mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
    
    # Start the application with metrics enabled
    log "INFO" "Launching GameForge with production configuration..."
    exec python3 -m uvicorn gameforge_metrics_app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --access-log \
        --log-config /app/config/logging.json \
        --loop uvloop \
        --http httptools
}

# ========================================================================
# Cleanup and Signal Handling
# ========================================================================

cleanup() {
    log "INFO" "🧹 Performing cleanup..."
    
    # Clean up temporary files
    if [ -d "/app/temp" ]; then
        find /app/temp -type f -mtime +1 -delete 2>/dev/null || true
    fi
    
    # Clean up old model versions (keep last 2 versions)
    python3 /app/scripts/download-models.py --cleanup 2>/dev/null || true
    
    log "INFO" "✅ Cleanup completed"
}

# Signal handlers
trap 'log "WARN" "Received SIGTERM, shutting down gracefully..."; cleanup; exit 0' TERM
trap 'log "WARN" "Received SIGINT, shutting down..."; cleanup; exit 0' INT

# ========================================================================
# Startup Validation Phase
# ========================================================================

validate_startup_environment() {
    log "INFO" "🔍 Validating startup environment..."
    
    # Check required environment variables
    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL" 
        "MINIO_ENDPOINT"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log "ERROR" "Required environment variable missing: $var"
            return 1
        fi
    done
    
    # Check disk space
    local available_space=$(df /app | awk 'NR==2 {print $4}')
    local required_space=10485760  # 10GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        log "ERROR" "Insufficient disk space: $(($available_space/1024/1024))GB available, 10GB required"
        return 1
    fi
    
    # Check GPU availability
    if command -v nvidia-smi >/dev/null 2>&1; then
        if nvidia-smi > /dev/null 2>&1; then
            local gpu_count=$(nvidia-smi --list-gpus | wc -l)
            log "INFO" "✅ GPU environment validated: $gpu_count GPU(s) available"
        else
            log "WARN" "⚠️ nvidia-smi failed, GPU may not be available"
        fi
    else
        log "WARN" "⚠️ nvidia-smi not found, running in CPU-only mode"
    fi
    
    log "INFO" "✅ Startup environment validation completed"
    return 0
}

# ========================================================================
# Main Startup Sequence
# ========================================================================

main() {
    local start_time=$(date +%s)
    
    # Run startup phases in sequence
    validate_startup_environment || {
        log "ERROR" "Environment validation failed"
        exit 1
    }
    
    check_dependencies || {
        log "ERROR" "Dependency check failed"
        exit 1
    }
    
    download_models || {
        log "ERROR" "Model download failed"
        exit 1
    }
    
    run_database_migrations || {
        log "ERROR" "Database migration failed"
        exit 1
    }
    
    # Calculate startup time
    local end_time=$(date +%s)
    local startup_duration=$((end_time - start_time))
    
    log "INFO" "🎯 Startup phases completed successfully in ${startup_duration}s"
    log "INFO" "🚀 Launching GameForge AI application..."
    
    # Start the application (this will exec and replace the shell)
    start_application
}

# Execute main function
main "$@"