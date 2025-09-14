#!/bin/bash

# Istio Service Mesh Installation Script for GameForge
# Enterprise-grade service mesh deployment with production configurations

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ISTIO_VERSION="${ISTIO_VERSION:-1.20.0}"
KIALI_VERSION="${KIALI_VERSION:-v1.74}"
NAMESPACE="${NAMESPACE:-gameforge}"
ISTIO_NAMESPACE="${ISTIO_NAMESPACE:-istio-system}"
MONITORING_NAMESPACE="${MONITORING_NAMESPACE:-monitoring}"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "$BLUE" "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_status "$RED" "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_status "$RED" "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if user has cluster-admin permissions
    if ! kubectl auth can-i create clusterroles &> /dev/null; then
        print_status "$RED" "Insufficient permissions. You need cluster-admin role to install Istio."
        exit 1
    fi
    
    print_status "$GREEN" "Prerequisites check passed"
}

# Function to download and install Istio
install_istio() {
    print_status "$BLUE" "Installing Istio ${ISTIO_VERSION}..."
    
    # Download Istio
    if [ ! -d "istio-${ISTIO_VERSION}" ]; then
        print_status "$BLUE" "Downloading Istio ${ISTIO_VERSION}..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} TARGET_ARCH=x86_64 sh -
    fi
    
    # Add istioctl to PATH
    export PATH="$PWD/istio-${ISTIO_VERSION}/bin:$PATH"
    
    # Verify installation
    if ! command -v istioctl &> /dev/null; then
        print_status "$RED" "istioctl installation failed"
        exit 1
    fi
    
    print_status "$GREEN" "Istio ${ISTIO_VERSION} downloaded successfully"
}

# Function to create namespaces
create_namespaces() {
    print_status "$BLUE" "Creating namespaces..."
    
    # Create istio-system namespace
    kubectl create namespace "$ISTIO_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Create GameForge namespace with Istio injection enabled
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace "$NAMESPACE" istio-injection=enabled --overwrite
    
    # Create monitoring namespace if it doesn't exist
    kubectl create namespace "$MONITORING_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
    
    print_status "$GREEN" "Namespaces created and configured"
}

# Function to install Istio control plane
install_istio_control_plane() {
    print_status "$BLUE" "Installing Istio control plane..."
    
    # Precheck
    istioctl x precheck
    
    # Install using IstioOperator configuration
    kubectl apply -f k8s/service-mesh/istio-operator.yaml
    
    # Wait for installation to complete
    print_status "$BLUE" "Waiting for Istio control plane to be ready..."
    kubectl wait --for=condition=Ready pods -l app=istiod -n "$ISTIO_NAMESPACE" --timeout=300s
    
    # Verify installation
    istioctl verify-install
    
    print_status "$GREEN" "Istio control plane installed successfully"
}

# Function to install Istio gateways
install_istio_gateways() {
    print_status "$BLUE" "Installing Istio gateways..."
    
    # Wait for gateways to be ready
    print_status "$BLUE" "Waiting for Istio gateways to be ready..."
    kubectl wait --for=condition=Ready pods -l app=istio-ingressgateway -n "$ISTIO_NAMESPACE" --timeout=300s
    kubectl wait --for=condition=Ready pods -l app=istio-eastwestgateway -n "$ISTIO_NAMESPACE" --timeout=300s || true
    
    # Get gateway external IPs
    print_status "$BLUE" "Getting gateway external IPs..."
    INGRESS_IP=$(kubectl get service istio-ingressgateway -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo "pending")
    EASTWEST_IP=$(kubectl get service istio-eastwestgateway -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo "pending")
    
    print_status "$GREEN" "Istio gateways installed successfully"
    print_status "$YELLOW" "Ingress Gateway IP: $INGRESS_IP"
    print_status "$YELLOW" "East-West Gateway IP: $EASTWEST_IP"
}

