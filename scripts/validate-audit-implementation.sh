#!/bin/bash
# Audit Logging Implementation Validation Script

echo "🔍 Validating GameForge Audit Logging Implementation"
echo "==========================================================="

VALIDATION_PASSED=true

# Check required files exist
echo "📁 Checking required files..."
required_files=(
    "docker-compose.audit.yml"
    "audit/configs/fluent-bit.conf"
    "audit/configs/parsers.conf"
    "audit/configs/audit-mapping.json"
    "audit/configs/kibana.yml"
    "audit/analytics/audit_analytics.py"
    "audit/compliance/compliance_rules.py"
    "audit/dashboards/audit-dashboard.json"
    "audit/alerts/audit-rules.yml"
    "audit/alerts/alertmanager.yml"
    "audit/scripts/audit_logger.py"
    "audit/scripts/manage-audit.sh"
    "AUDIT_LOGGING_IMPLEMENTATION_GUIDE.md"
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
    "audit/configs"
    "audit/collectors"
    "audit/processors" 
    "audit/analytics"
    "audit/compliance"
    "audit/dashboards"
    "audit/alerts"
    "audit/scripts"
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
    "audit/scripts/manage-audit.sh"
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
    if docker-compose -f docker-compose.audit.yml config > /dev/null 2>&1; then
        echo "✅ docker-compose.audit.yml syntax valid"
    else
        echo "❌ docker-compose.audit.yml syntax invalid"
        VALIDATION_PASSED=false
    fi
else
    echo "⚠️  Docker Compose not available, skipping syntax check"
fi

# Validate JSON files
echo -e "\n📄 Validating JSON files..."
json_files=(
    "audit/configs/audit-mapping.json"
    "audit/dashboards/audit-dashboard.json"
)

for file in "${json_files[@]}"; do
    if [ -f "$file" ]; then
        if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
            echo "✅ $file - valid JSON"
        else
            echo "❌ $file - invalid JSON"
            VALIDATION_PASSED=false
        fi
    fi
done

# Validate YAML files
echo -e "\n📄 Validating YAML files..."
yaml_files=(
    "audit/alerts/audit-rules.yml"
    "audit/alerts/alertmanager.yml"
    "audit/configs/kibana.yml"
)

for file in "${yaml_files[@]}"; do
    if [ -f "$file" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo "✅ $file - valid YAML"
        else
            echo "❌ $file - invalid YAML"
            VALIDATION_PASSED=false
        fi
    fi
done

# Check Python dependencies
echo -e "\n🐍 Checking Python dependencies..."
python_deps=("kafka-python" "requests" "elasticsearch")
for dep in "${python_deps[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo "✅ $dep - available"
    else
        echo "⚠️  $dep - not available (install with: pip install $dep)"
    fi
done

# Summary
echo -e "\n📊 VALIDATION SUMMARY"
echo "=============================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo "🎉 ALL VALIDATIONS PASSED"
    echo ""
    echo "🚀 Audit logging implementation is ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Deploy audit infrastructure: ./audit/scripts/manage-audit.sh deploy"
    echo "2. Initialize system configuration"
    echo "3. Integrate audit logging in applications"
    echo "4. Set up monitoring dashboards"
    echo "5. Configure alerting and notifications"
    echo ""
    echo "📖 For detailed instructions, see: AUDIT_LOGGING_IMPLEMENTATION_GUIDE.md"
    exit 0
else
    echo "❌ SOME VALIDATIONS FAILED"
    echo ""
    echo "Please fix the issues above before deployment."
    echo "Check the AUDIT_LOGGING_IMPLEMENTATION_GUIDE.md for troubleshooting guidance."
    exit 1
fi
