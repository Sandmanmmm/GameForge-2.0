# GameForge Production Secrets Management

## 🚀 Complete Deployment Guide

This repository contains a comprehensive production-ready secrets management system for GameForge, built with HashiCorp Vault, Docker Swarm, and enterprise security best practices.

## 📋 System Overview

### Architecture Components

- **HashiCorp Vault Cluster**: High-availability secret storage with Consul backend
- **Docker Swarm Secrets**: Native Docker secrets integration with Vault
- **SSL/TLS Automation**: Let's Encrypt certificate management
- **Monitoring Stack**: Prometheus, Grafana, ELK stack for observability
- **Automated Rotation**: Scheduled secret rotation with audit logging
- **Backup & Recovery**: Encrypted backups with S3 integration

### Security Features

- ✅ Vault cluster with HA and automatic unsealing
- ✅ Fine-grained access policies and authentication
- ✅ Automatic secret rotation with zero-downtime
- ✅ Encrypted secret storage and transmission
- ✅ Comprehensive audit logging and monitoring
- ✅ Disaster recovery and backup procedures

## 🏗️ Quick Start

### Prerequisites

```bash
# Required tools
- Docker Engine 20.10+
- Docker Compose 2.0+
- Vault CLI 1.15+
- OpenSSL
- jq
- curl

# System requirements
- 4GB+ RAM
- 20GB+ disk space
- Network access for Let's Encrypt
```

### 1. Environment Setup

```bash
# Clone and navigate to project
git clone <repository-url>
cd gameforge-production

# Set environment
export ENVIRONMENT=production
export VAULT_ADDR=http://vault-primary:8200

# Configure environment variables
cp secrets/config/production.env.example secrets/config/production.env
# Edit with your specific settings
```

### 2. Complete Deployment

```bash
# Full production deployment
./deploy-secrets-production.sh

# Or step-by-step deployment
DEPLOYMENT_MODE=secrets-only ./deploy-secrets-production.sh
DEPLOYMENT_MODE=apps-only ./deploy-secrets-production.sh
```

### 3. Verify Deployment

```bash
# Run health checks
./secrets/vault/scripts/health-check-secrets.sh

# Generate deployment summary
python3 secrets/scripts/deployment-summary.py --detailed

# Test secret access
vault kv get secret/gameforge/database
```

## 📖 Detailed Documentation

### Directory Structure

```
gameforge-production/
├── secrets/
│   ├── config/                 # Environment configurations
│   ├── vault/
│   │   ├── config/            # Vault and Consul configurations
│   │   ├── policies/          # Vault access policies
│   │   └── scripts/           # Management scripts
│   ├── docker/                # Docker integration
│   └── scripts/               # Deployment and maintenance
├── ssl/                       # SSL/TLS configurations
├── monitoring/                # Monitoring configurations
└── docker-compose.*.yml       # Service definitions
```

### Key Files

| File | Purpose |
|------|---------|
| `deploy-secrets-production.sh` | Master deployment script |
| `secrets/scripts/init-secrets.sh` | Initial Vault setup |
| `secrets/scripts/backup-vault.sh` | Automated backup |
| `secrets/scripts/recover-vault.sh` | Disaster recovery |
| `secrets/vault/scripts/rotate-secrets.sh` | Secret rotation |
| `secrets/vault/scripts/health-check-secrets.sh` | Health monitoring |

## 🔧 Configuration

### Environment Variables

```bash
# Vault Configuration
VAULT_ADDR=http://vault-primary:8200
VAULT_CLUSTER_ADDR=http://vault-primary:8201

# Security Settings
SECRET_ROTATION_ENABLED=true
SECRET_ROTATION_INTERVAL=24h
ENCRYPTION_KEY=your-encryption-key

# Monitoring
METRICS_ENABLED=true
SLACK_WEBHOOK_URL=your-slack-webhook

# SSL/TLS
SSL_ENABLED=true
LETSENCRYPT_EMAIL=admin@yourdomain.com
```

### Secret Mappings

Edit `secrets/docker/configs/secret-mappings.json`:

```json
{
  "database": {
    "vault_path": "secret/gameforge/database",
    "docker_secrets": {
      "username": "gameforge_postgres_user",
      "password": "gameforge_postgres_password"
    },
    "rotation_enabled": true
  }
}
```

## 🔐 Secret Management

### Adding New Secrets

```bash
# Store secret in Vault
vault kv put secret/gameforge/new-service \
    api_key="your-api-key" \
    secret_token="your-token"

# Update secret mappings
# Add to secrets/docker/configs/secret-mappings.json

# Trigger sync
docker kill -s SIGUSR1 $(docker ps -q -f name=vault-docker-bridge)
```

### Secret Rotation

```bash
# Manual rotation
./secrets/vault/scripts/rotate-secrets.sh

# Dry run to see what would be rotated
./secrets/vault/scripts/rotate-secrets.sh --dry-run

# Check rotation status
vault kv get secret/gameforge/database | grep rotated_at
```

