#!/bin/bash
# Vast.ai RTX4090 Deployment Script for GameForge Enhanced Generation Engine
# Usage: ./deploy-vastai-rtx4090.sh

set -e

echo "🚀 Starting GameForge Enhanced Generation Engine deployment on Vast.ai RTX4090..."

# Configuration
PROJECT_NAME="gameforge-enhanced-generation"
DOCKER_IMAGE="gameforge/enhanced-gen:rtx4090"
VAST_INSTANCE_TYPE="rtx4090"
MIN_GPU_MEMORY="20000"  # 20GB minimum
MIN_RAM="28000"         # 28GB minimum
MIN_DISK="80"           # 80GB minimum

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if vast CLI is installed
    if ! command -v vast &> /dev/null; then
        log_error "Vast CLI not found. Installing..."
        pip install vastai
    fi
    
    # Check if Docker is available locally for building
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found locally. Will use vast.ai for building."
    fi
    
    log_success "Prerequisites checked"
}

# Function to build Docker image for RTX4090
build_docker_image() {
    log_info "Building Docker image for RTX4090..."
    
    cat > Dockerfile.vastai-rtx4090 << 'EOF'
# GameForge Enhanced Generation Engine - RTX4090 Optimized
FROM nvidia/cuda:12.1-cudnn8-devel-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
ENV TORCH_CUDA_ARCH_LIST="8.9"  # RTX4090 architecture
ENV FORCE_CUDA="1"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    curl \
    unzip \
    build-essential \
    cmake \
    ninja-build \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install PyTorch with CUDA 12.1 support for RTX4090
RUN pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu121

# Install xFormers for memory optimization
RUN pip install xformers==0.0.22.post7 --index-url https://download.pytorch.org/whl/cu121

# Install core ML libraries
RUN pip install \
    diffusers==0.24.0 \
    transformers==4.35.0 \
    accelerate==0.24.0 \
    controlnet-aux==0.0.7 \
    compel==2.0.2

# Install image and audio processing
RUN pip install \
    Pillow==10.0.0 \
    opencv-python==4.8.0.76 \
    scikit-image==0.21.0 \
    imageio==2.31.6 \
    soundfile==0.12.1 \
    librosa==0.10.1 \
    trimesh==4.0.5

# Install web framework and utilities
RUN pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    redis==5.0.1 \
    aioredis==2.0.1 \
    numpy==1.24.4 \
    scipy==1.11.4 \
    tqdm==4.66.1

# Install monitoring and logging
RUN pip install \
    prometheus-client==0.18.0 \
    structlog==23.2.0 \
    rich==13.7.0

# Set working directory
WORKDIR /app

# Copy application code
COPY services/asset-gen-v2/ ./services/asset-gen-v2/
COPY core/ ./core/
COPY requirements.txt ./

# Install any additional requirements
RUN pip install -r requirements.txt || true

# Create necessary directories
RUN mkdir -p /app/generated_assets /app/asset_cache /app/models /app/logs

# Set permissions
RUN chmod -R 755 /app

# Environment variables for optimization
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
ENV TOKENIZERS_PARALLELISM=false

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5m --retries=3 \
    CMD python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU count:', torch.cuda.device_count())" || exit 1

# Expose port
EXPOSE 8080

# Default command
CMD ["python", "-m", "services.asset-gen-v2.main"]
EOF

    if command -v docker &> /dev/null; then
        log_info "Building Docker image locally..."
        docker build -f Dockerfile.vastai-rtx4090 -t $DOCKER_IMAGE .
        log_success "Docker image built successfully"
    else
        log_warning "Docker not available locally. Image will be built on vast.ai"
    fi
}

