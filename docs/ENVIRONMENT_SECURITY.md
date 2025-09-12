# Environment Security Guide
===============================

## 🚨 **CRITICAL: Environment Variables Security**

This project uses environment variables for sensitive configuration. **NEVER commit real secrets to git.**

## 📋 **Quick Setup**

### **Development Environment**
```bash
# 1. Copy the example file
cp .env.example .env
cp docker.env.example docker.env

# 2. Edit with your development values
# Use SECURE, RANDOM values - never use defaults!
```

### **Production Environment**
```bash
# Use environment variables or secrets management
export POSTGRES_PASSWORD="$(openssl rand -base64 32)"
export JWT_SECRET_KEY="$(openssl rand -base64 64)"
export VAULT_TOKEN="$(vault write -field=token auth/aws/login role=gameforge)"
```

## 🔐 **Required Secrets**

### **Database Secrets**
- `POSTGRES_PASSWORD`: Strong password (min 16 chars)
- `POSTGRES_USER`: Database username
- `POSTGRES_DB`: Database name

### **Application Secrets**
- `JWT_SECRET_KEY`: JWT signing key (min 32 chars, random)
- `SECRET_KEY`: Application secret key (min 32 chars, random)

### **Phase 4: Vault Secrets**
- `VAULT_ROOT_TOKEN`: Vault root access token
- `VAULT_TOKEN`: Application vault access token

### **Phase 4: Storage Secrets**
- `AWS_ACCESS_KEY_ID`: S3/MinIO access key
- `AWS_SECRET_ACCESS_KEY`: S3/MinIO secret key
- `MODEL_S3_BUCKET`: Model storage bucket name

## 🛡️ **Security Best Practices**

### **✅ DO**
- Use `.env.example` as template
- Generate random secrets: `openssl rand -base64 32`
- Use environment variables in production
- Rotate secrets regularly
- Use HashiCorp Vault for production secrets

### **❌ DON'T**
- Commit `.env` files with real secrets
- Use default or predictable passwords
- Share secrets in chat/email
- Hardcode secrets in source code

## 🚀 **Production Deployment**

### **Option 1: Environment Variables**
```yaml
# docker-compose.production.yml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  JWT_SECRET_KEY: ${JWT_SECRET_KEY}
  VAULT_TOKEN: ${VAULT_TOKEN}
```

### **Option 2: Docker Secrets**
```yaml
# docker-compose.production-hardened.yml
secrets:
  postgres_password:
    external: true
  jwt_secret:
    external: true
services:
  gameforge-app:
    secrets:
      - postgres_password
      - jwt_secret
```

### **Option 3: HashiCorp Vault** (Recommended)
```bash
# Store secrets in Vault
vault kv put secret/gameforge \
  postgres_password="$(openssl rand -base64 32)" \
  jwt_secret="$(openssl rand -base64 64)"

# Application retrieves from Vault using VAULT_TOKEN
```

## 🔍 **Security Verification**

Run our Phase 1 security scan to check for exposed secrets:
```bash
# Linux/macOS
make phase1

# Windows
.\scripts\phase1-demo.ps1
```

## 🆘 **Emergency: Secrets Exposed**

If secrets are accidentally committed:

1. **Immediate Action**:
   ```bash
   # Change all exposed secrets immediately
   # Rotate database passwords
   # Generate new JWT keys
   # Revoke and recreate vault tokens
   ```

2. **Git History Cleanup**:
   ```bash
   # Remove from git history (dangerous!)
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Force Push** (after team coordination):
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

## 📞 **Support**

- Security issues: Contact security team immediately
- Documentation: See `PHASE1_IMPLEMENTATION.md`
- Vault setup: See `docker-compose.production-hardened.yml`

---
**⚠️ Remember: When in doubt, treat it as a secret and protect it!**
