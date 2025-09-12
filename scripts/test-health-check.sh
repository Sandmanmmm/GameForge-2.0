#!/bin/bash
# Test health check with proper setup
set -x

# Set up the environment properly
mount -t securityfs securityfs /sys/kernel/security
mkdir -p /shared/security

# Run LSM and sysctl scripts to create status files
/usr/local/bin/lsm-detector.sh
/usr/local/bin/sysctls-hardening-docker-desktop.sh /shared/security

# Create init-status.json 
echo '{"status": "initializing", "timestamp": "'$(date -Iseconds)'", "uptime": "60s"}' > /shared/security/init-status.json

echo 'Status files created:'
ls -la /shared/security/

echo 'Running health check...'
/usr/local/bin/health-check.sh
echo "Health check exit code: $?"
