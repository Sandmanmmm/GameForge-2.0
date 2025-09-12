# ========================================================================
# GameForge Production Environment Setup Script (PowerShell)
# Creates necessary directories, sets permissions, and initializes environment
# ========================================================================

param(
    [switch]$Force,
    [string]$Domain = "gameforge.local",
    [string]$Email = "admin@gameforge.local"
)

# Set error handling
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] ⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] ✗ $Message" -ForegroundColor Red
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "GameForge Production Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# ========================================================================
# Environment Validation
# ========================================================================
Write-Log "Validating environment..."

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator for proper permissions setup"
    exit 1
}

# Check Docker installation
try {
    $dockerVersion = docker --version
    Write-Log "✓ Docker found: $dockerVersion"
} catch {
    Write-Error "Docker not found. Please install Docker Desktop first."
    exit 1
}

# Check Docker Compose installation
try {
    $composeVersion = docker-compose --version
    Write-Log "✓ Docker Compose found: $composeVersion"
} catch {
    Write-Error "Docker Compose not found. Please install Docker Compose first."
    exit 1
}

Write-Log "✓ Environment validation passed"

# ========================================================================
# Create Directory Structure
# ========================================================================
Write-Log "Creating production directory structure..."

$directories = @(
    "volumes",
    "volumes/logs",
    "volumes/cache", 
    "volumes/assets",
    "volumes/models",
    "volumes/static",
    "volumes/postgres",
    "volumes/postgres-logs",
    "volumes/redis",
    "volumes/elasticsearch",
    "volumes/elasticsearch-logs",
    "volumes/nginx-logs",
    "volumes/backup-logs",
    "volumes/certbot-logs",
    "ssl",
    "ssl/certs",
    "ssl/private",
    "nginx/conf.d",
    "elasticsearch/config"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Log "✓ Created directory: $dir"
    } else {
        Write-Log "Directory already exists: $dir"
    }
}

Write-Log "✓ Directory structure created"

# ========================================================================
# Create Environment Files
# ========================================================================
Write-Log "Creating environment configuration..."

if (-not (Test-Path ".env.production") -or $Force) {
    $envContent = @"
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
DOMAIN=$Domain
CERTBOT_EMAIL=$Email

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
ALLOWED_HOSTS=$Domain,localhost,127.0.0.1

# GPU Configuration
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
"@

    $envContent | Out-File -FilePath ".env.production" -Encoding UTF8
    Write-Log "✓ Created .env.production (PLEASE UPDATE PASSWORDS AND SECRETS!)"
} else {
    Write-Log "Environment file already exists: .env.production"
}

# ========================================================================
# Initialize Nginx Configuration
# ========================================================================
if (-not (Test-Path "nginx/nginx.conf") -or $Force) {
    Write-Log "Creating default Nginx configuration..."
    
    $nginxConf = @"
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
    log_format main '`$remote_addr - `$remote_user [`$time_local] "`$request" '
                    '`$status `$body_bytes_sent "`$http_referer" '
                    '"`$http_user_agent" "`$http_x_forwarded_for"';
    
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
"@

    $nginxConf | Out-File -FilePath "nginx/nginx.conf" -Encoding UTF8

    $gameforgeConf = @"
upstream gameforge_backend {
    server gameforge-app:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    return 301 https://`$host`$request_uri;
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
    limit_req_zone `$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Proxy configuration
    location / {
        proxy_pass http://gameforge_backend;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
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
"@

    $gameforgeConf | Out-File -FilePath "nginx/conf.d/gameforge.conf" -Encoding UTF8
    Write-Log "✓ Created Nginx configuration files"
}

# ========================================================================
# Generate Self-Signed SSL Certificate (for testing)
# ========================================================================
if (-not (Test-Path "ssl/certs/gameforge.crt") -or $Force) {
    Write-Log "Generating self-signed SSL certificate for testing..."
    
    try {
        # Check if OpenSSL is available
        $opensslVersion = openssl version 2>$null
        
        # Generate private key
        openssl genrsa -out "ssl/private/gameforge.key" 2048
        
        # Generate certificate
        openssl req -new -x509 -key "ssl/private/gameforge.key" -out "ssl/certs/gameforge.crt" -days 365 -subj "/C=US/ST=State/L=City/O=GameForge/OU=IT/CN=$Domain"
        
        Write-Log "✓ Self-signed SSL certificate generated"
        Write-Warning "Remember to replace with proper SSL certificates in production!"
    } catch {
        Write-Warning "OpenSSL not found. You'll need to generate SSL certificates manually."
        Write-Warning "For testing, you can use Docker to generate certificates:"
        Write-Warning "docker run --rm -v `${PWD}/ssl:/ssl alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /ssl/private/gameforge.key -out /ssl/certs/gameforge.crt -subj '/C=US/ST=State/L=City/O=GameForge/OU=IT/CN=$Domain'"
    }
}

# ========================================================================
# Create Windows-specific Scripts
# ========================================================================
Write-Log "Creating Windows management scripts..."

$startScript = @"
# Start GameForge Production Environment
Write-Host "Starting GameForge Production Environment..." -ForegroundColor Green
docker-compose -f docker-compose.production-secure.yml --env-file .env.production up -d
Write-Host "Environment started. Access at https://$Domain" -ForegroundColor Green
"@

$startScript | Out-File -FilePath "start-production.ps1" -Encoding UTF8

$stopScript = @"
# Stop GameForge Production Environment
Write-Host "Stopping GameForge Production Environment..." -ForegroundColor Yellow
docker-compose -f docker-compose.production-secure.yml down
Write-Host "Environment stopped." -ForegroundColor Green
"@

$stopScript | Out-File -FilePath "stop-production.ps1" -Encoding UTF8

$statusScript = @"
# Check GameForge Production Environment Status
Write-Host "GameForge Production Environment Status:" -ForegroundColor Cyan
docker-compose -f docker-compose.production-secure.yml ps
Write-Host "`nTo view logs:" -ForegroundColor Yellow
Write-Host "docker-compose -f docker-compose.production-secure.yml logs -f" -ForegroundColor White
"@

$statusScript | Out-File -FilePath "status-production.ps1" -Encoding UTF8

Write-Log "✓ Created management scripts"

# ========================================================================
# Final Setup Summary
# ========================================================================
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "GameForge Production Environment Setup Complete!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update passwords and secrets in .env.production" -ForegroundColor White
Write-Host "2. Configure OAuth credentials" -ForegroundColor White
Write-Host "3. Set up proper SSL certificates (replace self-signed)" -ForegroundColor White
Write-Host "4. Configure AWS credentials for backups" -ForegroundColor White
Write-Host "5. Review and customize configuration files as needed" -ForegroundColor White
Write-Host ""
Write-Host "To start the production environment:" -ForegroundColor Yellow
Write-Host "  .\start-production.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To check status:" -ForegroundColor Yellow
Write-Host "  .\status-production.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To stop the environment:" -ForegroundColor Yellow
Write-Host "  .\stop-production.ps1" -ForegroundColor White
Write-Host ""
Write-Warning "IMPORTANT: This setup uses default passwords. Update them before deployment!"
Write-Host "========================================================================" -ForegroundColor Cyan
