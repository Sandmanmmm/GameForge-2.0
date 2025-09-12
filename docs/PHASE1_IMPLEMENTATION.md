# Phase 1: Repository & Build Preparation

This document outlines the complete implementation of Phase 1 — Repository & Build Preparation for the GameForge AI Game Production platform.

## 🎯 Objective

Ensure the repository is buildable, secrets are not checked in, dependencies are locked, and artifacts are deterministic with comprehensive SBOM baseline.

## 📋 Implementation Status

### ✅ Completed Components

1. **Secrets Scanning Infrastructure**
   - Automated secrets detection with multiple tools
   - Git-secrets configuration and hooks
   - Pattern-based scanning for various secret types
   - Whitelist configuration for allowed patterns

2. **Dependency Version Locking**
   - Python dependencies with `pip-tools` and `requirements.in`
   - Node.js dependencies with `package-lock.json`
   - Multi-environment support (frontend/backend)

3. **Reproducible Build Configuration**
   - Docker build arguments for deterministic builds
   - Build metadata generation with VCS information
   - Cross-platform build scripts (Bash + PowerShell)

4. **SBOM Baseline Generation**
   - Multiple SBOM formats (JSON, SPDX, CycloneDX)
   - Comprehensive package inventory
   - Docker image SBOM support

## 🛠️ Tools and Scripts

### Primary Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `scripts/phase1-prep.sh` | Linux/macOS | Complete Phase 1 automation |
| `scripts/phase1-prep.ps1` | Windows | PowerShell version of Phase 1 automation |
| `scripts/setup-git-secrets.sh` | Linux/macOS | Git-secrets configuration |
| `Makefile` | Linux/macOS | Make-based automation |

### Tool Requirements

| Tool | Purpose | Installation |
|------|---------|--------------|
| `git-secrets` | Prevent committing secrets | `brew install git-secrets` |
| `trufflehog` | Advanced secret detection | `brew install trufflehog` |
| `syft` | SBOM generation | `brew install syft` |
| `pip-tools` | Python dependency locking | `pip install pip-tools` |
| `jq` | JSON processing | `brew install jq` |

## 🚀 Quick Start

### Method 1: Using Make (Recommended for Linux/macOS)

```bash
# Install required tools
make install-tools

# Run complete Phase 1 preparation
make phase1

# Check status
make status
```

### Method 2: Using Scripts Directly

**Linux/macOS:**
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run Phase 1 preparation
./scripts/phase1-prep.sh

# Setup git-secrets
./scripts/setup-git-secrets.sh
```

**Windows PowerShell:**
```powershell
# Run Phase 1 preparation
.\scripts\phase1-prep.ps1

# Skip certain steps if needed
.\scripts\phase1-prep.ps1 -SkipSecrets -SkipSBOM
```

### Method 3: Manual Step-by-Step

```bash
# 1. Secrets scan
git-secrets --scan
trufflehog filesystem . --json > secrets-report.json

# 2. Lock dependencies
pip-compile requirements.in
npm install --package-lock-only

# 3. Generate SBOM
syft packages dir:. -o json > sbom.json

# 4. Build with metadata
docker build --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
             --build-arg VCS_REF=$(git rev-parse HEAD) \
             --build-arg BUILD_VERSION=$(git describe --tags --always) \
             -f Dockerfile.production.enhanced .
```

## 📊 Expected Outcomes

### 1. Clean Repository State
- ✅ Zero secrets detected by scanning tools
- ✅ Appropriate `.gitignore` patterns for secret files
- ✅ Git hooks configured to prevent future secret commits

### 2. Locked Dependencies
- ✅ `requirements.txt` generated from `requirements.in`
- ✅ `package-lock.json` exists for reproducible Node.js builds
- ✅ All dependency versions pinned

### 3. Reproducible Builds
- ✅ Docker build arguments configured
- ✅ Build metadata available in `build-info.json`
- ✅ VCS reference tracking in builds

### 4. SBOM Baseline
- ✅ Multiple SBOM formats generated
- ✅ Package inventory documented
- ✅ Baseline for future vulnerability monitoring

## 📁 Generated Artifacts

```
phase1-reports/
├── secrets-scan-TIMESTAMP.json          # TruffleHog output
├── pattern-secrets-TIMESTAMP.txt        # Pattern-based scan results
├── gitleaks-TIMESTAMP.json             # Gitleaks output (if available)
└── ...

sbom/
├── sbom-baseline-TIMESTAMP.json         # Syft JSON format
├── sbom-baseline-TIMESTAMP.spdx.json    # SPDX format
├── package-inventory-TIMESTAMP.txt      # Human-readable inventory
└── sbom-summary-TIMESTAMP.md           # Summary report

