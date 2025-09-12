# GameForge GPU Workload Scheduling Integration
# ========================================================================
# Complete implementation guide for GPU workload scheduling with Docker Compose
# and Kubernetes integration
# ========================================================================

## Overview

This implementation provides comprehensive GPU workload scheduling for the GameForge AI game production platform, integrating both Docker Compose and Kubernetes deployment options with proper resource management, security, and monitoring.

## Architecture

### Docker Compose GPU Integration

1. **GPU-Optimized Services**:
   - `gameforge-gpu-inference`: High-performance inference workloads
   - `gameforge-gpu-training`: Model training and fine-tuning workloads
   - `gameforge-app`: Main application with GPU coordination
   - `gameforge-worker`: Background AI processing tasks

2. **Resource Management**:
   - Dynamic GPU allocation based on workload type
   - Memory and CPU limits scaled by GPU count
   - Shared memory volumes for high-performance IPC
   - Dedicated networks for GPU workload isolation

3. **Security Integration**:
   - Hardened container security contexts
   - GPU runtime isolation with nvidia-docker
   - Resource limits and monitoring
   - Vault integration for model security

### Kubernetes GPU Integration

1. **NVIDIA Device Plugin**: Automatic GPU discovery and allocation
2. **Resource Policies**: Priority-based scheduling and resource limits
3. **Storage Classes**: Optimized storage for model data and checkpoints
4. **Workload Templates**: Pre-configured deployments for different AI tasks

## Files Created/Modified

### Docker Compose Integration

1. **docker-compose.production-hardened.yml**:
   - Added GPU inference and training services
   - Enhanced resource templates for GPU workloads
   - Added GPU-specific networks and volumes
   - Integrated with existing security pipeline

2. **Dockerfile.gpu-workload**:
   - Multi-stage build optimized for NVIDIA GPUs
   - CUDA 12.1 with PyTorch and GPU-accelerated libraries
   - Security hardening with non-root user
   - GPU health checks and monitoring

3. **requirements-gpu.txt**:
   - GPU-optimized Python dependencies
   - PyTorch with CUDA support
   - Transformers, diffusers, and ML libraries
   - GPU memory optimization tools

### Kubernetes Integration

4. **k8s/gpu-device-plugin.yaml**:
   - NVIDIA Kubernetes device plugin deployment
   - Automatic GPU discovery and scheduling
   - Resource allocation and monitoring

5. **k8s/gpu-resource-policies.yaml**:
   - Priority classes for GPU workloads
   - Resource quotas and limits
   - Network policies for isolation

6. **k8s/gpu-storage.yaml**:
   - Storage classes for GPU workloads
   - Persistent volumes for model data
   - Volume claims for training checkpoints

7. **k8s/gpu-workloads.yaml**:
   - Inference deployment template
   - Training job template
   - Service definitions and ingress

### Deployment and Management

8. **deploy-gpu-workloads.ps1**:
   - Unified deployment script for both platforms
   - Environment configuration and validation
   - Service health checking and monitoring
   - Resource cleanup and management

### Documentation

9. **GPU_WORKLOAD_INTEGRATION_COMPLETE.md**:
   - Complete implementation guide
   - Usage examples and best practices
   - Troubleshooting and monitoring

## Usage Examples

### Docker Compose Deployment

```powershell
# Deploy with GPU support
.\deploy-gpu-workloads.ps1 -Action deploy -Platform docker -Mode gpu -GpuCount 2

# Check status
.\deploy-gpu-workloads.ps1 -Action status -Platform docker

# View logs
.\deploy-gpu-workloads.ps1 -Action logs -Platform docker

# Stop services
.\deploy-gpu-workloads.ps1 -Action stop -Platform docker
```

### Kubernetes Deployment

```powershell
# Deploy to Kubernetes
.\deploy-gpu-workloads.ps1 -Action k8s-deploy -Platform kubernetes -Namespace gameforge

# Hybrid deployment (both platforms)
.\deploy-gpu-workloads.ps1 -Action deploy -Platform hybrid -Mode gpu -GpuCount 4
```

### Manual Service Access

```bash
# Docker Compose services
docker compose -f docker-compose.production-hardened.yml exec gameforge-gpu-inference python -c "import torch; print(torch.cuda.device_count())"

# Kubernetes services
kubectl exec -n gameforge deployment/gameforge-gpu-inference -- python -c "import torch; print(torch.cuda.device_count())"
```

## Resource Configuration

### GPU Resource Templates

