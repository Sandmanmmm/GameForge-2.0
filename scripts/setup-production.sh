#!/bin/bash
# ========================================================================
# GameForge Production Environment Setup Script
# Creates necessary directories, sets permissions, and initializes environment
# ========================================================================

set -euo pipefail

echo "========================================================================"
echo "GameForge Production Environment Setup"
echo "========================================================================"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to create directory with proper permissions
create_dir() {
    local dir=$1
    local user=${2:-root}
    local group=${3:-root}
    local permissions=${4:-755}
    
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        chown "$user:$group" "$dir"
        chmod "$permissions" "$dir"
        log "✓ Created directory: $dir (${user}:${group}, ${permissions})"
    else
        log "Directory already exists: $dir"
    fi
}

# ========================================================================
# Environment Validation
# ========================================================================
log "Validating environment..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root for proper permissions setup"
    exit 1
fi

# Check Docker installation
if ! command -v docker >/dev/null 2>&1; then
    log "✗ Docker not found. Please install Docker first."
    exit 1
fi

# Check Docker Compose installation
if ! command -v docker-compose >/dev/null 2>&1; then
    log "✗ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

log "✓ Environment validation passed"

# ========================================================================
# Create Directory Structure
# ========================================================================
log "Creating production directory structure..."

# Application directories
create_dir "./volumes" "root" "root" "755"
create_dir "./volumes/logs" "1001" "1001" "755"
create_dir "./volumes/cache" "1001" "1001" "755"
create_dir "./volumes/assets" "1001" "1001" "755"
create_dir "./volumes/models" "1001" "1001" "755"
create_dir "./volumes/static" "1001" "1001" "755"

# Database directories
create_dir "./volumes/postgres" "999" "999" "700"
create_dir "./volumes/postgres-logs" "999" "999" "755"
create_dir "./volumes/redis" "999" "999" "755"

# Search and analytics
create_dir "./volumes/elasticsearch" "1000" "1000" "755"
create_dir "./volumes/elasticsearch-logs" "1000" "1000" "755"

# Infrastructure directories
create_dir "./volumes/nginx-logs" "101" "101" "755"
create_dir "./volumes/backup-logs" "1002" "1002" "755"
create_dir "./volumes/certbot-logs" "1003" "1003" "755"

# SSL directories
create_dir "./ssl" "root" "root" "755"
create_dir "./ssl/certs" "root" "root" "755"
create_dir "./ssl/private" "root" "root" "700"

# Configuration directories
create_dir "./nginx/conf.d" "root" "root" "755"
create_dir "./elasticsearch/config" "1000" "1000" "755"

log "✓ Directory structure created"

# ========================================================================
# Create Environment Files
# ========================================================================
log "Creating environment configuration..."

# Create .env.production if it doesn't exist
if [ ! -f ".env.production" ]; then
    cat > .env.production << 'EOF'
# GameForge Production Environment Configuration
# ========================================================================
# IMPORTANT: Update all default passwords and secrets before deployment!
# ========================================================================

# Application Configuration
GAMEFORGE_ENV=production
SECRET_KEY=your-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-change-this
LOG_LEVEL=info

# Database Configuration
POSTGRES_PASSWORD=change-this-postgres-password
REDIS_PASSWORD=change-this-redis-password
ELASTIC_PASSWORD=change-this-elastic-password

# OAuth Configuration
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret

# SSL Configuration
DOMAIN=gameforge.local
CERTBOT_EMAIL=admin@gameforge.local

# Backup Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BACKUP_BUCKET=gameforge-backups
AWS_REGION=us-east-1
BACKUP_RETENTION_DAYS=15

# Monitoring Configuration
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_RETENTION_TIME=15d
GRAFANA_ADMIN_PASSWORD=change-this-grafana-password

# Security Configuration
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_MINUTE=60
ALLOWED_HOSTS=gameforge.local,localhost,127.0.0.1

# GPU Configuration
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
EOF

    log "✓ Created .env.production (PLEASE UPDATE PASSWORDS AND SECRETS!)"
else
    log "Environment file already exists: .env.production"
fi

# ========================================================================
# Initialize Nginx Configuration
# ========================================================================
if [ ! -f "nginx/nginx.conf" ]; then
    log "Creating default Nginx configuration..."
    
    cat > nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Security headers
    server_tokens off;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    include /etc/nginx/conf.d/*.conf;
}
EOF

    cat > nginx/conf.d/gameforge.conf << 'EOF'
upstream gameforge_backend {
    server gameforge-app:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/gameforge.crt;
    ssl_certificate_key /etc/ssl/private/gameforge.key;
    
    # Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Proxy configuration
    location / {
        proxy_pass http://gameforge_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

    log "✓ Created Nginx configuration files"
fi

# ========================================================================
# Set Final Permissions
# ========================================================================
log "Setting final permissions..."

# Make scripts executable
find . -name "*.sh" -type f -exec chmod +x {} \;

# Set proper ownership for configuration files
chown -R root:root nginx/
chown -R root:root ssl/
chown -R 1000:1000 elasticsearch/ 2>/dev/null || true

log "✓ Permissions set"

# ========================================================================
# Generate Self-Signed SSL Certificate (for testing)
# ========================================================================
if [ ! -f "ssl/certs/gameforge.crt" ]; then
    log "Generating self-signed SSL certificate for testing..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/private/gameforge.key \
        -out ssl/certs/gameforge.crt \
        -subj "/C=US/ST=State/L=City/O=GameForge/OU=IT/CN=gameforge.local"
    
    chmod 600 ssl/private/gameforge.key
    chmod 644 ssl/certs/gameforge.crt
    
    log "✓ Self-signed SSL certificate generated"
    log "⚠ Remember to replace with proper SSL certificates in production!"
fi

# ========================================================================
# Final Setup Summary
# ========================================================================
echo "========================================================================"
echo "GameForge Production Environment Setup Complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Update passwords and secrets in .env.production"
echo "2. Configure OAuth credentials"
echo "3. Set up proper SSL certificates (replace self-signed)"
echo "4. Configure AWS credentials for backups"
echo "5. Review and customize configuration files as needed"
echo ""
echo "To start the production environment:"
echo "  docker-compose -f docker-compose.production-secure.yml --env-file .env.production up -d"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.production-secure.yml logs -f"
echo ""
echo "To check status:"
echo "  docker-compose -f docker-compose.production-secure.yml ps"
echo ""
echo "⚠ IMPORTANT: This setup uses default passwords. Update them before deployment!"
echo "========================================================================"