# Function to find suitable vast.ai instance
find_vastai_instance() {
    log_info "Searching for suitable RTX4090 instances..."
    
    # Search for RTX4090 instances with minimum requirements
    vast search offers \
        --type=bid \
        --gpu_name="RTX_4090" \
        --gpu_ram="$MIN_GPU_MEMORY" \
        --ram="$MIN_RAM" \
        --disk="$MIN_DISK" \
        --sort_by="score" \
        --order=desc \
        --limit=10 \
        --format=json > available_instances.json
    
    if [ -s available_instances.json ]; then
        log_success "Found suitable RTX4090 instances"
        
        # Display top 3 options
        log_info "Top 3 available instances:"
        head -3 available_instances.json | jq -r '.[] | "ID: \(.id) | GPU: \(.gpu_name) | RAM: \(.ram)GB | Price: $\(.dph_total)/hr"'
        
        # Get the best instance ID
        INSTANCE_ID=$(head -1 available_instances.json | jq -r '.[0].id')
        log_info "Selected instance ID: $INSTANCE_ID"
        
        return 0
    else
        log_error "No suitable RTX4090 instances found"
        return 1
    fi
}

# Function to create vast.ai instance
create_vastai_instance() {
    log_info "Creating vast.ai instance..."
    
    # Create the instance
    VAST_CREATE_OUTPUT=$(vast create instance $INSTANCE_ID \
        --image "$DOCKER_IMAGE" \
        --disk "$MIN_DISK" \
        --onstart-cmd "cd /app && python -m services.asset-gen-v2.main" \
        --ssh)
    
    # Extract instance ID from output
    NEW_INSTANCE_ID=$(echo "$VAST_CREATE_OUTPUT" | grep -o 'Started\. New instance is [0-9]*' | grep -o '[0-9]*$')
    
    if [ -n "$NEW_INSTANCE_ID" ]; then
        log_success "Instance created with ID: $NEW_INSTANCE_ID"
        echo "$NEW_INSTANCE_ID" > vast_instance_id.txt
        
        # Wait for instance to be ready
        log_info "Waiting for instance to be ready..."
        sleep 30
        
        return 0
    else
        log_error "Failed to create instance"
        return 1
    fi
}

# Function to deploy application
deploy_application() {
    local instance_id=$1
    log_info "Deploying application to instance $instance_id..."
    
    # Get instance info
    vast show instance $instance_id --format=json > instance_info.json
    
    if [ -s instance_info.json ]; then
        SSH_HOST=$(jq -r '.[0].ssh_host' instance_info.json)
        SSH_PORT=$(jq -r '.[0].ssh_port' instance_info.json)
        
        log_info "Instance details:"
        log_info "SSH Host: $SSH_HOST"
        log_info "SSH Port: $SSH_PORT"
        
        # Wait for SSH to be ready
        log_info "Waiting for SSH connection..."
        for i in {1..30}; do
            if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p $SSH_PORT root@$SSH_HOST "echo 'SSH Ready'" 2>/dev/null; then
                log_success "SSH connection established"
                break
            fi
            sleep 10
        done
        
        # Copy application files
        log_info "Copying application files..."
        scp -o StrictHostKeyChecking=no -P $SSH_PORT -r services/ core/ requirements.txt root@$SSH_HOST:/app/
        
        # Install dependencies and start services
        log_info "Installing dependencies and starting services..."
        ssh -o StrictHostKeyChecking=no -p $SSH_PORT root@$SSH_HOST << 'REMOTE_SCRIPT'
cd /app

# Install any missing dependencies
pip install -r requirements.txt

# Download and cache models
python -c "
import torch
from diffusers import StableDiffusionPipeline
print('Downloading Stable Diffusion model...')
pipeline = StableDiffusionPipeline.from_pretrained(
    'runwayml/stable-diffusion-v1-5',
    torch_dtype=torch.float16
)
print('Model downloaded and cached')
"

# Set up systemd service
cat > /etc/systemd/system/gameforge-gen.service << 'EOF'
[Unit]
Description=GameForge Enhanced Generation Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/app
Environment=PYTHONUNBUFFERED=1
Environment=CUDA_VISIBLE_DEVICES=0
ExecStart=/usr/bin/python -m services.asset-gen-v2.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable gameforge-gen.service
systemctl start gameforge-gen.service

# Check service status
systemctl status gameforge-gen.service
REMOTE_SCRIPT
        
        log_success "Application deployed successfully"
        return 0
    else
        log_error "Failed to get instance information"
        return 1
    fi
}

