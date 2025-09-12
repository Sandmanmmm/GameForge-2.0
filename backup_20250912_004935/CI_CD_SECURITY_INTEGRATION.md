# CI/CD Security Integration Guide
================================

## 🚀 **Quick Integration**

Add GameForge security checks to your CI/CD pipeline with these ready-to-use configurations.

## 📋 **GitHub Actions Integration**

### **`.github/workflows/security.yml`**
```yaml
name: Security Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install security tools
      run: |
        # Install Phase 1 security tools
        pip install pip-tools safety bandit
        
        # Install syft for SBOM generation
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
        
        # Install git-secrets
        git clone https://github.com/awslabs/git-secrets.git
        cd git-secrets && make install
        
    - name: Run Phase 1 Security Checks
      run: |
        chmod +x scripts/ci-security-pipeline.sh
        ./scripts/ci-security-pipeline.sh
        
    - name: Upload Security Reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-reports
        path: |
          ci-security-reports/
          sbom/
          phase1-reports/
```

### **Environment Variables Setup**
```yaml
# Add to repository secrets
env:
  POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
  VAULT_TOKEN: ${{ secrets.VAULT_TOKEN }}
```

## 🐙 **GitLab CI Integration**

### **`.gitlab-ci.yml`**
```yaml
stages:
  - security
  - build
  - test
  - deploy

variables:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  JWT_SECRET_KEY: ${JWT_SECRET_KEY}
  VAULT_TOKEN: ${VAULT_TOKEN}

security-scan:
  stage: security
  image: python:3.11-alpine
  before_script:
    - apk add --no-cache bash curl git make
    - pip install pip-tools safety bandit
    - curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
  script:
    - chmod +x scripts/ci-security-pipeline.sh
    - ./scripts/ci-security-pipeline.sh
  artifacts:
    reports:
      junit: ci-security-reports/*.xml
    paths:
      - ci-security-reports/
      - sbom/
      - phase1-reports/
    expire_in: 1 week
  only:
    - main
    - merge_requests
```

## 🔵 **Azure DevOps Integration**

### **`azure-pipelines.yml`**
```yaml
trigger:
- main

pool:
  vmImage: 'ubuntu-latest'

stages:
- stage: Security
  displayName: 'Security Scanning'
  jobs:
  - job: SecurityScan
    displayName: 'Run Security Checks'
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '3.11'
        
    - script: |
        pip install pip-tools safety bandit
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
      displayName: 'Install Security Tools'
      
    - script: |
        chmod +x scripts/ci-security-pipeline.sh
        ./scripts/ci-security-pipeline.sh
      displayName: 'Run Phase 1 Security Checks'
      env:
        POSTGRES_PASSWORD: $(POSTGRES_PASSWORD)
        JWT_SECRET_KEY: $(JWT_SECRET_KEY)
        VAULT_TOKEN: $(VAULT_TOKEN)
        
    - task: PublishTestResults@2
      condition: always()
      inputs:
        testResultsFiles: 'ci-security-reports/*.xml'
        
    - task: PublishBuildArtifacts@1
      condition: always()
      inputs:
        pathToPublish: 'ci-security-reports'
        artifactName: 'SecurityReports'
```

## 🐳 **Docker Integration**

### **Dockerfile.security**
```dockerfile
FROM python:3.11-alpine AS security-scanner

# Install security tools
RUN apk add --no-cache bash curl git make \
    && pip install pip-tools safety bandit \
    && curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

COPY scripts/ /app/scripts/
COPY requirements.txt package*.json Dockerfile* /app/

WORKDIR /app

# Run security checks
RUN chmod +x scripts/ci-security-pipeline.sh \
    && ./scripts/ci-security-pipeline.sh

# Copy reports to final image
FROM alpine:latest
COPY --from=security-scanner /app/ci-security-reports /reports/
COPY --from=security-scanner /app/sbom /reports/sbom/
```

## 🛠️ **Jenkins Integration**

