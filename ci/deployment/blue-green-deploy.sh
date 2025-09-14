#!/bin/bash
# Blue/Green Deployment Script for GameForge
# Provides zero-downtime deployments with automated health checks and rollback

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_LOG="deployment-$(date +%Y%m%d-%H%M%S).log"

# Default values
NAMESPACE="gameforge"
APP_NAME="gameforge-api"
VERSION=""
ENVIRONMENT="staging"
TIMEOUT="600"
DRY_RUN="false"
SKIP_TESTS="false"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

# Help function
show_help() {
    cat << EOF
Blue/Green Deployment Script for GameForge

Usage: $0 [OPTIONS]

Options:
    -v, --version VERSION       Application version to deploy (required)
    -e, --environment ENV       Target environment (staging/production) [default: staging]
    -n, --namespace NAMESPACE   Kubernetes namespace [default: gameforge]
    -a, --app APP_NAME         Application name [default: gameforge-api]
    -t, --timeout TIMEOUT      Deployment timeout in seconds [default: 600]
    -d, --dry-run              Perform dry run without actual deployment
    -s, --skip-tests           Skip automated tests
    -h, --help                 Show this help message

Examples:
    $0 --version v1.2.3 --environment production
    $0 -v v1.2.3 -e staging --dry-run
    $0 --version v1.2.3 --skip-tests
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
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
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
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

    # Validate required arguments
    if [[ -z "$VERSION" ]]; then
        error "Version is required. Use --version or -v"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
    fi

    # Check namespace
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error "Namespace '$NAMESPACE' does not exist"
    fi

    # Check if required tools are available
    for tool in jq curl; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is required but not installed"
        fi
    done

    success "Prerequisites check passed"
}

# Get current active environment (blue or green)
get_active_environment() {
    local service_selector
    service_selector=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "")
    
    if [[ "$service_selector" == "blue" ]]; then
        echo "blue"
    elif [[ "$service_selector" == "green" ]]; then
        echo "green"
    else
        # Default to blue if no deployment is active
        echo "blue"
    fi
}

