#!/bin/bash

# ========================================================================
# GameForge AI Production Platform - Vast.ai Deployment Script
# Comprehensive deployment script for cloud GPU instances
# ========================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================================================
# Configuration
# ========================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.vastai-production.yml"
ENV_FILE=".env.vastai-production"
DOCKERIGNORE_FILE=".dockerignore.vastai"

# Vast.ai specific settings
VASTAI_DEPLOYMENT=true
DEFAULT_MEMORY_LIMIT="24G"
DEFAULT_CPU_LIMIT="12.0"

# ========================================================================
# Helper Functions
# ========================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

check_requirements() {
    log_section "Checking Requirements"
    
    # Check if running on Vast.ai (look for common indicators)
    if [ -f "/etc/vast-ai" ] || [ -n "${VAST_INSTANCE_ID:-}" ] || [ -n "${CUDA_VISIBLE_DEVICES:-}" ]; then
        log_success "Vast.ai environment detected"
        export VASTAI_DETECTED=true
    else
        log_warning "Vast.ai environment not detected, but continuing..."
        export VASTAI_DETECTED=false
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    log_success "Docker Compose found: $(docker-compose --version)"
    
    # Check NVIDIA Docker runtime
    if ! docker info | grep -q "nvidia"; then
        log_warning "NVIDIA Docker runtime not detected - GPU features may not work"
    else
        log_success "NVIDIA Docker runtime detected"
    fi
    
    # Check GPU availability
    if command -v nvidia-smi &> /dev/null; then
        log_success "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits | while read line; do
            log_info "  GPU: $line"
        done
    else
        log_warning "nvidia-smi not found - GPU may not be available"
    fi
}

setup_environment() {
    log_section "Setting Up Environment"
    
    cd "$PROJECT_ROOT"
    
    # Copy dockerignore for optimized builds
    if [ -f "$DOCKERIGNORE_FILE" ]; then
        cp "$DOCKERIGNORE_FILE" .dockerignore
        log_success "Applied Vast.ai optimized .dockerignore"
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found!"
        log_info "Please create $ENV_FILE with your configuration"
        exit 1
    fi
    
    # Load environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Set Vast.ai specific environment variables
    export VASTAI_DEPLOYMENT=true
    export BUILD_DATE=$(date -Iseconds)
    export VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    export BUILD_VERSION="vastai-$(date +%Y%m%d-%H%M%S)"
    
    # Auto-detect Vast.ai instance ID if available
    if [ -z "${VASTAI_INSTANCE_ID:-}" ]; then
        if [ -f "/etc/hostname" ]; then
            DETECTED_ID=$(cat /etc/hostname | grep -o 'C[0-9]*' || echo "unknown")
            export VASTAI_INSTANCE_ID="$DETECTED_ID"
            log_info "Auto-detected Vast.ai instance ID: $VASTAI_INSTANCE_ID"
        fi
    fi
    
    log_success "Environment configured for Vast.ai deployment"
    log_info "Build version: $BUILD_VERSION"
    log_info "Instance ID: ${VASTAI_INSTANCE_ID:-unknown}"
}

create_volumes() {
    log_section "Creating Volume Directories"
    
    # Create necessary volume directories
    mkdir -p volumes/{training-data,model-checkpoints,security/{harbor-secret,harbor-ca,clair-data,clair-logs,notary-data,notary-certs}}
    
    # Set appropriate permissions
    chmod 755 volumes/training-data
    chmod 755 volumes/model-checkpoints
    chmod 700 volumes/security
    
    log_success "Volume directories created"
}

build_images() {
    log_section "Building Docker Images"
    
    log_info "Building optimized images for Vast.ai..."
    
    # Build with Vast.ai optimizations
    docker-compose -f "$COMPOSE_FILE" build \
        --parallel \
        --compress \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg BUILD_VERSION="$BUILD_VERSION"
    
    log_success "Images built successfully"
}

