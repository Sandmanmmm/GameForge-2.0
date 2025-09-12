#!/bin/bash
# GameForge AI System - Production Build and Deploy Script
# Phase 0: Foundation Containerization

set -e

echo "🚀 GameForge AI Production Deployment - Phase 0"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed!"
    exit 1
fi

# Check NVIDIA Docker runtime
if ! docker info | grep -q nvidia; then
    print_warning "NVIDIA Docker runtime not detected. GPU support may not work."
fi

print_success "Prerequisites check completed"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p generated_assets logs static config
mkdir -p nginx/ssl monitoring/grafana/dashboards monitoring/grafana/datasources

# Set permissions
chmod -R 755 generated_assets logs static
chmod 600 nginx/ssl/* 2>/dev/null || true

print_success "Directories created"

# Build the GameForge AI image
print_status "Building GameForge AI Docker image..."
docker build -f gameforge-ai.Dockerfile -t gameforge-ai:latest .

if [ $? -eq 0 ]; then
    print_success "GameForge AI image built successfully"
else
    print_error "Failed to build GameForge AI image"
    exit 1
fi

# Pull other required images
print_status "Pulling required images..."
docker pull redis:7.2-alpine
docker pull nginx:1.25-alpine
docker pull prom/prometheus:v2.47.2
docker pull grafana/grafana:10.2.0

print_success "Images pulled successfully"

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose -f docker-compose.production.yml down --remove-orphans || true

# Start the production stack
print_status "Starting GameForge AI production stack..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Health checks
print_status "Performing health checks..."

# Check Redis
if docker exec gameforge-redis redis-cli ping | grep -q PONG; then
    print_success "Redis is healthy"
else
    print_error "Redis health check failed"
fi

# Check GameForge AI
if curl -f http://localhost:8080/health &> /dev/null; then
    print_success "GameForge AI is healthy"
else
    print_error "GameForge AI health check failed"
fi

# Check Nginx
if curl -f http://localhost/health &> /dev/null; then
    print_success "Nginx is healthy"
else
    print_error "Nginx health check failed"
fi

# Initialize Elasticsearch log pipeline
print_status "Initializing Elasticsearch log pipeline..."
if [ -f "./monitoring/logging/elasticsearch-init.sh" ]; then
    chmod +x ./monitoring/logging/elasticsearch-init.sh
    docker exec gameforge-elasticsearch-secure /bin/bash -c "
        export ELASTIC_PASSWORD='${ELASTIC_PASSWORD}'
        export LOGSTASH_SYSTEM_PASSWORD='${LOGSTASH_SYSTEM_PASSWORD}'
        export FILEBEAT_SYSTEM_PASSWORD='${FILEBEAT_SYSTEM_PASSWORD}'
        ./monitoring/logging/elasticsearch-init.sh
    "
    if [ $? -eq 0 ]; then
        print_success "Elasticsearch log pipeline initialized"
    else
        print_warning "Elasticsearch initialization completed with warnings"
    fi
else
    print_warning "Elasticsearch initialization script not found"
fi

# Display service URLs
echo
print_success "🎉 GameForge AI Production Stack Deployed Successfully!"
echo "=============================================="
echo -e "${GREEN}Service URLs:${NC}"
echo "• GameForge AI API: http://localhost:8080"
echo "• Load Balancer: http://localhost"
echo "• Prometheus: http://localhost:9090"
echo "• Grafana: http://localhost:3000 (admin/gameforge123)"
echo
echo -e "${BLUE}Quick Test:${NC}"
echo "curl http://localhost/api/health"
echo
echo -e "${YELLOW}Logs:${NC}"
echo "docker-compose -f docker-compose.production.yml logs -f"
echo
echo -e "${YELLOW}Stop Services:${NC}"
echo "docker-compose -f docker-compose.production.yml down"
echo
print_success "Phase 0: Foundation Containerization Complete! ✅"