build-info.json                          # Build metadata
scripts/build-reproducible.sh            # Reproducible build script
scripts/build-reproducible.ps1           # Windows build script
```

## 🔧 Configuration Files

### Git-secrets Patterns

The setup includes detection patterns for:
- AWS credentials
- GitHub tokens (PAT, OAuth)
- OpenAI API keys
- Database connection strings
- JWT secrets
- Generic password/secret patterns
- AI service API keys

### Docker Build Arguments

Required build arguments for reproducible builds:
```dockerfile
ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION
ARG VARIANT=gpu
```

### Python Dependencies

Enhanced `requirements.in` includes:
- Core application dependencies
- Build tools (`pip-tools`, `wheel`, `setuptools`)
- Security scanning tools (`cyclonedx-bom`)
- Locked version ranges for stability

## ⚡ Automation Features

### Pre-commit Hooks

Automatically installed hooks check for:
- Secrets in staged files
- Potential secret files being added
- Hardcoded localhost URLs
- Basic security patterns

### Make Targets

| Target | Description |
|--------|-------------|
| `make phase1` | Complete Phase 1 execution |
| `make secrets` | Run only secrets scanning |
| `make deps` | Lock dependency versions |
| `make sbom` | Generate SBOM baseline |
| `make clean` | Clean Phase 1 artifacts |
| `make status` | Show preparation status |
| `make quick-check` | Fast security validation |

### PowerShell Parameters

The PowerShell script supports:
- `-SkipSecrets`: Skip secrets scanning
- `-SkipSBOM`: Skip SBOM generation
- `-OutputDir`: Custom output directory
- `-Verbose`: Detailed output

## 🔍 Verification

### Secrets Scan Verification
```bash
# Manual verification
git secrets --scan
trufflehog filesystem . --only-verified

# Check git hooks
ls -la .git/hooks/pre-commit
```

### Dependency Lock Verification
```bash
# Python
pip-compile --dry-run requirements.in

# Node.js
npm ls --depth=0
```

### Build Reproducibility Verification
```bash
# Build twice and compare
docker build --build-arg BUILD_DATE=2024-01-01T00:00:00Z \
             --build-arg VCS_REF=abc123 \
             -t test1 .
docker build --build-arg BUILD_DATE=2024-01-01T00:00:00Z \
             --build-arg VCS_REF=abc123 \
             -t test2 .

# Compare layer hashes
docker history test1
docker history test2
```

### SBOM Verification
```bash
# Validate SBOM formats
syft packages sbom/sbom-baseline-*.json --validate

# Check package counts
jq '.artifacts | length' sbom/sbom-baseline-*.json
```

## 🚨 Troubleshooting

### Common Issues

**1. git-secrets not found**
```bash
# macOS
brew install git-secrets

# Linux (manual)
git clone https://github.com/awslabs/git-secrets.git
cd git-secrets && make install
```

**2. pip-compile not available**
```bash
pip install pip-tools
```

**3. Secrets detected in repository**
```bash
# Review and remove secrets
git secrets --scan

# For historical secrets
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/secret/file' \
  --prune-empty --tag-name-filter cat -- --all
```

**4. SBOM generation fails**
```bash
# Install syft manually
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh
```

### Platform-Specific Notes

**Windows:**
- Use PowerShell scripts (`.ps1`)
- Ensure execution policy allows scripts: `Set-ExecutionPolicy RemoteSigned`
- Some tools may require WSL or Git Bash

**macOS:**
- Use Homebrew for tool installation
- Bash scripts should work natively

**Linux:**
- Install tools via package manager or manual compilation
- Ensure proper PATH configuration

## 🔗 Integration with CI/CD

### GitHub Actions Example
```yaml
name: Phase 1 Security Check
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Phase 1 Prep
        run: make phase1
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: phase1-reports
          path: phase1-reports/
```

### GitLab CI Example
```yaml
phase1:
  stage: security
  script:
    - make install-tools
    - make phase1
  artifacts:
    paths:
      - phase1-reports/
    expire_in: 1 week
```

## 📈 Metrics and Monitoring

Track Phase 1 effectiveness:
- Number of secrets prevented from commit
- Dependency lock file freshness
- SBOM comparison reports
- Build reproducibility success rate

## 🔄 Maintenance

### Regular Tasks
1. Update secret detection patterns monthly
2. Refresh SBOM baseline quarterly
3. Audit dependency locks for security updates
4. Validate reproducible build configuration

### Tool Updates
```bash
# Update detection tools
brew upgrade git-secrets trufflehog syft

# Update Python tools
pip install --upgrade pip-tools cyclonedx-bom
```

This completes the comprehensive Phase 1 implementation for GameForge, providing a robust foundation for secure, reproducible builds with comprehensive secret detection and SBOM baseline capabilities.