deploy_services() {
    log_section "Deploying Services"
    
    log_info "Starting security bootstrap..."
    docker-compose -f "$COMPOSE_FILE" up -d security-bootstrap
    
    # Wait for bootstrap to complete
    log_info "Waiting for security bootstrap to complete..."
    docker-compose -f "$COMPOSE_FILE" wait security-bootstrap
    
    log_info "Starting core infrastructure services..."
    docker-compose -f "$COMPOSE_FILE" up -d \
        security-monitor \
        postgres \
        redis \
        vault \
        elasticsearch
    
    # Wait for core services to be healthy
    log_info "Waiting for core services to be ready..."
    sleep 30
    
    log_info "Starting GPU services..."
    docker-compose -f "$COMPOSE_FILE" up -d \
        gameforge-gpu-inference \
        gameforge-gpu-training
    
    # Wait for GPU services
    log_info "Waiting for GPU services to initialize..."
    sleep 60
    
    log_info "Starting application services..."
    docker-compose -f "$COMPOSE_FILE" up -d \
        gameforge-app \
        gameforge-worker \
        nginx
    
    log_info "Starting monitoring services..."
    docker-compose -f "$COMPOSE_FILE" up -d \
        prometheus \
        grafana
    
    log_success "All services deployed"
}

check_health() {
    log_section "Checking Service Health"
    
    log_info "Waiting for services to become healthy..."
    
    # Check core services
    local services=("postgres" "redis" "vault" "elasticsearch" "gameforge-gpu-inference" "gameforge-app")
    
    for service in "${services[@]}"; do
        log_info "Checking $service..."
        local attempts=0
        local max_attempts=30
        
        while [ $attempts -lt $max_attempts ]; do
            if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; then
                log_success "$service is healthy"
                break
            fi
            
            attempts=$((attempts + 1))
            if [ $attempts -eq $max_attempts ]; then
                log_error "$service failed to become healthy"
                docker-compose -f "$COMPOSE_FILE" logs --tail=20 "$service"
                return 1
            fi
            
            sleep 10
        done
    done
    
    log_success "All critical services are healthy"
}

display_status() {
    log_section "Deployment Status"
    
    echo "Service Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo -e "\nGPU Status:"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits | while read line; do
            echo "  $line"
        done
    else
        echo "  nvidia-smi not available"
    fi
    
    echo -e "\nService Endpoints:"
    local host_ip=$(hostname -I | awk '{print $1}' || echo "localhost")
    echo "  GameForge App: http://$host_ip:8080"
    echo "  GPU Inference: http://$host_ip:8081"
    echo "  GPU Training: http://$host_ip:8082"
    echo "  Grafana: http://$host_ip:3000"
    echo "  Prometheus: http://$host_ip:9090"
    
    echo -e "\nResource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

cleanup_old_resources() {
    log_section "Cleaning Up Old Resources"
    
    log_info "Removing unused Docker resources..."
    docker system prune -f
    docker volume prune -f
    
    log_info "Removing old images..."
    docker image prune -f
    
    log_success "Cleanup completed"
}

show_logs() {
    log_section "Recent Service Logs"
    
    echo "GameForge App logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=10 gameforge-app
    
    echo -e "\nGPU Inference logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=10 gameforge-gpu-inference
    
    echo -e "\nGPU Training logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=10 gameforge-gpu-training
}

# ========================================================================
# Main Deployment Function
# ========================================================================
main() {
    log_section "GameForge AI Vast.ai Deployment"
    log_info "Starting deployment to Vast.ai cloud GPU instance..."
    
    # Parse command line arguments
    local SKIP_BUILD=false
    local SHOW_LOGS_ONLY=false
    local CLEANUP_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --logs)
                SHOW_LOGS_ONLY=true
                shift
                ;;
            --cleanup)
                CLEANUP_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-build    Skip building Docker images"
                echo "  --logs          Show recent service logs only"
                echo "  --cleanup       Clean up old resources only"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Handle special modes
    if [ "$SHOW_LOGS_ONLY" = true ]; then
        show_logs
        exit 0
    fi
    
    if [ "$CLEANUP_ONLY" = true ]; then
        cleanup_old_resources
        exit 0
    fi
    
    # Full deployment process
    check_requirements
    setup_environment
    create_volumes
    
    if [ "$SKIP_BUILD" = false ]; then
        build_images
    else
        log_info "Skipping image build as requested"
    fi
    
    deploy_services
    check_health
    display_status
    
    log_section "Deployment Complete!"
    log_success "GameForge AI Platform is now running on Vast.ai"
    log_info "Check the service endpoints above to access your deployment"
    log_info "Use 'docker-compose -f $COMPOSE_FILE logs -f <service>' to follow logs"
    log_info "Use '$0 --logs' to see recent logs from all services"
}

# ========================================================================
# Error Handling
# ========================================================================
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"
