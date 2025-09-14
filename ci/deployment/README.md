# Blue/Green Deployment Strategy for GameForge

This directory contains the automated blue/green deployment infrastructure for zero-downtime deployments.

## Overview

Blue/green deployment is a technique that reduces downtime and risk by running two identical production environments called Blue and Green. At any time, only one of the environments is live, with the other serving as a staging environment.

## Components

### 1. Deployment Scripts
- `blue-green-deploy.sh`: Main deployment orchestration script
- `health-check.sh`: Comprehensive health validation
- `rollback.sh`: Automated rollback mechanism
- `traffic-switch.sh`: Traffic routing management

### 2. Kubernetes Manifests
- `blue-green-service.yaml`: Service with label selectors for blue/green switching
- `blue-deployment.yaml`: Blue environment deployment
- `green-deployment.yaml`: Green environment deployment
- `ingress-controller.yaml`: Ingress configuration for traffic routing

### 3. Monitoring and Validation
- `deployment-tests.yaml`: Automated testing suite
- `metrics-validation.sh`: Performance and metrics validation
- `smoke-tests.sh`: Post-deployment validation

## Deployment Flow

1. **Preparation**: Validate current state and prepare new version
2. **Deploy**: Deploy new version to inactive environment (blue/green)
3. **Test**: Run comprehensive tests on new deployment
4. **Switch**: Route traffic to new environment
5. **Monitor**: Continuous monitoring for issues
6. **Cleanup**: Clean up old environment after validation

## Usage

```bash
# Deploy new version with blue/green strategy
./ci/deployment/blue-green-deploy.sh --version v1.2.3 --environment production

# Check deployment status
./ci/deployment/health-check.sh --environment production

# Rollback if needed
./ci/deployment/rollback.sh --environment production
```

## Configuration

Environment-specific configurations are managed through:
- Environment variables
- Kubernetes ConfigMaps
- Helm values files
- GitOps repository synchronization
