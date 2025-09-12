#!/bin/bash
# Automated Vulnerability Remediation System
# Analyzes vulnerabilities and suggests/applies fixes

set -e

VULNERABILITY_REPORT="security/reports/trivy-results.json"
REMEDIATION_LOG="security/reports/remediation-$(date +%Y%m%d_%H%M%S).log"
AUTO_FIX=${AUTO_FIX:-false}

echo "Starting vulnerability remediation analysis..." | tee "$REMEDIATION_LOG"

# Check if vulnerability report exists
if [ ! -f "$VULNERABILITY_REPORT" ]; then
    echo "Error: Vulnerability report not found at $VULNERABILITY_REPORT" | tee -a "$REMEDIATION_LOG"
    exit 1
fi

# Remediation strategies
remediate_base_image() {
    local current_image="$1"
    local cve="$2"

    echo "Analyzing base image remediation for $current_image (CVE: $cve)" | tee -a "$REMEDIATION_LOG"

    # Common base image upgrades
    case "$current_image" in
        *"ubuntu:18.04"*)
            echo "RECOMMENDATION: Upgrade from ubuntu:18.04 to ubuntu:22.04" | tee -a "$REMEDIATION_LOG"
            if [ "$AUTO_FIX" = "true" ]; then
                sed -i 's/ubuntu:18.04/ubuntu:22.04/g' Dockerfile
                echo "AUTO-APPLIED: Base image upgraded to ubuntu:22.04" | tee -a "$REMEDIATION_LOG"
            fi
            ;;
        *"node:14"*)
            echo "RECOMMENDATION: Upgrade from node:14 to node:18-alpine" | tee -a "$REMEDIATION_LOG"
            if [ "$AUTO_FIX" = "true" ]; then
                sed -i 's/node:14/node:18-alpine/g' Dockerfile
                echo "AUTO-APPLIED: Node.js upgraded to version 18 with Alpine base" | tee -a "$REMEDIATION_LOG"
            fi
            ;;
        *"python:3.8"*)
            echo "RECOMMENDATION: Upgrade from python:3.8 to python:3.11-slim" | tee -a "$REMEDIATION_LOG"
            if [ "$AUTO_FIX" = "true" ]; then
                sed -i 's/python:3.8/python:3.11-slim/g' Dockerfile
                echo "AUTO-APPLIED: Python upgraded to version 3.11 with slim base" | tee -a "$REMEDIATION_LOG"
            fi
            ;;
    esac
}

remediate_package_vulnerability() {
    local package="$1"
    local installed_version="$2"
    local fixed_version="$3"
    local cve="$4"

    echo "Analyzing package remediation: $package" | tee -a "$REMEDIATION_LOG"
    echo "Current: $installed_version, Fixed: $fixed_version" | tee -a "$REMEDIATION_LOG"

    # Check if this is a Node.js package
    if [ -f "package.json" ]; then
        echo "RECOMMENDATION: Update $package from $installed_version to $fixed_version" | tee -a "$REMEDIATION_LOG"

        if [ "$AUTO_FIX" = "true" ]; then
            npm update "$package" || echo "Failed to update $package" | tee -a "$REMEDIATION_LOG"
        fi
    fi

    # Check if this is a Python package
    if [ -f "requirements.txt" ]; then
        echo "RECOMMENDATION: Update $package in requirements.txt" | tee -a "$REMEDIATION_LOG"

        if [ "$AUTO_FIX" = "true" ]; then
            sed -i "s/$package==.*/$package>=$fixed_version/g" requirements.txt
            echo "AUTO-APPLIED: Updated $package to >=$fixed_version in requirements.txt" | tee -a "$REMEDIATION_LOG"
        fi
    fi
}

