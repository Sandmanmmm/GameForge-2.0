# GameForge AI SSL Certificate Configuration
# Production-grade SSL setup with automated certificate management

# ====================================================================
# SSL Certificate Environment Variables
# ====================================================================

# SSL Certificate Paths
SSL_CERT_PATH=/etc/ssl/certs/gameforge.crt
SSL_KEY_PATH=/etc/ssl/private/gameforge.key
SSL_CA_PATH=/etc/ssl/certs/gameforge-ca.crt

# Let's Encrypt Configuration
LETSENCRYPT_EMAIL=admin@gameforge.ai
LETSENCRYPT_DOMAIN=gameforge.production.com
ACME_CHALLENGE_PATH=/var/www/acme-challenge

# Certificate Auto-Renewal
CERT_RENEWAL_ENABLED=true
CERT_RENEWAL_SCHEDULE="0 3 * * 0"  # Weekly at 3 AM Sunday

# SSL Security Settings
SSL_PROTOCOLS="TLSv1.2 TLSv1.3"
SSL_CIPHERS="ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
SSL_SESSION_TIMEOUT=1d
SSL_SESSION_CACHE=shared:SSL:50m

# HSTS Configuration
HSTS_MAX_AGE=31536000
HSTS_INCLUDE_SUBDOMAINS=true
HSTS_PRELOAD=true

# ====================================================================
# SSL Certificate Generation Script
# ====================================================================

#!/bin/bash
# generate-ssl-certs.sh - Generate self-signed certificates for development

generate_self_signed_cert() {
    echo "Generating self-signed SSL certificate for GameForge AI..."
    
    # Create SSL directories
    mkdir -p /etc/ssl/certs /etc/ssl/private
    
    # Generate private key
    openssl genrsa -out "${SSL_KEY_PATH}" 2048
    
    # Generate certificate signing request
    openssl req -new -key "${SSL_KEY_PATH}" -out /tmp/gameforge.csr -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/CN=gameforge.local"
    
    # Generate self-signed certificate
    openssl x509 -req -in /tmp/gameforge.csr -signkey "${SSL_KEY_PATH}" -out "${SSL_CERT_PATH}" -days 365
    
    # Set proper permissions
    chmod 600 "${SSL_KEY_PATH}"
    chmod 644 "${SSL_CERT_PATH}"
    
    echo "SSL certificate generated successfully"
}

# ====================================================================
# Let's Encrypt Certificate Management
# ====================================================================

#!/bin/bash
# letsencrypt-setup.sh - Setup Let's Encrypt certificates for production

setup_letsencrypt() {
    echo "Setting up Let's Encrypt certificates..."
    
    # Install certbot
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
    
    # Generate certificate
    certbot certonly --webroot \
        --webroot-path="${ACME_CHALLENGE_PATH}" \
        --email "${LETSENCRYPT_EMAIL}" \
        --agree-tos \
        --no-eff-email \
        -d "${LETSENCRYPT_DOMAIN}"
    
    # Link certificates to expected paths
    ln -sf "/etc/letsencrypt/live/${LETSENCRYPT_DOMAIN}/fullchain.pem" "${SSL_CERT_PATH}"
    ln -sf "/etc/letsencrypt/live/${LETSENCRYPT_DOMAIN}/privkey.pem" "${SSL_KEY_PATH}"
    
    echo "Let's Encrypt certificates configured"
}

# ====================================================================
# Certificate Renewal Automation
# ====================================================================

#!/bin/bash
# renew-certificates.sh - Automated certificate renewal

renew_certificates() {
    echo "Checking certificate renewal..."
    
    # Test renewal (dry run)
    if certbot renew --dry-run; then
        echo "Certificate renewal test passed"
        
        # Perform actual renewal
        certbot renew --post-hook "systemctl reload nginx"
        
        # Restart GameForge services if needed
        docker-compose restart gameforge-app nginx
        
        echo "Certificate renewal completed"
    else
        echo "Certificate renewal test failed"
        exit 1
    fi
}

# ====================================================================
# Nginx SSL Configuration
# ====================================================================