# Function to run health checks
run_health_checks() {
    local instance_id=$1
    log_info "Running health checks on instance $instance_id..."
    
    # Get instance info
    SSH_HOST=$(jq -r '.[0].ssh_host' instance_info.json)
    SSH_PORT=$(jq -r '.[0].ssh_port' instance_info.json)
    
    # Run health checks
    ssh -o StrictHostKeyChecking=no -p $SSH_PORT root@$SSH_HOST << 'HEALTH_SCRIPT'
cd /app

# Check CUDA availability
python -c "
import torch
print('=== CUDA Health Check ===')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'CUDA Version: {torch.version.cuda}')
print(f'GPU Count: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    print(f'GPU Name: {torch.cuda.get_device_name(0)}')
    print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
print()
"

# Check service status
echo "=== Service Status ==="
systemctl is-active gameforge-gen.service
echo

# Check if API is responding
echo "=== API Health Check ==="
sleep 5
curl -f http://localhost:8080/health || echo "API not yet ready"
echo

# Check GPU utilization
echo "=== GPU Utilization ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
HEALTH_SCRIPT

    log_success "Health checks completed"
}

# Function to display deployment summary
display_summary() {
    local instance_id=$1
    
    echo
    log_success "🎉 GameForge Enhanced Generation Engine deployed successfully!"
    echo
    echo "=== Deployment Summary ==="
    echo "Instance ID: $instance_id"
    echo "Docker Image: $DOCKER_IMAGE"
    echo "GPU: RTX4090"
    
    if [ -s instance_info.json ]; then
        SSH_HOST=$(jq -r '.[0].ssh_host' instance_info.json)
        SSH_PORT=$(jq -r '.[0].ssh_port' instance_info.json)
        PUBLIC_IP=$(jq -r '.[0].public_ipaddr' instance_info.json)
        
        echo "SSH Access: ssh -p $SSH_PORT root@$SSH_HOST"
        echo "API Endpoint: http://$PUBLIC_IP:8080"
        echo "Health Check: http://$PUBLIC_IP:8080/health"
    fi
    
    echo
    echo "=== Useful Commands ==="
    echo "Monitor logs: vast logs $instance_id"
    echo "SSH to instance: vast ssh $instance_id"
    echo "Stop instance: vast stop instance $instance_id"
    echo "Destroy instance: vast destroy instance $instance_id"
    echo
    echo "=== Next Steps ==="
    echo "1. Test the API endpoints"
    echo "2. Generate test assets"
    echo "3. Monitor GPU utilization"
    echo "4. Scale as needed"
}

# Main deployment function
main() {
    log_info "Starting GameForge Enhanced Generation deployment..."
    
    # Check prerequisites
    check_prerequisites || exit 1
    
    # Build Docker image
    build_docker_image || exit 1
    
    # Find suitable instance
    find_vastai_instance || exit 1
    
    # Create instance
    create_vastai_instance || exit 1
    
    # Get the instance ID
    if [ -f vast_instance_id.txt ]; then
        INSTANCE_ID=$(cat vast_instance_id.txt)
    else
        log_error "Could not determine instance ID"
        exit 1
    fi
    
    # Deploy application
    deploy_application $INSTANCE_ID || exit 1
    
    # Run health checks
    run_health_checks $INSTANCE_ID || exit 1
    
    # Display summary
    display_summary $INSTANCE_ID
    
    log_success "Deployment completed successfully! 🚀"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"
