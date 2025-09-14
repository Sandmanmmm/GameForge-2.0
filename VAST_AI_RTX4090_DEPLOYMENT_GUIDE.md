# GameForge AI Platform - Vast.ai RTX 4090 Deployment Guide

## 🚀 Quick Start

The GameForge AI platform is **already fully configured** for vast.ai RTX 4090 deployment! All AI services are pre-built and integrated into the production-hardened Docker Compose file.

### 📋 Pre-Configured AI Services

| Service | Purpose | Port | Status |
|---------|---------|------|--------|
| `torchserve-rtx4090` | Model serving (24GB VRAM optimized) | 8080-8082 | ✅ Ready |
| `ray-head-rtx4090` | Distributed computing head | 8265 | ✅ Ready |
| `kubeflow-pipelines-rtx4090` | ML pipeline orchestration | 8080 | ✅ Ready |
| `dcgm-exporter-rtx4090` | GPU health monitoring | 9400 | ✅ Ready |
| `mlflow-model-registry-rtx4090` | Model registry & tracking | 5000 | ✅ Ready |

## 🎯 Vast.ai Instance Requirements

### Recommended Configuration:
- **GPU**: RTX 4090 (24GB VRAM)
- **RAM**: 32GB+ system memory
- **Storage**: 200GB+ SSD
- **CUDA**: 12.1+ with nvidia-container-toolkit

### Instance Selection on Vast.ai:
```bash
# Search for RTX 4090 instances
vastai search offers 'gpu_name=RTX_4090 ram>=32 disk_space>=200'

# Rent instance
vastai create instance <instance_id> --image ubuntu:22.04 --disk 200
```

## 🔧 Deployment Steps

### 1. Upload GameForge Platform
```bash
# Upload the entire GameForge repository to your vast.ai instance
rsync -avz --progress GameForge/ root@<instance_ip>:/opt/gameforge/
```

### 2. Run Deployment Script
```bash
cd /opt/gameforge
chmod +x deploy-ai-platform-vast-rtx4090.sh
./deploy-ai-platform-vast-rtx4090.sh
```

### 3. Verify Deployment
```bash
chmod +x verify-ai-platform-rtx4090.sh
./verify-ai-platform-rtx4090.sh
```

## 🐳 Manual Deployment (Alternative)

If you prefer manual control:

```bash
# Navigate to GameForge directory
cd /opt/gameforge

# Deploy AI services in stages
docker-compose -f docker/compose/docker-compose.production-hardened.yml up -d torchserve-rtx4090
docker-compose -f docker/compose/docker-compose.production-hardened.yml up -d ray-head-rtx4090
docker-compose -f docker/compose/docker-compose.production-hardened.yml up -d kubeflow-pipelines-rtx4090
docker-compose -f docker/compose/docker-compose.production-hardened.yml up -d dcgm-exporter-rtx4090
docker-compose -f docker/compose/docker-compose.production-hardened.yml up -d mlflow-model-registry-rtx4090
```

## 🌐 Service Access URLs

Once deployed, access services via:

### TorchServe Model Serving
- **Inference API**: `http://<instance_ip>:8080`
- **Management API**: `http://<instance_ip>:8081`
- **Metrics**: `http://<instance_ip>:8082/metrics`
- **Web UI**: `https://torchserve.gameforge.local` (via Traefik)

### Ray Distributed Computing
- **Dashboard**: `http://<instance_ip>:8265`
- **Client Connection**: `ray://<instance_ip>:10001`

### MLflow Model Registry
- **Web UI**: `http://<instance_ip>:5000`
- **Tracking API**: `http://<instance_ip>:5000/api/2.0/mlflow`

### GPU Monitoring
- **DCGM Metrics**: `http://<instance_ip>:9400/metrics`
- **Command Line**: `nvidia-smi` (available in all containers)

## 📊 Performance Optimization

### RTX 4090 Specific Settings