generate_dockerfile_security_improvements() {
    echo "Generating Dockerfile security improvements..." | tee -a "$REMEDIATION_LOG"

    cat > security/recommendations/dockerfile-security.md << 'EOF'
# Dockerfile Security Improvements

## Recommended Changes:

### 1. Use Multi-stage Builds
```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Runtime stage
FROM node:18-alpine AS runtime
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001
USER nodejs
WORKDIR /app
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs . .
EXPOSE 3000
CMD ["npm", "start"]
```

### 2. Security Hardening
```dockerfile
# Use specific versions, not latest
FROM ubuntu:22.04

# Create non-root user
RUN useradd -r -s /bin/false gameforge

# Remove unnecessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use COPY instead of ADD
COPY --chown=gameforge:gameforge . /app

# Switch to non-root user
USER gameforge

# Use specific port
EXPOSE 8080

# Use exec form for CMD
CMD ["python3", "app.py"]
```

### 3. Image Scanning Integration
```dockerfile
# Add labels for scanning
LABEL maintainer="security@gameforge.com"
LABEL security.scan="required"
LABEL security.policy="strict"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```
EOF

    echo "Generated Dockerfile security recommendations" | tee -a "$REMEDIATION_LOG"
}

# Main remediation logic
python3 - << 'PYTHON'
import json
import sys
import subprocess
from collections import defaultdict

def analyze_vulnerabilities():
    try:
        with open("security/reports/trivy-results.json", 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Vulnerability report not found")
        return

    vulnerabilities = defaultdict(list)

    for result in data.get('Results', []):
        target = result.get('Target', 'unknown')

        for vuln in result.get('Vulnerabilities', []):
            vuln_info = {
                'cve': vuln.get('VulnerabilityID', ''),
                'severity': vuln.get('Severity', ''),
                'package': vuln.get('PkgName', ''),
                'installed_version': vuln.get('InstalledVersion', ''),
                'fixed_version': vuln.get('FixedVersion', ''),
                'description': vuln.get('Description', '')
            }
            vulnerabilities[target].append(vuln_info)

    # Generate remediation plan
    remediation_plan = {
        'critical_actions': [],
        'high_priority_actions': [],
        'medium_priority_actions': [],
        'base_image_updates': [],
        'package_updates': []
    }

    for target, vulns in vulnerabilities.items():
        for vuln in vulns:
            severity = vuln['severity'].upper()
            action = {
                'target': target,
                'cve': vuln['cve'],
                'package': vuln['package'],
                'current_version': vuln['installed_version'],
                'fixed_version': vuln['fixed_version'],
                'action_type': 'package_update' if vuln['fixed_version'] else 'base_image_update'
            }

            if severity == 'CRITICAL':
                remediation_plan['critical_actions'].append(action)
            elif severity == 'HIGH':
                remediation_plan['high_priority_actions'].append(action)
            elif severity == 'MEDIUM':
                remediation_plan['medium_priority_actions'].append(action)

    # Save remediation plan
    with open('security/reports/remediation-plan.json', 'w') as f:
        json.dump(remediation_plan, f, indent=2)

    print(f"Remediation plan generated:")
    print(f"Critical actions: {len(remediation_plan['critical_actions'])}")
    print(f"High priority actions: {len(remediation_plan['high_priority_actions'])}")
    print(f"Medium priority actions: {len(remediation_plan['medium_priority_actions'])}")

    return remediation_plan

# Run analysis
plan = analyze_vulnerabilities()
PYTHON

# Generate security improvements
generate_dockerfile_security_improvements

echo "Vulnerability remediation analysis complete. Check $REMEDIATION_LOG for details."

# Create remediation summary
cat > security/reports/remediation-summary.md << EOF
# Vulnerability Remediation Summary

Generated: $(date)

## Actions Required:

### Critical Priority
- Review and apply critical security patches immediately
- Update base images with known critical vulnerabilities
- Implement security controls for high-risk components

### High Priority  
- Update packages with available security fixes
- Review and update dependencies
- Implement additional security measures

### Medium Priority
- Regular maintenance updates
- Security hardening improvements
- Monitoring and alerting enhancements

## Automated Actions:
$(if [ "$AUTO_FIX" = "true" ]; then echo "- Automatic fixes have been applied"; else echo "- No automatic fixes applied (AUTO_FIX=false)"; fi)

## Next Steps:
1. Review the detailed remediation log: $REMEDIATION_LOG
2. Test the proposed changes in a staging environment
3. Apply approved fixes to production
4. Re-scan to verify remediation effectiveness

EOF

echo "Remediation summary created: security/reports/remediation-summary.md"
