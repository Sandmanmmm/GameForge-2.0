# GameForge Kubernetes Deployment Guide

## 🚀 **Kubernetes Production Scaling**

This guide covers the transition from Windows scheduled tasks to a full Kubernetes production deployment with CronJobs and DaemonSets for enterprise-scale secret rotation.

## 📋 **Architecture Overview**

### **Components Deployed**

1. **CronJobs** - Replace Windows scheduled tasks for automated secret rotation
2. **DaemonSets** - Distributed monitoring across all cluster nodes  
3. **Monitoring Stack** - Prometheus + Grafana + AlertManager
4. **RBAC** - Service accounts and role-based access control
5. **Persistent Storage** - For metrics retention and configuration

### **Namespaces**

- `gameforge-security` - Secret rotation CronJobs and core security components
- `gameforge-monitoring` - Monitoring stack (Prometheus, Grafana, DaemonSets)

## 🛠️ **Prerequisites**

### **Required Tools**
```powershell
# Kubernetes CLI
kubectl version --client

# Docker for building images
docker --version

# Kustomize for configuration management
kustomize version
```

### **Cluster Requirements**
- Kubernetes 1.20+
- RBAC enabled
- Persistent volume support
- LoadBalancer or NodePort access (for Grafana)
- Minimum 4 CPU cores and 8GB RAM across cluster

## 🎯 **Quick Deployment**

### **1. One-Command Deployment**
```powershell
# Deploy everything to Kubernetes
.\deploy-k8s.ps1 -Environment production -BuildImages

# Or dry run to see what will be deployed
.\deploy-k8s.ps1 -Environment production -DryRun
```

### **2. Management Operations**
```powershell
# Check deployment status
.\k8s-manage.ps1 -Action status

# View logs
.\k8s-manage.ps1 -Action logs

# Manual secret rotation
.\k8s-manage.ps1 -Action rotate -SecretType application

# Setup port forwarding
.\k8s-manage.ps1 -Action port-forward
```

## 📦 **Detailed Deployment Steps**

### **Step 1: Prepare Environment**
```powershell
# Set required environment variables
$env:VAULT_ADDR = "https://vault.gameforge.com:8200"
$env:VAULT_TOKEN = "your-vault-token"
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/..."

# Verify Kubernetes access
kubectl cluster-info
```

### **Step 2: Build Container Images**
```powershell
# Build the secret rotation container
docker build -f Dockerfile.k8s -t gameforge/secret-rotation:latest .
docker tag gameforge/secret-rotation:latest gameforge/secret-rotation:v1.0.0-production
```

### **Step 3: Deploy to Kubernetes**
```powershell
# Deploy using Kustomize
cd k8s/overlays/production
kustomize build . | kubectl apply -f -

# Or use the deployment script
.\deploy-k8s.ps1 -Environment production
```

### **Step 4: Verify Deployment**
```powershell
# Check all components
kubectl get all -n gameforge-security
kubectl get all -n gameforge-monitoring

# Check CronJobs
kubectl get cronjobs -n gameforge-security

# Check DaemonSet
kubectl get daemonset -n gameforge-monitoring
```

## ⏰ **CronJob Schedules**

Replacing Windows scheduled tasks with Kubernetes CronJobs:

| Secret Type | Windows Schedule | Kubernetes CronJob | Frequency |
|-------------|------------------|-------------------|-----------|
| Internal | Daily 1:00 AM | `0 1 * * *` | Daily |
| Application | Every 45 days 3:00 AM | `0 3 1,15 * *` | Bi-monthly |
| TLS | Every 60 days 4:00 AM | `0 4 1,30 * *` | Monthly |
| Database | Every 90 days 5:00 AM | `0 5 1 1,4,7,10 *` | Quarterly |

### **CronJob Features**
- **Concurrency Control**: `concurrencyPolicy: Forbid`
- **History Retention**: Success/failure job history preserved
- **Timeout Protection**: `activeDeadlineSeconds` prevents hanging jobs
- **Retry Logic**: `backoffLimit` for automatic retries
- **Resource Limits**: CPU/memory constraints per job

## 🔍 **DaemonSet Monitoring**

The security monitor DaemonSet runs on every cluster node:

### **Components per Node**
1. **Node Exporter** (Port 9100)
   - System metrics (CPU, memory, disk, network)
   - File system monitoring
   - Process monitoring

2. **Security Monitor** (Port 9101)
   - Vault connectivity checks
   - Secret rotation status
   - Certificate expiry monitoring
   - Failed authentication detection
   - Privileged operation monitoring

### **Node Security Checks**
```yaml
node_security:
  file_integrity:
    paths:
      - "/etc/passwd"
      - "/etc/shadow" 
      - "/etc/sudoers"
      - "/etc/hosts"
  
  process_monitoring:
    suspicious_processes:
      - "nc", "ncat", "netcat"
      - "socat", "telnet"
  
  network_monitoring:
    suspicious_ports:
      - 1337, 31337, 4444, 5555
```

## 📊 **Monitoring Stack**

### **Prometheus Configuration**
- **Retention**: 30 days (production: 90 days)
- **Storage**: 20GB persistent volume
- **Scrape Targets**: 
  - Kubernetes API server
  - Node exporters (all nodes)
  - Security monitors (all nodes)
  - Vault metrics (if accessible)

