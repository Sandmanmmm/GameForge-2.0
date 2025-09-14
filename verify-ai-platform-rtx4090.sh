#!/bin/bash
# =============================================================================
# GameForge AI Platform Verification Script for RTX 4090 Deployment
# =============================================================================
# This script verifies the complete GameForge AI platform deployment on RTX 4090

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Service configuration
DOCKER_COMPOSE_FILE="docker/compose/docker-compose.production-hardened.yml"
AI_SERVICES=(
    "torchserve-rtx4090"
    "ray-head-rtx4090"
    "kubeflow-pipelines-rtx4090"
    "dcgm-exporter-rtx4090"
    "mlflow-model-registry-rtx4090"
)

# =============================================================================
# Utility Functions
# =============================================================================
print_header() {
    echo -e "\n${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' $(seq 1 ${#1}))${NC}"
}

print_status() {
    local status=$1
    local message=$2
    case $status in
        "pass")
            echo -e "  ${GREEN}✅ $message${NC}"
            ;;
        "fail")
            echo -e "  ${RED}❌ $message${NC}"
            ;;
        "warn")
            echo -e "  ${YELLOW}⚠️  $message${NC}"
            ;;
        "info")
            echo -e "  ${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# =============================================================================
# System Information
# =============================================================================
check_system_info() {
    print_header "SYSTEM INFORMATION"
    
    # GPU Information
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader)
        echo -e "${BOLD}GPU Configuration:${NC}"
        echo "$GPU_INFO" | while IFS=',' read -r name memory_total memory_used temp util; do
            print_status "info" "GPU: $name"
            print_status "info" "VRAM: $memory_used / $memory_total"
            print_status "info" "Temperature: ${temp}°C"
            print_status "info" "Utilization: ${util}%"
        done
    else
        print_status "fail" "nvidia-smi not available"
    fi
    
    # System Resources
    echo -e "\n${BOLD}System Resources:${NC}"
    TOTAL_MEM=$(free -h | awk '/^Mem:/{print $2}')
    USED_MEM=$(free -h | awk '/^Mem:/{print $3}')
    DISK_USAGE=$(df -h / | awk 'NR==2{print $3 "/" $2 " (" $5 ")"}')
    LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}')
    
    print_status "info" "Memory: $USED_MEM / $TOTAL_MEM"
    print_status "info" "Disk Usage: $DISK_USAGE"
    print_status "info" "Load Average:$LOAD_AVG"
}

# =============================================================================
# Docker Environment Verification
# =============================================================================
check_docker_environment() {
    print_header "DOCKER ENVIRONMENT"
    
    # Docker version
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        print_status "pass" "Docker installed: $DOCKER_VERSION"
    else
        print_status "fail" "Docker not installed"
        return 1
    fi
    
    # Docker Compose version
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | tr -d ',')
        print_status "pass" "Docker Compose installed: $COMPOSE_VERSION"
    else
        print_status "fail" "Docker Compose not installed"
        return 1
    fi
    
    # NVIDIA Container Runtime
    if docker info | grep -q nvidia; then
        print_status "pass" "NVIDIA container runtime available"
    else
        print_status "fail" "NVIDIA container runtime not configured"
    fi
    
    # Docker networks
    echo -e "\n${BOLD}Docker Networks:${NC}"
    for network in ai-network gpu-network ml-network monitoring-network; do
        if docker network ls | grep -q "$network"; then
            print_status "pass" "Network exists: $network"
        else
            print_status "warn" "Network missing: $network"
        fi
    done
}

# =============================================================================
# AI Services Status Check
# =============================================================================
check_ai_services() {
    print_header "AI PLATFORM SERVICES"
    
    echo -e "${BOLD}Service Status:${NC}"
    for service in "${AI_SERVICES[@]}"; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            UPTIME=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep "Up" | awk '{print $5, $6}')
            print_status "pass" "$service: Running ($UPTIME)"
        else
            print_status "fail" "$service: Not running"
        fi
    done
    
    # Container resource usage
    echo -e "\n${BOLD}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "(torchserve|ray|kubeflow|dcgm|mlflow)" || print_status "warn" "No AI services found in stats"
}

