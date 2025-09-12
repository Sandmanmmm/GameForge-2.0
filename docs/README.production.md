# GameForge Production Deployment Guide

## 🚀 Quick Start

1. **Configure Environment**:
   ```bash
   cp .env.production.secure .env.production
   # Edit .env.production with your secure credentials
   ```

2. **Deploy**:
   ```bash
   chmod +x scripts/deploy-production.sh
   ./scripts/deploy-production.sh
   ```

3. **Verify**:
   ```bash
   chmod +x scripts/health-check.sh
   ./scripts/health-check.sh
   ```

## 📊 Service URLs

- **Application**: https://localhost
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🔧 Management Commands

### Service Management
```bash
# Start all services
docker-compose -f docker-compose.production-secure.yml up -d

# Stop all services
docker-compose -f docker-compose.production-secure.yml down

# View logs
docker-compose -f docker-compose.production-secure.yml logs -f [service]

# Scale workers
docker-compose -f docker-compose.production-secure.yml up -d --scale gameforge-worker=3
```

### Database Operations
```bash
# Run migrations
docker-compose -f docker-compose.production-secure.yml exec gameforge-api python manage.py migrate

# Create backup
docker-compose -f docker-compose.production-secure.yml exec postgres pg_dump -U gameforge gameforge_production > backup.sql

# Restore backup
docker-compose -f docker-compose.production-secure.yml exec -T postgres psql -U gameforge -d gameforge_production < backup.sql
```

### Monitoring
```bash
# View system resources
docker stats

# Check service health
./scripts/health-check.sh

# View application metrics
curl http://localhost/metrics
```

## 🔒 Security Features

- ✅ Multi-stage Docker builds with minimal attack surface
- ✅ Non-root containers with dropped capabilities
- ✅ SSL/TLS termination with security headers
- ✅ Rate limiting and DDoS protection
- ✅ Secrets management with secure environment variables
- ✅ Network isolation between services
- ✅ Regular security updates via automated rebuilds

## 📈 Monitoring & Observability

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Elasticsearch**: Log aggregation and search
- **Custom metrics**: API performance, GPU usage, user activity

## 💾 Backup Strategy

- **Automated daily backups** to S3
- **15-day retention policy**
- **Point-in-time recovery** capability
- **Backup verification** and integrity checks

## 🔧 Troubleshooting

### Common Issues

1. **Services not starting**:
   ```bash
   docker-compose -f docker-compose.production-secure.yml logs [service]
   ```

2. **Database connection issues**:
   ```bash
   docker-compose -f docker-compose.production-secure.yml exec postgres pg_isready -U gameforge
   ```

3. **High memory usage**:
   ```bash
   docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
   ```

### Performance Tuning

- **GPU Memory**: Adjust `PYTORCH_CUDA_ALLOC_CONF` in environment
- **Worker Scaling**: Scale workers based on CPU/memory usage
- **Database**: Tune PostgreSQL settings for your workload
- **Redis**: Adjust memory policies and persistence settings

## 🎯 Production Checklist

- [ ] Environment variables configured with secure passwords
- [ ] SSL certificates installed and configured
- [ ] Backup strategy implemented and tested
- [ ] Monitoring dashboards configured
- [ ] Log aggregation working
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Security scan completed
- [ ] Disaster recovery plan documented
- [ ] Team trained on operations procedures

## 📞 Support

For production support and troubleshooting, check:
- Application logs: `docker-compose logs gameforge-api`
- System metrics: Grafana dashboard
- Error tracking: Sentry (if configured)
- Performance monitoring: Prometheus alerts