### **Jenkinsfile**
```groovy
pipeline {
    agent any
    
    environment {
        POSTGRES_PASSWORD = credentials('postgres-password')
        JWT_SECRET_KEY = credentials('jwt-secret-key')
        VAULT_TOKEN = credentials('vault-token')
    }
    
    stages {
        stage('Security Scan') {
            steps {
                script {
                    // Install security tools
                    sh '''
                        pip install pip-tools safety bandit
                        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
                    '''
                    
                    // Run security checks
                    sh '''
                        chmod +x scripts/ci-security-pipeline.sh
                        ./scripts/ci-security-pipeline.sh
                    '''
                }
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'ci-security-reports',
                        reportFiles: '*.html',
                        reportName: 'Security Report'
                    ])
                    
                    archiveArtifacts artifacts: 'ci-security-reports/**, sbom/**', fingerprint: true
                }
            }
        }
    }
}
```

## 🔧 **Pre-commit Hooks**

### **`.pre-commit-config.yaml`**
```yaml
repos:
- repo: local
  hooks:
  - id: gameforge-security-check
    name: GameForge Security Check
    entry: scripts/phase1-demo.ps1
    language: system
    pass_filenames: false
    always_run: true
    
- repo: https://github.com/psf/black
  rev: 23.3.0
  hooks:
  - id: black
    
- repo: https://github.com/PyCQA/bandit
  rev: 1.7.5
  hooks:
  - id: bandit
    args: ['-c', 'pyproject.toml']
```

## 📊 **Monitoring Integration**

### **Prometheus Metrics**
```yaml
# prometheus.yml
scrape_configs:
- job_name: 'gameforge-security'
  static_configs:
  - targets: ['localhost:8080']
  metrics_path: '/metrics/security'
  scrape_interval: 60s
```

### **Grafana Dashboard**
```json
{
  "dashboard": {
    "title": "GameForge Security Metrics",
    "panels": [
      {
        "title": "Security Scan Results",
        "type": "stat",
        "targets": [
          {
            "expr": "gameforge_security_scan_passed"
          }
        ]
      }
    ]
  }
}
```

## 🚨 **Failure Handling**

### **Security Check Failures**
```bash
# Handle different failure scenarios
if [ $security_result -ne 0 ]; then
    case $security_result in
        1) echo "❌ Secrets detected - BLOCK DEPLOYMENT" ;;
        2) echo "⚠️  Dependency issues - REVIEW REQUIRED" ;;
        3) echo "🔧 Build config issues - FIX AND RETRY" ;;
        *) echo "❓ Unknown security issue - INVESTIGATE" ;;
    esac
    
    # Send notifications
    curl -X POST "$SLACK_WEBHOOK" -d "{\"text\":\"🚨 Security check failed for $PROJECT_NAME\"}"
    
    # Block deployment
    exit 1
fi
```

## 📱 **Notification Setup**

### **Slack Integration**
```bash
# Add to CI environment
export SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# In security script
send_slack_notification() {
    local message="$1"
    local color="$2"  # good, warning, danger
    
    curl -X POST "$SLACK_WEBHOOK" \
         -H 'Content-type: application/json' \
         --data "{
           \"attachments\": [{
             \"color\": \"$color\",
             \"text\": \"$message\"
           }]
         }"
}
```

### **Email Notifications**
```bash
# Email on security issues
send_email_alert() {
    local subject="$1"
    local body="$2"
    
    echo "$body" | mail -s "$subject" security-team@gameforge.com
}
```

## 🎯 **Best Practices**

### **✅ DO**
- Run security checks on every commit
- Store secrets in CI/CD secret management
- Generate SBOM for every release
- Monitor security metrics
- Fail fast on critical security issues

### **❌ DON'T**
- Skip security checks for "hotfixes"
- Store secrets in CI/CD configuration files
- Ignore security warnings
- Deploy without SBOM validation
- Allow secrets in git history

## 🔍 **Troubleshooting**

### **Common Issues**
```bash
# Permission denied
chmod +x scripts/ci-security-pipeline.sh

# Missing tools
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Environment variables not set
echo "Check CI/CD secret configuration"
```

---
**🎉 Ready to secure your pipeline!** Choose your CI/CD platform and follow the integration guide above.
