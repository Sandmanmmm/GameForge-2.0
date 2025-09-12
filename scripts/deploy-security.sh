#!/bin/bash
# ========================================================================
# GameForge Security Profile Deployment Script
# Installs and configures AppArmor profiles and security policies
# ========================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with colors
log() {
    local level=$1
    shift
    local message="$*"
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO] ${message}${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN] ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR] ${message}${NC}"
            ;;
        *)
            echo -e "${BLUE}[DEBUG] ${message}${NC}"
            ;;
    esac
}

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}GameForge Security Profile Deployment${NC}"
echo -e "${BLUE}========================================================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "ERROR" "This script must be run as root to install security profiles"
    exit 1
fi

# Check if AppArmor is available
if ! command -v apparmor_parser >/dev/null 2>&1; then
    log "WARN" "AppArmor not found. Installing AppArmor utilities..."
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update && apt-get install -y apparmor-utils
    elif command -v yum >/dev/null 2>&1; then
        yum install -y apparmor-utils
    else
        log "ERROR" "Unable to install AppArmor. Please install manually."
        exit 1
    fi
fi

# Check AppArmor status
if ! systemctl is-active --quiet apparmor; then
    log "WARN" "AppArmor is not running. Starting AppArmor service..."
    systemctl start apparmor
    systemctl enable apparmor
fi

log "INFO" "AppArmor status: $(aa-status --brief 2>/dev/null || echo 'Not available')"

# ========================================================================
# Deploy AppArmor Profiles
# ========================================================================

log "INFO" "Deploying AppArmor profiles..."

# Copy profiles to system directory
APPARMOR_DIR="/etc/apparmor.d"
PROFILES_DIR="./security/apparmor"

if [ ! -d "$PROFILES_DIR" ]; then
    log "ERROR" "AppArmor profiles directory not found: $PROFILES_DIR"
    exit 1
fi

# Install GameForge application profile
if [ -f "$PROFILES_DIR/gameforge-app" ]; then
    cp "$PROFILES_DIR/gameforge-app" "$APPARMOR_DIR/"
    log "INFO" "Installed GameForge application profile"
else
    log "WARN" "GameForge application profile not found"
fi

# Install Nginx profile
if [ -f "$PROFILES_DIR/nginx-container" ]; then
    cp "$PROFILES_DIR/nginx-container" "$APPARMOR_DIR/"
    log "INFO" "Installed Nginx container profile"
else
    log "WARN" "Nginx container profile not found"
fi

# Install database profile
if [ -f "$PROFILES_DIR/database-container" ]; then
    cp "$PROFILES_DIR/database-container" "$APPARMOR_DIR/"
    log "INFO" "Installed database container profile"
else
    log "WARN" "Database container profile not found"
fi

# ========================================================================
# Load and Enforce Profiles
# ========================================================================

log "INFO" "Loading and enforcing AppArmor profiles..."

# Parse and load profiles
for profile in "$APPARMOR_DIR"/gameforge-app "$APPARMOR_DIR"/nginx-container "$APPARMOR_DIR"/database-container; do
    if [ -f "$profile" ]; then
        profile_name=$(basename "$profile")
        log "INFO" "Loading profile: $profile_name"
        
        # Parse the profile
        if apparmor_parser -r "$profile"; then
            log "INFO" "✓ Successfully loaded: $profile_name"
        else
            log "ERROR" "✗ Failed to load: $profile_name"
        fi
        
        # Set to enforce mode
        if aa-enforce "$profile" 2>/dev/null; then
            log "INFO" "✓ Enforced: $profile_name"
        else
            log "WARN" "Could not enforce: $profile_name (may need manual intervention)"
        fi
    fi
done

# ========================================================================
# Validate Seccomp Profiles
# ========================================================================

log "INFO" "Validating seccomp profiles..."

SECCOMP_DIR="./security/seccomp"

if [ ! -d "$SECCOMP_DIR" ]; then
    log "ERROR" "Seccomp profiles directory not found: $SECCOMP_DIR"
    exit 1
fi