```yaml
# Inference workload
resources:
  limits:
    memory: 16Gi
    cpu: "8"
    nvidia.com/gpu: 1
  requests:
    memory: 8Gi
    cpu: "4"
    nvidia.com/gpu: 1

# Training workload
resources:
  limits:
    memory: 32Gi
    cpu: "16"
    nvidia.com/gpu: 2
  requests:
    memory: 16Gi
    cpu: "8"
    nvidia.com/gpu: 2
```

### Environment Variables

```bash
# GPU Configuration
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048,garbage_collection_threshold:0.8

# Resource Scaling
GPU_COUNT=2
MEMORY_LIMIT=32G
CPU_LIMIT=16.0
```

## Monitoring and Health Checks

### GPU Health Monitoring

1. **Container Health Checks**:
   - PyTorch CUDA availability
   - GPU device count verification
   - Memory usage monitoring

2. **Service Monitoring**:
   - Prometheus GPU metrics
   - Grafana dashboards
   - Alert manager integration

3. **Kubernetes Monitoring**:
   - Device plugin status
   - Node GPU allocation
   - Pod resource usage

### Key Metrics

- GPU utilization percentage
- GPU memory usage
- Model inference latency
- Training throughput
- Queue depth and processing times

## Security Considerations

### Container Security

1. **Non-root Execution**: All GPU containers run as user `gameforge:1001`
2. **Resource Limits**: CPU, memory, and PID limits for all services
3. **Network Isolation**: Dedicated GPU network with restricted access
4. **Volume Security**: Read-only mounts where possible, secure tmpfs

### GPU Runtime Security

1. **NVIDIA Runtime**: Isolated GPU access via nvidia-docker
2. **Device Permissions**: Minimal required GPU capabilities
3. **Memory Protection**: CUDA memory allocation limits
4. **Process Isolation**: Separate containers for different workload types

## Troubleshooting

### Common Issues

1. **GPU Not Detected**:
   ```bash
   # Check NVIDIA drivers
   nvidia-smi
   
   # Verify Docker runtime
   docker info | grep nvidia
   ```

2. **Memory Issues**:
   ```bash
   # Check GPU memory
   nvidia-smi --query-gpu=memory.used,memory.total --format=csv
   
   # Adjust PYTORCH_CUDA_ALLOC_CONF
   export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024
   ```

3. **Service Health Issues**:
   ```powershell
   # Check service status
   .\deploy-gpu-workloads.ps1 -Action status
   
   # View detailed logs
   docker compose logs gameforge-gpu-inference
   ```

### Performance Optimization

1. **Memory Management**:
   - Tune CUDA memory allocation
   - Use gradient checkpointing for training
   - Optimize batch sizes for available memory

2. **Compute Optimization**:
   - Enable mixed precision training
   - Use compiled models with TorchScript
   - Optimize data loading pipelines

3. **Scaling Strategies**:
   - Scale inference services horizontally
   - Use multi-GPU training for large models
   - Implement model sharding for memory efficiency

## Integration Points

### Main Application Integration

The main `gameforge-app` service coordinates with GPU services through:

1. **Service Discovery**: Environment variables for GPU service endpoints
2. **Load Balancing**: Round-robin distribution of GPU workloads
3. **Resource Monitoring**: Real-time GPU utilization tracking
4. **Failover**: Automatic fallback to CPU processing if needed

### Model Management

1. **Model Storage**: Shared volumes for model artifacts
2. **Model Loading**: Optimized loading from cache or remote storage
3. **Model Versioning**: Integration with MLflow for model lifecycle
4. **Model Security**: Vault integration for model encryption and access control

## Next Steps

1. **Production Deployment**:
   - Run with actual GPU hardware
   - Performance testing and optimization
   - Security audit and compliance

2. **Monitoring Enhancement**:
   - Custom GPU metrics collection
   - Advanced alerting rules
   - Capacity planning dashboards

3. **Scaling Optimization**:
   - Auto-scaling based on queue depth
   - Multi-node GPU cluster support
   - Cross-platform workload migration

4. **Feature Enhancement**:
   - A/B testing for model deployments
   - Real-time model updates
   - Advanced scheduling algorithms

## Conclusion

This implementation provides a complete, production-ready GPU workload scheduling solution that integrates seamlessly with the existing GameForge infrastructure while maintaining security, performance, and monitoring requirements. The hybrid Docker Compose and Kubernetes approach ensures flexibility for different deployment scenarios and future scaling needs.
