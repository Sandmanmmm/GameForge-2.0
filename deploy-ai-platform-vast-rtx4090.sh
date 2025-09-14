#!/bin/bash
# =============================================================================
# GameForge AI Platform Deployment Script for Vast.ai RTX 4090
# =============================================================================
# This script deploys the complete GameForge AI platform on a Vast.ai RTX 4090 instance
# Services included: TorchServe, Ray Cluster, KubeFlow, MLflow, DCGM Monitoring

set -euo pipefail

# =============================================================================
# Configuration Variables
# =============================================================================
VAST_AI_INSTANCE_TYPE="RTX_4090"
DOCKER_COMPOSE_FILE="docker/compose/docker-compose.production-hardened.yml"
LOG_FILE="/tmp/gameforge-deployment-$(date +%Y%m%d-%H%M%S).log"
REQUIRED_GPU_MEMORY="24GB"
REQUIRED_SYSTEM_MEMORY="32GB"
REQUIRED_DISK_SPACE="200GB"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Function
# =============================================================================
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# System Requirements Check
# =============================================================================
check_system_requirements() {
    log "🔍 Checking system requirements for RTX 4090 deployment..."
    
    # Check for NVIDIA GPU
    if ! nvidia-smi &>/dev/null; then
        error "NVIDIA GPU not detected. This deployment requires RTX 4090."
    fi
    
    # Check GPU model
    GPU_MODEL=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)
    if [[ ! "$GPU_MODEL" =~ "4090" ]]; then
        warning "Expected RTX 4090, found: $GPU_MODEL. Continuing anyway..."
    fi
    
    # Check VRAM
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    if [ "$GPU_MEMORY" -lt 20000 ]; then  # 20GB minimum for 24GB RTX 4090
        error "Insufficient GPU memory: ${GPU_MEMORY}MB. RTX 4090 requires 24GB."
    fi
    
    # Check system memory
    SYSTEM_MEMORY=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$SYSTEM_MEMORY" -lt 30 ]; then
        warning "Low system memory: ${SYSTEM_MEMORY}GB. Recommended: 32GB+"
    fi
    
    # Check disk space
    DISK_SPACE=$(df -h / | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "${DISK_SPACE%.*}" -lt 150 ]; then
        warning "Low disk space: ${DISK_SPACE}GB available. Recommended: 200GB+"
    fi
    
    success "✅ System requirements check completed"
}

# =============================================================================
# NVIDIA Container Runtime Setup
# =============================================================================
setup_nvidia_runtime() {
    log "🔧 Setting up NVIDIA container runtime..."
    
    # Install nvidia-container-toolkit if not present
    if ! command -v nvidia-container-runtime &> /dev/null; then
        log "Installing NVIDIA container toolkit..."
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        
        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
    fi
    
    success "✅ NVIDIA container runtime configured"
}

# =============================================================================
# Docker Environment Setup
# =============================================================================
setup_docker_environment() {
    log "🐳 Setting up Docker environment..."
    
    # Create necessary directories
    sudo mkdir -p /opt/gameforge/{models,data,logs,config}
    sudo mkdir -p /var/lib/gameforge/{torchserve,ray,kubeflow,mlflow}
    
    # Set proper permissions
    sudo chown -R $USER:$USER /opt/gameforge
    sudo chown -R $USER:$USER /var/lib/gameforge
    
    # Create Docker networks if they don't exist
    docker network ls | grep -q ai-network || docker network create ai-network
    docker network ls | grep -q gpu-network || docker network create gpu-network
    docker network ls | grep -q ml-network || docker network create ml-network
    
    success "✅ Docker environment configured"
}

# =============================================================================
# AI Platform Services Deployment
# =============================================================================
deploy_ai_platform() {
    log "🚀 Deploying GameForge AI Platform on RTX 4090..."
    
    # Verify Docker Compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
    fi
    
    # Pull images first to check for issues
    log "📥 Pulling Docker images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull torchserve-rtx4090 ray-head-rtx4090 kubeflow-pipelines-rtx4090 dcgm-exporter-rtx4090 mlflow-model-registry-rtx4090 || {
        warning "Some images failed to pull. Building locally..."
    }
    
    # Build custom images
    log "🔨 Building custom AI platform images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build torchserve-rtx4090 ray-head-rtx4090
    
    # Deploy AI services in stages for better resource management
    log "🎯 Deploying TorchServe RTX 4090..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d torchserve-rtx4090
    
    # Wait for TorchServe to be ready
    log "⏳ Waiting for TorchServe to be ready..."
    timeout 300 bash -c 'until curl -f http://localhost:8080/ping; do sleep 5; done' || {
        error "TorchServe failed to start within 5 minutes"
    }
    
    log "🎯 Deploying Ray Cluster RTX 4090..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d ray-head-rtx4090
    
    # Wait for Ray head to be ready
    log "⏳ Waiting for Ray head to be ready..."
    sleep 30
    
    log "🎯 Deploying KubeFlow Pipelines RTX 4090..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d kubeflow-pipelines-rtx4090
    
    log "🎯 Deploying DCGM GPU Monitoring..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d dcgm-exporter-rtx4090
    
    log "🎯 Deploying MLflow Model Registry RTX 4090..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d mlflow-model-registry-rtx4090
    
    success "✅ AI Platform deployment completed"
}

