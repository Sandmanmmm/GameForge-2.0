#!/bin/bash
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
docker ps --format "table {{.Names}}\t{{.Ports}}"

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
