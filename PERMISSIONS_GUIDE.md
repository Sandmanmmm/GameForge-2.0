# GameForge File Permissions Guide

## Overview

This document outlines the proper file permissions and ownership for GameForge deployment, ensuring secure operation with non-root users while maintaining proper access controls.

## Permission Structure

### Development Environment (Owner: dev:dev)

| File Type | Path | Permissions | Owner | Purpose |
|-----------|------|-------------|-------|---------|
| Main Application | `gameforge/main.py` | 644 (rw-r--r--) | dev:dev | FastAPI application entry point |
| Core Modules | `gameforge/core/*.py` | 644 (rw-r--r--) | dev:dev | Core business logic |
| API Routers | `gameforge/api/**/*.py` | 644 (rw-r--r--) | dev:dev | API endpoint definitions |
| Source Code | `**/*.py` | 644 (rw-r--r--) | dev:dev | All Python source files |

### Production Environment (Runtime: gameforge user)

| File Type | Permissions | Owner | Runtime User | Notes |
|-----------|-------------|-------|--------------|-------|
| Application Code | 644 | dev:dev | gameforge | Read-only for app user |
| Configuration | 640 | dev:dev | gameforge | Group readable only |
| Secrets | 600 | dev:dev | dev | Owner only access |
| Runtime Data | 755 | gameforge:gameforge | gameforge | App user full control |
| Logs | 755 | gameforge:gameforge | gameforge | App user full control |

## File Permission Details

### Source Code Files (644)
```bash
# Permissions: rw-r--r--
# Owner: read + write
# Group: read only  
# Other: read only
chmod 644 gameforge/main.py
chmod 644 gameforge/core/*.py
chmod 644 gameforge/api/**/*.py
```

**Rationale:**
- Developers can modify source code
- Application can read source code
- No execute permissions on Python files (executed by interpreter)
- World-readable for transparency (no secrets in source)

### Configuration Files (640)
```bash
# Permissions: rw-r-----
# Owner: read + write
# Group: read only
# Other: no access
chmod 640 requirements.txt
chmod 640 docker-compose.yml
chmod 640 .env.example
```

**Rationale:**
- Developers can modify configuration
- Application group can read configuration
- No world access to prevent information disclosure

### Secret Files (600)
```bash
# Permissions: rw-------
# Owner: read + write only
# Group: no access
# Other: no access
chmod 600 .env
chmod 600 *.key
chmod 600 *secret*
```

**Rationale:**
- Only file owner can access secrets
- Prevents accidental disclosure
- Meets security compliance requirements

### Runtime Directories (755)
```bash
# Permissions: rwxr-xr-x
# Owner: full control
# Group: read + execute
# Other: read + execute
chmod 755 logs/
chmod 755 data/
chmod 755 uploads/
chmod 755 cache/
```

**Rationale:**
- Application needs write access for runtime data
- Monitoring tools need read access
- Execute permission for directory traversal

## User and Group Structure

### Development Users
```bash
# Developer user
useradd -m -s /bin/bash dev
usermod -aG dev dev

# Application user (non-login)
useradd -r -s /bin/false -d /opt/gameforge gameforge
```

### Group Memberships
- `dev` group: Developers and deployment tools
- `gameforge` group: Application runtime user
- `docker` group: Container runtime (if using Docker)

## Security Hardening

### 1. Non-Root Execution
```bash
# Application runs as non-root user
User=gameforge
Group=gameforge
SupplementaryGroups=

# Prevent privilege escalation
NoNewPrivileges=yes
```

### 2. Directory Isolation
```bash
# Application working directory
WorkingDirectory=/opt/gameforge

# Read-only root filesystem
ReadOnlyPaths=/
ReadWritePaths=/opt/gameforge/logs
ReadWritePaths=/opt/gameforge/data
ReadWritePaths=/tmp
```

### 3. Capability Restrictions
```bash
# Drop all capabilities
CapabilityBoundingSet=
AmbientCapabilities=

# Restrict system calls
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM
```

## Implementation Scripts

