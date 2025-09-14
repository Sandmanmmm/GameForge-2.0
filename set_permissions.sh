#!/bin/bash
# GameForge File Permissions Setup Script
# Sets proper file ownership and permissions for secure non-root deployment
# Usage: ./set_permissions.sh [environment]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
ENVIRONMENT="${1:-production}"

# User and group for file ownership
DEV_USER="dev"
DEV_GROUP="dev"
APP_USER="gameforge"
APP_GROUP="gameforge"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root (needed for chown operations)
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log "Running as root - can set ownership and permissions"
        CAN_CHOWN=true
    else
        warn "Not running as root - will only set permissions, not ownership"
        CAN_CHOWN=false
    fi
}

# Create users and groups if they don't exist
create_users() {
    if [[ "$CAN_CHOWN" == "true" ]]; then
        # Create dev user and group
        if ! getent group "$DEV_GROUP" > /dev/null 2>&1; then
            log "Creating group: $DEV_GROUP"
            groupadd "$DEV_GROUP"
        fi
        
        if ! getent passwd "$DEV_USER" > /dev/null 2>&1; then
            log "Creating user: $DEV_USER"
            useradd -g "$DEV_GROUP" -m -s /bin/bash "$DEV_USER"
        fi
        
        # Create application user and group for runtime
        if ! getent group "$APP_GROUP" > /dev/null 2>&1; then
            log "Creating group: $APP_GROUP"
            groupadd "$APP_GROUP"
        fi
        
        if ! getent passwd "$APP_USER" > /dev/null 2>&1; then
            log "Creating user: $APP_USER"
            useradd -g "$APP_GROUP" -m -s /bin/bash "$APP_USER"
        fi
    else
        info "Skipping user creation (requires root privileges)"
    fi
}

# Set permissions for source code files
set_source_permissions() {
    log "Setting permissions for source code files..."
    
    # Main application file
    if [[ -f "$PROJECT_ROOT/gameforge/main.py" ]]; then
        info "Setting permissions for main.py"
        chmod 644 "$PROJECT_ROOT/gameforge/main.py"
        [[ "$CAN_CHOWN" == "true" ]] && chown "$DEV_USER:$DEV_GROUP" "$PROJECT_ROOT/gameforge/main.py"
    fi
    
    # Core module files
    if [[ -d "$PROJECT_ROOT/gameforge/core" ]]; then
        info "Setting permissions for core module files"
        find "$PROJECT_ROOT/gameforge/core" -name "*.py" -type f -exec chmod 644 {} \;
        [[ "$CAN_CHOWN" == "true" ]] && find "$PROJECT_ROOT/gameforge/core" -name "*.py" -type f -exec chown "$DEV_USER:$DEV_GROUP" {} \;
    fi
    
    # API router files
    if [[ -d "$PROJECT_ROOT/gameforge/api" ]]; then
        info "Setting permissions for API router files"
        find "$PROJECT_ROOT/gameforge/api" -name "*.py" -type f -exec chmod 644 {} \;
        [[ "$CAN_CHOWN" == "true" ]] && find "$PROJECT_ROOT/gameforge/api" -name "*.py" -type f -exec chown "$DEV_USER:$DEV_GROUP" {} \;
    fi
    
    # All Python source files
    info "Setting permissions for all Python source files"
    find "$PROJECT_ROOT" -name "*.py" -type f -not -path "*/.*" -exec chmod 644 {} \;
    [[ "$CAN_CHOWN" == "true" ]] && find "$PROJECT_ROOT" -name "*.py" -type f -not -path "*/.*" -exec chown "$DEV_USER:$DEV_GROUP" {} \;
}