# =============================================================================
# Health Checks and Monitoring
# =============================================================================
run_health_checks() {
    log "🏥 Running health checks..."
    
    # Check TorchServe
    if curl -f http://localhost:8080/ping &>/dev/null; then
        success "✅ TorchServe is healthy"
    else
        error "❌ TorchServe health check failed"
    fi
    
    # Check TorchServe metrics
    if curl -f http://localhost:8082/metrics &>/dev/null; then
        success "✅ TorchServe metrics available"
    else
        warning "⚠️ TorchServe metrics not available"
    fi
    
    # Check Ray cluster
    if docker exec -i $(docker ps -q -f name=ray-head) ray status &>/dev/null; then
        success "✅ Ray cluster is healthy"
    else
        warning "⚠️ Ray cluster status check failed"
    fi
    
    # Check GPU utilization
    GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
    log "🔥 GPU Utilization: ${GPU_UTIL}%"
    
    # Check GPU memory usage
    GPU_MEM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    GPU_MEM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    log "💾 GPU Memory: ${GPU_MEM_USED}MB / ${GPU_MEM_TOTAL}MB"
    
    success "✅ Health checks completed"
}

# =============================================================================
# Display Service URLs
# =============================================================================
display_service_urls() {
    log "🌐 GameForge AI Platform Service URLs:"
    
    echo -e "\n${GREEN}TorchServe Model Serving:${NC}"
    echo "  • Inference API: http://localhost:8080"
    echo "  • Management API: http://localhost:8081"
    echo "  • Metrics: http://localhost:8082/metrics"
    echo "  • Web UI: https://torchserve.gameforge.local (via Traefik)"
    
    echo -e "\n${GREEN}Ray Cluster Dashboard:${NC}"
    echo "  • Ray Dashboard: http://localhost:8265"
    echo "  • Ray Client: ray://localhost:10001"
    
    echo -e "\n${GREEN}MLflow Model Registry:${NC}"
    echo "  • MLflow UI: http://localhost:5000"
    echo "  • MLflow Tracking: http://localhost:5000/api/2.0/mlflow"
    
    echo -e "\n${GREEN}KubeFlow Pipelines:${NC}"
    echo "  • KubeFlow UI: http://localhost:8080 (if port available)"
    
    echo -e "\n${GREEN}GPU Monitoring:${NC}"
    echo "  • DCGM Metrics: http://localhost:9400/metrics"
    echo "  • nvidia-smi: Available in all GPU containers"
    
    echo -e "\n${YELLOW}Logs Location:${NC} $LOG_FILE"
    echo -e "${YELLOW}Docker Compose File:${NC} $DOCKER_COMPOSE_FILE"
}

# =============================================================================
# Cleanup Function
# =============================================================================
cleanup() {
    log "🧹 Cleaning up temporary files..."
    # Add any cleanup operations here
    log "✅ Cleanup completed"
}

# =============================================================================
# Main Deployment Function
# =============================================================================
main() {
    log "🚀 Starting GameForge AI Platform deployment for Vast.ai RTX 4090"
    log "📋 Deployment configuration:"
    log "   • Instance Type: $VAST_AI_INSTANCE_TYPE"
    log "   • Docker Compose: $DOCKER_COMPOSE_FILE"
    log "   • Log File: $LOG_FILE"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_system_requirements
    setup_nvidia_runtime
    setup_docker_environment
    deploy_ai_platform
    run_health_checks
    display_service_urls
    
    success "🎉 GameForge AI Platform successfully deployed on RTX 4090!"
    success "🎯 The platform is ready for AI/ML workloads"
    
    log "📊 Deployment Summary:"
    log "   • TorchServe: Model serving with RTX 4090 optimization"
    log "   • Ray Cluster: Distributed computing for scaling"
    log "   • KubeFlow: ML pipeline orchestration"
    log "   • MLflow: Model registry and experiment tracking"
    log "   • DCGM: GPU health monitoring"
    log "   • Production Security: Hardened containers and networks"
}

# =============================================================================
# Script Execution
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
