#!/bin/bash

# Deployment Monitoring Script
# Provides real-time monitoring of blue/green deployments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-gameforge}"
SERVICE_NAME="${2:-gameforge-api}"
MONITORING_DURATION="${3:-300}" # 5 minutes

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# Function to get deployment status
get_deployment_status() {
    local deployment=$1
    kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "Unknown"
}

# Function to get pod count
get_pod_count() {
    local selector=$1
    kubectl get pods -n "$NAMESPACE" -l "$selector" --field-selector=status.phase=Running -o name 2>/dev/null | wc -l
}

# Function to get service metrics
get_service_metrics() {
    local service_url=$1
    local response=$(curl -s -w "%{http_code}:%{time_total}" "$service_url/api/v1/health" 2>/dev/null || echo "000:0")
    echo "$response"
}

# Function to monitor deployment progress
monitor_deployment() {
    local start_time=$(date +%s)
    local end_time=$((start_time + MONITORING_DURATION))
    
    print_status "$BLUE" "Starting deployment monitoring for $SERVICE_NAME in namespace $NAMESPACE"
    print_status "$BLUE" "Monitoring duration: ${MONITORING_DURATION}s"
    echo
    
    # Monitor loop
    while [ $(date +%s) -lt $end_time ]; do
        clear
        echo "═══════════════════════════════════════════════════════════════"
        echo "  GameForge Deployment Monitor - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "═══════════════════════════════════════════════════════════════"
        echo
        
        # Deployment Status
        echo "🚀 DEPLOYMENT STATUS:"
        echo "───────────────────────────────────────────────────────────────"
        
        # Check blue/green deployments
        blue_status=$(get_deployment_status "${SERVICE_NAME}-blue" 2>/dev/null || echo "Not Found")
        green_status=$(get_deployment_status "${SERVICE_NAME}-green" 2>/dev/null || echo "Not Found")
        
        if [ "$blue_status" = "True" ]; then
            print_status "$GREEN" "✓ Blue deployment: HEALTHY"
        elif [ "$blue_status" = "False" ]; then
            print_status "$RED" "✗ Blue deployment: UNHEALTHY"
        else
            print_status "$YELLOW" "○ Blue deployment: NOT FOUND"
        fi
        
        if [ "$green_status" = "True" ]; then
            print_status "$GREEN" "✓ Green deployment: HEALTHY"
        elif [ "$green_status" = "False" ]; then
            print_status "$RED" "✗ Green deployment: UNHEALTHY"
        else
            print_status "$YELLOW" "○ Green deployment: NOT FOUND"
        fi
        
        echo
        
        # Pod Status
        echo "📦 POD STATUS:"
        echo "───────────────────────────────────────────────────────────────"
        
        blue_pods=$(get_pod_count "app=${SERVICE_NAME},version=blue")
        green_pods=$(get_pod_count "app=${SERVICE_NAME},version=green")
        
        echo "Blue pods running: $blue_pods"
        echo "Green pods running: $green_pods"
        echo
        
        # Service Status
        echo "🌐 SERVICE STATUS:"
        echo "───────────────────────────────────────────────────────────────"
        
        # Get current active service
        active_service=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "unknown")
        print_status "$BLUE" "Active service version: $active_service"
        
        # Get service endpoint
        service_ip=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
        if [ "$service_ip" != "pending" ] && [ -n "$service_ip" ]; then
            service_url="http://$service_ip"
            metrics=$(get_service_metrics "$service_url")
            http_code=$(echo "$metrics" | cut -d':' -f1)
            response_time=$(echo "$metrics" | cut -d':' -f2)
            
            if [ "$http_code" = "200" ]; then
                print_status "$GREEN" "✓ Service health: OK (${response_time}s)"
            else
                print_status "$RED" "✗ Service health: FAILED (HTTP $http_code)"
            fi
        else
            print_status "$YELLOW" "○ Service endpoint: PENDING"
        fi
        
        echo
        
        # Traffic Distribution
        echo "📊 TRAFFIC DISTRIBUTION:"
        echo "───────────────────────────────────────────────────────────────"
        
        # Check ingress traffic split (if using ingress)
        ingress_info=$(kubectl get ingress "${SERVICE_NAME}-ingress" -n "$NAMESPACE" -o jsonpath='{.metadata.annotations}' 2>/dev/null || echo "{}")
        if echo "$ingress_info" | grep -q "canary"; then
            canary_weight=$(echo "$ingress_info" | grep -o '"nginx.ingress.kubernetes.io/canary-weight":"[0-9]*"' | cut -d'"' -f4)
            if [ -n "$canary_weight" ]; then
                print_status "$BLUE" "Canary traffic: ${canary_weight}%"
                print_status "$BLUE" "Stable traffic: $((100 - canary_weight))%"
            fi
        else
            print_status "$BLUE" "Traffic mode: Direct (100% to active version)"
        fi
        
        echo
        
        # Recent Events
        echo "📋 RECENT EVENTS:"
        echo "───────────────────────────────────────────────────────────────"
        kubectl get events -n "$NAMESPACE" --sort-by=.firstTimestamp | tail -5 | while IFS= read -r line; do
            if echo "$line" | grep -q "Error\|Failed\|Unhealthy"; then
                print_status "$RED" "$line"
            elif echo "$line" | grep -q "Started\|Created\|Successful"; then
                print_status "$GREEN" "$line"
            else
                echo "$line"
            fi
        done
        
        echo
        echo "═══════════════════════════════════════════════════════════════"
        echo "Press Ctrl+C to exit monitoring"
        echo "Time remaining: $((end_time - $(date +%s)))s"
        
        sleep 5
    done
    
    print_status "$BLUE" "Monitoring completed"
}

# Function to generate deployment report
generate_report() {
    local report_file="deployment-report-$(date +%Y%m%d-%H%M%S).txt"
    
    print_status "$BLUE" "Generating deployment report: $report_file"
    
    {
        echo "GameForge Deployment Report"
        echo "Generated: $(date)"
        echo "Namespace: $NAMESPACE"
        echo "Service: $SERVICE_NAME"
        echo
        echo "=== Final Status ==="
        echo "Blue deployment: $(get_deployment_status "${SERVICE_NAME}-blue")"
        echo "Green deployment: $(get_deployment_status "${SERVICE_NAME}-green")"
        echo "Blue pods: $(get_pod_count "app=${SERVICE_NAME},version=blue")"
        echo "Green pods: $(get_pod_count "app=${SERVICE_NAME},version=green")"
        echo
        echo "=== Service Configuration ==="
        kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o yaml
        echo
        echo "=== Recent Events ==="
        kubectl get events -n "$NAMESPACE" --sort-by=.firstTimestamp | tail -20
    } > "$report_file"
    
    print_status "$GREEN" "Report saved: $report_file"
}

# Main execution
case "${4:-monitor}" in
    "monitor")
        monitor_deployment
        ;;
    "report")
        generate_report
        ;;
    "status")
        echo "Blue deployment: $(get_deployment_status "${SERVICE_NAME}-blue")"
        echo "Green deployment: $(get_deployment_status "${SERVICE_NAME}-green")"
        echo "Blue pods: $(get_pod_count "app=${SERVICE_NAME},version=blue")"
        echo "Green pods: $(get_pod_count "app=${SERVICE_NAME},version=green")"
        ;;
    *)
        echo "Usage: $0 [namespace] [service_name] [duration] [monitor|report|status]"
        echo "Example: $0 gameforge gameforge-api 300 monitor"
        exit 1
        ;;
esac
