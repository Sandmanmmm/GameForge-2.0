#!/usr/bin/env python3
"""
========================================================================
GameForge AI - JSON Logging Configuration
Enterprise structured logging implementation
========================================================================
"""

import json
import os
import yaml
from datetime import datetime

def create_json_logging_config():
    """Create JSON logging configuration for all services"""
    
    # Docker Compose override for JSON logging
    json_logging_compose = {
        'version': '3.8',
        'services': {
            'gameforge-app': {
                'logging': {
                    'driver': 'json-file',
                    'options': {
                        'max-size': '10m',
                        'max-file': '3',
                        'labels': 'service,version,environment'
                    }
                },
                'environment': [
                    'LOG_FORMAT=json',
                    'LOG_LEVEL=info'
                ]
            },
            'gpu-inference': {
                'logging': {
                    'driver': 'json-file',
                    'options': {
                        'max-size': '10m',
                        'max-file': '3',
                        'labels': 'service,version,environment'
                    }
                },
                'environment': [
                    'LOG_FORMAT=json',
                    'LOG_LEVEL=info'
                ]
            },
            'redis': {
                'logging': {
                    'driver': 'json-file',
                    'options': {
                        'max-size': '10m',
                        'max-file': '3'
                    }
                }
            },
            'nginx': {
                'logging': {
                    'driver': 'json-file',
                    'options': {
                        'max-size': '10m',
                        'max-file': '3'
                    }
                }
            },
            'prometheus': {
                'logging': {
                    'driver': 'json-file',
                    'options': {
                        'max-size': '10m',
                        'max-file': '3'
                    }
                }
            },
            'grafana': {
                'logging': {
                    'driver': 'json-file',
                    'options': {
                        'max-size': '10m',
                        'max-file': '3'
                    }
                }
            }
        }
    }
    
    # Save JSON logging configuration
    with open('docker-compose.json-logging.yml', 'w') as f:
        yaml.dump(json_logging_compose, f, default_flow_style=False, indent=2)
    
    print("✅ JSON logging configuration created: docker-compose.json-logging.yml")

def create_filebeat_config():
    """Create Filebeat configuration for log aggregation"""
    
    filebeat_config = {
        'filebeat.inputs': [
            {
                'type': 'container',
                'paths': ['/var/lib/docker/containers/*/*.log'],
                'processors': [
                    {
                        'add_docker_metadata': {
                            'host': 'unix:///var/run/docker.sock'
                        }
                    }
                ]
            }
        ],
        'output.elasticsearch': {
            'hosts': ['elasticsearch:9200'],
            'index': 'gameforge-logs-%{+yyyy.MM.dd}'
        },
        'setup.template.name': 'gameforge-logs',
        'setup.template.pattern': 'gameforge-logs-*',
        'logging.level': 'info'
    }
    
    with open('filebeat.yml', 'w') as f:
        yaml.dump(filebeat_config, f, default_flow_style=False, indent=2)
    
    print("✅ Filebeat configuration created: filebeat.yml")

def create_nginx_json_config():
    """Create Nginx configuration with JSON logging"""
    
    nginx_config = '''
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # JSON logging format
    log_format json_combined escape=json
    '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"status": "$status",'
        '"body_bytes_sent":"$body_bytes_sent",'
        '"request_time":"$request_time",'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"upstream_addr":"$upstream_addr",'
        '"upstream_status":"$upstream_status",'
        '"upstream_response_time":"$upstream_response_time"'
    '}';

    access_log /var/log/nginx/access.log json_combined;
    error_log /var/log/nginx/error.log warn;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=1r/s;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    upstream gameforge_app {
        server gameforge-app:8080;
    }

    upstream gpu_inference {
        server gpu-inference:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # Rate limiting
        limit_req zone=general burst=5 nodelay;

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\\n";
            add_header Content-Type text/plain;
        }

        # API routes with higher rate limits
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://gameforge_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # GPU inference routes
        location /gpu/ {
            limit_req zone=api burst=10 nodelay;
            proxy_pass http://gpu_inference/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        # Default routes
        location / {
            proxy_pass http://gameforge_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
'''
    
    with open('nginx-json-logging.conf', 'w') as f:
        f.write(nginx_config)
    
    print("✅ Nginx JSON logging configuration created: nginx-json-logging.conf")

def create_metrics_endpoints():
    """Create metrics endpoint implementations"""
    
    # Python Flask metrics endpoint
    flask_metrics = '''
from flask import Flask, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import psutil
import threading

app = Flask(__name__)

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')
MEMORY_USAGE = Gauge('memory_usage_percent', 'Memory usage percentage')

def update_system_metrics():
    """Update system metrics in background"""
    while True:
        CPU_USAGE.set(psutil.cpu_percent())
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.percent)
        time.sleep(30)

# Start metrics update thread
metrics_thread = threading.Thread(target=update_system_metrics, daemon=True)
metrics_thread.start()

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': time.time()}

@app.before_request
def before_request():
    """Track request start time"""
    REQUEST_DURATION.time()

@app.after_request
def after_request(response):
    """Track request metrics"""
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
'''
    
    with open('gameforge_app_metrics.py', 'w') as f:
        f.write(flask_metrics)
    
    print("✅ Metrics endpoint implementation created: gameforge_app_metrics.py")

def create_grafana_provisioning():
    """Create Grafana dashboard provisioning"""
    
    # Provisioning configuration
    provisioning_config = {
        'apiVersion': 1,
        'providers': [
            {
                'name': 'gameforge-dashboards',
                'orgId': 1,
                'folder': '',
                'type': 'file',
                'disableDeletion': False,
                'updateIntervalSeconds': 10,
                'allowUiUpdates': True,
                'options': {
                    'path': '/etc/grafana/provisioning/dashboards'
                }
            }
        ]
    }
    
    os.makedirs('grafana/provisioning/dashboards', exist_ok=True)
    
    with open('grafana/provisioning/dashboards/dashboard.yml', 'w') as f:
        yaml.dump(provisioning_config, f, default_flow_style=False, indent=2)
    
    print("✅ Grafana dashboard provisioning created: grafana/provisioning/dashboards/")

def main():
    """Create all observability configurations"""
    print("Creating comprehensive observability configurations...")
    
    create_json_logging_config()
    create_filebeat_config()
    create_nginx_json_config()
    create_metrics_endpoints()
    create_grafana_provisioning()
    
    print("\n✅ ALL OBSERVABILITY CONFIGURATIONS CREATED")
    print("Next steps:")
    print("1. Deploy with: docker-compose -f docker-compose.yml -f docker-compose.json-logging.yml up")
    print("2. Copy nginx-json-logging.conf to nginx container")
    print("3. Add metrics endpoints to application code")
    print("4. Configure Grafana with provisioning")

if __name__ == "__main__":
    main()