# GameForge AI Production Platform - Vast.ai Cloud GPU Deployment

## Overview

This is a production-ready deployment of the GameForge AI Platform optimized for Vast.ai cloud GPU instances. It includes all security hardening, monitoring, and GPU optimization features from the main production deployment, streamlined for cloud deployment.

## Features

### 🔐 **Security Hardening**
- **Security Bootstrap**: One-shot initialization with security baseline configuration
- **Security Monitor**: Continuous monitoring of security posture
- **Container Security**: Seccomp profiles, capability dropping, non-root users
- **Network Isolation**: Segmented networks with internal/external separation
- **Vault Integration**: HashiCorp Vault for secrets management
- **Resource Limits**: Memory, CPU, and PID limits for all services

### 🚀 **GPU Optimization**
- **Dedicated GPU Services**: Separate inference and training services
- **NVIDIA Runtime**: Optimized CUDA 12.1 support with PyTorch 2.1
- **Memory Management**: Advanced CUDA memory allocation and garbage collection
- **Workload Coordination**: Load balancing between GPU services
- **Resource Allocation**: Configurable GPU memory fractions for different workloads

### 📊 **Production Monitoring**
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Comprehensive dashboards for system and GPU monitoring
- **Elasticsearch**: Centralized logging and search
- **Health Checks**: Automated service health monitoring
- **Resource Tracking**: Real-time CPU, memory, and GPU utilization

### 🛠 **Infrastructure**
- **PostgreSQL**: Production-grade database with performance tuning
- **Redis**: High-performance caching and job queuing
- **Nginx**: Reverse proxy with GPU service routing
- **Auto-scaling**: Dynamic resource allocation based on workload

## Quick Start

### Prerequisites

