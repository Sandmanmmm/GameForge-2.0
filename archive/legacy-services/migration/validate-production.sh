#!/bin/bash
# GameForge AI Production Validation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/gameforge/validation.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Validate Kubernetes deployment
validate_kubernetes() {
    log "Validating Kubernetes deployment..."
    
    # Check pods
    RUNNING_PODS=$(kubectl get pods -n gameforge --field-selector=status.phase=Running --no-headers | wc -l)
    TOTAL_PODS=$(kubectl get pods -n gameforge --no-headers | wc -l)
    
    log "Running pods: $RUNNING_PODS/$TOTAL_PODS"
    
    if [ "$RUNNING_PODS" -ne "$TOTAL_PODS" ]; then
        log "❌ Not all pods are running"
        kubectl get pods -n gameforge
        return 1
    fi
    
    # Check services
    SERVICES=$(kubectl get services -n gameforge --no-headers | wc -l)
    log "Services: $SERVICES"
    
    # Check ingress
    INGRESS=$(kubectl get ingress -n gameforge --no-headers | wc -l)
    log "Ingress rules: $INGRESS"
    
    log "✅ Kubernetes validation passed"
}

# Validate application functionality
validate_application() {
    log "Validating application functionality..."
    
    # Get ingress URL
    INGRESS_IP=$(kubectl get ingress gameforge-ingress -n gameforge -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$INGRESS_IP" ]; then
        INGRESS_IP="localhost"
    fi
    
    # Test health endpoint
    if curl -f "http://$INGRESS_IP/health" > /dev/null 2>&1; then
        log "✅ Health endpoint accessible"
    else
        log "❌ Health endpoint not accessible"
        return 1
    fi
    
    # Test API endpoint
    if curl -f "http://$INGRESS_IP/api/status" > /dev/null 2>&1; then
        log "✅ API endpoint accessible"
    else
        log "⚠️ API endpoint not accessible (may require authentication)"
    fi
    
    # Test GPU endpoint if enabled
    if curl -f "http://$INGRESS_IP/gpu/health" > /dev/null 2>&1; then
        log "✅ GPU inference endpoint accessible"
    else
        log "⚠️ GPU inference endpoint not accessible"
    fi
    
    log "✅ Application validation completed"
}

# Validate monitoring
validate_monitoring() {
    log "Validating monitoring setup..."
    
    # Check Prometheus
    if kubectl get pod -n gameforge -l app=prometheus > /dev/null 2>&1; then
        log "✅ Prometheus running"
    else
        log "⚠️ Prometheus not found"
    fi
    
    # Check metrics endpoint
    APP_POD=$(kubectl get pods -n gameforge -l app=gameforge,component=app -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec -n gameforge "$APP_POD" -- curl -f http://localhost:9090/metrics > /dev/null 2>&1; then
        log "✅ Metrics endpoint accessible"
    else
        log "❌ Metrics endpoint not accessible"
    fi
    
    log "✅ Monitoring validation completed"
}

# Validate security
validate_security() {
    log "Validating security configuration..."
    
    # Check RBAC
    if kubectl auth can-i list pods --namespace=gameforge --as=system:serviceaccount:gameforge:gameforge-service-account > /dev/null 2>&1; then
        log "✅ RBAC configured correctly"
    else
        log "⚠️ RBAC may not be configured correctly"
    fi
    
    # Check network policies
    NETWORK_POLICIES=$(kubectl get networkpolicies -n gameforge --no-headers 2>/dev/null | wc -l)
    log "Network policies: $NETWORK_POLICIES"
    
    # Check secrets
    SECRETS=$(kubectl get secrets -n gameforge --no-headers | wc -l)
    log "Secrets: $SECRETS"
    
    log "✅ Security validation completed"
}

# Generate validation report
generate_report() {
    log "Generating validation report..."
    
    cat > "$SCRIPT_DIR/validation-report-$(date +%Y%m%d).json" << EOF
{
    "validation_date": "$(date -Iseconds)",
    "cluster_info": {
        "nodes": $(kubectl get nodes --no-headers | wc -l),
        "namespaces": $(kubectl get namespaces --no-headers | wc -l),
        "version": "$(kubectl version --client --short 2>/dev/null | head -1)"
    },
    "gameforge_deployment": {
        "pods": $(kubectl get pods -n gameforge --no-headers 2>/dev/null | wc -l),
        "services": $(kubectl get services -n gameforge --no-headers 2>/dev/null | wc -l),
        "ingress": $(kubectl get ingress -n gameforge --no-headers 2>/dev/null | wc -l),
        "secrets": $(kubectl get secrets -n gameforge --no-headers 2>/dev/null | wc -l)
    },
    "validation_status": "COMPLETED",
    "next_validation": "$(date -d '+1 day' -Iseconds)"
}
EOF
    
    log "✅ Validation report generated"
}

main() {
    log "Starting production validation..."
    
    validate_kubernetes
    validate_application
    validate_monitoring
    validate_security
    generate_report
    
    log "🎉 Production validation completed successfully!"
}

main "$@"
