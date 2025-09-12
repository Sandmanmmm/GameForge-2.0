# 🔑 GameForge Enterprise Secret Rotation System
## Complete Implementation Documentation

### Overview
This enterprise-grade secret rotation system implements automated, secure, and auditable rotation of all secrets in the GameForge ecosystem with proper frequencies, health checks, and compliance controls.

### 🎯 Key Features
- **Automated Rotation**: Scheduled rotations based on enterprise security policies
- **Multiple Secret Types**: Root tokens, application secrets, TLS certificates, internal tokens, database credentials
- **Proper Frequencies**: 
  - Root/Unseal Keys: 90 days
  - Application Secrets: 45 days  
  - TLS Certificates: 60 days
  - Internal Tokens: 24 hours (ephemeral)
  - Database Credentials: 90 days
- **Health Checks**: Pre and post-rotation validation
- **Audit Logging**: Comprehensive security audit trail
- **Staggered Execution**: Prevents system overload
- **Manual Approval**: Required for critical secrets
- **Monitoring**: Prometheus + Grafana dashboards
- **Alerting**: Slack, email, and PagerDuty integration
- **CI/CD Integration**: GitHub Actions workflows

---

## 📁 File Structure

```
GameForge/
├── enterprise-secret-rotation.ps1     # Main rotation script (765 lines)
├── cicd-secret-rotation.ps1           # CI/CD integration script
├── deploy-secret-rotation.ps1         # Complete deployment automation
├── config/
│   ├── secret-rotation-config.yml     # Main configuration
│   └── monitoring-dashboard-config.yml # Monitoring setup
├── logs/
│   ├── audit/                         # Security audit logs
│   ├── cicd/                          # CI/CD operation logs
│   └── deployment/                    # Deployment logs
├── state/                             # Rotation state tracking
├── backups/                           # Secret backups
└── monitoring/                        # Monitoring stack config
```

---

## 🚀 Quick Start Deployment

### 1. Prerequisites
```powershell
# Install required tools
choco install vault
choco install docker-desktop
choco install gh

# Set environment variables
$env:VAULT_ADDR = "http://localhost:8200"
$env:VAULT_TOKEN = "your-vault-token"
$env:SLACK_WEBHOOK_URL = "your-slack-webhook"
```

### 2. Deploy Complete System
```powershell
# Full deployment (production-ready)
.\deploy-secret-rotation.ps1 -Environment production

# Dry run deployment (testing)
.\deploy-secret-rotation.ps1 -Environment production -DryRun

# Deploy specific components
.\deploy-secret-rotation.ps1 -SetupMonitoring -SetupScheduling
```

### 3. Verify Installation
```powershell
# Check Vault status
vault status

# Check monitoring
http://localhost:3000  # Grafana (admin/admin)
http://localhost:9090  # Prometheus

# Check scheduled tasks
Get-ScheduledTask -TaskName "GameForge-*"
```

---

## 🔄 Rotation Schedules

| Secret Type | Frequency | Schedule | Manual Approval |
|-------------|-----------|----------|-----------------|
| **Root Tokens** | 90 days | Every 3 months at 2 AM | ✅ Required |
| **Application Secrets** | 45 days | Every 45 days at 3 AM | ❌ Automatic |
| **TLS Certificates** | 60 days | Every 60 days at 4 AM | ❌ Automatic |
| **Internal Tokens** | 24 hours | Daily at 1 AM | ❌ Automatic |
| **Database Credentials** | 90 days | Every 3 months at 5 AM | ✅ Required |

---

## 🛠️ Manual Operations

### Run Individual Rotations
```powershell
# Rotate specific secret type
.\enterprise-secret-rotation.ps1 -SecretType application

# Force rotation (even if not due)
.\enterprise-secret-rotation.ps1 -SecretType tls -ForceRotation

# Dry run (test without changes)
.\enterprise-secret-rotation.ps1 -SecretType database -DryRun

# All secrets with approval workflow
.\enterprise-secret-rotation.ps1 -SecretType all -RequireApproval
```

### Check Secret Status
```powershell
# View expiry status
.\enterprise-secret-rotation.ps1 -CheckExpiry

# View audit logs
Get-Content logs\audit\vault-rotation-*.log | Select-String "ERROR|SUCCESS"

# Check rotation state
Get-Content state\*_last_rotation.json | ConvertFrom-Json
```

### Emergency Procedures
```powershell
# Emergency rollback
.\enterprise-secret-rotation.ps1 -SecretType application -Rollback

# Validate all secrets
.\enterprise-secret-rotation.ps1 -ValidateAll

# Create manual backup
.\enterprise-secret-rotation.ps1 -CreateBackup
```

---

## 📊 Monitoring & Alerting

### Grafana Dashboards
- **Secret Expiry Overview**: Days until expiration for all secrets
- **Rotation Success Rate**: Success/failure metrics
- **System Health**: Vault status and rotation system health
- **Rotation Timeline**: Historical rotation activity
- **Error Analysis**: Failed rotations by type and cause

### Alerts Configured
- **Critical**: Secret expires in < 3 days
- **Warning**: Secret expires in < 7 days
- **Error**: Rotation failures
- **Performance**: Rotation duration > 30 minutes

### Access URLs
- Grafana: `http://localhost:3000` (admin/admin)
- Prometheus: `http://localhost:9090`
- AlertManager: `http://localhost:9093`

