#!/usr/bin/env python3
"""
========================================================================
GameForge AI - Network Security and mTLS Implementation
Comprehensive networking hardening for production deployment
========================================================================
"""

import os
import yaml
import subprocess
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkSecurityConfigurator:
    """Configure network security, mTLS, and access controls"""
    
    def __init__(self):
        self.certs_dir = "certs"
        os.makedirs(self.certs_dir, exist_ok=True)
    
    def create_nginx_hardened_config(self):
        """Create hardened Nginx configuration with security headers and rate limiting"""
        
        nginx_config = '''
# GameForge AI - Hardened Nginx Configuration
# Production-ready with security headers, rate limiting, and mTLS

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Hide Nginx version
    server_tokens off;

    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;" always;

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=5r/s;
    limit_req_zone $binary_remote_addr zone=gpu:10m rate=2r/s;

    # Connection limiting
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # JSON logging format
    log_format json_combined escape=json
    '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"status": "$status",'
        '"body_bytes_sent":"$body_bytes_sent",'
        '"request_time":"$request_time",'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"upstream_addr":"$upstream_addr",'
        '"upstream_status":"$upstream_status",'
        '"upstream_response_time":"$upstream_response_time",'
        '"ssl_protocol":"$ssl_protocol",'
        '"ssl_cipher":"$ssl_cipher"'
    '}';

    access_log /var/log/nginx/access.log json_combined;
    error_log /var/log/nginx/error.log warn;

    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/x-javascript
        application/xml+rss
        application/json;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 10m;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # mTLS configuration
    ssl_verify_client optional;
    ssl_client_certificate /etc/nginx/certs/ca-cert.pem;
    ssl_trusted_certificate /etc/nginx/certs/ca-cert.pem;

    # Upstream servers
    upstream gameforge_app {
        server gameforge-app:8080 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    upstream gpu_inference {
        server gpu-inference:8000 max_fails=3 fail_timeout=60s;
        keepalive 16;
    }

    upstream prometheus {
        server prometheus:9090 max_fails=2 fail_timeout=30s;
    }

    upstream grafana {
        server grafana:3000 max_fails=2 fail_timeout=30s;
    }

    # Block common attack patterns
    map $request_uri $blocked {
        ~*\\.(php|asp|aspx|jsp)$ 1;
        ~*/wp-admin.* 1;
        ~*/wp-login.* 1;
        ~*/phpMyAdmin.* 1;
        ~*/admin.* 1;
        default 0;
    }

    # Main server block (HTTPS)
    server {
        listen 443 ssl http2;
        server_name localhost;

        # Connection limiting
        limit_conn addr 10;

        # SSL certificates
        ssl_certificate /etc/nginx/certs/server-cert.pem;
        ssl_certificate_key /etc/nginx/certs/server-key.pem;

        # Block malicious requests
        if ($blocked = 1) {
            return 444;
        }

        # Block requests with no User-Agent
        if ($http_user_agent = "") {
            return 444;
        }

        # Health check endpoint (no rate limiting)
        location = /health {
            access_log off;
            return 200 "healthy\\n";
            add_header Content-Type text/plain;
        }

        # Internal monitoring endpoints (require mTLS)
        location /monitoring/ {
            # Require valid client certificate
            if ($ssl_client_verify != SUCCESS) {
                return 403;
            }
            
            auth_basic "Monitoring Access";
            auth_basic_user_file /etc/nginx/.htpasswd;
            
            location /monitoring/prometheus/ {
                proxy_pass http://prometheus/;
                include /etc/nginx/proxy_params;
            }
            
            location /monitoring/grafana/ {
                proxy_pass http://grafana/;
                include /etc/nginx/proxy_params;
            }
        }

        # API authentication endpoints (strict rate limiting)
        location /api/auth/ {
            limit_req zone=login burst=3 nodelay;
            proxy_pass http://gameforge_app;
            include /etc/nginx/proxy_params;
        }

        # API endpoints (moderate rate limiting)
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://gameforge_app;
            include /etc/nginx/proxy_params;
        }

        # GPU inference endpoints (low rate limiting, high timeout)
        location /gpu/ {
            limit_req zone=gpu burst=5 nodelay;
            proxy_pass http://gpu_inference/;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
            proxy_send_timeout 300s;
            include /etc/nginx/proxy_params;
        }

        # Static content (cached)
        location /static/ {
            limit_req zone=general burst=10 nodelay;
            proxy_pass http://gameforge_app;
            proxy_cache_valid 200 1h;
            expires 1h;
            add_header Cache-Control "public, immutable";
            include /etc/nginx/proxy_params;
        }

        # Default application routes
        location / {
            limit_req zone=general burst=10 nodelay;
            proxy_pass http://gameforge_app;
            include /etc/nginx/proxy_params;
        }
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name localhost;
        return 301 https://$server_name$request_uri;
    }

    # Internal services (only accessible within Docker network)
    server {
        listen 8080;
        server_name internal;
        
        # Only allow internal network access
        allow 172.16.0.0/12;
        allow 10.0.0.0/8;
        allow 192.168.0.0/16;
        deny all;

        location /internal/health {
            proxy_pass http://gameforge_app/health;
        }

        location /internal/metrics {
            proxy_pass http://gameforge_app/metrics;
        }
    }
}
'''
        
        with open('nginx-hardened.conf', 'w', encoding='utf-8') as f:
            f.write(nginx_config)
        
        # Create proxy params file
        proxy_params = '''
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $server_name;
proxy_redirect off;
proxy_buffering off;
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
'''
        
        with open('nginx-proxy-params.conf', 'w', encoding='utf-8') as f:
            f.write(proxy_params)
        
        logger.info("Hardened Nginx configuration created")
    
    def create_mtls_certificates(self):
        """Create mTLS certificates for inter-service communication"""
        
        # Certificate generation script
        cert_script = '''#!/bin/bash
# GameForge AI mTLS Certificate Generation Script
set -e

CERTS_DIR="certs"
mkdir -p $CERTS_DIR

echo "=== Generating mTLS Certificates for GameForge AI ==="

# Generate CA private key
openssl genrsa -out $CERTS_DIR/ca-key.pem 4096

# Generate CA certificate
openssl req -new -x509 -days 3650 -key $CERTS_DIR/ca-key.pem -out $CERTS_DIR/ca-cert.pem -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/OU=Security/CN=GameForge CA"

# Generate server private key
openssl genrsa -out $CERTS_DIR/server-key.pem 4096

# Generate server certificate signing request
openssl req -new -key $CERTS_DIR/server-key.pem -out $CERTS_DIR/server.csr -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/OU=Security/CN=gameforge.local"

# Create server certificate extensions
cat > $CERTS_DIR/server-ext.conf << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = gameforge.local
DNS.2 = localhost
DNS.3 = nginx
DNS.4 = gameforge-app
DNS.5 = gpu-inference
IP.1 = 127.0.0.1
IP.2 = 172.18.0.1
EOF

# Generate server certificate signed by CA
openssl x509 -req -days 365 -in $CERTS_DIR/server.csr -CA $CERTS_DIR/ca-cert.pem -CAkey $CERTS_DIR/ca-key.pem -CAcreateserial -out $CERTS_DIR/server-cert.pem -extensions v3_req -extfile $CERTS_DIR/server-ext.conf

# Generate client private key
openssl genrsa -out $CERTS_DIR/client-key.pem 4096

# Generate client certificate signing request
openssl req -new -key $CERTS_DIR/client-key.pem -out $CERTS_DIR/client.csr -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/OU=Security/CN=gameforge-client"

# Generate client certificate signed by CA
openssl x509 -req -days 365 -in $CERTS_DIR/client.csr -CA $CERTS_DIR/ca-cert.pem -CAkey $CERTS_DIR/ca-key.pem -CAcreateserial -out $CERTS_DIR/client-cert.pem

# Generate DH parameters for enhanced security
openssl dhparam -out $CERTS_DIR/dhparam.pem 2048

# Set proper permissions
chmod 600 $CERTS_DIR/*-key.pem
chmod 644 $CERTS_DIR/*-cert.pem $CERTS_DIR/ca-cert.pem $CERTS_DIR/dhparam.pem

echo "Certificates generated successfully:"
echo "  CA Certificate: $CERTS_DIR/ca-cert.pem"
echo "  Server Certificate: $CERTS_DIR/server-cert.pem"
echo "  Client Certificate: $CERTS_DIR/client-cert.pem"

# Verify certificates
echo "Verifying certificates..."
openssl verify -CAfile $CERTS_DIR/ca-cert.pem $CERTS_DIR/server-cert.pem
openssl verify -CAfile $CERTS_DIR/ca-cert.pem $CERTS_DIR/client-cert.pem

echo "mTLS certificates ready for production deployment"
'''
        
        with open('scripts/generate-mtls-certs.sh', 'w', encoding='utf-8') as f:
            f.write(cert_script)
        
        os.chmod('scripts/generate-mtls-certs.sh', 0o755)
        
        logger.info("mTLS certificate generation script created")
    
    def create_network_security_compose(self):
        """Create Docker Compose configuration with network security"""
        
        security_compose = {
            'version': '3.8',
            'services': {
                'nginx': {
                    'image': 'nginx:alpine',
                    'ports': ['80:80', '443:443'],
                    'volumes': [
                        './nginx-hardened.conf:/etc/nginx/nginx.conf:ro',
                        './nginx-proxy-params.conf:/etc/nginx/proxy_params:ro',
                        './certs:/etc/nginx/certs:ro',
                        './.htpasswd:/etc/nginx/.htpasswd:ro'
                    ],
                    'networks': ['frontend', 'monitoring'],
                    'depends_on': ['gameforge-app', 'gpu-inference'],
                    'restart': 'unless-stopped',
                    'security_opt': ['no-new-privileges:true'],
                    'read_only': True,
                    'tmpfs': ['/var/cache/nginx', '/var/run'],
                    'sysctls': {
                        'net.core.somaxconn': 65535,
                        'net.ipv4.tcp_max_syn_backlog': 65535
                    }
                },
                'gameforge-app': {
                    'networks': ['frontend', 'backend', 'monitoring'],
                    'expose': ['8080'],
                    'environment': [
                        'TLS_CERT_FILE=/app/certs/server-cert.pem',
                        'TLS_KEY_FILE=/app/certs/server-key.pem',
                        'TLS_CA_FILE=/app/certs/ca-cert.pem',
                        'ENABLE_MTLS=true'
                    ],
                    'volumes': ['./certs:/app/certs:ro'],
                    'security_opt': ['no-new-privileges:true']
                },
                'gpu-inference': {
                    'networks': ['backend', 'gpu-network', 'monitoring'],
                    'expose': ['8000'],
                    'environment': [
                        'TLS_CERT_FILE=/app/certs/server-cert.pem',
                        'TLS_KEY_FILE=/app/certs/server-key.pem',
                        'TLS_CA_FILE=/app/certs/ca-cert.pem',
                        'ENABLE_MTLS=true'
                    ],
                    'volumes': ['./certs:/app/certs:ro'],
                    'security_opt': ['no-new-privileges:true']
                },
                'firewall': {
                    'image': 'alpine:latest',
                    'command': ['sh', '-c', '''
                        apk add --no-cache iptables
                        # Allow established connections
                        iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
                        # Allow loopback
                        iptables -A INPUT -i lo -j ACCEPT
                        # Allow HTTP/HTTPS from frontend network
                        iptables -A INPUT -p tcp --dport 80 -s 172.18.0.0/16 -j ACCEPT
                        iptables -A INPUT -p tcp --dport 443 -s 172.18.0.0/16 -j ACCEPT
                        # Block all other traffic
                        iptables -A INPUT -j DROP
                        # Keep container running
                        tail -f /dev/null
                    '''],
                    'networks': ['frontend'],
                    'cap_add': ['NET_ADMIN'],
                    'restart': 'unless-stopped'
                }
            },
            'networks': {
                'frontend': {
                    'driver': 'bridge',
                    'ipam': {
                        'config': [{'subnet': '172.18.0.0/16'}]
                    },
                    'driver_opts': {
                        'com.docker.network.bridge.enable_icc': 'false',
                        'com.docker.network.bridge.enable_ip_masquerade': 'true'
                    }
                },
                'backend': {
                    'driver': 'bridge',
                    'internal': True,
                    'ipam': {
                        'config': [{'subnet': '172.19.0.0/16'}]
                    }
                },
                'gpu-network': {
                    'driver': 'bridge',
                    'internal': True,
                    'ipam': {
                        'config': [{'subnet': '172.20.0.0/16'}]
                    }
                },
                'monitoring': {
                    'driver': 'bridge',
                    'internal': True,
                    'ipam': {
                        'config': [{'subnet': '172.21.0.0/16'}]
                    }
                }
            }
        }
        
        with open('docker-compose.network-security.yml', 'w', encoding='utf-8') as f:
            yaml.dump(security_compose, f, default_flow_style=False, indent=2)
        
        logger.info("Network security Docker Compose configuration created")
    
    def create_access_control_script(self):
        """Create access control and monitoring script"""
        
        access_script = '''#!/bin/bash
# GameForge AI Network Access Control and Monitoring
set -e

echo "=== GameForge AI Network Security Setup ==="

# Create htpasswd file for basic auth
if [ ! -f .htpasswd ]; then
    echo "Creating basic auth credentials..."
    # Default: admin/gameforge123 (change in production)
    echo 'admin:$apr1$8QAS7Jq/$8BYIpCGY8D9s4XpZJQGQl.' > .htpasswd
    chmod 600 .htpasswd
    echo "Basic auth file created (.htpasswd)"
fi

# Generate certificates if they don't exist
if [ ! -f certs/ca-cert.pem ]; then
    echo "Generating mTLS certificates..."
    ./scripts/generate-mtls-certs.sh
fi

# Create network monitoring script
cat > scripts/monitor-network-security.sh << 'EOF'
#!/bin/bash
# Network Security Monitoring Script

echo "=== Network Security Status ==="

# Check SSL certificate validity
echo "SSL Certificate Status:"
openssl x509 -in certs/server-cert.pem -noout -dates

echo ""
echo "Active Connections:"
docker exec nginx netstat -tulpn | grep LISTEN || echo "Nginx not running"

echo ""
echo "Network Traffic (last 10 lines):"
docker logs nginx --tail 10 2>/dev/null || echo "No nginx logs available"

echo ""
echo "Blocked IPs (if any):"
docker exec nginx cat /var/log/nginx/error.log | grep "limiting" | tail -5 2>/dev/null || echo "No rate limiting logs"

echo ""
echo "Security Headers Test:"
curl -Is https://localhost/health 2>/dev/null | grep -E "(X-Frame-Options|X-Content-Type-Options|Strict-Transport-Security)" || echo "HTTPS not available"

echo ""
echo "Network Interfaces:"
docker network ls | grep gameforge || echo "No gameforge networks found"
EOF

chmod +x scripts/monitor-network-security.sh

# Create network troubleshooting script
cat > scripts/network-troubleshoot.sh << 'EOF'
#!/bin/bash
# Network Troubleshooting Script

echo "=== Network Troubleshooting ==="

echo "Docker Networks:"
docker network ls

echo ""
echo "Container Network Connections:"
docker ps --format "table {{.Names}}\\t{{.Ports}}"

echo ""
echo "Internal DNS Resolution Test:"
docker exec gameforge-app nslookup redis 2>/dev/null || echo "DNS test failed - containers may not be running"

echo ""
echo "Service Connectivity Test:"
docker exec gameforge-app curl -s http://redis:6379 2>/dev/null && echo "Redis accessible" || echo "Redis not accessible"
docker exec gameforge-app curl -s http://gpu-inference:8000/health 2>/dev/null && echo "GPU service accessible" || echo "GPU service not accessible"

echo ""
echo "SSL/TLS Configuration Test:"
echo | openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | grep -E "(Verify return code|subject|issuer)" || echo "SSL test failed"
EOF

chmod +x scripts/network-troubleshoot.sh

echo "Network security configuration complete!"
echo ""
echo "Next steps:"
echo "1. Deploy with: docker-compose -f docker-compose.yml -f docker-compose.network-security.yml up -d"
echo "2. Monitor security: ./scripts/monitor-network-security.sh"
echo "3. Troubleshoot issues: ./scripts/network-troubleshoot.sh"
echo "4. Access monitoring: https://localhost/monitoring/ (requires client cert)"
'''
        
        with open('scripts/setup-network-security.sh', 'w', encoding='utf-8') as f:
            f.write(access_script)
        
        os.chmod('scripts/setup-network-security.sh', 0o755)
        
        logger.info("Network access control script created")
    
    def create_security_audit_script(self):
        """Create security audit and validation script"""
        
        audit_script = '''#!/usr/bin/env python3
"""
GameForge AI Network Security Audit Script
Validates network security configuration and identifies vulnerabilities
"""

import subprocess
import socket
import ssl
import requests
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkSecurityAuditor:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'vulnerabilities': [],
            'recommendations': []
        }
    
    def test_ssl_configuration(self):
        """Test SSL/TLS configuration"""
        logger.info("Testing SSL configuration...")
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection(('localhost', 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    
                    self.results['tests']['ssl'] = {
                        'status': 'PASS',
                        'protocol': ssock.version(),
                        'cipher': cipher[0] if cipher else None,
                        'cert_subject': cert.get('subject', []),
                        'cert_expiry': cert.get('notAfter', 'Unknown')
                    }
                    
                    # Check for weak ciphers
                    if cipher and 'RC4' in cipher[0]:
                        self.results['vulnerabilities'].append({
                            'severity': 'HIGH',
                            'description': 'Weak cipher RC4 detected',
                            'recommendation': 'Disable RC4 ciphers in Nginx configuration'
                        })
        
        except Exception as e:
            self.results['tests']['ssl'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"SSL test failed: {e}")
    
    def test_security_headers(self):
        """Test HTTP security headers"""
        logger.info("Testing security headers...")
        
        try:
            response = requests.get('https://localhost/health', 
                                 verify=False, timeout=10)
            
            headers = response.headers
            required_headers = {
                'X-Frame-Options': 'DENY',
                'X-Content-Type-Options': 'nosniff',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000',
                'Content-Security-Policy': 'default-src'
            }
            
            missing_headers = []
            for header, expected in required_headers.items():
                if header not in headers:
                    missing_headers.append(header)
                elif expected not in headers[header]:
                    missing_headers.append(f"{header} (incorrect value)")
            
            self.results['tests']['security_headers'] = {
                'status': 'PASS' if not missing_headers else 'PARTIAL',
                'present_headers': list(headers.keys()),
                'missing_headers': missing_headers
            }
            
            if missing_headers:
                self.results['vulnerabilities'].append({
                    'severity': 'MEDIUM',
                    'description': f'Missing security headers: {missing_headers}',
                    'recommendation': 'Add missing security headers to Nginx configuration'
                })
        
        except Exception as e:
            self.results['tests']['security_headers'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"Security headers test failed: {e}")
    
    def test_rate_limiting(self):
        """Test rate limiting effectiveness"""
        logger.info("Testing rate limiting...")
        
        try:
            # Make rapid requests to test rate limiting
            responses = []
            for i in range(15):  # Should trigger rate limit
                try:
                    resp = requests.get('https://localhost/api/health', 
                                      verify=False, timeout=5)
                    responses.append(resp.status_code)
                except:
                    responses.append(0)
            
            rate_limited = any(code == 429 for code in responses)
            
            self.results['tests']['rate_limiting'] = {
                'status': 'PASS' if rate_limited else 'FAIL',
                'responses': responses,
                'rate_limit_triggered': rate_limited
            }
            
            if not rate_limited:
                self.results['vulnerabilities'].append({
                    'severity': 'MEDIUM',
                    'description': 'Rate limiting not working effectively',
                    'recommendation': 'Review and tune rate limiting configuration'
                })
        
        except Exception as e:
            self.results['tests']['rate_limiting'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"Rate limiting test failed: {e}")
    
    def test_internal_service_exposure(self):
        """Test that internal services are not exposed"""
        logger.info("Testing internal service exposure...")
        
        internal_ports = [5432, 6379, 9090, 3000, 9200]  # postgres, redis, prometheus, grafana, elasticsearch
        exposed_ports = []
        
        for port in internal_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    exposed_ports.append(port)
                sock.close()
            except:
                pass
        
        self.results['tests']['internal_exposure'] = {
            'status': 'PASS' if not exposed_ports else 'FAIL',
            'exposed_ports': exposed_ports
        }
        
        if exposed_ports:
            self.results['vulnerabilities'].append({
                'severity': 'HIGH',
                'description': f'Internal services exposed on ports: {exposed_ports}',
                'recommendation': 'Remove port mappings for internal services'
            })
    
    def generate_audit_report(self):
        """Generate comprehensive audit report"""
        report = []
        report.append("=" * 80)
        report.append("GAMEFORGE AI - NETWORK SECURITY AUDIT REPORT")
        report.append("=" * 80)
        report.append(f"Audit Date: {self.results['timestamp']}")
        report.append("")
        
        # Test results summary
        report.append("TEST RESULTS:")
        report.append("-" * 40)
        
        for test_name, test_result in self.results['tests'].items():
            status_icon = "✅" if test_result['status'] == 'PASS' else "⚠️" if test_result['status'] == 'PARTIAL' else "❌"
            report.append(f"{status_icon} {test_name.replace('_', ' ').title()}: {test_result['status']}")
        
        report.append("")
        
        # Vulnerabilities
        if self.results['vulnerabilities']:
            report.append("VULNERABILITIES FOUND:")
            report.append("-" * 25)
            
            for vuln in self.results['vulnerabilities']:
                severity_icon = "🔴" if vuln['severity'] == 'HIGH' else "🟡" if vuln['severity'] == 'MEDIUM' else "🟢"
                report.append(f"{severity_icon} {vuln['severity']}: {vuln['description']}")
                report.append(f"   Recommendation: {vuln['recommendation']}")
                report.append("")
        else:
            report.append("✅ NO CRITICAL VULNERABILITIES FOUND")
            report.append("")
        
        # Overall security score
        total_tests = len(self.results['tests'])
        passed_tests = sum(1 for test in self.results['tests'].values() if test['status'] == 'PASS')
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report.append(f"OVERALL SECURITY SCORE: {score:.1f}%")
        report.append("")
        
        if score >= 90:
            report.append("🎉 EXCELLENT SECURITY POSTURE")
        elif score >= 75:
            report.append("✅ GOOD SECURITY POSTURE - Minor improvements needed")
        elif score >= 50:
            report.append("⚠️ MODERATE SECURITY POSTURE - Improvements required")
        else:
            report.append("❌ POOR SECURITY POSTURE - Immediate action required")
        
        return "\\n".join(report)
    
    def run_audit(self):
        """Run complete security audit"""
        logger.info("Starting network security audit...")
        
        self.test_ssl_configuration()
        self.test_security_headers()
        self.test_rate_limiting()
        self.test_internal_service_exposure()
        
        # Generate and save report
        report = self.generate_audit_report()
        
        with open('network_security_audit.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        with open('network_security_audit_report.txt', 'w') as f:
            f.write(report)
        
        print(report)
        
        # Return exit code based on vulnerabilities
        high_severity = any(v['severity'] == 'HIGH' for v in self.results['vulnerabilities'])
        return 1 if high_severity else 0

if __name__ == "__main__":
    auditor = NetworkSecurityAuditor()
    exit_code = auditor.run_audit()
    exit(exit_code)
'''
        
        with open('scripts/network-security-audit.py', 'w', encoding='utf-8') as f:
            f.write(audit_script)
        
        logger.info("Network security audit script created")

def main():
    """Create all network security configurations"""
    logger.info("Creating comprehensive network security configurations...")
    
    configurator = NetworkSecurityConfigurator()
    
    configurator.create_nginx_hardened_config()
    configurator.create_mtls_certificates()
    configurator.create_network_security_compose()
    configurator.create_access_control_script()
    configurator.create_security_audit_script()
    
    logger.info("\nALL NETWORK SECURITY CONFIGURATIONS CREATED")
    logger.info("Key components:")
    logger.info("1. Hardened Nginx config: nginx-hardened.conf")
    logger.info("2. mTLS certificates: scripts/generate-mtls-certs.sh")
    logger.info("3. Network security compose: docker-compose.network-security.yml")
    logger.info("4. Access control setup: scripts/setup-network-security.sh")
    logger.info("5. Security audit: scripts/network-security-audit.py")

if __name__ == "__main__":
    main()