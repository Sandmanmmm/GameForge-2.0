# GameForge RTX 4090 Production Deployment Guide
# Updated with Docker fixes and port handling

## Quick Start (Recommended)

### Option 1: Automated Script
```bash
# Copy the startup script to RTX 4090
scp start_gameforge_rtx4090.sh root@108.172.120.126:/workspace/

# Make it executable and run
ssh root@108.172.120.126 "chmod +x /workspace/start_gameforge_rtx4090.sh && /workspace/start_gameforge_rtx4090.sh"
```

### Option 2: Manual Steps
```bash
# SSH into RTX 4090
ssh root@108.172.120.126

# Start Docker daemon
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker is working
docker --version
docker info

# Check port availability
netstat -tuln | grep :8080

# If port 8080 is busy, use 8081
python gameforge_production_deployer.py --port 8081

# Or use default port 8080 if available
python gameforge_production_deployer.py
```

## Files to Copy to RTX 4090

1. **gameforge_production_deployer.py** - Main deployment service
2. **requirements_production_deployer.txt** - Python dependencies  
3. **start_gameforge_rtx4090.sh** - Automated startup script
4. **docker-compose.production-hardened.yml** - Production stack configuration

## Copy Commands
```bash
# Copy all required files
scp gameforge_production_deployer.py root@108.172.120.126:/workspace/
scp requirements_production_deployer.txt root@108.172.120.126:/workspace/
scp start_gameforge_rtx4090.sh root@108.172.120.126:/workspace/
scp docker/compose/docker-compose.production-hardened.yml root@108.172.120.126:/workspace/
```

## Installation on RTX 4090
```bash
# Install Python dependencies
pip install -r requirements_production_deployer.txt

# Start the deployer (will auto-detect available port)
python gameforge_production_deployer.py
```

## API Endpoints
- **Health Check**: http://108.172.120.126:8080/health
- **API Documentation**: http://108.172.120.126:8080/docs
- **Deploy Stack**: POST http://108.172.120.126:8080/deploy
- **Stack Status**: GET http://108.172.120.126:8080/status
- **Service Logs**: GET http://108.172.120.126:8080/logs/{service_name}

## Troubleshooting

### Docker Issues
```bash
# If Docker fails to start
sudo systemctl status docker
sudo journalctl -u docker

# Restart Docker
sudo systemctl restart docker
```

### Port Issues
```bash
# Check what's using port 8080
netstat -tuln | grep :8080
lsof -i :8080

# Use alternative port
python gameforge_production_deployer.py --port 8081
```

### Service Issues
```bash
# Check service logs
docker-compose -f docker-compose.production-hardened.yml logs
```

## Production Stack Services
The deployer manages these 14 services:
- Traefik (Load Balancer)
- GameForge API
- Frontend
- PostgreSQL + Redis
- GPU Workloads
- Security Services
- Monitoring (Prometheus, Grafana)
- MLflow Tracking

## Success Indicators
✅ Docker daemon running
✅ All 14 services healthy
✅ GPU detected and available
✅ API responding on all endpoints
✅ Web interface accessible