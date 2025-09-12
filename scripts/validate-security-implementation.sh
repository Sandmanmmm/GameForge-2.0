#!/bin/bash
# Security Implementation Validation Script

echo "🔒 Validating GameForge Security Implementation"
echo "=============================================================="

VALIDATION_PASSED=true

# Check required files exist
echo "📁 Checking required files..."
required_files=(
    "docker-compose.security.yml"
    ".github/workflows/security-scan.yml"
    "ci/gitlab/.gitlab-ci-security.yml"
    "security/policies/opa-security-policy.rego"
    "security/policies/k8s-admission-policy.yaml"
    "security/configs/trivy.yaml"
    "security/configs/clair-config.yaml"
    "security/configs/harbor.yml"
    "security/configs/prometheus.yml"
    "security/configs/security_rules.yml"
    "security/dashboards/security-dashboard.json"
    "security/scripts/comprehensive-scan.sh"
    "security/scripts/auto-remediation.sh"
    "security/scripts/secure-deploy.sh"
    "security/scripts/generate-security-report.sh"
    "SECURITY_IMPLEMENTATION_GUIDE.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        VALIDATION_PASSED=false
    fi
done

# Check directory structure
echo -e "\n📂 Checking directory structure..."
required_dirs=(
    "security/configs"
    "security/policies"
    "security/scripts"
    "security/reports"
    "security/dashboards"
    ".github/workflows"
    "ci/gitlab"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/"
    else
        echo "❌ $dir/ - MISSING"
        VALIDATION_PASSED=false
    fi
done

# Check script permissions
echo -e "\n🔧 Checking script permissions..."
scripts=(
    "security/scripts/comprehensive-scan.sh"
    "security/scripts/auto-remediation.sh"
    "security/scripts/secure-deploy.sh"
    "security/scripts/generate-security-report.sh"
)

for script in "${scripts[@]}"; do
    if [ -x "$script" ]; then
        echo "✅ $script - executable"
    else
        echo "⚠️  $script - setting executable permission"
        chmod +x "$script" 2>/dev/null || echo "❌ Failed to set permissions"
    fi
done

# Validate Docker Compose syntax
echo -e "\n🐳 Validating Docker Compose syntax..."
if command -v docker-compose &> /dev/null; then
    if docker-compose -f docker-compose.security.yml config > /dev/null 2>&1; then
        echo "✅ docker-compose.security.yml syntax valid"
    else
        echo "❌ docker-compose.security.yml syntax invalid"
        VALIDATION_PASSED=false
    fi
else
    echo "⚠️  Docker Compose not available, skipping syntax check"
fi

# Validate YAML files
echo -e "\n📄 Validating YAML files..."
yaml_files=(
    "security/policies/k8s-admission-policy.yaml"
    "security/configs/prometheus.yml"
    ".github/workflows/security-scan.yml"
    "security/configs/trivy.yaml"
    "security/configs/clair-config.yaml"
    "security/configs/harbor.yml"
)

for file in "${yaml_files[@]}"; do
    if [ -f "$file" ]; then
        # Simple YAML validation using Python
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo "✅ $file - valid YAML"
        else
            echo "❌ $file - invalid YAML"
            VALIDATION_PASSED=false
        fi
    fi
done

# Check for required environment variables documentation
echo -e "\n🔑 Checking environment variable documentation..."
if grep -q "HARBOR_USERNAME" SECURITY_IMPLEMENTATION_GUIDE.md; then
    echo "✅ Environment variables documented"
else
    echo "⚠️  Environment variables not documented"
fi

# Check for security scanner availability
echo -e "\n🔍 Checking security tool availability..."
tools=("docker" "kubectl" "git")
for tool in "${tools[@]}"; do
    if command -v "$tool" &> /dev/null; then
        echo "✅ $tool - available"
    else
        echo "⚠️  $tool - not available (install for full functionality)"
    fi
done

# Security configuration validation
echo -e "\n🛡️  Validating security configurations..."

# Check if Trivy config has proper settings
if [ -f "security/configs/trivy.yaml" ] && grep -q "severity" "security/configs/trivy.yaml"; then
    echo "✅ Trivy configuration includes severity settings"
else
    echo "⚠️  Trivy configuration may be incomplete"
fi

# Check if CI/CD workflow has security gates
if [ -f ".github/workflows/security-scan.yml" ] && grep -q "security-gate" ".github/workflows/security-scan.yml"; then
    echo "✅ GitHub Actions includes security gates"
else
    echo "⚠️  GitHub Actions security gates may be incomplete"
fi

# Summary
echo -e "\n📊 VALIDATION SUMMARY"
echo "=============================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo "🎉 ALL VALIDATIONS PASSED"
    echo ""
    echo "🚀 Security implementation is ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Deploy security infrastructure: docker-compose -f docker-compose.security.yml up -d"
    echo "2. Configure CI/CD pipelines with required secrets/variables"
    echo "3. Deploy Kubernetes security policies: kubectl apply -f security/policies/"
    echo "4. Set up monitoring dashboards in Grafana"
    echo "5. Test security scanning: ./security/scripts/comprehensive-scan.sh gameforge:latest"
    echo ""
    echo "📖 For detailed instructions, see: SECURITY_IMPLEMENTATION_GUIDE.md"
    exit 0
else
    echo "❌ SOME VALIDATIONS FAILED"
    echo ""
    echo "Please fix the issues above before deployment."
    echo "Check the SECURITY_IMPLEMENTATION_GUIDE.md for troubleshooting guidance."
    exit 1
fi