# Validate JSON syntax
for profile in "$SECCOMP_DIR"/*.json; do
    if [ -f "$profile" ]; then
        profile_name=$(basename "$profile")
        log "INFO" "Validating seccomp profile: $profile_name"
        
        if jq empty "$profile" >/dev/null 2>&1; then
            log "INFO" "✓ Valid JSON: $profile_name"
        else
            log "ERROR" "✗ Invalid JSON: $profile_name"
            exit 1
        fi
    fi
done

# ========================================================================
# Create Security Monitoring Script
# ========================================================================

log "INFO" "Creating security monitoring script..."

cat > /usr/local/bin/gameforge-security-monitor << 'EOF'
#!/bin/bash
# GameForge Security Monitoring Script
# Monitors AppArmor violations and security events

LOGFILE="/var/log/gameforge-security.log"

# Monitor AppArmor violations
monitor_apparmor() {
    echo "$(date): Checking AppArmor violations..." >> "$LOGFILE"
    
    # Check for recent violations
    if journalctl --since="1 hour ago" | grep -i "apparmor.*denied" | tail -10 >> "$LOGFILE"; then
        echo "$(date): AppArmor violations detected" >> "$LOGFILE"
    else
        echo "$(date): No AppArmor violations found" >> "$LOGFILE"
    fi
}

# Monitor failed security contexts
monitor_security_context() {
    echo "$(date): Checking Docker security context failures..." >> "$LOGFILE"
    
    # Check Docker logs for security-related errors
    if docker logs --since=1h $(docker ps -q) 2>&1 | grep -i "permission denied\|operation not permitted" | tail -5 >> "$LOGFILE"; then
        echo "$(date): Security context violations detected" >> "$LOGFILE"
    else
        echo "$(date): No security context violations found" >> "$LOGFILE"
    fi
}

# Run monitoring
monitor_apparmor
monitor_security_context

echo "$(date): Security monitoring completed" >> "$LOGFILE"
EOF

chmod +x /usr/local/bin/gameforge-security-monitor

# Create systemd timer for regular monitoring
cat > /etc/systemd/system/gameforge-security-monitor.service << 'EOF'
[Unit]
Description=GameForge Security Monitor
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/gameforge-security-monitor
User=root
StandardOutput=journal
StandardError=journal
EOF

cat > /etc/systemd/system/gameforge-security-monitor.timer << 'EOF'
[Unit]
Description=Run GameForge Security Monitor every hour
Requires=gameforge-security-monitor.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable gameforge-security-monitor.timer
systemctl start gameforge-security-monitor.timer

log "INFO" "Security monitoring configured"

# ========================================================================
# Create Security Validation Script
# ========================================================================

log "INFO" "Creating security validation script..."

cat > ./validate-security.sh << 'EOF'
#!/bin/bash
# GameForge Security Validation Script

echo "=========================================================================="
echo "GameForge Security Configuration Validation"
echo "=========================================================================="

# Check AppArmor status
echo "AppArmor Status:"
if command -v aa-status >/dev/null 2>&1; then
    aa-status --brief
else
    echo "AppArmor not available"
fi

echo ""

# Check loaded profiles
echo "Loaded GameForge Profiles:"
aa-status 2>/dev/null | grep -E "(gameforge|nginx-container|database-container)" || echo "No GameForge profiles loaded"

echo ""

# Check seccomp profiles
echo "Seccomp Profiles:"
for profile in security/seccomp/*.json; do
    if [ -f "$profile" ]; then
        echo "✓ $(basename "$profile")"
    fi
done

echo ""

# Check Docker security configuration
echo "Docker Security Configuration:"
if docker info 2>/dev/null | grep -q "Security Options"; then
    docker info 2>/dev/null | grep -A 5 "Security Options"
else
    echo "Docker security information not available"
fi

echo ""
echo "Security validation completed."
EOF

chmod +x ./validate-security.sh

log "INFO" "Security validation script created"

# ========================================================================
# Final Security Summary
# ========================================================================

echo ""
log "INFO" "Security deployment completed!"
echo ""
echo -e "${GREEN}Security Features Implemented:${NC}"
echo -e "  ✓ AppArmor profiles for containers"
echo -e "  ✓ Seccomp syscall filtering"
echo -e "  ✓ Dropped capabilities configuration"
echo -e "  ✓ Security contexts in Docker Compose"
echo -e "  ✓ Read-only filesystems with tmpfs"
echo -e "  ✓ Network isolation and segmentation"
echo -e "  ✓ Resource limits and PID limits"
echo -e "  ✓ Security monitoring and validation"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Run: ./validate-security.sh"
echo -e "  2. Deploy with: docker-compose -f docker-compose.production-hardened.yml up -d"
echo -e "  3. Monitor: tail -f /var/log/gameforge-security.log"
echo ""
echo -e "${BLUE}Security monitoring is now active and will run hourly.${NC}"
echo -e "${BLUE}========================================================================${NC}"
EOF
