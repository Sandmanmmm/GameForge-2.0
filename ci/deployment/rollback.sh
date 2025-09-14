#!/bin/bash
# Automated Rollback Script for GameForge Blue/Green Deployments
# Quickly reverts to the previous stable deployment in case of issues

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLLBACK_LOG="rollback-$(date +%Y%m%d-%H%M%S).log"

# Default values
NAMESPACE="gameforge"
APP_NAME="gameforge-api"
ENVIRONMENT="staging"
FORCE="false"
DRY_RUN="false"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ROLLBACK_LOG"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

# Help function
show_help() {
    cat << EOF
Automated Rollback Script for GameForge Blue/Green Deployments

Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV       Target environment (staging/production) [default: staging]
    -n, --namespace NAMESPACE   Kubernetes namespace [default: gameforge]
    -a, --app APP_NAME         Application name [default: gameforge-api]
    -f, --force                Force rollback without confirmation
    -d, --dry-run              Show what would be rolled back without doing it
    -h, --help                 Show this help message

Examples:
    $0 --environment production
    $0 -e staging --force
    $0 --dry-run
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -a|--app)
                APP_NAME="$2"
                shift 2
                ;;
            -f|--force)
                FORCE="true"
                shift
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
}

# Get current active deployment
get_current_deployment() {
    local current_selector
    current_selector=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "")
    echo "$current_selector"
}

# Get deployment information
get_deployment_info() {
    local deployment_name="$1"
    
    if kubectl get deployment "$deployment_name" -n "$NAMESPACE" &> /dev/null; then
        local version
        version=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.metadata.labels.version}' 2>/dev/null || echo "unknown")
        local created
        created=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.metadata.creationTimestamp}' 2>/dev/null || echo "unknown")
        local replicas
        replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        local desired
        desired=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
        
        echo "Version: $version, Created: $created, Status: $replicas/$desired ready"
    else
        echo "Deployment not found"
    fi
}

# Confirm rollback
confirm_rollback() {
    if [[ "$FORCE" == "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo
    echo -e "${YELLOW}WARNING: This will perform a rollback operation!${NC}"
    echo
    read -p "Are you sure you want to proceed? (yes/no): " -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Rollback cancelled by user"
        exit 0
    fi
}

# Perform health check on target deployment
health_check_deployment() {
    local deployment_name="$1"
    
    log "Performing health check on $deployment_name..."
    
    # Check if deployment exists and is ready
    if ! kubectl get deployment "$deployment_name" -n "$NAMESPACE" &> /dev/null; then
        error "Deployment $deployment_name does not exist"
    fi
    
    # Check pod status
    local ready_replicas
    ready_replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    local desired_replicas
    desired_replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [[ "$ready_replicas" != "$desired_replicas" ]] || [[ "$ready_replicas" == "0" ]]; then
        error "Deployment $deployment_name is not healthy: $ready_replicas/$desired_replicas pods ready"
    fi
    
    # Test health endpoint
    local pod_name
    pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,deployment=${deployment_name##*-}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "$pod_name" ]]; then
        if ! kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -sf "http://localhost:8000/api/v1/health" &> /dev/null; then
            warning "Health endpoint check failed for $deployment_name"
        else
            success "Health check passed for $deployment_name"
        fi
    fi
}

# Switch service to target deployment
switch_service() {
    local target_deployment="$1"
    
    log "Switching service to $target_deployment deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would switch service selector to deployment: $target_deployment"
        return 0
    fi
    
    # Update service selector
    kubectl patch service "$APP_NAME" -n "$NAMESPACE" -p '{"spec":{"selector":{"deployment":"'$target_deployment'"}}}'
    
    # Verify the switch
    local current_selector
    current_selector=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.deployment}')
    
    if [[ "$current_selector" != "$target_deployment" ]]; then
        error "Failed to switch service to $target_deployment deployment"
    fi
    
    success "Service switched to $target_deployment deployment"
}

# Monitor rollback
monitor_rollback() {
    local target_deployment="$1"
    
    log "Monitoring rollback for 1 minute..."
    
    local monitor_duration=60
    local check_interval=10
    local checks=$((monitor_duration / check_interval))
    
    for ((i=1; i<=checks; i++)); do
        log "Monitor check $i/$checks..."
        
        # Check service endpoint
        if kubectl exec -n "$NAMESPACE" deployment/"${APP_NAME}-${target_deployment}" -- curl -sf "http://localhost:8000/api/v1/health" &> /dev/null; then
            log "Service is responding correctly"
        else
            warning "Service health check failed"
        fi
        
        sleep $check_interval
    done
    
    success "Rollback monitoring completed"
}

# Create rollback record
create_rollback_record() {
    local from_deployment="$1"
    local to_deployment="$2"
    
    log "Creating rollback record..."
    
    # Create ConfigMap with rollback information
    cat > "/tmp/rollback-record.yaml" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: rollback-$(date +%Y%m%d-%H%M%S)
  namespace: ${NAMESPACE}
  labels:
    app: ${APP_NAME}
    rollback: "true"
data:
  timestamp: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  from_deployment: "${from_deployment}"
  to_deployment: "${to_deployment}"
  triggered_by: "$(whoami)"
  environment: "${ENVIRONMENT}"
  reason: "automated-rollback"
EOF

    if [[ "$DRY_RUN" != "true" ]]; then
        kubectl apply -f "/tmp/rollback-record.yaml"
    fi
}

# Main rollback function
main() {
    log "Starting automated rollback for GameForge $APP_NAME"
    log "Environment: $ENVIRONMENT"
    log "Namespace: $NAMESPACE"
    log "Dry Run: $DRY_RUN"
    
    # Get current deployment state
    local current_deployment
    current_deployment=$(get_current_deployment)
    
    if [[ -z "$current_deployment" ]]; then
        error "Cannot determine current active deployment"
    fi
    
    log "Current active deployment: $current_deployment"
    
    # Determine target deployment (switch blue<->green)
    local target_deployment
    if [[ "$current_deployment" == "blue" ]]; then
        target_deployment="green"
    elif [[ "$current_deployment" == "green" ]]; then
        target_deployment="blue"
    else
        error "Invalid current deployment: $current_deployment"
    fi
    
    log "Target rollback deployment: $target_deployment"
    
    # Show deployment information
    log "Current deployment info: $(get_deployment_info "${APP_NAME}-${current_deployment}")"
    log "Target deployment info: $(get_deployment_info "${APP_NAME}-${target_deployment}")"
    
    # Check if target deployment exists and is healthy
    health_check_deployment "${APP_NAME}-${target_deployment}"
    
    # Confirm rollback
    confirm_rollback
    
    # Create rollback record
    create_rollback_record "$current_deployment" "$target_deployment"
    
    # Switch service
    switch_service "$target_deployment"
    
    # Monitor rollback
    monitor_rollback "$target_deployment"
    
    success "Rollback completed successfully!"
    log "Service switched from $current_deployment to $target_deployment"
    log "Rollback log saved to: $ROLLBACK_LOG"
    
    # Show final status
    log "Final deployment info: $(get_deployment_info "${APP_NAME}-${target_deployment}")"
}

# Parse arguments and run main function
parse_args "$@"
main