1. **Vast.ai Account**: Sign up at [vast.ai](https://vast.ai)
2. **GPU Instance**: Rent a GPU instance with:
   - NVIDIA GPU (RTX 3090, RTX 4090, or V100 recommended)
   - At least 16GB RAM
   - 100GB+ storage
   - Ubuntu 20.04+ with Docker pre-installed

### Deployment Steps

1. **Clone Repository**:
   ```bash
   git clone <your-repo-url>
   cd ai-game-production-p
   ```

2. **Configure Environment**:
   ```bash
   # Copy and edit the environment file
   cp .env.vastai-production .env.vastai-production.local
   nano .env.vastai-production.local
   ```

   **Important**: Update these critical settings:
   ```bash
   # Security (CHANGE THESE!)
   POSTGRES_PASSWORD=your_secure_postgres_password_here
   REDIS_PASSWORD=your_secure_redis_password_here
   JWT_SECRET_KEY=your_jwt_secret_key_here
   SECRET_KEY=your_app_secret_key_here
   VAULT_ROOT_TOKEN=your_vault_root_token_here
   
   # OpenAI API
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Vast.ai Instance
   VASTAI_INSTANCE_ID=your_instance_id_here
   ```

3. **Deploy with Script** (Recommended):
   ```bash
   # Linux/Unix
   chmod +x deploy-vastai-production.sh
   ./deploy-vastai-production.sh
   
   # Windows PowerShell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\deploy-vastai-production.ps1
   ```

4. **Manual Deployment**:
   ```bash
   # Copy optimized .dockerignore
   cp .dockerignore.vastai .dockerignore
   
   # Load environment
   source .env.vastai-production
   
   # Build and deploy
   docker-compose -f docker-compose.vastai-production.yml build
   docker-compose -f docker-compose.vastai-production.yml up -d
   ```

## Service Architecture

### Core Services

| Service | Port | Description |
|---------|------|-------------|
| **gameforge-app** | 8080 | Main application server |
| **gameforge-gpu-inference** | 8081 | GPU inference service |
| **gameforge-gpu-training** | 8082 | GPU training service |
| **nginx** | 80/443 | Reverse proxy and load balancer |

### Infrastructure Services

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache and job queue |
| **vault** | 8200 | HashiCorp Vault (secrets) |
| **elasticsearch** | 9200 | Search and logging |

### Monitoring Services

| Service | Port | Description |
|---------|------|-------------|
| **prometheus** | 9090 | Metrics collection |
| **grafana** | 3000 | Monitoring dashboards |

## GPU Configuration

### GPU Memory Allocation

The platform optimally allocates GPU memory across services:

- **Inference Service**: 70% GPU memory (optimized for low latency)
- **Training Service**: 90% GPU memory (maximum throughput)
- **Main App**: Shared access for light GPU tasks

### CUDA Optimization

Key CUDA optimizations applied:

```bash
# Memory management
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,garbage_collection_threshold:0.8,expandable_segments:True

# Performance tuning
CUDA_LAUNCH_BLOCKING=0
CUDA_CACHE_DISABLE=0
PYTORCH_JIT=1
```

### GPU Service Endpoints

Access GPU services through the main app or directly:

```bash
# Through main app (recommended)
http://your-instance-ip/api/gpu/inference/
http://your-instance-ip/api/gpu/training/

# Direct access
http://your-instance-ip:8081/  # Inference
http://your-instance-ip:8082/  # Training
```

## Security Configuration

### Authentication & Secrets

The platform uses HashiCorp Vault for secure secret management:

1. **Database Credentials**: Stored in Vault with automatic rotation
2. **API Keys**: Encrypted storage for OpenAI and other external APIs
3. **JWT Tokens**: Secure token generation and validation
4. **SSL Certificates**: Automated certificate management

### Network Security

- **Frontend Network**: Public-facing services (nginx)
- **Backend Network**: Internal services (database, cache)
- **GPU Network**: High-performance GPU service communication
- **Vault Network**: Isolated secrets management
- **Monitoring Network**: Observability services

### Container Security

All containers implement security best practices:

- **Non-root Users**: All services run as non-root
- **Read-only Filesystems**: Where possible
- **Capability Dropping**: Minimal required capabilities
- **Seccomp Profiles**: Syscall filtering
- **Resource Limits**: Memory, CPU, and PID limits

## Monitoring & Observability

### Grafana Dashboards

Access Grafana at `http://your-instance-ip:3000`:

- **GPU Utilization**: Real-time GPU metrics
- **Application Performance**: Response times, error rates
- **Infrastructure Health**: CPU, memory, disk usage
- **Security Monitoring**: Security events and compliance

### Prometheus Metrics

Key metrics collected:

- GPU utilization and memory usage
- Application request/response metrics
- Database performance indicators
- Cache hit rates
- Security events

### Log Management

Centralized logging through Elasticsearch:

- **Application Logs**: Structured JSON logging
- **Security Logs**: Authentication and authorization events
- **Performance Logs**: Request tracing and profiling
- **Error Logs**: Exception tracking and debugging

## Management Commands

### Service Management

```bash
# Check service status
docker-compose -f docker-compose.vastai-production.yml ps

# View logs
docker-compose -f docker-compose.vastai-production.yml logs -f gameforge-app
docker-compose -f docker-compose.vastai-production.yml logs -f gameforge-gpu-inference

# Restart services
docker-compose -f docker-compose.vastai-production.yml restart gameforge-app

# Scale services
docker-compose -f docker-compose.vastai-production.yml up -d --scale gameforge-worker=3
```

### Health Checks

```bash
# Check all service health
./deploy-vastai-production.sh --logs

# Manual health checks
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

### Resource Monitoring

```bash
# GPU utilization
nvidia-smi

# Container resources
docker stats

# System resources
htop
```

## Troubleshooting

### Common Issues

1. **GPU Not Detected**:
   ```bash
   # Check NVIDIA runtime
   docker info | grep nvidia
   
   # Test GPU access
   docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
   ```

2. **Service Won't Start**:
   ```bash
   # Check logs
   docker-compose -f docker-compose.vastai-production.yml logs service-name
   
   # Check health
   docker-compose -f docker-compose.vastai-production.yml ps
   ```

3. **Out of Memory**:
   ```bash
   # Check GPU memory
   nvidia-smi
   
   # Adjust GPU memory fractions in .env file
   GPU_MEMORY_FRACTION="0.5"  # Reduce for inference
   ```

4. **Build Failures**:
   ```bash
   # Clean Docker cache
   docker system prune -a
   
   # Rebuild specific service
   docker-compose -f docker-compose.vastai-production.yml build --no-cache service-name
   ```

### Performance Tuning

1. **GPU Memory Optimization**:
   - Adjust `GPU_MEMORY_FRACTION` based on workload
   - Monitor memory usage with `nvidia-smi`
   - Use mixed precision training (`MIXED_PRECISION=fp16`)

2. **CPU Optimization**:
   - Adjust worker counts based on CPU cores
   - Monitor CPU usage and adjust limits
   - Use CPU affinity for GPU services

3. **Memory Optimization**:
   - Monitor container memory usage
   - Adjust memory limits based on actual usage
   - Use memory-mapped files for large datasets

### Support

For issues and support:

1. **Check Logs**: Always start with service logs
2. **Monitor Resources**: Use Grafana dashboards
3. **Vast.ai Support**: Contact Vast.ai for instance-specific issues
4. **Community**: Check GitHub issues and discussions

## Cost Optimization

### Vast.ai Instance Selection

**Recommended Instances**:
- **Development**: RTX 3070/3080 (8-12 GB VRAM, $0.20-0.40/hour)
- **Production**: RTX 4090 (24 GB VRAM, $0.50-0.80/hour)
- **Training**: Multiple GPU setups (2x RTX 4090, $1.00-1.50/hour)

### Cost Saving Tips

1. **Spot Instances**: Use interruptible instances for development
2. **Auto-scaling**: Scale down unused services
3. **Model Caching**: Persistent model storage to avoid re-downloads
4. **Monitoring**: Use alerts to avoid unexpected costs

## Security Checklist

Before production deployment:

- [ ] Change all default passwords in `.env.vastai-production`
- [ ] Configure SSL certificates for HTTPS
- [ ] Set up backup and disaster recovery
- [ ] Configure monitoring and alerting
- [ ] Review and test security policies
- [ ] Enable firewall rules for your instance
- [ ] Set up log retention policies
- [ ] Configure secret rotation schedules

## Updates and Maintenance

### Regular Updates

```bash
# Update images
docker-compose -f docker-compose.vastai-production.yml pull

# Rebuild with updates
./deploy-vastai-production.sh

# Backup before updates
docker-compose -f docker-compose.vastai-production.yml exec postgres pg_dump -U gameforge gameforge_prod > backup.sql
```

### Scheduled Maintenance

1. **Daily**: Check service health and logs
2. **Weekly**: Update container images
3. **Monthly**: Review security policies and rotate secrets
4. **Quarterly**: Performance optimization and capacity planning

---

**Ready to Deploy?** Follow the Quick Start guide above and your GameForge AI Platform will be running on Vast.ai in minutes!