# Set permissions for configuration files
set_config_permissions() {
    log "Setting permissions for configuration files..."
    
    # Configuration files (readable by app user, not world-readable)
    local config_files=(
        "requirements.txt"
        "docker-compose*.yml"
        "Dockerfile"
        ".env.example"
    )
    
    for pattern in "${config_files[@]}"; do
        for file in $PROJECT_ROOT/$pattern; do
            if [[ -f "$file" ]]; then
                info "Setting permissions for $(basename "$file")"
                chmod 640 "$file"
                [[ "$CAN_CHOWN" == "true" ]] && chown "$DEV_USER:$DEV_GROUP" "$file"
            fi
        done
    done
    
    # Secret files (if they exist) - highly restricted
    local secret_files=(
        ".env"
        "*.key"
        "*.pem"
        "*secret*"
        "*credentials*"
    )
    
    for pattern in "${secret_files[@]}"; do
        for file in $PROJECT_ROOT/$pattern; do
            if [[ -f "$file" ]]; then
                warn "Found secret file: $(basename "$file") - setting restrictive permissions"
                chmod 600 "$file"
                [[ "$CAN_CHOWN" == "true" ]] && chown "$DEV_USER:$DEV_GROUP" "$file"
            fi
        done
    done
}

# Set permissions for runtime directories
set_runtime_permissions() {
    log "Setting permissions for runtime directories..."
    
    # Runtime directories that the app needs to write to
    local runtime_dirs=(
        "logs"
        "data"
        "uploads"
        "cache"
        "tmp"
    )
    
    for dir in "${runtime_dirs[@]}"; do
        if [[ -d "$PROJECT_ROOT/$dir" ]]; then
            info "Setting permissions for $dir directory"
            chmod 755 "$PROJECT_ROOT/$dir"
            find "$PROJECT_ROOT/$dir" -type f -exec chmod 644 {} \;
            find "$PROJECT_ROOT/$dir" -type d -exec chmod 755 {} \;
            [[ "$CAN_CHOWN" == "true" ]] && chown -R "$APP_USER:$APP_GROUP" "$PROJECT_ROOT/$dir"
        fi
    done
    
    # Create runtime directories if they don't exist
    for dir in "${runtime_dirs[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            info "Creating runtime directory: $dir"
            mkdir -p "$PROJECT_ROOT/$dir"
            chmod 755 "$PROJECT_ROOT/$dir"
            [[ "$CAN_CHOWN" == "true" ]] && chown "$APP_USER:$APP_GROUP" "$PROJECT_ROOT/$dir"
        fi
    done
}

# Set permissions for scripts
set_script_permissions() {
    log "Setting permissions for executable scripts..."
    
    # Shell scripts should be executable
    find "$PROJECT_ROOT" -name "*.sh" -type f -exec chmod 755 {} \;
    [[ "$CAN_CHOWN" == "true" ]] && find "$PROJECT_ROOT" -name "*.sh" -type f -exec chown "$DEV_USER:$DEV_GROUP" {} \;
    
    # Python scripts in scripts directory
    if [[ -d "$PROJECT_ROOT/scripts" ]]; then
        find "$PROJECT_ROOT/scripts" -name "*.py" -type f -exec chmod 755 {} \;
        [[ "$CAN_CHOWN" == "true" ]] && find "$PROJECT_ROOT/scripts" -name "*.py" -type f -exec chown "$DEV_USER:$DEV_GROUP" {} \;
    fi
}

# Set directory permissions
set_directory_permissions() {
    log "Setting directory permissions..."
    
    # Source code directories - readable and executable for group, not world
    find "$PROJECT_ROOT" -type d -not -path "*/.*" -exec chmod 755 {} \;
    [[ "$CAN_CHOWN" == "true" ]] && find "$PROJECT_ROOT" -type d -not -path "*/.*" -exec chown "$DEV_USER:$DEV_GROUP" {} \;
}

