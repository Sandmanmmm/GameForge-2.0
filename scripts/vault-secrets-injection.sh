#!/bin/bash
# ========================================================================
# Vault Secrets Injection Script
# Replaces hard-coded environment variables with Vault secrets
# ========================================================================

set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
VAULT_NAMESPACE="${VAULT_NAMESPACE:-gameforge}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Wait for Vault to be available
wait_for_vault() {
    log "Waiting for Vault to be available..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
            log "Vault is available"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log "Vault not ready, attempt $attempt/$max_attempts"
        sleep 2
    done
    
    error "Vault failed to become available after $max_attempts attempts"
    return 1
}

# Initialize Vault with secrets
init_vault_secrets() {
    log "Initializing Vault secrets..."
    
    # Enable KV v2 secrets engine
    vault secrets enable -path=secret kv-v2 2>/dev/null || true
    
    # Create database secrets
    vault kv put secret/database \
        postgres_password="$(openssl rand -base64 32)" \
        postgres_user="gameforge" \
        postgres_db="gameforge_prod"
    
    # Create Redis secrets
    vault kv put secret/redis \
        redis_password="$(openssl rand -base64 32)"
    
    # Create Elasticsearch secrets
    vault kv put secret/elasticsearch \
        elastic_password="$(openssl rand -base64 32)" \
        elastic_user="elastic"
    
    # Create application secrets
    vault kv put secret/application \
        jwt_secret="$(openssl rand -base64 64)" \
        app_secret="$(openssl rand -base64 64)" \
        encryption_key="$(openssl rand -base64 32)"
    
    # Create MinIO secrets
    vault kv put secret/minio \
        root_user="gameforge-admin" \
        root_password="$(openssl rand -base64 32)" \
        access_key="gameforge-models-access" \
        secret_key="$(openssl rand -base64 64)"
    
    log "Vault secrets initialized successfully"
}

# Fetch secret from Vault
get_vault_secret() {
    local path="$1"
    local field="$2"
    
    vault kv get -field="$field" "secret/$path" 2>/dev/null || {
        error "Failed to retrieve secret from $path/$field"
        return 1
    }
}

# Export secrets as environment variables
export_vault_secrets() {
    log "Exporting secrets from Vault..."
    
    # Database secrets
    export POSTGRES_PASSWORD=$(get_vault_secret "database" "postgres_password")
    export POSTGRES_USER=$(get_vault_secret "database" "postgres_user")
    export POSTGRES_DB=$(get_vault_secret "database" "postgres_db")
    
    # Redis secrets
    export REDIS_PASSWORD=$(get_vault_secret "redis" "redis_password")
    
    # Elasticsearch secrets
    export ELASTIC_PASSWORD=$(get_vault_secret "elasticsearch" "elastic_password")
    export ELASTIC_USER=$(get_vault_secret "elasticsearch" "elastic_user")
    
    # Application secrets
    export JWT_SECRET_KEY=$(get_vault_secret "application" "jwt_secret")
    export SECRET_KEY=$(get_vault_secret "application" "app_secret")
    export ENCRYPTION_KEY=$(get_vault_secret "application" "encryption_key")
    
    # MinIO secrets
    export MINIO_ROOT_USER=$(get_vault_secret "minio" "root_user")
    export MINIO_ROOT_PASSWORD=$(get_vault_secret "minio" "root_password")
    export MINIO_ACCESS_KEY=$(get_vault_secret "minio" "access_key")
    export MINIO_SECRET_KEY=$(get_vault_secret "minio" "secret_key")
    
    log "All secrets exported successfully"
}

# Create .env file with secrets
create_env_file() {
    log "Creating .env file with Vault secrets..."
    
    cat > .env.vault << EOF
# ========================================================================
# Environment variables from Vault
# Generated on $(date)
# ========================================================================

# Database Configuration
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_DB=${POSTGRES_DB}

# Redis Configuration
REDIS_PASSWORD=${REDIS_PASSWORD}

# Elasticsearch Configuration
ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
ELASTIC_USER=${ELASTIC_USER}

# Application Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# MinIO Configuration
MINIO_ROOT_USER=${MINIO_ROOT_USER}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY}

# Vault Configuration
VAULT_ADDR=${VAULT_ADDR}
VAULT_TOKEN=${VAULT_TOKEN}
VAULT_NAMESPACE=${VAULT_NAMESPACE}
EOF

    chmod 600 .env.vault
    log "Environment file created: .env.vault"
}

# Main execution
main() {
    log "Starting Vault secrets injection..."
    
    # Check if Vault token is provided
    if [ -z "$VAULT_TOKEN" ]; then
        error "VAULT_TOKEN environment variable is required"
        exit 1
    fi
    
    # Set Vault environment
    export VAULT_ADDR
    export VAULT_TOKEN
    
    # Wait for Vault to be available
    wait_for_vault
    
    # Initialize secrets in Vault
    init_vault_secrets
    
    # Export secrets to environment
    export_vault_secrets
    
    # Create .env file
    create_env_file
    
    log "Vault secrets injection completed successfully"
    log "Use: docker-compose --env-file .env.vault up -d"
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi