# GPU Workload Scheduling Implementation Guide

This document provides a comprehensive guide for implementing GPU workload scheduling in GameForge, ensuring that AI workloads are properly distributed across GPU nodes with appropriate resource management and scheduling policies.

## 🎯 Overview

The GPU workload scheduling solution includes:

1. **NVIDIA Device Plugin** - Exposes GPU resources to Kubernetes
2. **Resource Policies** - Manages GPU resource allocation and limits
3. **Workload Templates** - Optimized deployments for different AI tasks
4. **Node Management** - Automated GPU node labeling and configuration
5. **Storage Solutions** - Persistent storage for models, datasets, and outputs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GPU Workload Scheduling                     │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│ │   Training      │ │   Inference     │ │ Asset Generation │  │
│ │   Workloads     │ │   Workloads     │ │   Workloads      │  │
│ │                 │ │                 │ │                  │  │
│ │ • High Priority │ │ • Med Priority  │ │ • Med Priority   │  │
│ │ • 1-4 GPUs      │ │ • 1 GPU         │ │ • 1 GPU          │  │
│ │ • High Memory   │ │ • Med Memory    │ │ • Med Memory     │  │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Resource Management                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│ │ Resource Quotas │ │ Priority Classes│ │ Pod Disruption  │  │
│ │ • GPU Limits    │ │ • High Training │ │ • Budget Policy │  │
│ │ • CPU/Memory    │ │ • Med Inference │ │ • Availability  │  │
│ │ • Storage       │ │ • Low Batch     │ │ • Constraints   │  │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Node Scheduling                             │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│ │ Node Affinity   │ │ GPU Taints      │ │ Node Labels     │  │
│ │ • GPU Required  │ │ • GPU-Only      │ │ • accelerator   │  │
│ │ • Memory Tiers  │ │ • NoSchedule    │ │ • gpu-type      │  │
│ │ • Workload Type │ │ • Tolerations   │ │ • workload-type │  │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    GPU Device Plugin                           │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│ │ NVIDIA Plugin   │ │ Node Discovery  │ │ Resource Export │  │
│ │ • DaemonSet     │ │ • Auto-labeling │ │ • nvidia.com/gpu│  │
│ │ • GPU Detection │ │ • Feature Detect│ │ • Allocatable   │  │
│ │ • Health Check  │ │ • Node Metadata │ │ • Capacity      │  │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

Ensure your cluster meets these requirements:

```powershell
# Check kubectl connectivity
kubectl cluster-info

# Verify GPU nodes are available
kubectl get nodes

# Check NVIDIA drivers on GPU nodes
# (Run on each GPU node)
nvidia-smi
```

### 2. Setup GPU Nodes

Label and configure your GPU nodes:

```powershell
# Auto-detect and setup all GPU nodes
.\setup-gpu-nodes.ps1 -AutoDetect

# Or setup specific nodes
.\setup-gpu-nodes.ps1 -NodeNames "gpu-node-1,gpu-node-2" -GPUType "nvidia-rtx"

# Verify node configuration
.\setup-gpu-nodes.ps1 -Action verify
```

### 3. Deploy GPU Workload Scheduling

Deploy the complete GPU scheduling infrastructure:

```powershell
# Deploy all components
.\deploy-gpu-workloads.ps1

# Verify deployment
.\deploy-gpu-workloads.ps1 -Action verify

# Check device plugin status
kubectl get daemonset nvidia-device-plugin-daemonset -n kube-system
```

### 4. Test GPU Workloads

Verify that workloads can request and use GPUs:

```powershell
# Check GPU resource availability
kubectl describe nodes | findstr -A 5 "Allocatable:"

# Monitor GPU workload pods
kubectl get pods -n gameforge -l gpu-enabled=true

# View resource usage
kubectl top nodes
kubectl top pods -n gameforge
```

## 📁 File Structure

```
k8s/
├── gpu-device-plugin.yaml      # NVIDIA device plugin DaemonSet
├── gpu-workload-policies.yaml  # Resource quotas and policies
├── gpu-ai-workloads.yaml      # AI workload deployments
└── gpu-storage.yaml           # Persistent storage for AI workloads

scripts/
├── deploy-gpu-workloads.ps1   # Main deployment script
├── setup-gpu-nodes.ps1        # Node preparation script
└── GPU_WORKLOAD_SCHEDULING.md # This documentation
```

## 🎛️ Configuration Details

### GPU Node Labels

Each GPU node receives these labels for scheduling:

| Label | Purpose | Values |
|-------|---------|---------|
| `accelerator` | GPU vendor | `nvidia` |
| `gpu-type` | Hardware type | `nvidia-tesla`, `nvidia-rtx`, `nvidia-geforce` |
| `gpu-memory` | Memory tier | `low`, `medium`, `high`, `ultra` |
| `workload-type` | Intended use | `training`, `inference`, `mixed` |
| `node-type` | Node role | `gpu-worker` |
| `gameforge.ai/gpu-enabled` | GameForge flag | `true` |