The platform is pre-optimized for RTX 4090:

```yaml
# TorchServe RTX 4090 Configuration
environment:
  - CUDA_VISIBLE_DEVICES=0
  - TORCH_CUDA_ARCH_LIST=8.9  # RTX 4090 architecture
  - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048,expandable_segments:True
  - JAVA_OPTS=-Xms2g -Xmx8g   # JVM tuned for 24GB VRAM
```

### Memory Management
- **TorchServe**: Configured for 24GB VRAM with batch size 16
- **Ray**: Optimized worker configuration for GPU memory
- **KubeFlow**: Resource-aware pipeline scheduling

## 🔒 Security Features

### Production Hardening
- ✅ Non-root containers with dedicated users
- ✅ Read-only filesystems where possible
- ✅ Security contexts with capability dropping
- ✅ Network isolation with dedicated AI networks
- ✅ Resource limits and reservations
- ✅ Health checks and monitoring

### Network Security
- Isolated networks: `ai-network`, `gpu-network`, `ml-network`
- Traefik reverse proxy with TLS termination
- Internal service communication only

## 🐛 Troubleshooting

### Common Issues

1. **GPU Not Detected**
   ```bash
   # Install NVIDIA container toolkit
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
       sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
       sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

2. **Out of Memory**
   ```bash
   # Check GPU memory usage
   nvidia-smi
   
   # Reduce batch sizes in configs/torchserve/config.properties
   batch_size=8  # Reduce from 16 if needed
   max_workers=8 # Reduce from 16 if needed
   ```

3. **Service Won't Start**
   ```bash
   # Check logs
   docker-compose -f docker/compose/docker-compose.production-hardened.yml logs torchserve-rtx4090
   
   # Check system resources
   free -h
   df -h
   ```

### Log Locations
- **Application Logs**: `/var/lib/gameforge/*/logs/`
- **Docker Logs**: `docker-compose logs <service_name>`
- **System Logs**: `/var/log/syslog`

## 📈 Monitoring & Metrics

### Prometheus Metrics
- **TorchServe**: `http://<instance_ip>:8082/metrics`
- **DCGM GPU**: `http://<instance_ip>:9400/metrics`
- **Ray**: `http://<instance_ip>:8265/api/v0/metrics`

### Grafana Dashboards
Pre-configured dashboards for:
- GPU utilization and memory
- TorchServe inference performance
- Ray cluster resource usage
- MLflow experiment tracking

## 🔄 Scaling & High Availability

### Horizontal Scaling
```bash
# Scale Ray workers
docker-compose -f docker/compose/docker-compose.production-hardened.yml up -d --scale ray-worker-rtx4090=3

# Scale TorchServe workers (via config)
# Edit configs/torchserve/config.properties:
# default_workers_per_model=8
```

### Load Balancing
- Traefik handles load balancing between service instances
- Ray automatically distributes workloads across workers
- TorchServe supports multiple model instances

## 📚 Additional Resources

### Configuration Files
- **Docker Services**: `docker/services/`
- **TorchServe Config**: `configs/torchserve/`
- **Kubernetes Manifests**: `k8s/ai-platform/`
- **Monitoring**: `configs/grafana/`, `configs/prometheus/`

### Documentation
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **AI Implementation**: `docs/AI_IMPLEMENTATION_COMPLETE.md`
- **GPU Workloads**: `docs/GPU_WORKLOAD_INTEGRATION_COMPLETE.md`

## 🎉 Success Criteria

Your deployment is successful when:
- ✅ All 5 AI services show "Up" status
- ✅ TorchServe responds to ping at port 8080
- ✅ Ray dashboard accessible at port 8265
- ✅ MLflow UI accessible at port 5000
- ✅ GPU utilization visible in DCGM metrics
- ✅ No errors in service logs

**Platform Status**: Ready for production AI/ML workloads on RTX 4090! 🚀
