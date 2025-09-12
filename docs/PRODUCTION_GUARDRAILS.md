# 🛡️ GameForge Production Guardrails

Comprehensive automation to prevent repository bloat and maintain production-ready standards.

## 🎯 Overview

After cleaning up from 61 configuration files to 6 essential files, these guardrails ensure we never regress back to a bloated, unmaintainable state.

## 🚫 What Gets Blocked

### 🔒 Security Violations
- **`.env` files** - No secrets in repository
- **`.pem`, `.key`, `.crt`** - No certificates/keys in repository
- **Password/token files** - No credential files
- **Large files >50MB** - Use Git LFS or external storage

### 🏗️ Structure Violations
- **Unauthorized top-level files** - Only approved files at repository root
- **Too many compose files** - Maximum 4 Docker Compose files
- **Dockerfile proliferation** - Maximum 10 Dockerfiles total
- **Mixed package managers** - Either npm OR yarn, not both

### 📦 Dependency Violations
- **Package.json sprawl** - Warning if >3 package.json files
- **Config file bloat** - Warning if >15 configuration files

## ✅ Approved Repository Structure

```
gameforge/
├── 📄 Approved Top-Level Files:
│   ├── README.md, LICENSE, CHANGELOG.md
│   ├── package.json, package-lock.json
│   ├── Dockerfile, docker-compose*.yml
│   ├── .gitignore, .dockerignore, .npmrc
│   ├── .env.example, .env.template
│   └── components.json, DOCKER_STRUCTURE.md
│
├── 📁 Approved Directories:
│   ├── src/          # Source code
│   ├── docker/       # Container configurations
│   ├── k8s/          # Kubernetes manifests
│   ├── scripts/      # Automation scripts
│   ├── monitoring/   # Observability
│   ├── security/     # Security configurations
│   ├── tests/        # Test suites
│   ├── docs/         # Documentation
│   ├── backend/      # Backend application
│   └── frontend/     # Frontend application
│
└── 🚫 Everything else gets blocked!
```

## 🔧 Implementation Layers

### 1. CI/CD Guardrails (`.github/workflows/guardrails.yml`)
- **Trigger**: Every push and pull request
- **Scope**: Comprehensive repository scanning
- **Action**: Block merge if violations found
- **Report**: Detailed violation summary

### 2. Pre-commit Hook (`scripts/guardrails-check.ps1`)
- **Trigger**: Before every commit
- **Scope**: Local development protection
- **Action**: Block commit if violations found
- **Features**: Auto-fix mode available

### 3. Manual Check Script (`scripts/guardrails-check.sh`)
- **Trigger**: On-demand execution
- **Scope**: Full repository validation
- **Action**: Report violations
- **Use**: Before releases, cleanup verification

## 🚀 Setup Instructions

### Install Pre-commit Hook
```powershell
# Install the guardrails pre-commit hook
.\scripts\setup-guardrails.ps1
```

### Manual Checks
```powershell
# Run guardrails check
.\scripts\guardrails-check.ps1

# Run with auto-fix mode
.\scripts\guardrails-check.ps1 -FixMode

# Run with verbose output
.\scripts\guardrails-check.ps1 -Verbose
```

### Emergency Bypass (Use Sparingly!)
```bash
# Bypass pre-commit hook (emergency only)
git commit --no-verify -m "Emergency fix"
```

## 📊 Guardrail Categories

### 🔒 Security Guardrails
| Check | Limit | Action |
|-------|-------|---------|
| `.env` files | 0 allowed | Block commit |
| Certificate files | 0 allowed | Block commit |
| Large files | <50MB | Block commit |
| Sensitive patterns | 0 allowed | Block commit |

### 🏗️ Structure Guardrails  
| Check | Limit | Action |
|-------|-------|---------|
| Top-level files | Approved list only | Block commit |
| Compose files | ≤4 files | Block commit |
| Dockerfiles | ≤10 files | Block commit |
| Directory structure | Approved dirs only | Block commit |

### 📦 Dependency Guardrails
| Check | Limit | Action |
|-------|-------|---------|
| package.json files | ≤3 files | Warning |
| Package managers | Single type | Block commit |
| Config files | ≤15 files | Warning |

## 🎯 Benefits

✅ **Prevents Regression** - Can't go back to bloated state  
✅ **Enforces Standards** - Consistent repository structure  
✅ **Security First** - No secrets accidentally committed  
✅ **Developer Friendly** - Clear error messages and fixes  
✅ **CI/CD Integration** - Automated enforcement  
✅ **Local Protection** - Catch issues before push  

## 🔧 Customization

### Adding Allowed Files
Edit `guardrails-check.ps1`:
```powershell
$allowedFiles = @(
    'README.md', 'LICENSE', 
    'your-new-file.md'  # Add here
)
```

### Adjusting Limits
```powershell
# In guardrails-check.ps1
if ($composeCount -gt 4) {  # Change limit here
if ($dockerfileCount -gt 10) {  # Change limit here
```

### Adding New Checks
```powershell
# Add custom checks in guardrails-check.ps1
Write-Host "Checking custom requirement..." -ForegroundColor White
$customViolation = # Your logic here
if ($customViolation) {
    Write-Host "❌ BLOCKED: Custom violation!" -ForegroundColor Red
    $violations++
}
```

## 🚨 Common Violations & Fixes

### ❌ ".env files detected"
```powershell
# Fix: Rename to template
mv .env .env.example

# Or: Remove and use Vault/K8s secrets
rm .env
```

### ❌ "Too many compose files"
```powershell
# Fix: Consolidate using overrides
# Keep: docker-compose.yml, docker-compose.dev.yml, docker-compose.prod.yml
# Remove: docker-compose.staging.yml, docker-compose.test.yml, etc.
```

### ❌ "Unauthorized top-level files"
```powershell
# Fix: Move to appropriate directory
mv random-config.json config/
mv utility-script.py scripts/
```

### ❌ "Mixed package managers"
```powershell
# Fix: Choose one
rm yarn.lock  # Keep npm
# OR
rm package-lock.json  # Keep yarn
```

## 📈 Metrics & Monitoring

The guardrails provide metrics on:
- **Violation trends** - Are we regressing?
- **File count tracking** - Monitoring bloat
- **Security posture** - Secret leakage prevention
- **Structure compliance** - Organizational health

## 🏆 Success Criteria

A successful guardrails implementation means:
- ✅ Zero security violations in main branch
- ✅ Consistent repository structure
- ✅ Controlled file growth
- ✅ Developer adoption (minimal bypasses)
- ✅ Clean CI/CD pipeline

## 🆘 Troubleshooting

### Pre-commit Hook Not Running
```powershell
# Reinstall
.\scripts\setup-guardrails.ps1

# Check hook exists
ls .git\hooks\pre-commit
```

### False Positives
```powershell
# Review and adjust rules in:
# - scripts/guardrails-check.ps1
# - .github/workflows/guardrails.yml
```

### Performance Issues
```powershell
# For large repos, exclude directories:
# Add to $excludePaths in guardrails-check.ps1
```

---

## 🎉 Result

**Before Guardrails**: Risk of regression to 61+ config files  
**After Guardrails**: Locked at 6 essential files with controlled growth  

**Your repository is now production-ready and bloat-resistant!** 🚀