### Resource Requests and Limits

#### Training Workloads
```yaml
resources:
  requests:
    cpu: 4
    memory: 16Gi
    nvidia.com/gpu: 1
  limits:
    cpu: 8
    memory: 32Gi
    nvidia.com/gpu: 1
```

#### Inference Workloads
```yaml
resources:
  requests:
    cpu: 2
    memory: 8Gi
    nvidia.com/gpu: 1
  limits:
    cpu: 4
    memory: 16Gi
    nvidia.com/gpu: 1
```

#### Asset Generation
```yaml
resources:
  requests:
    cpu: 3
    memory: 12Gi
    nvidia.com/gpu: 1
  limits:
    cpu: 6
    memory: 24Gi
    nvidia.com/gpu: 1
```

### Priority Classes

Workloads are assigned priority classes for scheduling:

| Priority Class | Value | Use Case |
|----------------|-------|----------|
| `high-priority-training` | 1000 | Critical model training |
| `medium-priority-inference` | 500 | Production inference |
| `low-priority-batch` | 100 | Batch processing |

### GPU Tolerations

All GPU workloads include these tolerations:

```yaml
tolerations:
- key: nvidia.com/gpu
  operator: Exists
  effect: NoSchedule
- key: accelerator
  operator: Equal
  value: nvidia
  effect: NoSchedule
```

## 🗄️ Storage Configuration

### Persistent Volume Claims

| PVC | Size | Access Mode | Purpose |
|-----|------|-------------|---------|
| `gameforge-model-storage` | 500Gi | ReadWriteMany | Shared model files |
| `gameforge-dataset-storage` | 1Ti | ReadOnlyMany | Training datasets |
| `gameforge-checkpoint-storage` | 200Gi | ReadWriteMany | Training checkpoints |
| `gameforge-asset-storage` | 300Gi | ReadWriteMany | Generated assets |
| `gameforge-logs-storage` | 100Gi | ReadWriteMany | Application logs |

### Storage Classes

| Class | Performance | Use Case |
|-------|-------------|----------|
| `fast-ssd` | Premium | Models, checkpoints |
| `standard-ssd` | Standard | Datasets, assets |
| `standard-hdd` | Economy | Logs, archives |

## 🔍 Monitoring and Troubleshooting

### Checking GPU Availability

```powershell
# Check cluster GPU resources
kubectl describe nodes | findstr -A 10 "Allocatable:"

# View GPU resource quotas
kubectl describe resourcequota gpu-resource-quota -n gameforge

# Check device plugin logs
kubectl logs -n kube-system -l name=nvidia-device-plugin-ds
```

### Debugging Workload Scheduling

```powershell
# Check pod scheduling status
kubectl describe pod <pod-name> -n gameforge

# View node affinity constraints
kubectl get pods -n gameforge -o wide

# Check resource conflicts
kubectl get events -n gameforge --sort-by='.lastTimestamp'
```

### Common Issues and Solutions

#### 1. Device Plugin Not Starting

**Problem**: Device plugin pods are not running
```
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
```

**Solution**: Check node labels and NVIDIA drivers
```powershell
# Verify node labels
kubectl get nodes -l accelerator=nvidia

# Check NVIDIA drivers on nodes
ssh <node> "nvidia-smi"

# Restart device plugin
kubectl delete pods -n kube-system -l name=nvidia-device-plugin-ds
```

#### 2. Pods Stuck in Pending State

**Problem**: GPU workload pods remain in Pending status

**Solution**: Check scheduling constraints
```powershell
# Check pod events
kubectl describe pod <pod-name> -n gameforge

# Verify node resources
kubectl describe nodes | findstr -A 5 "nvidia.com/gpu"

# Check resource quotas
kubectl describe resourcequota gpu-resource-quota -n gameforge
```

#### 3. GPU Not Available in Container

**Problem**: Containers can't access GPU hardware

**Solution**: Verify runtime and drivers
```powershell
# Check container runtime
kubectl describe node <gpu-node> | findstr -A 5 "Container Runtime"

# Verify NVIDIA container runtime
docker info | findstr -i nvidia

# Test GPU access in pod
kubectl exec -it <pod-name> -n gameforge -- nvidia-smi
```

## 🔧 Customization

### Adding New GPU Types

To support additional GPU types:

1. **Update node labeling script**:
```powershell
# Edit setup-gpu-nodes.ps1
# Add new GPU detection logic
elseif ($nodeInfo -match "A100") {
    $gpuInfo.GPUType = "nvidia-a100"
    $gpuInfo.MemoryGB = 40
}
```