# Function to apply GameForge service mesh configuration
apply_gameforge_mesh_config() {
    print_status "$BLUE" "Applying GameForge service mesh configuration..."
    
    # Apply virtual services and destination rules
    kubectl apply -f k8s/service-mesh/virtual-services.yaml
    
    # Apply traffic management policies
    kubectl apply -f k8s/service-mesh/traffic-management.yaml
    
    # Apply security and observability configuration
    kubectl apply -f k8s/service-mesh/security-observability.yaml
    
    print_status "$GREEN" "GameForge service mesh configuration applied"
}

# Function to install Kiali
install_kiali() {
    print_status "$BLUE" "Installing Kiali dashboard..."
    
    # Install Kiali Operator
    kubectl apply -f https://raw.githubusercontent.com/kiali/kiali-operator/${KIALI_VERSION}/deploy/kiali/kiali_cr.yaml
    
    # Apply Kiali configuration
    kubectl apply -f k8s/service-mesh/monitoring-dashboard.yaml
    
    # Wait for Kiali to be ready
    print_status "$BLUE" "Waiting for Kiali to be ready..."
    kubectl wait --for=condition=Ready pods -l app=kiali -n "$ISTIO_NAMESPACE" --timeout=300s
    
    # Get Kiali URL
    KIALI_IP=$(kubectl get service kiali-loadbalancer -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo "pending")
    
    print_status "$GREEN" "Kiali dashboard installed successfully"
    print_status "$YELLOW" "Kiali URL: http://$KIALI_IP/kiali"
}

# Function to validate mesh installation
validate_mesh() {
    print_status "$BLUE" "Validating service mesh installation..."
    
    # Check Istio status
    istioctl proxy-status
    
    # Check configuration
    istioctl analyze --all-namespaces
    
    # Verify mTLS is working
    print_status "$BLUE" "Checking mTLS configuration..."
    kubectl exec "$(kubectl get pod -l app=gameforge-api -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')" -c istio-proxy -n "$NAMESPACE" -- openssl s_client -showcerts -connect gameforge-api-service:8000 -alpn istio 2>/dev/null | grep -o "Verify return code: [0-9]*" || true
    
    print_status "$GREEN" "Service mesh validation completed"
}

# Function to create TLS certificates
create_tls_certificates() {
    print_status "$BLUE" "Creating TLS certificates for GameForge..."
    
    # Create self-signed certificate for development (replace with real certs in production)
    if ! kubectl get secret gameforge-tls-secret -n "$ISTIO_NAMESPACE" &> /dev/null; then
        print_status "$BLUE" "Creating self-signed TLS certificate..."
        
        # Create certificate
        openssl req -x509 -newkey rsa:4096 -keyout gameforge.key -out gameforge.crt -days 365 -nodes \
            -subj "/CN=api.gameforge.local/O=GameForge/C=US" \
            -addext "subjectAltName=DNS:api.gameforge.local,DNS:gameforge.local,DNS:*.gameforge.local"
        
        # Create Kubernetes secret
        kubectl create secret tls gameforge-tls-secret \
            --cert=gameforge.crt \
            --key=gameforge.key \
            -n "$ISTIO_NAMESPACE"
        
        # Clean up certificate files
        rm -f gameforge.key gameforge.crt
        
        print_status "$GREEN" "TLS certificate created"
    else
        print_status "$YELLOW" "TLS certificate already exists"
    fi
}

# Function to update existing GameForge deployments
update_gameforge_deployments() {
    print_status "$BLUE" "Updating GameForge deployments for service mesh..."
    
    # Add version labels to existing deployments if they don't exist
    kubectl patch deployment gameforge-api -n "$NAMESPACE" -p '{"spec":{"template":{"metadata":{"labels":{"version":"stable"}}}}}' || true
    kubectl patch deployment postgres -n "$NAMESPACE" -p '{"spec":{"template":{"metadata":{"labels":{"version":"stable"}}}}}' || true
    kubectl patch deployment redis -n "$NAMESPACE" -p '{"spec":{"template":{"metadata":{"labels":{"version":"stable"}}}}}' || true
    
    # Restart deployments to inject Istio sidecars
    kubectl rollout restart deployment -n "$NAMESPACE"
    
    # Wait for rollout to complete
    print_status "$BLUE" "Waiting for deployments to restart with Istio sidecars..."
    kubectl rollout status deployment/gameforge-api -n "$NAMESPACE" --timeout=300s || true
    kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=300s || true
    kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=300s || true
    
    print_status "$GREEN" "GameForge deployments updated for service mesh"
}

