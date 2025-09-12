# GameForge Monitoring Stack

This directory contains the observability stack for GameForge including:

## Components

- **prometheus/** - Metrics collection and storage
- **grafana/** - Visualization and dashboards  
- **alertmanager/** - Alert routing and notifications
- **dashboards/** - Pre-built Grafana dashboards

## Usage

All monitoring components are deployed via:
- Docker Compose: `docker-compose.yml`
- Kubernetes: `k8s/base/monitoring.yaml`

## Configuration

- Prometheus scrapes metrics from all GameForge services
- Grafana provides visual dashboards for performance monitoring
- Alertmanager handles alert notifications for critical issues