### **Grafana Dashboards**
- **Access**: Port-forward or LoadBalancer
- **Credentials**: admin/gameforge123 (change in production)
- **Datasource**: Prometheus (auto-provisioned)
- **Dashboards**: Node metrics, security alerts, rotation status

### **AlertManager Rules**
```yaml
# Example alerts
- alert: SecretRotationFailed
  expr: increase(secret_rotation_failures_total[5m]) > 0
  labels:
    severity: critical
  annotations:
    summary: "Secret rotation failed"

- alert: VaultConnectivityLost  
  expr: up{job="vault"} == 0
  for: 5m
  labels:
    severity: critical
```

## 🛡️ **Security Features**

### **RBAC Configuration**
```yaml
# Service accounts with minimal permissions
- secret-rotation-sa: Secrets, ConfigMaps, Events, Jobs
- monitoring-sa: Nodes, Pods, Services, Metrics
```

### **Pod Security**
- **Non-root containers**: `runAsUser: 1001`
- **Read-only root filesystem**: Where possible
- **No privilege escalation**: `allowPrivilegeEscalation: false`
- **Dropped capabilities**: `drop: ALL`

### **Network Policies** (Optional)
```yaml
# Restrict traffic between namespaces
# Allow only necessary communication
```

## 🔧 **Management Commands**

### **Daily Operations**
```powershell
# Check overall health
.\k8s-manage.ps1 -Action status

# View recent rotation logs
.\k8s-manage.ps1 -Action logs

# Manual rotation when needed
.\k8s-manage.ps1 -Action rotate -SecretType application

# Access monitoring dashboards
.\k8s-manage.ps1 -Action port-forward
# Then browse to http://localhost:3000
```

### **Maintenance Tasks**
```powershell
# Clean up old jobs
.\k8s-manage.ps1 -Action cleanup

# Scale components
.\k8s-manage.ps1 -Action scale -Replicas 2

# Update configuration
kubectl apply -k k8s/overlays/production

# Restart DaemonSet
kubectl rollout restart daemonset/security-monitor -n gameforge-monitoring
```

### **Troubleshooting**
```powershell
# Check failed pods
kubectl get pods --field-selector=status.phase=Failed -A

# Describe problematic resources
kubectl describe cronjob secret-rotation-application -n gameforge-security

# Check events
kubectl get events -n gameforge-security --sort-by='.lastTimestamp'

# Pod logs
kubectl logs -l app.kubernetes.io/component=job -n gameforge-security --tail=100
```

## 📈 **Scaling Considerations**

### **Horizontal Scaling**
- **Prometheus**: Can run multiple replicas with shared storage
- **Grafana**: Single replica recommended (or use external database)
- **DaemonSet**: Automatically scales with cluster nodes

### **Vertical Scaling**
```yaml
# Production resource requirements
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m" 
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### **Storage Scaling**
```yaml
# Increase PVC size
spec:
  resources:
    requests:
      storage: 50Gi  # Increased from 20Gi
```

## 🚨 **Production Checklist**

### **Before Deployment**
- [ ] Kubernetes cluster ready and accessible
- [ ] RBAC enabled
- [ ] Persistent volume storage available
- [ ] Docker images built and tagged
- [ ] Environment variables set (VAULT_ADDR, VAULT_TOKEN)
- [ ] Network policies configured (if required)
- [ ] Monitoring endpoints accessible

### **After Deployment**
- [ ] All CronJobs created and scheduled
- [ ] DaemonSet pods running on all nodes
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards accessible
- [ ] Manual rotation test successful
- [ ] Alerts configured and tested
- [ ] Backup procedures validated
- [ ] Documentation updated

### **Ongoing Monitoring**
- [ ] Monitor CronJob execution success/failure
- [ ] Check DaemonSet pod health across nodes
- [ ] Review Grafana dashboards regularly
- [ ] Validate secret rotation completion
- [ ] Monitor storage usage growth
- [ ] Check for security alerts

## 🔄 **Migration from Windows Tasks**

### **Transition Plan**
1. **Deploy Kubernetes stack** alongside Windows tasks
2. **Validate CronJob execution** for 1 week
3. **Compare rotation success rates** between systems
4. **Disable Windows scheduled tasks** one at a time
5. **Monitor for 48 hours** after each migration
6. **Complete cutover** when all validations pass

### **Rollback Plan**
- Keep Windows scheduled tasks disabled but configured
- Re-enable Windows tasks if Kubernetes issues occur
- Use manual rotations as backup during transition

## 📚 **Additional Resources**

### **Configuration Files**
- `k8s/base/` - Base Kubernetes manifests
- `k8s/overlays/production/` - Production-specific configurations
- `Dockerfile.k8s` - Container image definition
- `deploy-k8s.ps1` - Automated deployment script
- `k8s-manage.ps1` - Management operations script

### **Monitoring URLs** (with port-forward)
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090  
- AlertManager: http://localhost:9093

### **Key Metrics to Monitor**
- `secret_rotation_success_total` - Successful rotations
- `secret_rotation_duration_seconds` - Rotation execution time
- `vault_connectivity_status` - Vault health from each node
- `certificate_expiry_days` - Certificate expiration tracking
- `failed_authentication_count` - Security incident detection

---

**🎯 The GameForge secret rotation system is now ready for enterprise Kubernetes production deployment with distributed monitoring and cloud-native scheduling!**
