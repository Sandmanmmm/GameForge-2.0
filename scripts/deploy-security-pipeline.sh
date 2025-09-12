#!/bin/bash
# GameForge Phase 3 Security Pipeline Deployment Script
set -e

echo "ðŸ” Starting GameForge Phase 3 Security Pipeline Deployment"
echo "=========================================================="

# Load security environment variables
if [ -f .env.security ]; then
    export $(cat .env.security | grep -v '^#' | xargs)
    echo "âœ… Loaded security environment variables"
else
    echo "âŒ .env.security file not found. Run configure-security-environment.ps1 first."
    exit 1
fi

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "âŒ Docker is not running. Please start Docker first."
    exit 1
fi

echo "âœ… Docker is running"

# Create network if it doesn't exist
docker network create security-pipeline 2>/dev/null || echo "Security pipeline network already exists"

echo "ðŸš€ Deploying Phase 3 Security Services..."

# Deploy security services in dependency order
echo "ðŸ“Š Starting Security Metrics Collector..."
docker-compose -f docker-compose.production-hardened.yml up -d security-metrics

echo "ðŸ” Starting Security Scanner..."
docker-compose -f docker-compose.production-hardened.yml up -d security-scanner

echo "ðŸ“‹ Starting SBOM Generator..."
docker-compose -f docker-compose.production-hardened.yml up -d sbom-generator

echo "âœï¸ Starting Image Signer..."
docker-compose -f docker-compose.production-hardened.yml up -d image-signer

echo "ðŸ“Š Starting Security Dashboard..."
docker-compose -f docker-compose.production-hardened.yml up -d security-dashboard

echo "ðŸ¢ Starting Harbor Registry..."
docker-compose -f docker-compose.production-hardened.yml up -d harbor-registry

echo "â³ Waiting for services to be healthy..."
sleep 30

echo "ðŸ” Checking service status..."
docker-compose -f docker-compose.production-hardened.yml ps security-scanner security-metrics sbom-generator image-signer security-dashboard

echo ""
echo "âœ… Phase 3 Security Pipeline Deployment Complete!"
echo ""
echo "ðŸŒ Access Points:"
echo "  â€¢ Security Scanner:  http://localhost:8082"
echo "  â€¢ SBOM Generator:    http://localhost:8083"
echo "  â€¢ Harbor Registry:   http://localhost:8084"
echo "  â€¢ Security Dashboard: http://localhost:3001"
echo ""
echo "ðŸ“‹ Next Steps:"
echo "  1. Generate signing keys: ./generate-cosign-keys.sh"
echo "  2. Configure Harbor: Access http://localhost:8084 (admin/nm4GcExZIP%E*lCV*JNusX7L)"
echo "  3. Import security dashboards into Grafana"
echo ""