# Validate permissions
validate_permissions() {
    log "Validating file permissions..."
    
    local errors=0
    
    # Check main.py permissions
    if [[ -f "$PROJECT_ROOT/gameforge/main.py" ]]; then
        local perms=$(stat -c "%a" "$PROJECT_ROOT/gameforge/main.py")
        if [[ "$perms" != "644" ]]; then
            error "main.py has incorrect permissions: $perms (expected 644)"
            ((errors++))
        else
            info "main.py permissions: $perms ✓"
        fi
    fi
    
    # Check core files permissions
    while IFS= read -r -d '' file; do
        local perms=$(stat -c "%a" "$file")
        if [[ "$perms" != "644" ]]; then
            error "$(basename "$file") has incorrect permissions: $perms (expected 644)"
            ((errors++))
        fi
    done < <(find "$PROJECT_ROOT/gameforge/core" -name "*.py" -type f -print0 2>/dev/null || true)
    
    # Check API files permissions
    while IFS= read -r -d '' file; do
        local perms=$(stat -c "%a" "$file")
        if [[ "$perms" != "644" ]]; then
            error "$(basename "$file") has incorrect permissions: $perms (expected 644)"
            ((errors++))
        fi
    done < <(find "$PROJECT_ROOT/gameforge/api" -name "*.py" -type f -print0 2>/dev/null || true)
    
    if [[ $errors -eq 0 ]]; then
        log "All file permissions are correct ✓"
    else
        error "Found $errors permission errors"
        return 1
    fi
}

# Generate deployment ready permissions script
generate_deployment_script() {
    log "Generating deployment permissions script..."
    
    cat > "$PROJECT_ROOT/deploy_permissions.sh" << 'EOF'
#!/bin/bash
# GameForge Deployment Permissions Script
# Run this script on the target deployment environment
# Usage: ./deploy_permissions.sh

set -euo pipefail

APP_USER="gameforge"
APP_GROUP="gameforge"

# Create application user if it doesn't exist
if ! getent passwd "$APP_USER" > /dev/null 2>&1; then
    echo "Creating application user: $APP_USER"
    useradd -r -s /bin/false -d /opt/gameforge "$APP_USER"
fi

# Set ownership for runtime
chown -R "$APP_USER:$APP_GROUP" .
chmod -R u=rwX,g=rX,o= .

# Ensure Python files are not executable
find . -name "*.py" -type f -exec chmod 644 {} \;

# Ensure scripts are executable
find . -name "*.sh" -type f -exec chmod 755 {} \;

# Set restrictive permissions on sensitive files
if [[ -f ".env" ]]; then
    chmod 600 .env
fi

echo "Deployment permissions set successfully"
EOF
    
    chmod 755 "$PROJECT_ROOT/deploy_permissions.sh"
    [[ "$CAN_CHOWN" == "true" ]] && chown "$DEV_USER:$DEV_GROUP" "$PROJECT_ROOT/deploy_permissions.sh"
    
    info "Generated deploy_permissions.sh for production deployment"
}

# Main execution
main() {
    log "Starting GameForge permissions setup for $ENVIRONMENT environment"
    
    check_privileges
    create_users
    set_source_permissions
    set_config_permissions
    set_runtime_permissions
    set_script_permissions
    set_directory_permissions
    validate_permissions
    generate_deployment_script
    
    log "GameForge permissions setup completed successfully!"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        info "For production deployment:"
        info "1. Copy files to target system"
        info "2. Run: ./deploy_permissions.sh as root"
        info "3. Run application as non-root user: $APP_USER"
    fi
    
    # Display permission summary
    echo
    echo "=== PERMISSION SUMMARY ==="
    echo "Source code files (*.py): 644 (rw-r--r--)"
    echo "Configuration files: 640 (rw-r-----)"
    echo "Secret files: 600 (rw-------)"
    echo "Executable scripts: 755 (rwxr-xr-x)"
    echo "Directories: 755 (rwxr-xr-x)"
    echo "Runtime directories: 755 with $APP_USER:$APP_GROUP ownership"
    echo "========================="
}

# Run main function
main "$@"