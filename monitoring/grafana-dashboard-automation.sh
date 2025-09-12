#!/bin/bash
# ========================================================================
# Grafana Dashboard Auto-Import and Provisioning System
# GameForge AI Production Monitoring Dashboard Automation
# ========================================================================

set -euo pipefail

# Configuration
GRAFANA_URL="${GRAFANA_URL:-http://grafana:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"
DASHBOARD_DIR="/app/dashboards"
PROVISIONING_DIR="/etc/grafana/provisioning"

echo "🚀 Starting Grafana Dashboard Auto-Import System..."

# ========================================================================
# Wait for Grafana to be ready
# ========================================================================
wait_for_grafana() {
    echo "⏳ Waiting for Grafana to be ready..."
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "${GRAFANA_URL}/api/health" > /dev/null 2>&1; then
            echo "✅ Grafana is ready!"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts - Grafana not ready, waiting..."
        sleep 5
        ((attempt++))
    done
    
    echo "❌ Grafana failed to become ready after $max_attempts attempts"
    return 1
}

# ========================================================================
# Create API key for automation
# ========================================================================
create_api_key() {
    echo "🔑 Creating Grafana API key..."
    
    local response=$(curl -s -X POST \
        "${GRAFANA_URL}/api/auth/keys" \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        -d '{
            "name": "gameforge-automation",
            "role": "Admin",
            "secondsToLive": 31536000
        }')
    
    if echo "$response" | grep -q '"key"'; then
        API_KEY=$(echo "$response" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
        echo "✅ API key created successfully"
        return 0
    else
        echo "⚠️ API key creation failed or key already exists"
        # Try to use default admin credentials
        return 1
    fi
}

# ========================================================================
# Import dashboard function
# ========================================================================
import_dashboard() {
    local dashboard_file="$1"
    local dashboard_name=$(basename "$dashboard_file" .json)
    
    echo "📊 Importing dashboard: $dashboard_name"
    
    # Read dashboard JSON
    local dashboard_json=$(cat "$dashboard_file")
    
    # Create import payload
    local import_payload=$(cat <<EOF
{
    "dashboard": $dashboard_json,
    "overwrite": true,
    "inputs": [
        {
            "name": "DS_PROMETHEUS",
            "type": "datasource",
            "pluginId": "prometheus",
            "value": "prometheus"
        },
        {
            "name": "DS_ELASTICSEARCH",
            "type": "datasource", 
            "pluginId": "elasticsearch",
            "value": "elasticsearch"
        }
    ]
}
EOF
)
    
    # Import dashboard
    local auth_header=""
    if [ -n "${API_KEY:-}" ]; then
        auth_header="Authorization: Bearer $API_KEY"
    else
        auth_header="Authorization: Basic $(echo -n "${GRAFANA_USER}:${GRAFANA_PASSWORD}" | base64)"
    fi
    
    local response=$(curl -s -X POST \
        "${GRAFANA_URL}/api/dashboards/import" \
        -H "Content-Type: application/json" \
        -H "$auth_header" \
        -d "$import_payload")
    
    if echo "$response" | grep -q '"id"'; then
        echo "✅ Dashboard '$dashboard_name' imported successfully"
        local dashboard_url=$(echo "$response" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
        echo "🔗 Dashboard URL: ${GRAFANA_URL}${dashboard_url}"
    else
        echo "❌ Failed to import dashboard '$dashboard_name'"
        echo "Response: $response"
    fi
}

# ========================================================================
# Create GameForge Overview Dashboard
# ========================================================================
create_overview_dashboard() {
    echo "📊 Creating GameForge Overview Dashboard..."
    
    cat > "${DASHBOARD_DIR}/gameforge-overview.json" <<'EOF'
{
  "dashboard": {
    "id": null,
    "title": "GameForge AI - Production Overview",
    "description": "Comprehensive overview of GameForge AI platform production metrics",
    "tags": ["gameforge", "ai", "production", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Health Score",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(up{job=~\"gameforge.*\"})*100",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 80},
                {"color": "green", "value": 95}
              ]
            },
            "unit": "percent"
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Active Inference Sessions",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(gameforge_active_inference_sessions)",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {"mode": "palette-classic"},
            "unit": "short"
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "GPU Utilization",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(gameforge_gpu_utilization_percent)",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90}
              ]
            },
            "unit": "percent"
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
      },
      {
        "id": 4,
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(gameforge_http_requests_total{status=~\"5..\"}[5m])*100",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 5}
              ]
            },
            "unit": "percent"
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
      },
      {
        "id": 5,
        "title": "Request Rate (RPS)",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(gameforge_http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 6,
        "title": "Response Time Distribution",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(gameforge_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile",
            "refId": "A"
          },
          {
            "expr": "histogram_quantile(0.50, rate(gameforge_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile",
            "refId": "B"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 7,
        "title": "AI Inference Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(gameforge_inference_requests_total[5m])",
            "legendFormat": "Inference Rate",
            "refId": "A"
          },
          {
            "expr": "avg(gameforge_inference_duration_seconds)",
            "legendFormat": "Avg Duration",
            "refId": "B"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF
}

# ========================================================================
# Create Infrastructure Dashboard
# ========================================================================
create_infrastructure_dashboard() {
    echo "📊 Creating Infrastructure Dashboard..."
    
    cat > "${DASHBOARD_DIR}/gameforge-infrastructure.json" <<'EOF'
{
  "dashboard": {
    "id": null,
    "title": "GameForge AI - Infrastructure",
    "description": "Infrastructure metrics for GameForge AI platform",
    "tags": ["gameforge", "infrastructure", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "CPU Usage by Container",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total{name=~\"gameforge.*\"}[5m])*100",
            "legendFormat": "{{name}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {"unit": "percent", "max": 100}
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Memory Usage by Container",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage_bytes{name=~\"gameforge.*\"}/1024/1024",
            "legendFormat": "{{name}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {"unit": "decbytes"}
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Network I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_network_receive_bytes_total{name=~\"gameforge.*\"}[5m])",
            "legendFormat": "{{name}} RX",
            "refId": "A"
          },
          {
            "expr": "rate(container_network_transmit_bytes_total{name=~\"gameforge.*\"}[5m])",
            "legendFormat": "{{name}} TX",
            "refId": "B"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Disk I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_fs_reads_bytes_total{name=~\"gameforge.*\"}[5m])",
            "legendFormat": "{{name}} Read",
            "refId": "A"
          },
          {
            "expr": "rate(container_fs_writes_bytes_total{name=~\"gameforge.*\"}[5m])",
            "legendFormat": "{{name}} Write",
            "refId": "B"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF
}

# ========================================================================
# Create Security Dashboard
# ========================================================================
create_security_dashboard() {
    echo "📊 Creating Security Dashboard..."
    
    cat > "${DASHBOARD_DIR}/gameforge-security.json" <<'EOF'
{
  "dashboard": {
    "id": null,
    "title": "GameForge AI - Security Monitoring",
    "description": "Security events and authentication monitoring",
    "tags": ["gameforge", "security", "authentication"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Authentication Events",
        "type": "logs",
        "targets": [
          {
            "expr": "",
            "refId": "A",
            "query": "tags:security AND (auth OR login OR unauthorized)",
            "bucketAggs": []
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "HTTP Error Rates by Status Code",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(gameforge_http_requests_total{status=~\"4..|5..\"}[5m])",
            "legendFormat": "{{status}}",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 3,
        "title": "Failed Authentication Attempts",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(gameforge_auth_failures_total[1h])",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ]
  }
}
EOF
}

# ========================================================================
# Create AI/ML Performance Dashboard
# ========================================================================
create_aiml_dashboard() {
    echo "📊 Creating AI/ML Performance Dashboard..."
    
    cat > "${DASHBOARD_DIR}/gameforge-aiml.json" <<'EOF'
{
  "dashboard": {
    "id": null,
    "title": "GameForge AI - ML Performance",
    "description": "AI/ML specific performance metrics and GPU monitoring",
    "tags": ["gameforge", "ai", "ml", "gpu"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "GPU Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "gameforge_gpu_utilization_percent",
            "legendFormat": "GPU {{gpu_id}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {"unit": "percent", "max": 100}
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "GPU Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "gameforge_gpu_memory_used_bytes",
            "legendFormat": "GPU {{gpu_id}} Used",
            "refId": "A"
          },
          {
            "expr": "gameforge_gpu_memory_total_bytes",
            "legendFormat": "GPU {{gpu_id}} Total",
            "refId": "B"
          }
        ],
        "yAxes": [
          {"unit": "decbytes"}
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Inference Latency Distribution",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(gameforge_inference_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile",
            "refId": "A"
          },
          {
            "expr": "histogram_quantile(0.50, rate(gameforge_inference_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile",
            "refId": "B"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Model Performance by Type",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(gameforge_inference_requests_total[5m])",
            "legendFormat": "{{model_name}}",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ]
  }
}
EOF
}

# ========================================================================
# Setup datasources
# ========================================================================
setup_datasources() {
    echo "🔗 Setting up Grafana datasources..."
    
    # Prometheus datasource
    cat > "${PROVISIONING_DIR}/datasources/prometheus.yml" <<EOF
apiVersion: 1
datasources:
  - name: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "5s"
      queryTimeout: "60s"
      httpMethod: "POST"
    
  - name: elasticsearch
    type: elasticsearch
    access: proxy
    url: http://elasticsearch:9200
    database: "gameforge-logs-*"
    jsonData:
      index: "gameforge-logs-*"
      timeField: "@timestamp"
      esVersion: "7.10.0"
      logMessageField: "message"
      logLevelField: "log.level"
    secureJsonData:
      basicAuthPassword: "${ELASTIC_PASSWORD}"
    basicAuth: true
    basicAuthUser: "elastic"
EOF
}

# ========================================================================
# Main execution
# ========================================================================
main() {
    echo "🚀 GameForge Dashboard Auto-Import Starting..."
    
    # Create directories
    mkdir -p "${DASHBOARD_DIR}"
    mkdir -p "${PROVISIONING_DIR}/dashboards"
    mkdir -p "${PROVISIONING_DIR}/datasources"
    
    # Wait for Grafana
    wait_for_grafana
    
    # Setup datasources
    setup_datasources
    
    # Create API key (optional, will fallback to basic auth)
    create_api_key || echo "⚠️ Using basic authentication instead of API key"
    
    # Create dashboards
    create_overview_dashboard
    create_infrastructure_dashboard
    create_security_dashboard
    create_aiml_dashboard
    
    # Import all dashboards
    echo "📥 Importing dashboards..."
    for dashboard in "${DASHBOARD_DIR}"/*.json; do
        if [ -f "$dashboard" ]; then
            import_dashboard "$dashboard"
        fi
    done
    
    echo "✅ Dashboard auto-import completed!"
    echo "🌐 Access Grafana at: ${GRAFANA_URL}"
    echo "👤 Username: ${GRAFANA_USER}"
    echo "🔐 Password: ${GRAFANA_PASSWORD}"
    
    # Keep container running for continuous monitoring
    echo "🔄 Dashboard auto-import service running..."
    while true; do
        sleep 3600  # Check every hour for new dashboards
        echo "🔄 Checking for dashboard updates..."
        for dashboard in "${DASHBOARD_DIR}"/*.json; do
            if [ -f "$dashboard" ] && [ "$dashboard" -nt "/tmp/last_import" ]; then
                echo "📊 Detected updated dashboard, re-importing..."
                import_dashboard "$dashboard"
            fi
        done
        touch /tmp/last_import
    done
}

# Run main function
main "$@"