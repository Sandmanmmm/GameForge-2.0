#!/bin/bash
# Advanced Monitoring Integrations Validation Script

echo "🎯 Validating GameForge Advanced Monitoring Integrations"
echo "================================================================"

VALIDATION_PASSED=true

# Check GPU monitoring files
echo "🖥️ Checking GPU monitoring files..."
gpu_files=(
    "docker-compose.gpu-monitoring.yml"
    "monitoring/configs/prometheus-gpu.yml"
    "monitoring/configs/gpu-rules.yml"
    "monitoring/configs/gpu-datasources.yml"
    "monitoring/configs/gpu-provisioning.yml"
)

for file in "${gpu_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        VALIDATION_PASSED=false
    fi
done

# Check custom dashboard files
echo -e "\n📊 Checking custom dashboard files..."
dashboard_files=(
    "monitoring/dashboards/gpu/gpu-overview.json"
    "monitoring/dashboards/game-analytics/game-analytics.json"
    "monitoring/dashboards/business/business-intelligence.json"
    "monitoring/dashboards/gameforge/system-overview.json"
)

for file in "${dashboard_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        VALIDATION_PASSED=false
    fi
done

# Check AlertManager files
echo -e "\n🚨 Checking AlertManager files..."
alertmanager_files=(
    "docker-compose.alertmanager.yml"
    "monitoring/alerting/configs/alertmanager.yml"
    "monitoring/alerting/templates/gameforge.tmpl"
    "monitoring/alerting/webhooks/webhook_handler.py"
    "monitoring/alerting/webhooks/Dockerfile"
    "monitoring/alerting/webhooks/requirements.txt"
)

for file in "${alertmanager_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        VALIDATION_PASSED=false
    fi
done

# Check log pipeline files
echo -e "\n📊 Checking log pipeline files..."
log_files=(
    "docker-compose.log-pipeline.yml"
    "monitoring/logging/filebeat/filebeat.yml"
    "monitoring/logging/logstash/logstash.conf"
    "monitoring/logging/ml-processing/ml_processor.py"
    "monitoring/logging/ml-processing/Dockerfile"
    "monitoring/logging/ml-processing/requirements.txt"
)

for file in "${log_files[@]}"; do
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
    "monitoring/gpu"
    "monitoring/exporters"
    "monitoring/dashboards/gpu"
    "monitoring/dashboards/game-analytics"
    "monitoring/dashboards/business"
    "monitoring/dashboards/gameforge"
    "monitoring/alerting/configs"
    "monitoring/alerting/templates"
    "monitoring/alerting/webhooks"
    "monitoring/logging/filebeat"
    "monitoring/logging/logstash"
    "monitoring/logging/ml-processing"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/"
    else
        echo "❌ $dir/ - MISSING"
        VALIDATION_PASSED=false
    fi
done

# Validate JSON files
echo -e "\n📄 Validating JSON files..."
json_files=(
    "monitoring/dashboards/gpu/gpu-overview.json"
    "monitoring/dashboards/game-analytics/game-analytics.json"
    "monitoring/dashboards/business/business-intelligence.json"
    "monitoring/dashboards/gameforge/system-overview.json"
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
    "monitoring/configs/prometheus-gpu.yml"
    "monitoring/configs/gpu-rules.yml"
    "monitoring/configs/gpu-datasources.yml"
    "monitoring/configs/gpu-provisioning.yml"
    "monitoring/alerting/configs/alertmanager.yml"
    "monitoring/logging/filebeat/filebeat.yml"
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

# Summary
echo -e "\n📊 VALIDATION SUMMARY"
echo "=============================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo "🎉 ALL VALIDATIONS PASSED"
    echo ""
    echo "🚀 Advanced monitoring integrations are ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Deploy GPU monitoring: docker-compose -f docker-compose.gpu-monitoring.yml up -d"
    echo "2. Deploy AlertManager: docker-compose -f docker-compose.alertmanager.yml up -d"  
    echo "3. Deploy log pipeline: docker-compose -f docker-compose.log-pipeline.yml up -d"
    echo "4. Configure alerting credentials and endpoints"
    echo "5. Import custom dashboards to Grafana"
    echo "6. Test monitoring and alerting functionality"
    echo ""
    echo "📖 For detailed instructions, see: ADVANCED_MONITORING_INTEGRATIONS_GUIDE.md"
    exit 0
else
    echo "❌ SOME VALIDATIONS FAILED"
    echo ""
    echo "Please fix the issues above before deployment."
    echo "Check the ADVANCED_MONITORING_INTEGRATIONS_GUIDE.md for troubleshooting guidance."
    exit 1
fi