### Backup and Recovery

```bash
# Create backup
./secrets/scripts/backup-vault.sh

# List available backups
./secrets/scripts/backup-vault.sh --list-backups

# Restore from backup
./secrets/scripts/recover-vault.sh /path/to/backup.tar.gz.enc

# Interactive restore
./secrets/scripts/recover-vault.sh backup.tar.gz --interactive
```

## 📊 Monitoring and Alerting

### Health Checks

```bash
# Run comprehensive health check
./secrets/vault/scripts/health-check-secrets.sh

# Continuous monitoring
python3 secrets/docker/health_check.py --continuous

# JSON output for automation
./secrets/vault/scripts/health-check-secrets.sh --json
```

### Prometheus Metrics

Available metrics:
- `gameforge_vault_response_time_seconds`
- `gameforge_secrets_accessible_total`
- `gameforge_health_score_percent`
- `gameforge_vault_sealed`

Access metrics: `http://localhost:8080/metrics`

### Grafana Dashboards

- Vault Health Dashboard
- Secret Access Patterns
- Security Audit Dashboard
- System Performance

Access: `http://localhost:3000` (admin/admin)

## 🚨 Troubleshooting

### Common Issues

#### Vault Sealed

```bash
# Check Vault status
vault status

# Unseal if needed
./secrets/scripts/init-secrets.sh --unseal
```

#### Secrets Not Accessible

```bash
# Check Vault authentication
vault auth -method=token

# Verify secret exists
vault kv list secret/gameforge/

# Check Docker secrets
docker secret ls
```

#### SSL Certificate Issues

```bash
# Check certificate status
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -text -noout

# Renew certificates
docker exec certbot certbot renew --dry-run
```

### Debug Mode

```bash
# Enable debug logging
export VAULT_LOG_LEVEL=debug
export DEBUG=true

# Run with verbose output
./deploy-secrets-production.sh --dry-run
```

## 🔄 Maintenance

### Regular Tasks

1. **Daily**: Run health checks
2. **Weekly**: Review audit logs
3. **Monthly**: Test backup/recovery
4. **Quarterly**: Rotate root credentials

### Scheduled Jobs

```bash
# Add to crontab
0 2 * * * /path/to/secrets/scripts/backup-vault.sh
0 */6 * * * /path/to/secrets/vault/scripts/health-check-secrets.sh
0 3 * * 0 /path/to/secrets/vault/scripts/rotate-secrets.sh
```

## 🛡️ Security Best Practices

### Access Control

1. Use least-privilege access policies
2. Regularly audit access logs
3. Implement multi-factor authentication
4. Rotate credentials regularly

### Network Security

1. Use private networks for internal communication
2. Implement firewall rules
3. Enable TLS for all connections
4. Monitor network traffic

### Operational Security

1. Secure backup storage
2. Implement change management
3. Regular security assessments
4. Incident response procedures

## 📚 Advanced Configuration

### High Availability

For production HA setup:

```bash
# Deploy Vault cluster
docker stack deploy -c docker-compose.vault.yml vault-cluster

# Configure auto-unseal with cloud KMS
vault write sys/seal-config type=awskms key_id=your-kms-key
```

### Performance Tuning

```bash
# Adjust Vault performance
vault write sys/config/performance/replication \
    mode=performance \
    secondary_token=your-token

# Database connection pooling
vault write database/config/postgresql \
    max_open_connections=10 \
    max_idle_connections=5
```

### Integration Examples

#### Kubernetes Integration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gameforge-database
type: Opaque
data:
  username: {{ vault_kv_get "secret/gameforge/database" "username" | b64enc }}
  password: {{ vault_kv_get "secret/gameforge/database" "password" | b64enc }}
```

#### CI/CD Integration

```bash
# GitHub Actions example
- name: Deploy with secrets
  env:
    VAULT_ADDR: ${{ secrets.VAULT_ADDR }}
    VAULT_TOKEN: ${{ secrets.VAULT_TOKEN }}
  run: ./deploy-secrets-production.sh
```

## 🆘 Support and Contributing

### Getting Help

1. Check troubleshooting section
2. Review logs: `docker-compose logs -f`
3. Run diagnostics: `./secrets/scripts/deployment-summary.py`
4. Contact support team

### Contributing

1. Fork the repository
2. Create feature branch
3. Test changes thoroughly
4. Submit pull request

### License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📞 Emergency Procedures

### Disaster Recovery

1. **Assess Impact**: Run health checks
2. **Isolate Issue**: Stop affected services
3. **Restore from Backup**: Use recovery scripts
4. **Validate Recovery**: Run full test suite
5. **Document Incident**: Update runbooks

### Emergency Contacts

- **Security Team**: security@gameforge.com
- **DevOps Team**: devops@gameforge.com
- **On-Call**: +1-555-GAMEFORGE

---

*Last Updated: $(date)*
*Version: 1.0.0*
*Environment: Production*
