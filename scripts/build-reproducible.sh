#!/bin/bash

# GameForge Production Build Script with Reproducible Builds

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔨 GameForge Production Build${NC}"
echo "================================"

# Get build metadata
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD)
BUILD_VERSION=$(git describe --tags --always --dirty)

echo -e "${GREEN}Build Metadata:${NC}"
echo "  Date: $BUILD_DATE"
echo "  Commit: $VCS_REF"
echo "  Version: $BUILD_VERSION"

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️  Warning: Uncommitted changes detected${NC}"
    read -p "Continue with build? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Build cancelled${NC}"
        exit 1
    fi
fi

# Run pre-build hygiene checks
echo -e "\n${BLUE}📋 Running Pre-Build Hygiene Checks...${NC}"
if command -v powershell &> /dev/null; then
    powershell -ExecutionPolicy Bypass -File phase1-prebuild-hygiene.ps1
else
    echo -e "${YELLOW}PowerShell not found, skipping hygiene checks${NC}"
fi

# Lock dependencies
echo -e "\n${BLUE}📦 Locking Dependencies...${NC}"
if [ -f "requirements.in" ]; then
    if command -v pip-compile &> /dev/null; then
        pip-compile requirements.in --resolver=backtracking
    else
        pip freeze > requirements.txt
    fi
    echo -e "${GREEN}✅ Python dependencies locked${NC}"
fi

if [ -f "package.json" ] && [ ! -f "package-lock.json" ]; then
    npm install --package-lock-only
    echo -e "${GREEN}✅ Node dependencies locked${NC}"
fi

# Generate SBOM
echo -e "\n${BLUE}📋 Generating SBOM...${NC}"
if command -v syft &> /dev/null; then
    mkdir -p sbom
    syft packages dir:. -o json > "sbom/sbom-prebuild-${VCS_REF}.json"
    echo -e "${GREEN}✅ SBOM generated${NC}"
else
    echo -e "${YELLOW}Syft not found, creating simple dependency list${NC}"
    mkdir -p sbom
    echo "{\"created\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",\"tool\":\"build.sh\",\"commit\":\"${VCS_REF}\"}" > "sbom/sbom-simple-${VCS_REF}.json"
fi

# Build Docker images with buildkit
echo -e "\n${BLUE}🐳 Building Docker Images...${NC}"

# Enable BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build production image
docker build \
    --build-arg BUILD_DATE="${BUILD_DATE}" \
    --build-arg VCS_REF="${VCS_REF}" \
    --build-arg BUILD_VERSION="${BUILD_VERSION}" \
    --tag gameforge:${BUILD_VERSION} \
    --tag gameforge:latest \
    --file Dockerfile.production \
    --cache-from gameforge:latest \
    --progress=plain \
    .

echo -e "${GREEN}✅ Production image built${NC}"

# Generate post-build SBOM
echo -e "\n${BLUE}📋 Generating Post-Build SBOM...${NC}"
if command -v syft &> /dev/null; then
    syft packages docker:gameforge:${BUILD_VERSION} -o json > "sbom/sbom-image-${VCS_REF}.json"
    echo -e "${GREEN}✅ Image SBOM generated${NC}"
fi

# Run security scan
echo -e "\n${BLUE}🔒 Running Security Scan...${NC}"
if command -v trivy &> /dev/null; then
    trivy image gameforge:${BUILD_VERSION}
else
    echo -e "${YELLOW}Trivy not found, skipping security scan${NC}"
fi

# Tag for registry
if [ -n "${REGISTRY_URL:-}" ]; then
    docker tag gameforge:${BUILD_VERSION} ${REGISTRY_URL}/gameforge:${BUILD_VERSION}
    docker tag gameforge:latest ${REGISTRY_URL}/gameforge:latest
    echo -e "${GREEN}✅ Images tagged for registry${NC}"
fi

echo -e "\n${GREEN}✅ Build Complete!${NC}"
echo "Images:"
echo "  - gameforge:${BUILD_VERSION}"
echo "  - gameforge:latest"

# Save build metadata
cat > build-info.json <<EOF
{
  "build_date": "${BUILD_DATE}",
  "vcs_ref": "${VCS_REF}",
  "version": "${BUILD_VERSION}",
  "builder": "$(whoami)@$(hostname)",
  "docker_version": "$(docker --version)",
  "platform": "$(uname -s)/$(uname -m)"
}
EOF

echo -e "\n${BLUE}Build metadata saved to build-info.json${NC}"
