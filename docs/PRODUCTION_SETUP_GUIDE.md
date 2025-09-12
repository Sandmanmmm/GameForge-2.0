
# GameForge Production Docker Setup Instructions

## Prerequisites
1. **Docker Desktop** with WSL2 backend (Windows) or Docker Engine (Linux)
2. **NVIDIA Container Toolkit** for GPU support
3. **Docker Compose** v2.0+
4. **Git** for version control

## Quick Start Guide

### 1. Environment Configuration
```bash
# Copy the environment template
cp .env.production.template .env.production

# Edit the environment file with your actual values
# - Set strong passwords for DB_PASSWORD and JWT_SECRET
# - Configure your API keys (OpenAI, Replicate, etc.)
# - Set backup S3 bucket if using backups
```

### 2. SSL Configuration (Optional but Recommended)
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificates for testing
openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes
```

### 3. Deploy Production Stack
```bash
# For Linux/macOS
./scripts/deploy-production.sh

# For Windows
scripts\deploy-production.bat
```

### 4. Verify Deployment
- **API Health**: http://localhost/health
- **Grafana**: http://localhost:3000 (admin/your_grafana_password)
- **Prometheus**: http://localhost:9090
- **API Documentation**: http://localhost/docs

## Security Features Implemented

✅ **Container Security**
- Non-root user execution
- Dropped capabilities
- No new privileges
- Security contexts

✅ **Network Security**
- Isolated Docker network
- Rate limiting (10 req/s for API, 30 req/s for assets)
- SSL/TLS support
- Security headers

✅ **Data Security**
- Encrypted environment variables
- Secure password handling
- Database backup encryption
- JWT token security

✅ **Monitoring & Observability**
- Prometheus metrics collection
- Grafana dashboards
- Health checks for all services
- Log aggregation with ELK stack

## Production Optimizations

🚀 **Performance**
- Multi-stage Docker builds
- Image layer caching
- Resource limits and reservations
- GPU memory optimization
- Redis caching with LRU eviction

🔄 **Scalability**
- Horizontal scaling ready
- Load balancing with Nginx
- Background worker processes
- Queue-based job processing

💾 **Data Persistence**
- Named volumes for data
- Automated daily backups
- S3 backup storage
- 15-day metric retention

## Monitoring Dashboards

The production setup includes pre-configured monitoring:

1. **System Metrics**: CPU, Memory, Disk, Network
2. **Application Metrics**: API response times, error rates
3. **Business Metrics**: User requests, model usage
4. **Security Metrics**: Failed logins, rate limit hits

## Backup Strategy

📋 **Automated Backups**
- Daily PostgreSQL dumps
- Compressed and encrypted backups
- S3 upload for off-site storage
- 7-day local retention
- Point-in-time recovery capability

## Troubleshooting

### Common Issues

1. **GPU Not Available**
   ```bash
   # Check NVIDIA runtime
   docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
   ```

2. **Permission Denied**
   ```bash
   # Fix script permissions
   chmod +x scripts/*.sh
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using the port
   netstat -tlnp | grep :80
   ```

4. **Memory Issues**
   ```bash
   # Check Docker resources
   docker system df
   docker system prune
   ```

### Service Logs
```bash
# View all service logs
docker-compose -f docker-compose.production-secure.yml logs

# View specific service logs
docker-compose -f docker-compose.production-secure.yml logs gameforge-api
```

## Production Checklist

Before going live, ensure:

- [ ] Environment variables are properly configured
- [ ] SSL certificates are installed and valid
- [ ] Database is backed up and restore tested
- [ ] Monitoring alerts are configured
- [ ] Security scanning completed
- [ ] Load testing performed
- [ ] Documentation updated
- [ ] Team has access to monitoring dashboards
