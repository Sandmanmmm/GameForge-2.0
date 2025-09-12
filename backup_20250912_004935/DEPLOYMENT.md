# GameForge Production Deployment Checklist

## Pre-Deployment Checklist

### 🔧 Environment Setup
- [ ] Verify Docker and Docker Compose are installed
- [ ] Confirm system meets minimum requirements:
  - [ ] RAM: 16GB+ (32GB recommended)
  - [ ] Storage: 100GB+ free space
  - [ ] CPU: 8+ cores recommended
- [ ] Check network ports are available:
  - [ ] Port 80 (HTTP)
  - [ ] Port 443 (HTTPS)
  - [ ] Port 3000 (Grafana)
  - [ ] Port 9090 (Prometheus)

### 🔐 Security Configuration
- [ ] Set production environment variables in `.env.production`:
  - [ ] `POSTGRES_PASSWORD` - Strong database password
  - [ ] `JWT_SECRET` - 256-bit random secret key
  - [ ] `JWT_REFRESH_SECRET` - Different 256-bit random secret
  - [ ] `ENCRYPTION_KEY` - 32-byte encryption key
  - [ ] `SESSION_SECRET` - Strong session secret
- [ ] Configure SSL certificates:
  - [ ] Obtain SSL certificate for domain
  - [ ] Update nginx configuration with cert paths
  - [ ] Test SSL configuration
- [ ] Review CORS origins in environment file
- [ ] Set up proper firewall rules
- [ ] Configure rate limiting settings

### 📊 Database Setup
- [ ] Verify PostgreSQL 17.4+ is configured
- [ ] Database backup strategy in place
- [ ] Connection pooling configured
- [ ] Database user permissions set correctly
- [ ] Prisma schema migrations ready

### 🚀 Redis Configuration
- [ ] Redis/Memurai 7.2+ installed and running
- [ ] Memory allocation configured (recommend 4GB+)
- [ ] Persistence settings configured
- [ ] Queue monitoring enabled

### 🔍 Monitoring Setup
- [ ] Prometheus configuration reviewed
- [ ] Grafana dashboard imported
- [ ] Alert rules configured
- [ ] Notification channels set up (email, Slack, etc.)
- [ ] Log aggregation configured

### 🧪 Testing
- [ ] Run unit tests: `npm test`
- [ ] Run integration tests: `npm run test:integration`
- [ ] Load testing completed
- [ ] Security scanning performed
- [ ] Database migration tested

## Deployment Steps

### 1. Pre-Deployment
```powershell
# Clone/update repository
git pull origin main

# Set environment variables
$env:POSTGRES_PASSWORD = "your-secure-password"
$env:JWT_SECRET = "your-jwt-secret"
# ... set other required variables

# Verify configuration
docker-compose -f docker-compose.prod.yml config
```

### 2. Deploy
```powershell
# Run deployment script
.\deploy.ps1
```

### 3. Post-Deployment Verification
- [ ] All containers are running: `docker-compose ps`
- [ ] Health checks pass: 
  - [ ] Backend: http://localhost:3001/api/health
  - [ ] Frontend: http://localhost/
  - [ ] Database: Connection test
- [ ] Monitor logs for errors: `docker-compose logs -f`
- [ ] Verify metrics in Grafana: http://localhost:3000/
- [ ] Test user registration and login
- [ ] Test asset generation pipeline
- [ ] Verify WebSocket connections
- [ ] Check job queue processing

## Production URLs
- **Frontend Application**: http://localhost/ (or your domain)
- **Backend API**: http://localhost:3001/
- **API Documentation**: http://localhost:3001/api/docs
- **Grafana Dashboard**: http://localhost:3000/ (admin/admin)
- **Prometheus Metrics**: http://localhost:9090/
- **Health Check**: http://localhost:3001/api/health

## Default Credentials
⚠️ **CHANGE THESE IN PRODUCTION!**
- **Grafana**: admin/admin
- **Database**: gameforge_user/(from POSTGRES_PASSWORD)

## Backup Strategy
- **Database**: Automated daily backups to `./backups/`
- **Upload Files**: Included in backup script
- **Configuration**: Version controlled in Git
- **Recovery**: Use backup files with restore script

## Monitoring Alerts
- Backend API downtime
- High response times (>2s)
- Error rates (>10%)
- Database connection issues
- High resource usage (CPU >80%, Memory >90%)
- Queue processing delays
- Container restarts

## Scaling Considerations
- **Horizontal Scaling**: Add more backend containers
- **Database**: Consider read replicas for high load
- **Redis**: Cluster mode for high availability
- **Load Balancing**: nginx can handle multiple backend instances
- **CDN**: Consider CloudFlare or AWS CloudFront for static assets

## Troubleshooting

### Common Issues
1. **Port conflicts**: Check if ports are already in use
2. **Memory issues**: Ensure sufficient RAM allocation
3. **Database connection**: Verify credentials and network
4. **SSL errors**: Check certificate paths and permissions
5. **Queue not processing**: Verify Redis connection

### Debug Commands
```powershell
# Check container logs
docker-compose -f docker-compose.prod.yml logs [service-name]

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Access container shell
docker-compose -f docker-compose.prod.yml exec [service-name] /bin/bash

# View resource usage
docker stats

# Check network connectivity
docker-compose -f docker-compose.prod.yml exec backend ping postgres
```

## Rollback Plan
1. Stop current deployment: `docker-compose -f docker-compose.prod.yml down`
2. Restore from backup: Use latest backup in `./backups/`
3. Start previous version: `docker-compose -f docker-compose.prod.yml up -d`
4. Verify system health

## Support Contacts
- **Technical Lead**: [Your contact info]
- **Infrastructure**: [Infrastructure contact]
- **Emergency**: [Emergency contact]

---
**Last Updated**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Version**: 1.0.0