### Linux/Unix (Bash)
```bash
#!/bin/bash
# Run as root for initial setup
./set_permissions.sh production

# For deployment
./deploy_permissions.sh
```

### Windows (PowerShell)
```powershell
# Run as Administrator for initial setup
.\Set-Permissions.ps1 -Environment production

# For deployment  
.\Deploy-Permissions.ps1
```

## Validation Commands

### Check File Permissions
```bash
# Verify main.py permissions
stat -c "%a %n" gameforge/main.py
# Expected: 644 gameforge/main.py

# Verify core module permissions
find gameforge/core -name "*.py" -exec stat -c "%a %n" {} \;
# Expected: 644 for all files

# Verify API router permissions
find gameforge/api -name "*.py" -exec stat -c "%a %n" {} \;
# Expected: 644 for all files
```

### Check Ownership
```bash
# Verify file ownership
ls -la gameforge/main.py
# Expected: -rw-r--r-- dev dev

# Verify runtime directory ownership
ls -la logs/
# Expected: drwxr-xr-x gameforge gameforge
```

## Docker Considerations

### Dockerfile Permissions
```dockerfile
# Create non-root user
RUN groupadd -r gameforge && useradd -r -g gameforge gameforge

# Copy application with correct ownership
COPY --chown=gameforge:gameforge . /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER gameforge

# Expose port (non-privileged)
EXPOSE 8000
```

### Docker Compose Security
```yaml
services:
  gameforge:
    user: gameforge:gameforge
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - ./logs:/app/logs:rw
      - ./data:/app/data:rw
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

## Monitoring and Auditing

### File Integrity Monitoring
```bash
# Create baseline
find gameforge/ -type f -exec sha256sum {} \; > file_integrity.baseline

# Check for changes
find gameforge/ -type f -exec sha256sum {} \; | diff - file_integrity.baseline
```

### Permission Auditing
```bash
# Audit script
#!/bin/bash
echo "=== GameForge Permission Audit ==="

# Check for world-writable files
find . -type f -perm -002 -ls

# Check for files with excessive permissions
find . -type f -perm -066 -ls

# Check for SUID/SGID files
find . -type f \( -perm -4000 -o -perm -2000 \) -ls

echo "=== Audit Complete ==="
```

## Troubleshooting

### Common Permission Issues

1. **Application can't read config files**
   ```bash
   # Solution: Add app user to dev group
   usermod -aG dev gameforge
   ```

2. **Application can't write to logs**
   ```bash
   # Solution: Fix log directory ownership
   chown -R gameforge:gameforge logs/
   chmod 755 logs/
   ```

3. **Deployment script fails**
   ```bash
   # Solution: Run with appropriate privileges
   sudo ./deploy_permissions.sh
   ```

### Permission Reset
```bash
# Reset all permissions to default
./set_permissions.sh production

# Verify after reset
./validate_permissions.sh
```

## Compliance and Standards

### Security Standards Met
- ✅ **Principle of Least Privilege**: Minimal permissions for operation
- ✅ **Non-Root Execution**: Application runs without root privileges
- ✅ **File Integrity**: Read-only application code
- ✅ **Secret Protection**: Restricted access to sensitive files
- ✅ **Audit Trail**: Permission changes are logged

### Compliance Frameworks
- **NIST Cybersecurity Framework**: ID.AM-2 (Asset Management)
- **CIS Controls**: 3.3 (Configure Data Access Control Lists)
- **SOC 2**: CC6.1 (Logical and Physical Access Controls)
- **ISO 27001**: A.9.1.1 (Access Control Policy)

## Summary

The GameForge permission structure follows security best practices:

1. **Source code**: 644 permissions with dev:dev ownership
2. **Runtime**: Non-root execution as gameforge user
3. **Secrets**: Highly restricted 600 permissions
4. **Data**: Isolated runtime directories with appropriate access

This ensures secure deployment while maintaining operational functionality and meeting compliance requirements.

---

**Last Updated**: September 13, 2025  
**Review Schedule**: Monthly security review  
**Contact**: Development team for permission-related issues