# =============================================================================
# TorchServe Verification
# =============================================================================
check_torchserve() {
    print_header "TORCHSERVE MODEL SERVING"
    
    # Service health
    if curl -sf http://localhost:8080/ping &>/dev/null; then
        print_status "pass" "TorchServe inference API responding"
    else
        print_status "fail" "TorchServe inference API not responding"
        return 1
    fi
    
    if curl -sf http://localhost:8081/models &>/dev/null; then
        print_status "pass" "TorchServe management API responding"
    else
        print_status "fail" "TorchServe management API not responding"
    fi
    
    if curl -sf http://localhost:8082/metrics &>/dev/null; then
        print_status "pass" "TorchServe metrics endpoint responding"
    else
        print_status "warn" "TorchServe metrics endpoint not responding"
    fi
    
    # Model information
    echo -e "\n${BOLD}Registered Models:${NC}"
    MODEL_LIST=$(curl -sf http://localhost:8081/models 2>/dev/null || echo "[]")
    if [[ "$MODEL_LIST" == "[]" ]]; then
        print_status "warn" "No models currently registered"
    else
        echo "$MODEL_LIST" | jq -r '.models[].modelName' 2>/dev/null | while read -r model; do
            print_status "info" "Model: $model"
        done
    fi
    
    # Performance metrics
    echo -e "\n${BOLD}Performance Metrics:${NC}"
    METRICS=$(curl -sf http://localhost:8082/metrics 2>/dev/null | grep -E "(Requests|gpu)" | head -5 || echo "No metrics available")
    if [[ "$METRICS" != "No metrics available" ]]; then
        echo "$METRICS" | while read -r line; do
            print_status "info" "$line"
        done
    else
        print_status "warn" "Performance metrics not available"
    fi
}

# =============================================================================
# Ray Cluster Verification
# =============================================================================
check_ray_cluster() {
    print_header "RAY DISTRIBUTED COMPUTING"
    
    # Ray dashboard
    if curl -sf http://localhost:8265 &>/dev/null; then
        print_status "pass" "Ray dashboard responding"
    else
        print_status "fail" "Ray dashboard not responding"
        return 1
    fi
    
    # Ray cluster status
    echo -e "\n${BOLD}Cluster Status:${NC}"
    RAY_STATUS=$(docker exec -i $(docker ps -q -f name=ray-head) ray status 2>/dev/null || echo "Ray status unavailable")
    if [[ "$RAY_STATUS" != "Ray status unavailable" ]]; then
        echo "$RAY_STATUS" | head -10
    else
        print_status "fail" "Cannot retrieve Ray cluster status"
    fi
    
    # Ray nodes
    echo -e "\n${BOLD}Ray Nodes:${NC}"
    RAY_NODES=$(docker exec -i $(docker ps -q -f name=ray-head) ray list nodes 2>/dev/null || echo "Node list unavailable")
    if [[ "$RAY_NODES" != "Node list unavailable" ]]; then
        echo "$RAY_NODES"
    else
        print_status "warn" "Cannot retrieve Ray node information"
    fi
}

# =============================================================================
# MLflow Verification
# =============================================================================
check_mlflow() {
    print_header "MLFLOW MODEL REGISTRY"
    
    # MLflow UI
    if curl -sf http://localhost:5000 &>/dev/null; then
        print_status "pass" "MLflow UI responding"
    else
        print_status "fail" "MLflow UI not responding"
        return 1
    fi
    
    # MLflow API
    if curl -sf http://localhost:5000/api/2.0/mlflow/experiments/list &>/dev/null; then
        print_status "pass" "MLflow API responding"
    else
        print_status "warn" "MLflow API not responding"
    fi
    
    # Experiments
    echo -e "\n${BOLD}MLflow Experiments:${NC}"
    EXPERIMENTS=$(curl -sf http://localhost:5000/api/2.0/mlflow/experiments/list 2>/dev/null | jq -r '.experiments[].name' 2>/dev/null || echo "No experiments")
    if [[ "$EXPERIMENTS" != "No experiments" ]]; then
        echo "$EXPERIMENTS" | while read -r exp; do
            print_status "info" "Experiment: $exp"
        done
    else
        print_status "warn" "No experiments found"
    fi
}

# =============================================================================
# GPU Monitoring Verification
# =============================================================================
check_gpu_monitoring() {
    print_header "GPU MONITORING (DCGM)"
    
    # DCGM metrics
    if curl -sf http://localhost:9400/metrics &>/dev/null; then
        print_status "pass" "DCGM metrics endpoint responding"
        
        # Sample GPU metrics
        echo -e "\n${BOLD}GPU Metrics Sample:${NC}"
        GPU_METRICS=$(curl -sf http://localhost:9400/metrics 2>/dev/null | grep -E "(DCGM_FI_DEV_GPU_UTIL|DCGM_FI_DEV_MEM_COPY_UTIL|DCGM_FI_DEV_GPU_TEMP)" | head -5)
        if [[ -n "$GPU_METRICS" ]]; then
            echo "$GPU_METRICS" | while read -r metric; do
                print_status "info" "$metric"
            done
        fi
    else
        print_status "fail" "DCGM metrics endpoint not responding"
    fi
    
    # Real-time GPU status
    echo -e "\n${BOLD}Real-time GPU Status:${NC}"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=timestamp,name,pci.bus_id,driver_version,pstate,pcie.link.gen.current,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used --format=csv,noheader | head -3
    fi
}

# =============================================================================
# Network Connectivity Tests
# =============================================================================
check_network_connectivity() {
    print_header "NETWORK CONNECTIVITY"
    
    # Internal service communication
    echo -e "${BOLD}Service Endpoints:${NC}"
    
    ENDPOINTS=(
        "http://localhost:8080/ping:TorchServe Inference"
        "http://localhost:8081/models:TorchServe Management"
        "http://localhost:8082/metrics:TorchServe Metrics"
        "http://localhost:8265:Ray Dashboard"
        "http://localhost:5000:MLflow UI"
        "http://localhost:9400/metrics:DCGM Metrics"
    )
    
    for endpoint in "${ENDPOINTS[@]}"; do
        IFS=':' read -r url name <<< "$endpoint"
        if curl -sf "$url" &>/dev/null; then
            print_status "pass" "$name accessible"
        else
            print_status "fail" "$name not accessible"
        fi
    done
    
    # Traefik routing (if available)
    echo -e "\n${BOLD}Traefik Routing:${NC}"
    if curl -sf http://localhost:8080/api/entrypoints &>/dev/null; then
        print_status "pass" "Traefik API responding"
    else
        print_status "warn" "Traefik not available or not configured"
    fi
}

# =============================================================================
# Security Status Check
# =============================================================================
check_security_status() {
    print_header "SECURITY STATUS"
    
    # Container security
    echo -e "${BOLD}Container Security:${NC}"
    
    # Check for privileged containers (should be minimal)
    PRIVILEGED_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Command}}" | grep -c "privileged" || echo "0")
    if [[ "$PRIVILEGED_CONTAINERS" -eq 0 ]]; then
        print_status "pass" "No privileged containers running"
    else
        print_status "warn" "$PRIVILEGED_CONTAINERS privileged containers found"
    fi
    
    # Check for containers running as root
    echo -e "\n${BOLD}Container Users:${NC}"
    for service in "${AI_SERVICES[@]}"; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            CONTAINER_ID=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q "$service")
            USER_INFO=$(docker exec "$CONTAINER_ID" whoami 2>/dev/null || echo "unknown")
            if [[ "$USER_INFO" == "root" ]]; then
                print_status "warn" "$service running as root"
            else
                print_status "pass" "$service running as: $USER_INFO"
            fi
        fi
    done
    
    # Network security
    echo -e "\n${BOLD}Network Security:${NC}"
    EXPOSED_PORTS=$(docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(0.0.0.0:|::)" | wc -l)
    print_status "info" "$EXPOSED_PORTS services with exposed ports"
}

# =============================================================================
# Performance Benchmarks
# =============================================================================
run_performance_tests() {
    print_header "PERFORMANCE BENCHMARKS"
    
    echo -e "${BOLD}GPU Performance:${NC}"
    
    # GPU memory bandwidth test
    if command -v nvidia-smi &> /dev/null; then
        GPU_PERF=$(nvidia-smi --query-gpu=clocks.current.graphics,clocks.current.memory,power.draw,temperature.gpu --format=csv,noheader,nounits)
        echo "$GPU_PERF" | while IFS=',' read -r gpu_clock mem_clock power temp; do
            print_status "info" "GPU Clock: ${gpu_clock} MHz"
            print_status "info" "Memory Clock: ${mem_clock} MHz"
            print_status "info" "Power Draw: ${power} W"
            print_status "info" "Temperature: ${temp}°C"
        done
    fi
    
    # TorchServe performance test (if available)
    echo -e "\n${BOLD}TorchServe Performance:${NC}"
    if curl -sf http://localhost:8080/ping &>/dev/null; then
        # Simple latency test
        START_TIME=$(date +%s%N)
        curl -sf http://localhost:8080/ping &>/dev/null
        END_TIME=$(date +%s%N)
        LATENCY=$(( (END_TIME - START_TIME) / 1000000 ))
        print_status "info" "API Latency: ${LATENCY} ms"
    fi
    
    # Docker performance
    echo -e "\n${BOLD}Container Performance:${NC}"
    CONTAINER_COUNT=$(docker ps | grep -c "Up" || echo "0")
    print_status "info" "Running containers: $CONTAINER_COUNT"
    
    # System load
    LOAD_1MIN=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    print_status "info" "System load (1min): $LOAD_1MIN"
}

# =============================================================================
# Logs and Troubleshooting
# =============================================================================
check_logs() {
    print_header "RECENT LOGS AND ERRORS"
    
    echo -e "${BOLD}Recent Errors in Logs:${NC}"
    for service in "${AI_SERVICES[@]}"; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            ERROR_COUNT=$(docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=100 "$service" 2>/dev/null | grep -i error | wc -l)
            WARNING_COUNT=$(docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=100 "$service" 2>/dev/null | grep -i warning | wc -l)
            
            if [[ "$ERROR_COUNT" -eq 0 ]]; then
                print_status "pass" "$service: No errors in recent logs"
            else
                print_status "warn" "$service: $ERROR_COUNT errors, $WARNING_COUNT warnings"
            fi
        fi
    done
    
    # Disk space for logs
    echo -e "\n${BOLD}Log Storage:${NC}"
    LOG_SIZE=$(du -sh /var/lib/docker/containers 2>/dev/null | awk '{print $1}' || echo "unknown")
    print_status "info" "Docker log storage: $LOG_SIZE"
}

# =============================================================================
# Summary Report
# =============================================================================
generate_summary() {
    print_header "DEPLOYMENT SUMMARY"
    
    # Count successful checks
    TOTAL_SERVICES=${#AI_SERVICES[@]}
    RUNNING_SERVICES=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -c "Up" || echo "0")
    
    echo -e "${BOLD}Overall Status:${NC}"
    print_status "info" "AI Services: $RUNNING_SERVICES / $TOTAL_SERVICES running"
    
    # Provide recommendations
    echo -e "\n${BOLD}Recommendations:${NC}"
    if [[ "$RUNNING_SERVICES" -eq "$TOTAL_SERVICES" ]]; then
        print_status "pass" "All AI services are running successfully"
        print_status "pass" "Platform ready for AI/ML workloads"
    elif [[ "$RUNNING_SERVICES" -gt 0 ]]; then
        print_status "warn" "Some services need attention"
        print_status "info" "Check logs for failed services"
    else
        print_status "fail" "No AI services running"
        print_status "info" "Run deployment script or check configuration"
    fi
    
    # Next steps
    echo -e "\n${BOLD}Next Steps:${NC}"
    print_status "info" "View TorchServe: http://localhost:8080"
    print_status "info" "View Ray Dashboard: http://localhost:8265"
    print_status "info" "View MLflow: http://localhost:5000"
    print_status "info" "Monitor GPU: nvidia-smi or http://localhost:9400/metrics"
    
    echo -e "\n${CYAN}${BOLD}GameForge AI Platform Verification Complete!${NC}"
}

# =============================================================================
# Main Function
# =============================================================================
main() {
    echo -e "${CYAN}${BOLD}"
    echo "=================================================================="
    echo "  GameForge AI Platform Verification - RTX 4090 Deployment"
    echo "=================================================================="
    echo -e "${NC}"
    echo "Timestamp: $(date)"
    echo "Platform: vast.ai RTX 4090"
    echo "Configuration: Production Hardened"
    echo ""
    
    # Run all verification checks
    check_system_info
    check_docker_environment
    check_ai_services
    check_torchserve
    check_ray_cluster
    check_mlflow
    check_gpu_monitoring
    check_network_connectivity
    check_security_status
    run_performance_tests
    check_logs
    generate_summary
}

# =============================================================================
# Script Execution
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