2. **Update workload affinity**:
```yaml
# Add to gpu-ai-workloads.yaml
nodeAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
    nodeSelectorTerms:
    - matchExpressions:
      - key: gpu-type
        operator: In
        values: ["nvidia-tesla", "nvidia-rtx", "nvidia-a100"]
```

### Adjusting Resource Limits

Modify resource requests/limits based on your requirements:

```yaml
# For memory-intensive workloads
resources:
  requests:
    memory: 32Gi
    nvidia.com/gpu: 2
  limits:
    memory: 64Gi
    nvidia.com/gpu: 2
```

### Custom Priority Classes

Create additional priority classes for specific workloads:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-realtime-inference
value: 1500
globalDefault: false
description: "Critical priority for real-time inference workloads"
```

## 📊 Scaling Considerations

### Horizontal Scaling

GPU workloads can be scaled using:

1. **Horizontal Pod Autoscaler (HPA)**:
   - Scales based on CPU/memory metrics
   - Custom GPU utilization metrics
   - Queue depth metrics

2. **Manual scaling**:
```powershell
kubectl scale deployment gameforge-inference --replicas=5 -n gameforge
```

### Vertical Scaling

Use Vertical Pod Autoscaler (VPA) for resource optimization:

1. **Automatic resource adjustment**
2. **Memory and CPU optimization**
3. **GPU resource recommendations**

### Multi-GPU Support

For workloads requiring multiple GPUs:

```yaml
resources:
  requests:
    nvidia.com/gpu: 4
  limits:
    nvidia.com/gpu: 4
```

## 🔐 Security Considerations

### Pod Security Standards

GPU workloads follow security best practices:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
```

### Network Policies

GPU workloads are isolated using network policies:

```yaml
# Only allow communication within gameforge namespace
# Block unnecessary external access
# Allow specific service communications
```

### Resource Isolation

GPU nodes are tainted to prevent non-GPU workloads:

```yaml
tolerations:
- key: nvidia.com/gpu
  operator: Exists
  effect: NoSchedule
```

## 🎯 Best Practices

### 1. Resource Planning
- **GPU Memory**: Plan for model size + batch size + overhead
- **CPU Cores**: 2-4 cores per GPU for data preprocessing
- **Memory**: 4-8GB RAM per GPU for optimal performance

### 2. Workload Optimization
- **Training**: Use high-priority scheduling and dedicated nodes
- **Inference**: Optimize for throughput with multiple replicas
- **Development**: Use low-priority scheduling with shared resources

### 3. Monitoring
- **GPU Utilization**: Monitor with Prometheus/Grafana
- **Resource Usage**: Track memory and compute utilization
- **Queue Metrics**: Monitor workload queue depths

### 4. Cost Optimization
- **Spot Instances**: Use for non-critical workloads
- **Mixed Instance Types**: Combine different GPU types
- **Workload Scheduling**: Schedule heavy workloads during off-peak hours

## 📈 Performance Tuning

### GPU Memory Optimization

```yaml
env:
- name: GPU_MEMORY_FRACTION
  value: "0.9"  # Use 90% of GPU memory
- name: NVIDIA_MPS_PIPE_DIRECTORY
  value: "/tmp/nvidia-mps"  # Enable MPS for sharing
```

### Batch Size Optimization

```yaml
env:
- name: BATCH_SIZE
  value: "32"  # Optimize based on GPU memory
- name: GRADIENT_ACCUMULATION_STEPS
  value: "4"   # For larger effective batch sizes
```

### Data Loading Optimization

```yaml
env:
- name: NUM_WORKERS
  value: "8"   # Parallel data loading
- name: PIN_MEMORY
  value: "true"  # Faster GPU transfers
```

## 🎉 Conclusion

This GPU workload scheduling implementation provides:

✅ **Automated GPU Resource Management**
✅ **Optimized Workload Scheduling**
✅ **Scalable AI Infrastructure**
✅ **Resource Isolation and Security**
✅ **Performance Monitoring**
✅ **Cost Optimization**

The solution ensures that GameForge's AI workloads efficiently utilize GPU resources while maintaining high availability and performance standards.

## 🆘 Support

For issues or questions:

1. **Check logs**: `kubectl logs -n kube-system -l name=nvidia-device-plugin-ds`
2. **Verify setup**: `.\deploy-gpu-workloads.ps1 -Action verify`
3. **Review events**: `kubectl get events -n gameforge --sort-by='.lastTimestamp'`
4. **Test GPU access**: `kubectl exec -it <pod> -- nvidia-smi`

## 🔄 Updates

To update the GPU scheduling infrastructure:

```powershell
# Update device plugin
kubectl set image daemonset/nvidia-device-plugin-daemonset nvidia-device-plugin-ctr=nvcr.io/nvidia/k8s-device-plugin:v0.14.2 -n kube-system

# Update workload deployments
kubectl apply -f k8s/gpu-ai-workloads.yaml

# Verify updates
.\deploy-gpu-workloads.ps1 -Action verify
```
