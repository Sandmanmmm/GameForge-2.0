#!/bin/bash
# GameForge AI Migration Script
# Comprehensive production migration automation
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/gameforge/migration.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Pre-migration checks
pre_migration_checks() {
    log "Running pre-migration checks..."
    
    # Check Kubernetes cluster connectivity
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log "❌ Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check required tools
    for tool in kubectl helm docker; do
        if ! command -v $tool > /dev/null 2>&1; then
            log "❌ Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check cluster resources
    NODES=$(kubectl get nodes --no-headers | wc -l)
    if [ "$NODES" -lt 3 ]; then
        log "⚠️ Warning: Less than 3 nodes available"
    fi
    
    # Check GPU nodes
    GPU_NODES=$(kubectl get nodes -l accelerator=nvidia-tesla-gpu --no-headers | wc -l)
    if [ "$GPU_NODES" -eq 0 ]; then
        log "⚠️ Warning: No GPU nodes found"
    fi
    
    log "✅ Pre-migration checks completed"
}

# Create namespace and RBAC
setup_namespace() {
    log "Setting up namespace and RBAC..."
    
    kubectl apply -f k8s/manifests/01-namespace.yaml
    
    # Service account
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gameforge-service-account
  namespace: gameforge
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gameforge-cluster-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gameforge-cluster-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: gameforge-cluster-role
subjects:
- kind: ServiceAccount
  name: gameforge-service-account
  namespace: gameforge
EOF
    
    log "✅ Namespace and RBAC configured"
}

# Deploy with Kubernetes manifests
deploy_with_manifests() {
    log "Deploying with Kubernetes manifests..."
    
    # Apply manifests in order
    for manifest in k8s/manifests/*.yaml; do
        log "Applying $(basename "$manifest")..."
        kubectl apply -f "$manifest"
        sleep 5
    done
    
    log "✅ Kubernetes manifests deployed"
}

# Deploy with Helm
deploy_with_helm() {
    log "Deploying with Helm chart..."
    
    # Add required repositories
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install dependencies
    helm dependency update helm/gameforge/
    
    # Install GameForge
    helm upgrade --install gameforge helm/gameforge/ \
        --namespace gameforge \
        --create-namespace \
        --wait \
        --timeout 10m
    
    log "✅ Helm deployment completed"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=gameforge -n gameforge --timeout=300s
    
    # Check service endpoints
    ENDPOINTS=$(kubectl get endpoints -n gameforge --no-headers | wc -l)
    if [ "$ENDPOINTS" -eq 0 ]; then
        log "❌ No service endpoints found"
        return 1
    fi
    
    # Test health endpoint
    APP_POD=$(kubectl get pods -n gameforge -l app=gameforge,component=app -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec -n gameforge "$APP_POD" -- curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log "✅ Health check passed"
    else
        log "❌ Health check failed"
        return 1
    fi
    
    log "✅ Deployment verification completed"
}

# Post-migration tasks
post_migration_tasks() {
    log "Running post-migration tasks..."
    
    # Configure monitoring
    kubectl apply -f - << EOF
apiVersion: v1
kind: Service
metadata:
  name: gameforge-monitoring
  namespace: gameforge
  labels:
    app: gameforge
    component: monitoring
spec:
  selector:
    app: gameforge
    component: app
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
EOF
    
    # Set up ingress controller if not present
    if ! kubectl get ingressclass nginx > /dev/null 2>&1; then
        log "Installing nginx ingress controller..."
        helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
        helm repo update
        helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
            --namespace ingress-nginx \
            --create-namespace
    fi
    
    # Configure cert-manager if not present
    if ! kubectl get namespace cert-manager > /dev/null 2>&1; then
        log "Installing cert-manager..."
        helm repo add jetstack https://charts.jetstack.io
        helm repo update
        helm upgrade --install cert-manager jetstack/cert-manager \
            --namespace cert-manager \
            --create-namespace \
            --set installCRDs=true
    fi
    
    log "✅ Post-migration tasks completed"
}

# Rollback function
rollback_deployment() {
    log "Rolling back deployment..."
    
    if command -v helm > /dev/null 2>&1; then
        helm rollback gameforge --namespace gameforge
    else
        kubectl delete namespace gameforge
    fi
    
    log "✅ Rollback completed"
}

# Main migration function
main() {
    log "Starting GameForge AI migration to production..."
    
    DEPLOYMENT_METHOD="${1:-helm}"  # Default to helm
    
    case "$DEPLOYMENT_METHOD" in
        "manifests"|"k8s")
            pre_migration_checks
            setup_namespace
            deploy_with_manifests
            verify_deployment
            post_migration_tasks
            ;;
        "helm")
            pre_migration_checks
            setup_namespace
            deploy_with_helm
            verify_deployment
            post_migration_tasks
            ;;
        "rollback")
            rollback_deployment
            ;;
        *)
            log "Usage: $0 [manifests|helm|rollback]"
            exit 1
            ;;
    esac
    
    log "🎉 GameForge AI migration completed successfully!"
    
    # Display access information
    log "Access Information:"
    log "- Application: https://gameforge.production.com"
    log "- Monitoring: https://gameforge.production.com/monitoring"
    log "- GPU Inference: https://gameforge.production.com/gpu"
}

# Error handling
trap 'log "Migration failed: $BASH_COMMAND"; exit 1' ERR

main "$@"
