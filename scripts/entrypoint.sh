#!/bin/bash
set -e

# GameForge Application Entrypoint Script
# This script handles the startup of the GameForge FastAPI application
# with proper uvicorn/gunicorn configuration based on environment

# Set default values
export GAMEFORGE_ENV=${GAMEFORGE_ENV:-production}
export WORKERS=${WORKERS:-4}
export MAX_WORKERS=${MAX_WORKERS:-8}
export WORKER_TIMEOUT=${WORKER_TIMEOUT:-300}
export WORKER_CLASS=${WORKER_CLASS:-uvicorn.workers.UvicornWorker}
export LOG_LEVEL=${LOG_LEVEL:-info}

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Wait for dependencies
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1
    
    log "Waiting for $service_name at $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log "$service_name is ready!"
            return 0
        fi
        log "Attempt $attempt/$max_attempts: $service_name not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log "ERROR: $service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Parse database URL to extract host and port
parse_db_url() {
    local db_url=$1
    # Extract host and port from postgresql://user:pass@host:port/db
    local host_port=$(echo "$db_url" | sed -n 's/.*@\([^:]*\):\([0-9]*\).*/\1 \2/p')
    echo $host_port
}

# Pre-flight checks
pre_flight_checks() {
    log "🔍 Running pre-flight checks..."
    
    # Check required environment variables
    if [ -z "$DATABASE_URL" ]; then
        log "ERROR: DATABASE_URL environment variable is required"
        exit 1
    fi
    
    if [ -z "$REDIS_URL" ]; then
        log "ERROR: REDIS_URL environment variable is required"
        exit 1
    fi
    
    # Wait for database
    db_info=$(parse_db_url "$DATABASE_URL")
    if [ -n "$db_info" ]; then
        set -- $db_info
        wait_for_service "$1" "$2" "PostgreSQL"
    else
        log "WARNING: Could not parse database URL, skipping database check"
    fi
    
    # Wait for Redis
    redis_host=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\):\([0-9]*\).*/\1/p')
    redis_port=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\):\([0-9]*\).*/\2/p')
    
    if [ -n "$redis_host" ] && [ -n "$redis_port" ]; then
        wait_for_service "$redis_host" "$redis_port" "Redis"
    else
        log "WARNING: Could not parse Redis URL, skipping Redis check"
    fi
    
    log "✅ Pre-flight checks completed"
}

# Model download and cache setup
setup_models() {
    log "🤖 Setting up model cache..."
    
    # Create model cache directory if it doesn't exist
    mkdir -p /tmp/models
    
    # Download required models if specified
    if [ -n "$REQUIRED_MODELS" ]; then
        log "📥 Downloading required models: $REQUIRED_MODELS"
        python -c "
import os
import asyncio
from gameforge.core.config import get_settings

async def download_models():
    settings = get_settings()
    models = os.getenv('REQUIRED_MODELS', '').split(',')
    for model in models:
        if model.strip():
            print(f'📥 Would download model: {model.strip()}')
            # TODO: Implement actual model download logic

if __name__ == '__main__':
    asyncio.run(download_models())
" || log "WARNING: Model download failed, continuing..."
    fi
    
    log "✅ Model cache setup completed"
}

# GPU setup and validation
setup_gpu() {
    if [ "$ENABLE_GPU" = "true" ]; then
        log "🎮 Setting up GPU configuration..."
        
        # Check if NVIDIA GPU is available
        if command -v nvidia-smi >/dev/null 2>&1; then
            log "🎮 NVIDIA GPU detected:"
            nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits
            
            # Set GPU memory configuration
            export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-max_split_size_mb:512,garbage_collection_threshold:0.6,expandable_segments:True}
            export CUDA_LAUNCH_BLOCKING=${CUDA_LAUNCH_BLOCKING:-0}
            export CUDA_CACHE_DISABLE=${CUDA_CACHE_DISABLE:-0}
            export PYTORCH_JIT=${PYTORCH_JIT:-1}
            
            log "✅ GPU configuration completed"
        else
            log "⚠️  NVIDIA GPU not detected, running in CPU mode"
            export ENABLE_GPU=false
        fi
    else
        log "💻 Running in CPU mode"
    fi
}

# Security setup
setup_security() {
    log "🔒 Setting up security configuration..."
    
    # Ensure log directory exists with proper permissions
    mkdir -p /app/logs
    chmod 755 /app/logs
    
    # Ensure cache directory exists with proper permissions
    mkdir -p /app/cache
    chmod 755 /app/cache
    
    # Set file permissions for sensitive files
    if [ -f "/app/.env" ]; then
        chmod 600 /app/.env
    fi
    
    log "✅ Security setup completed"
}

# Application startup
start_application() {
    log "🚀 Starting GameForge application..."
    
    case "$GAMEFORGE_ENV" in
        "development")
            log "🔧 Starting in development mode with uvicorn..."
            exec python -m uvicorn gameforge.app:app \
                --host 0.0.0.0 \
                --port 8080 \
                --reload \
                --log-level "$LOG_LEVEL" \
                --access-log
            ;;
        "production")
            log "🏭 Starting in production mode with gunicorn..."
            exec gunicorn \
                --config gunicorn.conf.py \
                --bind 0.0.0.0:8080 \
                --workers "$WORKERS" \
                --worker-class "$WORKER_CLASS" \
                --timeout "$WORKER_TIMEOUT" \
                --log-level "$LOG_LEVEL" \
                --access-logfile - \
                --error-logfile - \
                gameforge.app:app
            ;;
        "testing")
            log "🧪 Starting in testing mode..."
            exec python -m uvicorn gameforge.app:app \
                --host 0.0.0.0 \
                --port 8080 \
                --log-level debug
            ;;
        *)
            log "ERROR: Unknown GAMEFORGE_ENV: $GAMEFORGE_ENV"
            log "Valid values: development, production, testing"
            exit 1
            ;;
    esac
}

# Signal handlers
handle_signal() {
    log "📡 Received signal, shutting down gracefully..."
    # The application will handle graceful shutdown via lifespan
    exit 0
}

# Trap signals
trap handle_signal SIGTERM SIGINT

# Main execution
main() {
    log "🎮 GameForge Application Entrypoint"
    log "Environment: $GAMEFORGE_ENV"
    log "Workers: $WORKERS"
    log "Worker Class: $WORKER_CLASS"
    log "Worker Timeout: ${WORKER_TIMEOUT}s"
    
    # Run startup phases
    pre_flight_checks
    setup_security
    setup_gpu
    setup_models
    
    # Calculate startup duration
    startup_duration=$(($(date +%s) - ${STARTUP_TIME:-$(date +%s)}))
    log "✅ Startup phases completed successfully in ${startup_duration}s"
    log "🚀 Launching GameForge AI application..."
    
    # Start the application (this will exec and replace the shell)
    start_application
}

# Execute main function
main "$@"