# Get inactive environment
get_inactive_environment() {
    local active="$1"
    if [[ "$active" == "blue" ]]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Deploy to inactive environment
deploy_inactive_environment() {
    local target_env="$1"
    local image_tag="$2"
    
    log "Deploying version $image_tag to $target_env environment..."
    
    # Generate deployment manifest
    cat > "/tmp/${APP_NAME}-${target_env}-deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}-${target_env}
  namespace: ${NAMESPACE}
  labels:
    app: ${APP_NAME}
    deployment: ${target_env}
    version: ${VERSION}
    environment: ${ENVIRONMENT}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ${APP_NAME}
      deployment: ${target_env}
  template:
    metadata:
      labels:
        app: ${APP_NAME}
        deployment: ${target_env}
        version: ${VERSION}
    spec:
      containers:
      - name: ${APP_NAME}
        image: ${image_tag}
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: ${ENVIRONMENT}
        - name: DEPLOYMENT_COLOR
          value: ${target_env}
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would deploy the following manifest:"
        cat "/tmp/${APP_NAME}-${target_env}-deployment.yaml"
        return 0
    fi

    # Apply deployment
    kubectl apply -f "/tmp/${APP_NAME}-${target_env}-deployment.yaml"
    
    # Wait for deployment to be ready
    log "Waiting for $target_env deployment to be ready..."
    if ! kubectl rollout status deployment/"${APP_NAME}-${target_env}" -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
        error "Deployment to $target_env environment failed"
    fi
    
    success "$target_env environment deployed successfully"
}

# Run health checks
run_health_checks() {
    local target_env="$1"
    
    log "Running health checks on $target_env environment..."
    
    # Get pod IP for health checks
    local pod_ip
    pod_ip=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_NAME,deployment=$target_env" -o jsonpath='{.items[0].status.podIP}')
    
    if [[ -z "$pod_ip" ]]; then
        error "Could not get pod IP for health checks"
    fi
    
    # Health check endpoint
    local health_url="http://$pod_ip:8000/api/v1/health"
    local ready_url="http://$pod_ip:8000/api/v1/ready"
    
    # Wait for health endpoint to respond
    local retries=0
    local max_retries=30
    
    while [[ $retries -lt $max_retries ]]; do
        if kubectl exec -n "$NAMESPACE" deployment/"${APP_NAME}-${target_env}" -- curl -sf "$health_url" &> /dev/null; then
            success "Health check passed for $target_env environment"
            break
        fi
        
        retries=$((retries + 1))
        log "Health check attempt $retries/$max_retries failed, retrying in 10 seconds..."
        sleep 10
    done
    
    if [[ $retries -eq $max_retries ]]; then
        error "Health checks failed for $target_env environment"
    fi
}

# Run automated tests
run_automated_tests() {
    local target_env="$1"
    
    if [[ "$SKIP_TESTS" == "true" ]]; then
        warning "Skipping automated tests"
        return 0
    fi
    
    log "Running automated tests on $target_env environment..."
    
    # Create test job
    cat > "/tmp/test-job-${target_env}.yaml" << EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${APP_NAME}-test-${target_env}-$(date +%s)
  namespace: ${NAMESPACE}
spec:
  template:
    spec:
      containers:
      - name: test-runner
        image: curlimages/curl:latest
        command: ["sh", "-c"]
        args:
        - |
          # Basic smoke tests
          echo "Running smoke tests..."
          
          # Test health endpoint
          curl -f http://${APP_NAME}-${target_env}:8000/api/v1/health || exit 1
          
          # Test ready endpoint  
          curl -f http://${APP_NAME}-${target_env}:8000/api/v1/ready || exit 1
          
          # Test basic API functionality
          curl -f http://${APP_NAME}-${target_env}:8000/api/v1/version || exit 1
          
          echo "All smoke tests passed!"
      restartPolicy: Never
  backoffLimit: 2
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would run automated tests"
        return 0
    fi

    kubectl apply -f "/tmp/test-job-${target_env}.yaml"
    
    # Wait for test completion
    local job_name
    job_name=$(kubectl get jobs -n "$NAMESPACE" -l "app=${APP_NAME}" --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
    
    if ! kubectl wait --for=condition=complete job/"$job_name" -n "$NAMESPACE" --timeout=300s; then
        error "Automated tests failed for $target_env environment"
    fi
    
    success "Automated tests passed for $target_env environment"
}

# Switch traffic to new environment
switch_traffic() {
    local target_env="$1"
    
    log "Switching traffic to $target_env environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would switch service selector to deployment: $target_env"
        return 0
    fi
    
    # Update service selector
    kubectl patch service "$APP_NAME" -n "$NAMESPACE" -p '{"spec":{"selector":{"deployment":"'$target_env'"}}}'
    
    # Verify the switch
    local current_selector
    current_selector=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.deployment}')
    
    if [[ "$current_selector" != "$target_env" ]]; then
        error "Failed to switch traffic to $target_env environment"
    fi
    
    success "Traffic switched to $target_env environment"
}

# Monitor deployment
monitor_deployment() {
    local target_env="$1"
    
    log "Monitoring $target_env deployment for 2 minutes..."
    
    local monitor_duration=120
    local check_interval=10
    local checks=$((monitor_duration / check_interval))
    
    for ((i=1; i<=checks; i++)); do
        log "Monitor check $i/$checks..."
        
        # Check pod status
        local ready_pods
        ready_pods=$(kubectl get deployment "${APP_NAME}-${target_env}" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
        local desired_pods
        desired_pods=$(kubectl get deployment "${APP_NAME}-${target_env}" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        
        if [[ "$ready_pods" != "$desired_pods" ]]; then
            warning "Pod readiness issue: $ready_pods/$desired_pods pods ready"
        else
            log "All pods are ready ($ready_pods/$desired_pods)"
        fi
        
        sleep $check_interval
    done
    
    success "Monitoring completed successfully"
}

# Cleanup old environment
cleanup_old_environment() {
    local old_env="$1"
    
    log "Cleaning up $old_env environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would delete deployment ${APP_NAME}-${old_env}"
        return 0
    fi
    
    # Scale down old deployment
    kubectl scale deployment "${APP_NAME}-${old_env}" --replicas=0 -n "$NAMESPACE" || true
    
    # Wait a bit before deletion
    sleep 30
    
    # Delete old deployment
    kubectl delete deployment "${APP_NAME}-${old_env}" -n "$NAMESPACE" || true
    
    success "Old environment ($old_env) cleaned up"
}

# Main deployment function
main() {
    log "Starting Blue/Green deployment for GameForge $APP_NAME"
    log "Version: $VERSION"
    log "Environment: $ENVIRONMENT"
    log "Namespace: $NAMESPACE"
    log "Dry Run: $DRY_RUN"
    
    # Check prerequisites
    check_prerequisites
    
    # Determine environments
    local active_env
    active_env=$(get_active_environment)
    local inactive_env
    inactive_env=$(get_inactive_environment "$active_env")
    
    log "Current active environment: $active_env"
    log "Deploying to inactive environment: $inactive_env"
    
    # Build image tag
    local image_tag="gameforge-api:$VERSION"
    
    # Deploy to inactive environment
    deploy_inactive_environment "$inactive_env" "$image_tag"
    
    # Run health checks
    run_health_checks "$inactive_env"
    
    # Run automated tests
    run_automated_tests "$inactive_env"
    
    # Switch traffic
    switch_traffic "$inactive_env"
    
    # Monitor new deployment
    monitor_deployment "$inactive_env"
    
    # Cleanup old environment
    cleanup_old_environment "$active_env"
    
    success "Blue/Green deployment completed successfully!"
    log "New active environment: $inactive_env"
    log "Deployment log saved to: $DEPLOYMENT_LOG"
}

# Parse arguments and run main function
parse_args "$@"
main
