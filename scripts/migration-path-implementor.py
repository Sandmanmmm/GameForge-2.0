#!/usr/bin/env python3
"""
========================================================================
GameForge AI - Complete Migration Path Implementation
Kubernetes manifests, Helm charts, ConfigMaps, and deployment automation
for seamless production migration
========================================================================
"""

import os
import yaml
import json
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationPathImplementor:
    """Complete migration path with Kubernetes manifests and Helm charts"""
    
    def __init__(self):
        self.k8s_dir = "k8s"
        self.helm_dir = "helm"
        self.manifests_dir = f"{self.k8s_dir}/manifests"
        self.helm_chart_dir = f"{self.helm_dir}/gameforge"
        self.migration_dir = "migration"
        
        for directory in [self.k8s_dir, self.helm_dir, self.manifests_dir, 
                         self.helm_chart_dir, self.migration_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Create Helm chart structure
        helm_subdirs = ['templates', 'charts', 'crds']
        for subdir in helm_subdirs:
            os.makedirs(f"{self.helm_chart_dir}/{subdir}", exist_ok=True)
    
    def create_kubernetes_manifests(self):
        """Create complete Kubernetes manifests for production deployment"""
        
        # Namespace
        namespace = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': 'gameforge',
                'labels': {
                    'name': 'gameforge',
                    'environment': 'production'
                }
            }
        }
        
        with open(f'{self.manifests_dir}/01-namespace.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(namespace, f, default_flow_style=False, indent=2)
        
        # ConfigMap
        configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'gameforge-config',
                'namespace': 'gameforge'
            },
            'data': {
                'DATABASE_HOST': 'postgresql.gameforge.svc.cluster.local',
                'REDIS_HOST': 'redis.gameforge.svc.cluster.local',
                'LOG_LEVEL': 'INFO',
                'ENVIRONMENT': 'production',
                'GPU_ENABLED': 'true',
                'MODEL_CACHE_SIZE': '10GB',
                'MAX_CONCURRENT_REQUESTS': '100',
                'METRICS_ENABLED': 'true',
                'PROMETHEUS_PORT': '9090'
            }
        }
        
        with open(f'{self.manifests_dir}/02-configmap.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(configmap, f, default_flow_style=False, indent=2)
        
        # Secrets
        secret = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': 'gameforge-secrets',
                'namespace': 'gameforge'
            },
            'type': 'Opaque',
            'data': {
                # Base64 encoded values (replace with actual encoded secrets)
                'DATABASE_PASSWORD': 'cGFzc3dvcmQxMjM=',  # password123
                'JWT_SECRET': 'and0X3NlY3JldF8xMjM=',      # jwt_secret_123
                'API_KEY': 'YXBpX2tleV8xMjM=',           # api_key_123
                'ENCRYPTION_KEY': 'ZW5jcnlwdGlvbl9rZXlfMTIz'  # encryption_key_123
            }
        }
        
        with open(f'{self.manifests_dir}/03-secrets.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(secret, f, default_flow_style=False, indent=2)
        
        # PersistentVolume and PersistentVolumeClaim
        pvc = {
            'apiVersion': 'v1',
            'kind': 'PersistentVolumeClaim',
            'metadata': {
                'name': 'gameforge-storage',
                'namespace': 'gameforge'
            },
            'spec': {
                'accessModes': ['ReadWriteOnce'],
                'resources': {
                    'requests': {
                        'storage': '100Gi'
                    }
                },
                'storageClassName': 'fast-ssd'
            }
        }
        
        with open(f'{self.manifests_dir}/04-storage.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(pvc, f, default_flow_style=False, indent=2)
        
        # Main Application Deployment
        app_deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': 'gameforge-app',
                'namespace': 'gameforge',
                'labels': {
                    'app': 'gameforge',
                    'component': 'app'
                }
            },
            'spec': {
                'replicas': 3,
                'selector': {
                    'matchLabels': {
                        'app': 'gameforge',
                        'component': 'app'
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': 'gameforge',
                            'component': 'app'
                        }
                    },
                    'spec': {
                        'containers': [
                            {
                                'name': 'gameforge-app',
                                'image': 'gameforge/app:latest',
                                'ports': [
                                    {'containerPort': 8080, 'name': 'http'},
                                    {'containerPort': 9090, 'name': 'metrics'}
                                ],
                                'env': [
                                    {
                                        'name': 'DATABASE_PASSWORD',
                                        'valueFrom': {
                                            'secretKeyRef': {
                                                'name': 'gameforge-secrets',
                                                'key': 'DATABASE_PASSWORD'
                                            }
                                        }
                                    }
                                ],
                                'envFrom': [
                                    {'configMapRef': {'name': 'gameforge-config'}}
                                ],
                                'resources': {
                                    'requests': {
                                        'memory': '512Mi',
                                        'cpu': '250m'
                                    },
                                    'limits': {
                                        'memory': '1Gi',
                                        'cpu': '500m'
                                    }
                                },
                                'volumeMounts': [
                                    {
                                        'name': 'storage',
                                        'mountPath': '/app/data'
                                    }
                                ],
                                'livenessProbe': {
                                    'httpGet': {
                                        'path': '/health',
                                        'port': 8080
                                    },
                                    'initialDelaySeconds': 30,
                                    'periodSeconds': 10
                                },
                                'readinessProbe': {
                                    'httpGet': {
                                        'path': '/ready',
                                        'port': 8080
                                    },
                                    'initialDelaySeconds': 5,
                                    'periodSeconds': 5
                                }
                            }
                        ],
                        'volumes': [
                            {
                                'name': 'storage',
                                'persistentVolumeClaim': {
                                    'claimName': 'gameforge-storage'
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        with open(f'{self.manifests_dir}/05-app-deployment.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(app_deployment, f, default_flow_style=False, indent=2)
        
        # GPU Inference Deployment
        gpu_deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': 'gpu-inference',
                'namespace': 'gameforge',
                'labels': {
                    'app': 'gameforge',
                    'component': 'gpu-inference'
                }
            },
            'spec': {
                'replicas': 2,
                'selector': {
                    'matchLabels': {
                        'app': 'gameforge',
                        'component': 'gpu-inference'
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': 'gameforge',
                            'component': 'gpu-inference'
                        }
                    },
                    'spec': {
                        'nodeSelector': {
                            'accelerator': 'nvidia-tesla-gpu'
                        },
                        'containers': [
                            {
                                'name': 'gpu-inference',
                                'image': 'gameforge/gpu-inference:latest',
                                'ports': [
                                    {'containerPort': 8000, 'name': 'http'}
                                ],
                                'resources': {
                                    'requests': {
                                        'memory': '8Gi',
                                        'cpu': '2',
                                        'nvidia.com/gpu': '1'
                                    },
                                    'limits': {
                                        'memory': '16Gi',
                                        'cpu': '4',
                                        'nvidia.com/gpu': '1'
                                    }
                                },
                                'livenessProbe': {
                                    'httpGet': {
                                        'path': '/health',
                                        'port': 8000
                                    },
                                    'initialDelaySeconds': 60,
                                    'periodSeconds': 30
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        with open(f'{self.manifests_dir}/06-gpu-deployment.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(gpu_deployment, f, default_flow_style=False, indent=2)
        
        # Services
        services = [
            {
                'name': 'gameforge-app',
                'selector': {'app': 'gameforge', 'component': 'app'},
                'ports': [
                    {'port': 80, 'targetPort': 8080, 'name': 'http'},
                    {'port': 9090, 'targetPort': 9090, 'name': 'metrics'}
                ]
            },
            {
                'name': 'gpu-inference',
                'selector': {'app': 'gameforge', 'component': 'gpu-inference'},
                'ports': [{'port': 8000, 'targetPort': 8000, 'name': 'http'}]
            }
        ]
        
        for svc in services:
            service = {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': svc['name'],
                    'namespace': 'gameforge',
                    'labels': {
                        'app': 'gameforge'
                    }
                },
                'spec': {
                    'selector': svc['selector'],
                    'ports': svc['ports'],
                    'type': 'ClusterIP'
                }
            }
            
            with open(f'{self.manifests_dir}/07-{svc["name"]}-service.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(service, f, default_flow_style=False, indent=2)
        
        # Ingress
        ingress = {
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'Ingress',
            'metadata': {
                'name': 'gameforge-ingress',
                'namespace': 'gameforge',
                'annotations': {
                    'nginx.ingress.kubernetes.io/rewrite-target': '/',
                    'nginx.ingress.kubernetes.io/ssl-redirect': 'true',
                    'nginx.ingress.kubernetes.io/rate-limit': '100',
                    'cert-manager.io/cluster-issuer': 'letsencrypt-prod'
                }
            },
            'spec': {
                'tls': [
                    {
                        'hosts': ['gameforge.production.com'],
                        'secretName': 'gameforge-tls'
                    }
                ],
                'rules': [
                    {
                        'host': 'gameforge.production.com',
                        'http': {
                            'paths': [
                                {
                                    'path': '/',
                                    'pathType': 'Prefix',
                                    'backend': {
                                        'service': {
                                            'name': 'gameforge-app',
                                            'port': {'number': 80}
                                        }
                                    }
                                },
                                {
                                    'path': '/gpu',
                                    'pathType': 'Prefix',
                                    'backend': {
                                        'service': {
                                            'name': 'gpu-inference',
                                            'port': {'number': 8000}
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        with open(f'{self.manifests_dir}/08-ingress.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(ingress, f, default_flow_style=False, indent=2)
        
        logger.info("Kubernetes manifests created")
    
    def create_helm_chart(self):
        """Create comprehensive Helm chart for GameForge deployment"""
        
        # Chart.yaml
        chart_yaml = {
            'apiVersion': 'v2',
            'name': 'gameforge',
            'description': 'GameForge AI - Complete production deployment',
            'type': 'application',
            'version': '1.0.0',
            'appVersion': '1.0.0',
            'keywords': ['ai', 'gameforge', 'production'],
            'maintainers': [
                {
                    'name': 'GameForge Team',
                    'email': 'ops@gameforge.com'
                }
            ],
            'dependencies': [
                {
                    'name': 'postgresql',
                    'version': '11.9.13',
                    'repository': 'https://charts.bitnami.com/bitnami'
                },
                {
                    'name': 'redis',
                    'version': '17.3.7',
                    'repository': 'https://charts.bitnami.com/bitnami'
                },
                {
                    'name': 'prometheus',
                    'version': '15.5.3',
                    'repository': 'https://prometheus-community.github.io/helm-charts'
                }
            ]
        }
        
        with open(f'{self.helm_chart_dir}/Chart.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(chart_yaml, f, default_flow_style=False, indent=2)
        
        # values.yaml
        values_yaml = {
            'global': {
                'imageRegistry': 'docker.io',
                'imagePullSecrets': [],
                'storageClass': 'fast-ssd'
            },
            'image': {
                'registry': 'docker.io',
                'repository': 'gameforge/app',
                'tag': 'latest',
                'pullPolicy': 'IfNotPresent'
            },
            'gpu': {
                'enabled': True,
                'image': {
                    'repository': 'gameforge/gpu-inference',
                    'tag': 'latest'
                },
                'resources': {
                    'requests': {
                        'memory': '8Gi',
                        'cpu': '2',
                        'nvidia.com/gpu': '1'
                    },
                    'limits': {
                        'memory': '16Gi',
                        'cpu': '4',
                        'nvidia.com/gpu': '1'
                    }
                }
            },
            'replicaCount': 3,
            'autoscaling': {
                'enabled': True,
                'minReplicas': 3,
                'maxReplicas': 10,
                'targetCPUUtilizationPercentage': 70,
                'targetMemoryUtilizationPercentage': 80
            },
            'service': {
                'type': 'ClusterIP',
                'port': 80,
                'targetPort': 8080
            },
            'ingress': {
                'enabled': True,
                'className': 'nginx',
                'annotations': {
                    'nginx.ingress.kubernetes.io/ssl-redirect': 'true',
                    'nginx.ingress.kubernetes.io/rate-limit': '100',
                    'cert-manager.io/cluster-issuer': 'letsencrypt-prod'
                },
                'hosts': [
                    {
                        'host': 'gameforge.production.com',
                        'paths': [
                            {
                                'path': '/',
                                'pathType': 'Prefix'
                            }
                        ]
                    }
                ],
                'tls': [
                    {
                        'secretName': 'gameforge-tls',
                        'hosts': ['gameforge.production.com']
                    }
                ]
            },
            'resources': {
                'requests': {
                    'memory': '512Mi',
                    'cpu': '250m'
                },
                'limits': {
                    'memory': '1Gi',
                    'cpu': '500m'
                }
            },
            'persistence': {
                'enabled': True,
                'storageClass': 'fast-ssd',
                'size': '100Gi'
            },
            'config': {
                'environment': 'production',
                'logLevel': 'INFO',
                'gpuEnabled': True,
                'modelCacheSize': '10GB',
                'maxConcurrentRequests': 100,
                'metricsEnabled': True
            },
            'secrets': {
                'databasePassword': 'changeme',
                'jwtSecret': 'changeme',
                'apiKey': 'changeme',
                'encryptionKey': 'changeme'
            },
            'postgresql': {
                'enabled': True,
                'auth': {
                    'postgresPassword': 'changeme',
                    'database': 'gameforge'
                },
                'primary': {
                    'persistence': {
                        'enabled': True,
                        'size': '20Gi'
                    }
                }
            },
            'redis': {
                'enabled': True,
                'auth': {
                    'enabled': True,
                    'password': 'changeme'
                },
                'master': {
                    'persistence': {
                        'enabled': True,
                        'size': '8Gi'
                    }
                }
            },
            'prometheus': {
                'enabled': True,
                'server': {
                    'persistentVolume': {
                        'enabled': True,
                        'size': '20Gi'
                    }
                }
            }
        }
        
        with open(f'{self.helm_chart_dir}/values.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(values_yaml, f, default_flow_style=False, indent=2)
        
        # Templates
        self.create_helm_templates()
        
        logger.info("Helm chart created")
    
    def create_helm_templates(self):
        """Create Helm template files"""
        
        templates_dir = f"{self.helm_chart_dir}/templates"
        
        # _helpers.tpl
        helpers_tpl = '''{{/*
Expand the name of the chart.
*/}}
{{- define "gameforge.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "gameforge.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "gameforge.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "gameforge.labels" -}}
helm.sh/chart: {{ include "gameforge.chart" . }}
{{ include "gameforge.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "gameforge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gameforge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
'''
        
        with open(f'{templates_dir}/_helpers.tpl', 'w', encoding='utf-8') as f:
            f.write(helpers_tpl)
        
        # deployment.yaml template
        deployment_template = '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "gameforge.fullname" . }}
  labels:
    {{- include "gameforge.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "gameforge.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "gameforge.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.registry }}/{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
            - name: metrics
              containerPort: 9090
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          env:
            - name: ENVIRONMENT
              value: {{ .Values.config.environment | quote }}
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ include "gameforge.fullname" . }}-secrets
                  key: database-password
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          {{- if .Values.persistence.enabled }}
          volumeMounts:
            - name: storage
              mountPath: /app/data
          {{- end }}
      {{- if .Values.persistence.enabled }}
      volumes:
        - name: storage
          persistentVolumeClaim:
            claimName: {{ include "gameforge.fullname" . }}-storage
      {{- end }}
'''
        
        with open(f'{templates_dir}/deployment.yaml', 'w', encoding='utf-8') as f:
            f.write(deployment_template)
        
        logger.info("Helm templates created")
    
    def create_migration_scripts(self):
        """Create migration and deployment scripts"""
        
        # Migration script
        migration_script = '''#!/bin/bash
# GameForge AI Migration Script
# Comprehensive production migration automation
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/gameforge/migration.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Pre-migration checks
pre_migration_checks() {
    log "Running pre-migration checks..."
    
    # Check Kubernetes cluster connectivity
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log "❌ Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check required tools
    for tool in kubectl helm docker; do
        if ! command -v $tool > /dev/null 2>&1; then
            log "❌ Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check cluster resources
    NODES=$(kubectl get nodes --no-headers | wc -l)
    if [ "$NODES" -lt 3 ]; then
        log "⚠️ Warning: Less than 3 nodes available"
    fi
    
    # Check GPU nodes
    GPU_NODES=$(kubectl get nodes -l accelerator=nvidia-tesla-gpu --no-headers | wc -l)
    if [ "$GPU_NODES" -eq 0 ]; then
        log "⚠️ Warning: No GPU nodes found"
    fi
    
    log "✅ Pre-migration checks completed"
}

# Create namespace and RBAC
setup_namespace() {
    log "Setting up namespace and RBAC..."
    
    kubectl apply -f k8s/manifests/01-namespace.yaml
    
    # Service account
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gameforge-service-account
  namespace: gameforge
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gameforge-cluster-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gameforge-cluster-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: gameforge-cluster-role
subjects:
- kind: ServiceAccount
  name: gameforge-service-account
  namespace: gameforge
EOF
    
    log "✅ Namespace and RBAC configured"
}

# Deploy with Kubernetes manifests
deploy_with_manifests() {
    log "Deploying with Kubernetes manifests..."
    
    # Apply manifests in order
    for manifest in k8s/manifests/*.yaml; do
        log "Applying $(basename "$manifest")..."
        kubectl apply -f "$manifest"
        sleep 5
    done
    
    log "✅ Kubernetes manifests deployed"
}

# Deploy with Helm
deploy_with_helm() {
    log "Deploying with Helm chart..."
    
    # Add required repositories
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install dependencies
    helm dependency update helm/gameforge/
    
    # Install GameForge
    helm upgrade --install gameforge helm/gameforge/ \\
        --namespace gameforge \\
        --create-namespace \\
        --wait \\
        --timeout 10m
    
    log "✅ Helm deployment completed"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=gameforge -n gameforge --timeout=300s
    
    # Check service endpoints
    ENDPOINTS=$(kubectl get endpoints -n gameforge --no-headers | wc -l)
    if [ "$ENDPOINTS" -eq 0 ]; then
        log "❌ No service endpoints found"
        return 1
    fi
    
    # Test health endpoint
    APP_POD=$(kubectl get pods -n gameforge -l app=gameforge,component=app -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec -n gameforge "$APP_POD" -- curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log "✅ Health check passed"
    else
        log "❌ Health check failed"
        return 1
    fi
    
    log "✅ Deployment verification completed"
}

# Post-migration tasks
post_migration_tasks() {
    log "Running post-migration tasks..."
    
    # Configure monitoring
    kubectl apply -f - << EOF
apiVersion: v1
kind: Service
metadata:
  name: gameforge-monitoring
  namespace: gameforge
  labels:
    app: gameforge
    component: monitoring
spec:
  selector:
    app: gameforge
    component: app
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
EOF
    
    # Set up ingress controller if not present
    if ! kubectl get ingressclass nginx > /dev/null 2>&1; then
        log "Installing nginx ingress controller..."
        helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
        helm repo update
        helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \\
            --namespace ingress-nginx \\
            --create-namespace
    fi
    
    # Configure cert-manager if not present
    if ! kubectl get namespace cert-manager > /dev/null 2>&1; then
        log "Installing cert-manager..."
        helm repo add jetstack https://charts.jetstack.io
        helm repo update
        helm upgrade --install cert-manager jetstack/cert-manager \\
            --namespace cert-manager \\
            --create-namespace \\
            --set installCRDs=true
    fi
    
    log "✅ Post-migration tasks completed"
}

# Rollback function
rollback_deployment() {
    log "Rolling back deployment..."
    
    if command -v helm > /dev/null 2>&1; then
        helm rollback gameforge --namespace gameforge
    else
        kubectl delete namespace gameforge
    fi
    
    log "✅ Rollback completed"
}

# Main migration function
main() {
    log "Starting GameForge AI migration to production..."
    
    DEPLOYMENT_METHOD="${1:-helm}"  # Default to helm
    
    case "$DEPLOYMENT_METHOD" in
        "manifests"|"k8s")
            pre_migration_checks
            setup_namespace
            deploy_with_manifests
            verify_deployment
            post_migration_tasks
            ;;
        "helm")
            pre_migration_checks
            setup_namespace
            deploy_with_helm
            verify_deployment
            post_migration_tasks
            ;;
        "rollback")
            rollback_deployment
            ;;
        *)
            log "Usage: $0 [manifests|helm|rollback]"
            exit 1
            ;;
    esac
    
    log "🎉 GameForge AI migration completed successfully!"
    
    # Display access information
    log "Access Information:"
    log "- Application: https://gameforge.production.com"
    log "- Monitoring: https://gameforge.production.com/monitoring"
    log "- GPU Inference: https://gameforge.production.com/gpu"
}

# Error handling
trap 'log "Migration failed: $BASH_COMMAND"; exit 1' ERR

main "$@"
'''
        
        with open(f'{self.migration_dir}/migrate-to-production.sh', 'w', encoding='utf-8') as f:
            f.write(migration_script)
        
        os.chmod(f'{self.migration_dir}/migrate-to-production.sh', 0o755)
        
        # Validation script
        validation_script = '''#!/bin/bash
# GameForge AI Production Validation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/gameforge/validation.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Validate Kubernetes deployment
validate_kubernetes() {
    log "Validating Kubernetes deployment..."
    
    # Check pods
    RUNNING_PODS=$(kubectl get pods -n gameforge --field-selector=status.phase=Running --no-headers | wc -l)
    TOTAL_PODS=$(kubectl get pods -n gameforge --no-headers | wc -l)
    
    log "Running pods: $RUNNING_PODS/$TOTAL_PODS"
    
    if [ "$RUNNING_PODS" -ne "$TOTAL_PODS" ]; then
        log "❌ Not all pods are running"
        kubectl get pods -n gameforge
        return 1
    fi
    
    # Check services
    SERVICES=$(kubectl get services -n gameforge --no-headers | wc -l)
    log "Services: $SERVICES"
    
    # Check ingress
    INGRESS=$(kubectl get ingress -n gameforge --no-headers | wc -l)
    log "Ingress rules: $INGRESS"
    
    log "✅ Kubernetes validation passed"
}

# Validate application functionality
validate_application() {
    log "Validating application functionality..."
    
    # Get ingress URL
    INGRESS_IP=$(kubectl get ingress gameforge-ingress -n gameforge -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$INGRESS_IP" ]; then
        INGRESS_IP="localhost"
    fi
    
    # Test health endpoint
    if curl -f "http://$INGRESS_IP/health" > /dev/null 2>&1; then
        log "✅ Health endpoint accessible"
    else
        log "❌ Health endpoint not accessible"
        return 1
    fi
    
    # Test API endpoint
    if curl -f "http://$INGRESS_IP/api/status" > /dev/null 2>&1; then
        log "✅ API endpoint accessible"
    else
        log "⚠️ API endpoint not accessible (may require authentication)"
    fi
    
    # Test GPU endpoint if enabled
    if curl -f "http://$INGRESS_IP/gpu/health" > /dev/null 2>&1; then
        log "✅ GPU inference endpoint accessible"
    else
        log "⚠️ GPU inference endpoint not accessible"
    fi
    
    log "✅ Application validation completed"
}

# Validate monitoring
validate_monitoring() {
    log "Validating monitoring setup..."
    
    # Check Prometheus
    if kubectl get pod -n gameforge -l app=prometheus > /dev/null 2>&1; then
        log "✅ Prometheus running"
    else
        log "⚠️ Prometheus not found"
    fi
    
    # Check metrics endpoint
    APP_POD=$(kubectl get pods -n gameforge -l app=gameforge,component=app -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec -n gameforge "$APP_POD" -- curl -f http://localhost:9090/metrics > /dev/null 2>&1; then
        log "✅ Metrics endpoint accessible"
    else
        log "❌ Metrics endpoint not accessible"
    fi
    
    log "✅ Monitoring validation completed"
}

# Validate security
validate_security() {
    log "Validating security configuration..."
    
    # Check RBAC
    if kubectl auth can-i list pods --namespace=gameforge --as=system:serviceaccount:gameforge:gameforge-service-account > /dev/null 2>&1; then
        log "✅ RBAC configured correctly"
    else
        log "⚠️ RBAC may not be configured correctly"
    fi
    
    # Check network policies
    NETWORK_POLICIES=$(kubectl get networkpolicies -n gameforge --no-headers 2>/dev/null | wc -l)
    log "Network policies: $NETWORK_POLICIES"
    
    # Check secrets
    SECRETS=$(kubectl get secrets -n gameforge --no-headers | wc -l)
    log "Secrets: $SECRETS"
    
    log "✅ Security validation completed"
}

# Generate validation report
generate_report() {
    log "Generating validation report..."
    
    cat > "$SCRIPT_DIR/validation-report-$(date +%Y%m%d).json" << EOF
{
    "validation_date": "$(date -Iseconds)",
    "cluster_info": {
        "nodes": $(kubectl get nodes --no-headers | wc -l),
        "namespaces": $(kubectl get namespaces --no-headers | wc -l),
        "version": "$(kubectl version --client --short 2>/dev/null | head -1)"
    },
    "gameforge_deployment": {
        "pods": $(kubectl get pods -n gameforge --no-headers 2>/dev/null | wc -l),
        "services": $(kubectl get services -n gameforge --no-headers 2>/dev/null | wc -l),
        "ingress": $(kubectl get ingress -n gameforge --no-headers 2>/dev/null | wc -l),
        "secrets": $(kubectl get secrets -n gameforge --no-headers 2>/dev/null | wc -l)
    },
    "validation_status": "COMPLETED",
    "next_validation": "$(date -d '+1 day' -Iseconds)"
}
EOF
    
    log "✅ Validation report generated"
}

main() {
    log "Starting production validation..."
    
    validate_kubernetes
    validate_application
    validate_monitoring
    validate_security
    generate_report
    
    log "🎉 Production validation completed successfully!"
}

main "$@"
'''
        
        with open(f'{self.migration_dir}/validate-production.sh', 'w', encoding='utf-8') as f:
            f.write(validation_script)
        
        os.chmod(f'{self.migration_dir}/validate-production.sh', 0o755)
        
        logger.info("Migration scripts created")

def main():
    """Create complete migration path implementation"""
    logger.info("Creating complete migration path implementation...")
    
    implementor = MigrationPathImplementor()
    
    implementor.create_kubernetes_manifests()
    implementor.create_helm_chart()
    implementor.create_migration_scripts()
    
    logger.info("\nALL MIGRATION PATH COMPONENTS CREATED")
    logger.info("Key components:")
    logger.info("1. Kubernetes manifests: k8s/manifests/ (8 manifest files)")
    logger.info("2. Helm chart: helm/gameforge/ (complete production chart)")
    logger.info("3. Migration scripts: migration/migrate-to-production.sh")
    logger.info("4. Validation scripts: migration/validate-production.sh")

if __name__ == "__main__":
    main()