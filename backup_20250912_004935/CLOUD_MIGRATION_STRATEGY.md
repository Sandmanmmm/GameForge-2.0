# GameForge Production Cloud Migration Strategy
# ===============================================================
# Migration from KIND HA Cluster to Production Cloud Kubernetes
# Maintaining Docker Integration & GameForge Compatibility
# ===============================================================

# PHASE 1: Cloud Provider Setup
# ===============================================================

## AWS EKS Migration Path
```bash
# 1. Create EKS cluster with managed node groups
eksctl create cluster --name gameforge-production \
  --version 1.27 \
  --region us-west-2 \
  --nodegroup-name compute-nodes \
  --node-type m5.xlarge \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed \
  --node-labels="node-type=compute,tier=worker" \
  --asg-access

# 2. Add monitoring node group
eksctl create nodegroup --cluster=gameforge-production \
  --name monitoring-nodes \
  --node-type m5.large \
  --nodes 1 \
  --nodes-min 1 \
  --nodes-max 2 \
  --node-labels="node-type=monitoring,tier=worker"

# 3. Configure AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller/crds?ref=master"
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=gameforge-production
```

## Azure AKS Migration Path
```bash
# 1. Create AKS cluster with multiple node pools
az aks create \
  --resource-group gameforge-resources \
  --name gameforge-production \
  --node-count 2 \
  --node-vm-size Standard_D4s_v3 \
  --generate-ssh-keys \
  --enable-managed-identity \
  --nodepool-name compute \
  --nodepool-labels node-type=compute,tier=worker

# 2. Add monitoring node pool
az aks nodepool add \
  --resource-group gameforge-resources \
  --cluster-name gameforge-production \
  --name monitoring \
  --node-count 1 \
  --node-vm-size Standard_D2s_v3 \
  --node-taints dedicated=monitoring:NoSchedule \
  --labels node-type=monitoring,tier=worker
```

## Google GKE Migration Path
```bash
# 1. Create GKE cluster with node pools
gcloud container clusters create gameforge-production \
  --zone us-central1-a \
  --node-locations us-central1-a,us-central1-b \
  --num-nodes 2 \
  --machine-type n1-standard-4 \
  --node-labels node-type=compute,tier=worker

# 2. Add monitoring node pool
gcloud container node-pools create monitoring \
  --cluster gameforge-production \
  --zone us-central1-a \
  --num-nodes 1 \
  --machine-type n1-standard-2 \
  --node-labels node-type=monitoring,tier=worker
```

# PHASE 2: Container Registry Migration
# ===============================================================

## Docker Image Registry Strategy
```bash
# 1. Tag existing GameForge images for cloud registry
docker tag gameforge:phase2-phase4-production-gpu ${CLOUD_REGISTRY}/gameforge:latest
docker tag gameforge:phase2-phase4-production-gpu ${CLOUD_REGISTRY}/gameforge:v1.0.0

# AWS ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.us-west-2.amazonaws.com
docker push ${AWS_ACCOUNT}.dkr.ecr.us-west-2.amazonaws.com/gameforge:latest

# Azure ACR
az acr login --name gameforgeregistry
docker push gameforgeregistry.azurecr.io/gameforge:latest

# Google GCR
gcloud auth configure-docker
docker push gcr.io/${PROJECT_ID}/gameforge:latest
```

# PHASE 3: Kubernetes Configuration Migration
# ===============================================================

## Update Image References
# Replace local images with cloud registry images in all deployments

## Cloud-Specific Service Configurations
### AWS (using ALB)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: gameforge-grafana-external-prod
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
spec:
  type: LoadBalancer
```

### Azure (using Standard LB)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: gameforge-grafana-external-prod
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-resource-group: "gameforge-resources"
spec:
  type: LoadBalancer
```

### Google Cloud (using Cloud Load Balancer)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: gameforge-grafana-external-prod
  annotations:
    cloud.google.com/load-balancer-type: "External"
spec:
  type: LoadBalancer
```

# PHASE 4: Storage Migration
# ===============================================================

## Cloud Storage Classes
### AWS EBS
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gameforge-storage
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
allowVolumeExpansion: true
```

### Azure Disk
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gameforge-storage
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_LRS
  cachingmode: ReadOnly
allowVolumeExpansion: true
```

### Google Persistent Disk
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gameforge-storage
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
allowVolumeExpansion: true
```

# PHASE 5: Security & Compliance Migration
# ===============================================================

## Cloud-Native Security Integration
### AWS
- IAM Roles for Service Accounts (IRSA)
- AWS Secrets Manager integration
- VPC CNI for network security
- AWS Security Groups

### Azure
- Azure Active Directory integration
- Azure Key Vault CSI driver
- Azure Policy for compliance
- Network Security Groups

### Google Cloud
- Workload Identity
- Secret Manager CSI driver
- Binary Authorization
- VPC-native networking

# PHASE 6: CI/CD Pipeline Updates
# ===============================================================

## Cloud-Native Build & Deploy
```yaml
# GitHub Actions example
name: Deploy GameForge to Cloud
on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Build GameForge Docker Image
      run: |
        docker build -t gameforge:${{ github.sha }} .
        
    - name: Push to Cloud Registry
      run: |
        # Cloud-specific push commands
        
    - name: Deploy to Kubernetes
      run: |
        # Update image tags in k8s manifests
        sed -i 's|gameforge:latest|${CLOUD_REGISTRY}/gameforge:${{ github.sha }}|g' k8s/overlays/production/*.yaml
        kubectl apply -k k8s/overlays/production
```

# PHASE 7: Monitoring & Observability Enhancement
# ===============================================================

## Cloud-Native Monitoring Integration
### Extend current Prometheus/Grafana with cloud services
- AWS CloudWatch integration
- Azure Monitor integration  
- Google Cloud Monitoring integration

## Enhanced Logging
- Centralized logging with cloud-native solutions
- Log aggregation and analysis
- Audit logging compliance

# PHASE 8: Disaster Recovery & Backup
# ===============================================================

## Multi-Region Deployment
- Cross-region cluster federation
- Automated backup strategies
- Data replication policies

## Business Continuity
- Zero-downtime deployments
- Rolling updates with health checks
- Automated rollback procedures

# PHASE 9: Cost Optimization
# ===============================================================

## Resource Optimization
- Horizontal Pod Autoscaling (HPA)
- Vertical Pod Autoscaling (VPA)
- Cluster Autoscaling
- Spot/Preemptible instances for non-critical workloads

## Monitoring & Alerting
- Cost monitoring dashboards
- Budget alerts and quotas
- Resource utilization optimization

# MIGRATION CHECKLIST
# ===============================================================
☐ Cloud provider account setup and permissions
☐ Container registry setup and image migration
☐ Kubernetes cluster creation with node groups
☐ LoadBalancer service configuration update
☐ Storage class and PVC migration
☐ DNS and ingress configuration
☐ Security and compliance setup
☐ CI/CD pipeline updates
☐ Monitoring and logging configuration
☐ Backup and disaster recovery setup
☐ Performance testing and validation
☐ Documentation and runbook updates
