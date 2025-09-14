#!/usr/bin/env bash
"""
GameForge Vast.ai RTX 4090 Deployment Script
Complete setup and deployment for vast.ai instance with RTX 4090
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTANCE_TYPE="RTX4090"
MIN_VRAM="20"  # Minimum 20GB VRAM
GAMEFORGE_REPO="https://github.com/your-org/gameforge.git"
DOCKER_COMPOSE_FILE="docker-compose.vastai-rtx4090.yml"

echo -e "${BLUE}🚀 GameForge Vast.ai RTX 4090 Deployment${NC}"
echo "=================================================="

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on vast.ai
check_vast_ai() {
    print_status "Checking vast.ai environment..."
    
    if [ ! -f "/etc/vast_ai" ] && [ ! -d "/opt/vast" ]; then
        print_warning "Not detected as vast.ai instance, proceeding anyway..."
    else
        print_status "Vast.ai environment detected"
    fi
}

# Check RTX 4090 availability
check_rtx4090() {
    print_status "Checking RTX 4090 availability..."
    
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits)
        echo "GPU Info: $GPU_INFO"
        
        if echo "$GPU_INFO" | grep -q "RTX 4090"; then
            print_status "RTX 4090 detected!"
            
            # Check VRAM
            VRAM=$(echo "$GPU_INFO" | grep "RTX 4090" | cut -d',' -f2 | tr -d ' ')
            VRAM_GB=$((VRAM / 1024))
            
            if [ "$VRAM_GB" -ge "$MIN_VRAM" ]; then
                print_status "VRAM check passed: ${VRAM_GB}GB"
            else
                print_error "Insufficient VRAM: ${VRAM_GB}GB (minimum ${MIN_VRAM}GB required)"
                exit 1
            fi
        else
            print_error "RTX 4090 not found. Available GPUs:"
            nvidia-smi --list-gpus
            exit 1
        fi
    else
        print_error "nvidia-smi not found. NVIDIA drivers may not be installed."
        exit 1
    fi
}

# Install required packages
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Update package list
    sudo apt-get update -qq
    
    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        print_status "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
    else
        print_status "Docker already installed"
    fi
    
    # Install Docker Compose if not present
    if ! command -v docker-compose &> /dev/null; then
        print_status "Installing Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    else
        print_status "Docker Compose already installed"
    fi
    
    # Install NVIDIA Container Toolkit
    if ! docker info 2>/dev/null | grep -q nvidia; then
        print_status "Installing NVIDIA Container Toolkit..."
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt-get update -qq
        sudo apt-get install -y nvidia-docker2
        sudo systemctl restart docker
    else
        print_status "NVIDIA Container Toolkit already configured"
    fi
    
    # Install additional tools
    sudo apt-get install -y \
        git \
        htop \
        iotop \
        python3-pip \
        python3-venv \
        wget \
        curl \
        unzip
    
    print_status "Dependencies installed successfully"
}

# Clone or update GameForge repository
setup_gameforge() {
    print_status "Setting up GameForge repository..."
    
    if [ -d "gameforge" ]; then
        print_status "Updating existing GameForge repository..."
        cd gameforge
        git pull origin main
        cd ..
    else
        print_status "Cloning GameForge repository..."
        git clone $GAMEFORGE_REPO gameforge
    fi
    
    cd gameforge
    
    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    chmod +x scripts/*.py 2>/dev/null || true
    
    print_status "GameForge repository ready"
}

# Setup Python environment for model management
setup_python_env() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    
    # Install additional packages for RTX 4090
    pip install \
        torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 \
        transformers \
        diffusers \
        accelerate \
        huggingface_hub \
        torchserve \
        torch-model-archiver
    
    print_status "Python environment configured"
}

# Create necessary directories and set permissions
setup_directories() {
    print_status "Setting up directories..."
    
    # Create model directories
    sudo mkdir -p /models
    sudo chown -R $USER:$USER /models
    chmod 755 /models
    
    # Create log directories
    mkdir -p logs/torchserve
    mkdir -p logs/ray
    mkdir -p logs/prometheus
    mkdir -p logs/grafana
    
    # Create data directories for persistence
    mkdir -p data/prometheus
    mkdir -p data/grafana
    mkdir -p data/mlflow
    
    print_status "Directories created"
}

# Configure Docker daemon for optimal performance
configure_docker() {
    print_status "Configuring Docker for RTX 4090..."
    
    # Create Docker daemon configuration
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "data-root": "/var/lib/docker"
}
EOF
    
    # Restart Docker
    sudo systemctl restart docker
    
    # Test NVIDIA Docker
    print_status "Testing NVIDIA Docker integration..."
    docker run --rm --gpus all nvidia/cuda:12.2-base-ubuntu20.04 nvidia-smi
    
    print_status "Docker configured successfully"
}

# Deploy the AI platform
deploy_platform() {
    print_status "Deploying GameForge AI Platform on RTX 4090..."
    
    # Set environment variables
    export GPU_MEMORY_FRACTION=0.7
    export CUDA_VISIBLE_DEVICES=0
    export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
    
    # Create Docker network
    docker network create ai-platform 2>/dev/null || true
    
    # Deploy using Docker Compose
    docker-compose -f docker/compose/$DOCKER_COMPOSE_FILE up -d
    
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check service health
    check_service_health
}

# Check service health
check_service_health() {
    print_status "Checking service health..."
    
    services=("prometheus" "grafana" "torchserve" "ray-head" "ray-worker")
    
    for service in "${services[@]}"; do
        if docker-compose -f docker/compose/$DOCKER_COMPOSE_FILE ps $service | grep -q "Up"; then
            print_status "$service: ✅ Running"
        else
            print_warning "$service: ❌ Not running"
        fi
    done
    
    # Check GPU access in containers
    print_status "Checking GPU access in TorchServe..."
    docker exec torchserve nvidia-smi || print_warning "GPU not accessible in TorchServe container"
}

# Download and deploy models
deploy_models() {
    print_status "Deploying AI models optimized for RTX 4090..."
    
    # Activate Python environment
    source venv/bin/activate
    
    # Run model manager
    python scripts/rtx4090-model-manager.py &
    MODEL_MANAGER_PID=$!
    
    print_status "Model manager started with PID: $MODEL_MANAGER_PID"
    
    # Wait for initial models to download
    sleep 60
    
    print_status "Models deployment initiated"
}

# Setup monitoring and alerting
setup_monitoring() {
    print_status "Setting up monitoring and alerting..."
    
    # Deploy monitoring stack
    docker-compose -f docker/compose/docker-compose.monitoring.yml up -d
    
    print_status "Monitoring stack deployed"
    print_status "Grafana available at: http://localhost:3000 (admin:admin123)"
    print_status "Prometheus available at: http://localhost:9090"
}

# Show deployment summary
show_summary() {
    echo ""
    echo -e "${GREEN}🎉 GameForge RTX 4090 Deployment Complete!${NC}"
    echo "=================================================="
    echo ""
    echo -e "${BLUE}Services:${NC}"
    echo "• Grafana Dashboard: http://localhost:3000 (admin:admin123)"
    echo "• Prometheus Metrics: http://localhost:9090"
    echo "• TorchServe API: http://localhost:8080"
    echo "• Ray Dashboard: http://localhost:8265"
    echo "• Jupyter Lab: http://localhost:8888"
    echo "• MLflow UI: http://localhost:5000"
    echo ""
    echo -e "${BLUE}RTX 4090 Status:${NC}"
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Access Grafana dashboard to monitor RTX 4090 performance"
    echo "2. Use TorchServe API to run inference on deployed models"
    echo "3. Monitor GPU utilization and adjust model deployment as needed"
    echo "4. Check logs: docker-compose logs -f [service-name]"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "• This vast.ai instance will be charged until terminated"
    echo "• Monitor costs and terminate when not in use"
    echo "• Data is not persistent across instance restarts"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}Starting GameForge RTX 4090 deployment...${NC}"
    
    check_vast_ai
    check_rtx4090
    install_dependencies
    setup_gameforge
    setup_python_env
    setup_directories
    configure_docker
    deploy_platform
    deploy_models
    setup_monitoring
    show_summary
    
    print_status "Deployment completed successfully! 🚀"
}

# Run main function
main "$@"