# nginx/ssl.conf - SSL configuration for Nginx
server {
    listen 80;
    server_name gameforge.production.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name gameforge.production.com;
    
    # SSL Certificate Configuration
    ssl_certificate ${SSL_CERT_PATH};
    ssl_certificate_key ${SSL_KEY_PATH};
    
    # SSL Security Configuration
    ssl_protocols ${SSL_PROTOCOLS};
    ssl_ciphers ${SSL_CIPHERS};
    ssl_prefer_server_ciphers on;
    ssl_session_timeout ${SSL_SESSION_TIMEOUT};
    ssl_session_cache ${SSL_SESSION_CACHE};
    ssl_session_tickets off;
    
    # HSTS Configuration
    add_header Strict-Transport-Security "max-age=${HSTS_MAX_AGE}; includeSubDomains; preload" always;
    
    # Security Headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;" always;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate ${SSL_CA_PATH};
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Location configuration
    location / {
        proxy_pass http://gameforge-app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # SSL-specific headers
        proxy_set_header SSL-Client-Cert $ssl_client_cert;
        proxy_set_header SSL-Client-Verify $ssl_client_verify;
        proxy_set_header SSL-Protocol $ssl_protocol;
        proxy_set_header SSL-Cipher $ssl_cipher;
    }
    
    # ACME challenge location for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root ${ACME_CHALLENGE_PATH};
    }
    
    # Security configurations
    location /nginx_status {
        stub_status;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
}

# ====================================================================
# Docker Compose SSL Integration
# ====================================================================

# docker-compose.ssl.yml - SSL override for production
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/ssl.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/ssl/certs:/etc/ssl/certs:ro
      - /etc/ssl/private:/etc/ssl/private:ro
      - /var/www/acme-challenge:/var/www/acme-challenge:ro
    environment:
      - SSL_CERT_PATH=${SSL_CERT_PATH}
      - SSL_KEY_PATH=${SSL_KEY_PATH}
      - SSL_CA_PATH=${SSL_CA_PATH}
    depends_on:
      - gameforge-app
    restart: unless-stopped
    
  certbot:
    image: certbot/certbot
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:rw
      - /var/www/acme-challenge:/var/www/acme-challenge:rw
    environment:
      - LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}
      - LETSENCRYPT_DOMAIN=${LETSENCRYPT_DOMAIN}
    command: |
      sh -c "
        if [ ! -f /etc/letsencrypt/live/${LETSENCRYPT_DOMAIN}/fullchain.pem ]; then
          certbot certonly --webroot \
            --webroot-path=/var/www/acme-challenge \
            --email ${LETSENCRYPT_EMAIL} \
            --agree-tos \
            --no-eff-email \
            -d ${LETSENCRYPT_DOMAIN}
        fi
        
        # Setup renewal cron job
        echo '0 3 * * 0 certbot renew --post-hook \"docker-compose restart nginx\"' | crontab -
        
        # Keep container running for renewals
        crond -f
      "

# ====================================================================
# SSL Certificate Validation
# ====================================================================

#!/bin/bash
# validate-ssl.sh - Validate SSL certificate configuration

validate_ssl_config() {
    echo "Validating SSL configuration..."
    
    # Check certificate files exist
    if [[ ! -f "${SSL_CERT_PATH}" ]]; then
        echo "❌ SSL certificate not found: ${SSL_CERT_PATH}"
        return 1
    fi
    
    if [[ ! -f "${SSL_KEY_PATH}" ]]; then
        echo "❌ SSL private key not found: ${SSL_KEY_PATH}"
        return 1
    fi
    
    # Validate certificate
    if openssl x509 -in "${SSL_CERT_PATH}" -text -noout > /dev/null 2>&1; then
        echo "✅ SSL certificate is valid"
    else
        echo "❌ SSL certificate is invalid"
        return 1
    fi
    
    # Check certificate expiration
    expiry_date=$(openssl x509 -in "${SSL_CERT_PATH}" -noout -enddate | cut -d= -f2)
    expiry_epoch=$(date -d "${expiry_date}" +%s)
    current_epoch=$(date +%s)
    days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    if [[ ${days_until_expiry} -lt 30 ]]; then
        echo "⚠️ SSL certificate expires in ${days_until_expiry} days"
    else
        echo "✅ SSL certificate valid for ${days_until_expiry} days"
    fi
    
    # Test SSL connection
    if timeout 10 openssl s_client -connect localhost:443 -servername "${LETSENCRYPT_DOMAIN}" < /dev/null > /dev/null 2>&1; then
        echo "✅ SSL connection test passed"
    else
        echo "❌ SSL connection test failed"
        return 1
    fi
    
    echo "✅ SSL configuration validation completed"
    return 0
}

# ====================================================================
# Production SSL Setup Instructions
# ====================================================================

# 1. For development/testing:
#    ./generate-ssl-certs.sh

# 2. For production with Let's Encrypt:
#    docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up -d

# 3. For custom certificates:
#    - Place certificate in SSL_CERT_PATH
#    - Place private key in SSL_KEY_PATH
#    - Restart services: docker-compose restart nginx

# 4. Validate configuration:
#    ./validate-ssl.sh

# 5. Test HTTPS endpoint:
#    curl -I https://gameforge.production.com/health