# Function to setup monitoring integration
setup_monitoring_integration() {
    print_status "$BLUE" "Setting up monitoring integration..."
    
    # Apply ServiceMonitor configurations
    kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: gameforge-mesh-monitoring
  namespace: $MONITORING_NAMESPACE
  labels:
    app: gameforge
    monitoring: istio
spec:
  selector:
    matchLabels:
      app: gameforge-api
  endpoints:
  - port: http-monitoring
    interval: 30s
    path: /stats/prometheus
    scheme: http
  namespaceSelector:
    matchNames:
    - $NAMESPACE
EOF
    
    print_status "$GREEN" "Monitoring integration configured"
}

# Function to generate installation report
generate_report() {
    local report_file="istio-installation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    print_status "$BLUE" "Generating installation report: $report_file"
    
    {
        echo "GameForge Istio Service Mesh Installation Report"
        echo "Generated: $(date)"
        echo "Istio Version: $ISTIO_VERSION"
        echo "Kiali Version: $KIALI_VERSION"
        echo
        echo "=== Cluster Information ==="
        kubectl cluster-info
        echo
        echo "=== Istio Status ==="
        istioctl version
        echo
        echo "=== Gateway External IPs ==="
        echo "Ingress Gateway: $(kubectl get service istio-ingressgateway -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo 'pending')"
        echo "East-West Gateway: $(kubectl get service istio-eastwestgateway -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo 'pending')"
        echo "Kiali Dashboard: http://$(kubectl get service kiali-loadbalancer -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo 'pending')/kiali"
        echo
        echo "=== Deployed Resources ==="
        kubectl get all -n "$ISTIO_NAMESPACE"
        echo
        echo "=== GameForge Namespace Status ==="
        kubectl get all -n "$NAMESPACE"
        echo
        echo "=== Configuration Analysis ==="
        istioctl analyze --all-namespaces
    } > "$report_file"
    
    print_status "$GREEN" "Installation report saved: $report_file"
}

# Main installation function
main() {
    print_status "$BLUE" "Starting GameForge Istio Service Mesh Installation"
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --istio-version)
                ISTIO_VERSION="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --skip-kiali)
                SKIP_KIALI=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --istio-version VERSION    Istio version to install (default: 1.20.0)"
                echo "  --namespace NAMESPACE      GameForge namespace (default: gameforge)"
                echo "  --skip-kiali              Skip Kiali installation"
                echo "  --help                     Show this help message"
                exit 0
                ;;
            *)
                print_status "$RED" "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Installation steps
    check_prerequisites
    install_istio
    create_namespaces
    create_tls_certificates
    install_istio_control_plane
    install_istio_gateways
    apply_gameforge_mesh_config
    update_gameforge_deployments
    
    if [ "${SKIP_KIALI:-false}" != "true" ]; then
        install_kiali
    fi
    
    setup_monitoring_integration
    validate_mesh
    generate_report
    
    echo
    print_status "$GREEN" "🎉 GameForge Istio Service Mesh installation completed successfully!"
    echo
    print_status "$BLUE" "Next steps:"
    echo "1. Access Kiali dashboard for service topology visualization"
    echo "2. Configure DNS entries for *.gameforge.local to point to the ingress gateway"
    echo "3. Replace self-signed certificates with production certificates"
    echo "4. Review and customize traffic policies in k8s/service-mesh/"
    echo "5. Monitor service mesh metrics in Grafana dashboards"
    echo
    print_status "$YELLOW" "Important URLs:"
    echo "- Kiali Dashboard: http://$(kubectl get service kiali-loadbalancer -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo 'pending')/kiali"
    echo "- GameForge API: https://api.gameforge.local (after DNS configuration)"
    echo "- Istio Ingress: $(kubectl get service istio-ingressgateway -n "$ISTIO_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo 'pending')"
}

# Run main function
main "$@"