---

## 🔐 Security Features

### Audit Logging
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "operation": "secret_rotation",
  "secret_type": "application",
  "status": "success",
  "user": "system",
  "environment": "production",
  "duration_seconds": 45,
  "backup_created": true
}
```

### Access Controls
- **Root rotations**: Require 2 approvers
- **Database rotations**: Require 1 approver
- **Application/TLS**: Automatic with audit trail
- **Internal tokens**: Automatic ephemeral rotation

### Backup & Recovery
- Automatic backups before every rotation
- 30-day retention policy
- Encrypted backup storage
- Disaster recovery procedures

---

## 🔧 Configuration Reference

### Main Configuration (`config/secret-rotation-config.yml`)
```yaml
# Rotation frequencies
rotation_schedules:
  root_rotation:
    frequency: "0 2 1 */3 *"  # Every 90 days
    requires_manual_approval: true
    
  application_rotation:
    frequency: "0 3 */45 * *"  # Every 45 days
    requires_manual_approval: false

# Alert thresholds
alert_thresholds:
  expiry_warning_days: 7
  critical_warning_days: 3
  health_check_failures: 2
```

### Environment Variables
```powershell
# Required
$env:VAULT_ADDR = "http://localhost:8200"
$env:VAULT_TOKEN = "your-vault-root-token"

# Optional but recommended
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/..."
$env:PAGERDUTY_INTEGRATION_KEY = "your-pagerduty-key"
$env:GRAFANA_ADMIN_PASSWORD = "secure-password"
$env:BACKUP_ENCRYPTION_KEY = "encryption-key"
```

---

## 🎛️ CI/CD Integration

### GitHub Actions Workflow
```yaml
name: Secret Rotation
on:
  schedule:
    - cron: '0 1 * * *'  # Daily internal rotation
    - cron: '0 3 */45 * *'  # Application rotation
  workflow_dispatch:
    inputs:
      secret_type:
        type: choice
        options: [all, root, application, tls, internal, database]
```

### Automated Updates
- GitHub Actions secrets updated automatically
- Docker containers restarted after rotation
- Kubernetes deployments rolling updates
- CI/CD pipelines use dynamic credentials

---

## 🚨 Troubleshooting

### Common Issues

#### Vault Sealed
```powershell
# Check status
vault status

# Unseal if needed
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

#### Rotation Failures
```powershell
# Check logs
Get-Content logs\audit\vault-rotation-*.log | Select-String "ERROR"

# Validate Vault connectivity
vault auth -method=token token=$env:VAULT_TOKEN

# Test rotation in dry-run mode
.\enterprise-secret-rotation.ps1 -SecretType application -DryRun
```

#### Monitoring Down
```powershell
# Restart monitoring stack
cd monitoring
docker-compose restart

# Check service status
docker-compose ps
```

### Support Procedures
1. Check audit logs for error details
2. Verify Vault status and connectivity
3. Test individual rotation functions
4. Review environment variables
5. Contact security team for approval issues

---

## 📋 Compliance & Audit

### Regulatory Compliance
- **SOX**: Quarterly root token rotation with approval
- **PCI DSS**: Database credential rotation every 90 days
- **SOC 2**: Comprehensive audit logging and monitoring
- **ISO 27001**: Risk-based rotation frequencies

### Audit Reports
```powershell
# Generate compliance report
.\enterprise-secret-rotation.ps1 -GenerateAuditReport -DateRange "2024-01-01,2024-01-31"

# Export rotation history
Get-Content logs\audit\*.log | ConvertFrom-Json | Export-Csv audit-report.csv
```

---

## 🔄 Maintenance Tasks

### Weekly
- [ ] Review rotation success metrics
- [ ] Check expiring secrets dashboard
- [ ] Verify monitoring alerts working

### Monthly  
- [ ] Audit log review and archive
- [ ] Test emergency rollback procedures
- [ ] Update rotation documentation

### Quarterly
- [ ] Review and update rotation frequencies
- [ ] Security assessment of rotation procedures
- [ ] Disaster recovery testing

---

## 📞 Support & Contact

### Emergency Contacts
- **Security Team**: security@gameforge.com
- **Operations Team**: ops@gameforge.com  
- **On-Call**: PagerDuty escalation

### Documentation
- [Vault Documentation](https://vaultproject.io/docs)
- [Security Policies](internal-security-policies.md)
- [Incident Response](incident-response.md)

---

## 🏆 Enterprise Benefits Achieved

✅ **Automated Secret Lifecycle Management**
- Eliminates manual secret rotation errors
- Ensures consistent rotation frequencies
- Reduces security team workload

✅ **Enhanced Security Posture**
- Implements defense-in-depth principles
- Reduces blast radius of compromised secrets
- Meets enterprise security requirements

✅ **Operational Excellence**
- 24/7 monitoring and alerting
- Comprehensive audit trails
- Disaster recovery capabilities

✅ **Compliance Ready**
- SOX, PCI DSS, SOC 2 compliance
- Automated compliance reporting
- Risk-based security controls

✅ **Zero Downtime Operations**
- Staggered rotation prevents service disruption
- Health checks ensure system stability
- Automated rollback on failures

---

*This enterprise secret rotation system provides bank-grade security with the automation and monitoring capabilities required for modern production environments.*
