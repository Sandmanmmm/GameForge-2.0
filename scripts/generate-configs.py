#!/usr/bin/env python3
"""
GameForge Configuration Generator
Generates Docker Compose and Kubernetes manifests from single source of truth
"""

import yaml
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import argparse

class ConfigGenerator:
    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.global_config = self.config.get('global', {})
        self.services = self.config.get('services', {})
        self.networking = self.config.get('networking', {})
        self.storage = self.config.get('storage', {})

    def generate_docker_compose(self, output_file: str = "docker-compose.generated.yml"):
        """Generate Docker Compose from service definitions"""
        compose = {
            'version': '3.8',
            'services': {},
            'volumes': {},
            'networks': {
                'gameforge': {
                    'driver': 'bridge'
                }
            }
        }

        # Generate services
        for service_name, service_config in self.services.items():
            compose_service = self._service_to_compose(service_name, service_config)
            compose['services'][service_name] = compose_service

        # Generate volumes
        for service_name, service_config in self.services.items():
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                if volume.get('type') == 'persistentVolume':
                    volume_name = f"{service_name}_{volume['name']}"
                    compose['volumes'][volume_name] = {
                        'driver': 'local'
                    }

        # Write to file
        with open(output_file, 'w') as f:
            yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Generated Docker Compose: {output_file}")

    def generate_kubernetes(self, output_dir: str = "k8s/generated"):
        """Generate Kubernetes manifests from service definitions"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate namespace
        self._generate_namespace(output_dir)

        # Generate each service
        for service_name, service_config in self.services.items():
            self._generate_k8s_service(service_name, service_config, output_dir)

        # Generate ingress
        if self.networking.get('ingress', {}).get('enabled'):
            self._generate_ingress(output_dir)

        # Generate storage classes
        self._generate_storage_classes(output_dir)

        print(f"✅ Generated Kubernetes manifests in: {output_dir}")

    def _service_to_compose(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert service config to Docker Compose format"""
        compose_service = {
            'image': config['image'],
            'container_name': f"gameforge_{name}",
            'restart': 'unless-stopped',
            'networks': ['gameforge']
        }

        # Ports
        if 'ports' in config:
            compose_service['ports'] = []
            for port in config['ports']:
                compose_service['ports'].append(f"{port['port']}:{port['targetPort']}")

        # Environment
        if 'environment' in config:
            compose_service['environment'] = config['environment']

        # Volumes
        if 'volumes' in config:
            compose_service['volumes'] = []
            for volume in config['volumes']:
                if volume.get('type') == 'persistentVolume':
                    volume_name = f"{name}_{volume['name']}"
                    compose_service['volumes'].append(f"{volume_name}:{volume['mountPath']}")
                elif volume.get('type') == 'emptyDir':
                    # Use tmpfs for emptyDir
                    compose_service.setdefault('tmpfs', []).append(volume['mountPath'])

        # Health check
        if 'healthCheck' in config:
            hc = config['healthCheck']
            if 'path' in hc:
                compose_service['healthcheck'] = {
                    'test': f"curl -f http://localhost:{hc['port']}{hc['path']} || exit 1",
                    'interval': f"{hc.get('periodSeconds', 30)}s",
                    'timeout': '3s',
                    'retries': 3,
                    'start_period': f"{hc.get('initialDelaySeconds', 10)}s"
                }

        # Resources (Docker Compose deploy section)
        if 'resources' in config:
            resources = config['resources']
            compose_service['deploy'] = {
                'resources': {
                    'limits': {
                        'cpus': resources.get('limits', {}).get('cpu', '1.0').rstrip('m'),
                        'memory': resources.get('limits', {}).get('memory', '512M')
                    },
                    'reservations': {
                        'cpus': resources.get('requests', {}).get('cpu', '0.1').rstrip('m'),
                        'memory': resources.get('requests', {}).get('memory', '128M')
                    }
                }
            }

            # GPU support
            if 'nvidia.com/gpu' in resources.get('requests', {}):
                compose_service['deploy']['resources']['reservations']['devices'] = [{
                    'driver': 'nvidia',
                    'count': int(resources['requests']['nvidia.com/gpu']),
                    'capabilities': ['gpu']
                }]

        # Replicas
        if 'replicas' in config and config['replicas'] > 1:
            compose_service['deploy'] = compose_service.get('deploy', {})
            compose_service['deploy']['replicas'] = config['replicas']

        return compose_service

    def _generate_namespace(self, output_dir: str):
        """Generate Kubernetes namespace"""
        namespace = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': self.global_config.get('namespace', 'gameforge'),
                'labels': {
                    'app.kubernetes.io/name': self.global_config.get('project', 'gameforge'),
                    'app.kubernetes.io/version': self.global_config.get('version', '1.0.0')
                }
            }
        }

        with open(f"{output_dir}/00-namespace.yaml", 'w') as f:
            yaml.dump(namespace, f, default_flow_style=False)

    def _generate_k8s_service(self, name: str, config: Dict[str, Any], output_dir: str):
        """Generate Kubernetes Deployment and Service for a service"""
        
        # Generate Deployment
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': name,
                'namespace': self.global_config.get('namespace', 'gameforge'),
                'labels': {
                    'app': name,
                    'app.kubernetes.io/name': name,
                    'app.kubernetes.io/component': config.get('type', 'service')
                }
            },
            'spec': {
                'replicas': config.get('replicas', 1),
                'selector': {
                    'matchLabels': {
                        'app': name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': name
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': name,
                            'image': config['image'],
                            'ports': [{'containerPort': port['targetPort'], 'name': port['name']} 
                                     for port in config.get('ports', [])],
                            'resources': config.get('resources', {}),
                            'env': [{'name': k, 'value': str(v)} 
                                   for k, v in config.get('environment', {}).items()],
                            'securityContext': {
                                'runAsNonRoot': True,
                                'allowPrivilegeEscalation': False,
                                'readOnlyRootFilesystem': True,
                                'capabilities': {'drop': ['ALL']}
                            }
                        }],
                        'securityContext': {
                            'fsGroup': 1001,
                            'runAsGroup': 1001,
                            'runAsUser': 1001
                        }
                    }
                }
            }
        }

        # Add volumes if present
        if 'volumes' in config:
            deployment['spec']['template']['spec']['volumes'] = []
            deployment['spec']['template']['spec']['containers'][0]['volumeMounts'] = []
            
            for volume in config['volumes']:
                volume_name = volume['name']
                
                if volume.get('type') == 'persistentVolume':
                    # PVC
                    deployment['spec']['template']['spec']['volumes'].append({
                        'name': volume_name,
                        'persistentVolumeClaim': {
                            'claimName': f"{name}-{volume_name}"
                        }
                    })
                elif volume.get('type') == 'emptyDir':
                    deployment['spec']['template']['spec']['volumes'].append({
                        'name': volume_name,
                        'emptyDir': {}
                    })
                
                deployment['spec']['template']['spec']['containers'][0]['volumeMounts'].append({
                    'name': volume_name,
                    'mountPath': volume['mountPath']
                })

        # Add health checks
        if 'healthCheck' in config:
            hc = config['healthCheck']
            container = deployment['spec']['template']['spec']['containers'][0]
            
            if 'path' in hc:
                container['livenessProbe'] = {
                    'httpGet': {
                        'path': hc['path'],
                        'port': hc['port']
                    },
                    'initialDelaySeconds': hc.get('initialDelaySeconds', 30),
                    'periodSeconds': hc.get('periodSeconds', 30)
                }
                container['readinessProbe'] = {
                    'httpGet': {
                        'path': hc['path'],
                        'port': hc['port']
                    },
                    'initialDelaySeconds': hc.get('initialDelaySeconds', 10),
                    'periodSeconds': hc.get('periodSeconds', 10)
                }

        # Generate Service
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': name,
                'namespace': self.global_config.get('namespace', 'gameforge'),
                'labels': {
                    'app': name
                }
            },
            'spec': {
                'selector': {
                    'app': name
                },
                'ports': [{'port': port['port'], 'targetPort': port['targetPort'], 'name': port['name']} 
                         for port in config.get('ports', [])]
            }
        }

        # Write files
        with open(f"{output_dir}/{name}-deployment.yaml", 'w') as f:
            yaml.dump(deployment, f, default_flow_style=False)

        with open(f"{output_dir}/{name}-service.yaml", 'w') as f:
            yaml.dump(service, f, default_flow_style=False)

        # Generate PVCs if needed
        if 'volumes' in config:
            for volume in config['volumes']:
                if volume.get('type') == 'persistentVolume':
                    pvc = {
                        'apiVersion': 'v1',
                        'kind': 'PersistentVolumeClaim',
                        'metadata': {
                            'name': f"{name}-{volume['name']}",
                            'namespace': self.global_config.get('namespace', 'gameforge')
                        },
                        'spec': {
                            'accessModes': ['ReadWriteOnce'],
                            'resources': {
                                'requests': {
                                    'storage': volume.get('size', '10Gi')
                                }
                            },
                            'storageClassName': volume.get('storageClass', 'standard')
                        }
                    }
                    
                    with open(f"{output_dir}/{name}-{volume['name']}-pvc.yaml", 'w') as f:
                        yaml.dump(pvc, f, default_flow_style=False)

        # Generate HPA if scaling is configured
        if 'scaling' in config:
            scaling = config['scaling']
            hpa = {
                'apiVersion': 'autoscaling/v2',
                'kind': 'HorizontalPodAutoscaler',
                'metadata': {
                    'name': f"{name}-hpa",
                    'namespace': self.global_config.get('namespace', 'gameforge')
                },
                'spec': {
                    'scaleTargetRef': {
                        'apiVersion': 'apps/v1',
                        'kind': 'Deployment',
                        'name': name
                    },
                    'minReplicas': scaling.get('minReplicas', 1),
                    'maxReplicas': scaling.get('maxReplicas', 10),
                    'metrics': [{
                        'type': 'Resource',
                        'resource': {
                            'name': 'cpu',
                            'target': {
                                'type': 'Utilization',
                                'averageUtilization': scaling.get('targetCPU', 80)
                            }
                        }
                    }]
                }
            }
            
            with open(f"{output_dir}/{name}-hpa.yaml", 'w') as f:
                yaml.dump(hpa, f, default_flow_style=False)

    def _generate_ingress(self, output_dir: str):
        """Generate Kubernetes Ingress"""
        ingress_config = self.networking['ingress']
        
        ingress = {
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'Ingress',
            'metadata': {
                'name': 'gameforge-ingress',
                'namespace': self.global_config.get('namespace', 'gameforge'),
                'annotations': ingress_config.get('annotations', {})
            },
            'spec': {
                'ingressClassName': ingress_config.get('className', 'nginx'),
                'rules': []
            }
        }

        # Add TLS
        if 'tls' in ingress_config:
            ingress['spec']['tls'] = [{
                'hosts': [rule['host'] for rule in ingress_config['rules']],
                'secretName': ingress_config['tls']['secretName']
            }]

        # Add rules
        for rule in ingress_config['rules']:
            ingress['spec']['rules'].append({
                'host': rule['host'],
                'http': {
                    'paths': [{
                        'path': '/',
                        'pathType': 'Prefix',
                        'backend': {
                            'service': {
                                'name': rule['service'],
                                'port': {
                                    'number': rule['port']
                                }
                            }
                        }
                    }]
                }
            })

        with open(f"{output_dir}/ingress.yaml", 'w') as f:
            yaml.dump(ingress, f, default_flow_style=False)

    def _generate_storage_classes(self, output_dir: str):
        """Generate Kubernetes StorageClasses"""
        if 'classes' in self.storage:
            for storage_class in self.storage['classes']:
                sc = {
                    'apiVersion': 'storage.k8s.io/v1',
                    'kind': 'StorageClass',
                    'metadata': {
                        'name': storage_class['name']
                    },
                    'provisioner': storage_class['provisioner'],
                    'parameters': storage_class.get('parameters', {}),
                    'allowVolumeExpansion': True
                }
                
                with open(f"{output_dir}/storage-class-{storage_class['name']}.yaml", 'w') as f:
                    yaml.dump(sc, f, default_flow_style=False)

def main():
    parser = argparse.ArgumentParser(description='Generate Docker Compose and Kubernetes manifests')
    parser.add_argument('--config', default='config/services.yaml', help='Service configuration file')
    parser.add_argument('--compose', action='store_true', help='Generate Docker Compose')
    parser.add_argument('--k8s', action='store_true', help='Generate Kubernetes manifests')
    parser.add_argument('--all', action='store_true', help='Generate both Docker Compose and Kubernetes')
    parser.add_argument('--output-dir', default='generated', help='Output directory for K8s manifests')
    parser.add_argument('--compose-file', default='docker-compose.generated.yml', help='Docker Compose output file')
    
    args = parser.parse_args()

    if not any([args.compose, args.k8s, args.all]):
        args.all = True

    generator = ConfigGenerator(args.config)

    if args.compose or args.all:
        generator.generate_docker_compose(args.compose_file)

    if args.k8s or args.all:
        generator.generate_kubernetes(args.output_dir)

    print("🎯 Single source of truth configuration complete!")

if __name__ == '__main__':
    main()