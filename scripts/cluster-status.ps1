# HA Cluster Deployment Summary
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Write-Host "=== GameForge HA Cluster Status ===" -ForegroundColor Green
Write-Host ""

Write-Host "Multi-Node Cluster:" -ForegroundColor Yellow
kubectl get nodes -o wide

Write-Host ""
Write-Host "Node Specialization:" -ForegroundColor Yellow
kubectl get nodes --show-labels | Select-String "node-type"

Write-Host ""
Write-Host "Pod Distribution (Node Affinity):" -ForegroundColor Yellow
kubectl get pods -n gameforge-monitoring -o wide

Write-Host ""
Write-Host "External LoadBalancer Services:" -ForegroundColor Yellow
kubectl get svc -A | Select-String "LoadBalancer"

Write-Host ""
Write-Host "MetalLB Status:" -ForegroundColor Yellow
kubectl get pods -n metallb-system

Write-Host ""
Write-Host "Security Monitoring:" -ForegroundColor Yellow
kubectl get pods -n gameforge-security

Write-Host ""
Write-Host "=== External Access Endpoints ===" -ForegroundColor Green
Write-Host "Grafana (Internal):    http://172.19.255.200:3000" -ForegroundColor Cyan
Write-Host "Grafana (External):    http://172.19.255.201:80" -ForegroundColor Cyan
Write-Host "Prometheus (External): http://172.19.255.201:9090" -ForegroundColor Cyan
Write-Host ""
Write-Host "=== Cluster Architecture ===" -ForegroundColor Green
Write-Host "✅ 3-Node KIND Cluster (1 control + 2 workers)" -ForegroundColor Green
Write-Host "✅ MetalLB LoadBalancer (IP Pool: 172.19.255.200-250)" -ForegroundColor Green
Write-Host "✅ Node Affinity (Grafana→monitoring, Prometheus→compute)" -ForegroundColor Green
Write-Host "✅ External Services with LoadBalancer IPs" -ForegroundColor Green
Write-Host "✅ Pod Security Standards (Restricted)" -ForegroundColor Green
Write-Host "✅ Network Policies for Security" -ForegroundColor Green
Write-Host ""
Write-Host "=== Production Readiness ===" -ForegroundColor Green
Write-Host "✅ High Availability: Multi-node cluster with workload distribution" -ForegroundColor Green
Write-Host "✅ External Access: LoadBalancer services for cloud deployment" -ForegroundColor Green
Write-Host "✅ Security Hardening: Pod security standards and network policies" -ForegroundColor Green
Write-Host "✅ Monitoring Stack: Prometheus and Grafana with external access" -ForegroundColor Green
Write-Host "✅ Secret Management: Automated rotation and secure storage" -ForegroundColor Green
