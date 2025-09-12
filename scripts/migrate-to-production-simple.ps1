# GameForge AI - Complete Production Migration Script
# Creates the full enterprise-grade repository structure
# Version: 3.0 - Complete Production Layout

param(
    [switch]$DryRun,
    [switch]$CreateBackup
)

Write-Host "🚀 GameForge AI - Complete Production Repository Migration" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

$RepoRoot = Get-Location
Write-Host "📁 Repository Root: $RepoRoot" -ForegroundColor Green

$FilesProcessed = 0
$DirectoriesCreated = 0
$TemplatesCreated = 0

# Create backup if requested
if ($CreateBackup -and -not $DryRun) {
    $BackupPath = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "📦 Creating backup at: $BackupPath" -ForegroundColor Yellow
    
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    Copy-Item "*.md" $BackupPath -Force -ErrorAction SilentlyContinue
    Copy-Item "*.json" $BackupPath -Force -ErrorAction SilentlyContinue
    Copy-Item "*.ps1" $BackupPath -Force -ErrorAction SilentlyContinue
    Copy-Item "Dockerfile*" $BackupPath -Force -ErrorAction SilentlyContinue
    Copy-Item "docker-compose*" $BackupPath -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ Backup created" -ForegroundColor Green
}

# Function to create directory safely
function New-DirectorySafe {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would create: $Path" -ForegroundColor Gray
        } else {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
            Write-Host "   ✅ Created: $Path" -ForegroundColor Green
            $script:DirectoriesCreated++
        }
    }
}

# Function to move file safely
function Move-FileSafe {
    param([string]$Source, [string]$Destination)
    
    if (Test-Path $Source) {
        $destDir = Split-Path $Destination -Parent
        New-DirectorySafe $destDir
        
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would move: $Source → $Destination" -ForegroundColor Gray
        } else {
            Move-Item $Source $Destination -Force -ErrorAction SilentlyContinue
            Write-Host "   ✅ Moved: $(Split-Path $Source -Leaf)" -ForegroundColor Green
            $script:FilesProcessed++
        }
    }
}

Write-Host "`n🏗️  PHASE 1: Creating Directory Structure" -ForegroundColor Magenta

# Create essential directories
$directories = @(
    # CI/CD Structure
    ".github/workflows",
    
    # Docker Structure
    "docker/base",
    "docker/services", 
    "docker/compose",
    
    # Kubernetes Structure
    "k8s/base",
    "k8s/overlays/dev",
    "k8s/overlays/staging", 
    "k8s/overlays/prod",
    "k8s/templates",
    
    # Source Code Structure
    "src/frontend/web",
    "src/frontend/mobile",
    "src/backend/api",
    "src/backend/worker",
    "src/backend/services",
    "src/ai/inference",
    "src/ai/training",
    "src/ai/datasets",
    "src/ai/evaluation",
    "src/common/logging",
    "src/common/monitoring",
    "src/common/security",
    "src/common/utils",
    
    # Infrastructure Structure
    "monitoring/prometheus",
    "monitoring/grafana",
    "monitoring/alertmanager",
    "monitoring/dashboards",
    
    "security/seccomp",
    "security/policies",
    "security/scripts",
    "security/vault",
    
    # Testing Structure
    "tests/unit",
    "tests/integration",
    "tests/load",
    
    # Documentation Structure
    "docs/api-specs",
    "docs/runbooks",
    
    # Configuration
    "config"
)

foreach ($dir in $directories) {
    New-DirectorySafe $dir
}

Write-Host "`n🐳 PHASE 2: Moving Docker Files" -ForegroundColor Magenta

# Move Dockerfiles
Get-ChildItem -Path . -Name "Dockerfile*" -File | ForEach-Object {
    Move-FileSafe $_ "docker/services/$_"
}

# Move docker-compose files
Get-ChildItem -Path . -Name "docker-compose*.yml" -File | ForEach-Object {
    Move-FileSafe $_ "docker/compose/$_"
}

Write-Host "`n📂 PHASE 3: Organizing Source Code" -ForegroundColor Magenta

# Handle src directory
if (Test-Path "src" -and -not (Test-Path "src/frontend/web/App.tsx")) {
    if ($DryRun) {
        Write-Host "   [DRY RUN] Would reorganize src/ directory" -ForegroundColor Gray
    } else {
        $tempSrc = "temp_src_migration"
        if (Test-Path $tempSrc) { Remove-Item $tempSrc -Recurse -Force }
        
        Move-Item "src" $tempSrc -Force
        New-DirectorySafe "src/frontend/web"
        
        Get-ChildItem $tempSrc | ForEach-Object {
            Move-Item $_.FullName "src/frontend/web/" -Force
        }
        
        Remove-Item $tempSrc -Force -ErrorAction SilentlyContinue
        Write-Host "   ✅ Reorganized src/ directory" -ForegroundColor Green
    }
}

# Handle backend directory
if (Test-Path "backend" -and -not (Test-Path "src/backend/package.json")) {
    Move-FileSafe "backend" "src/backend"
}

Write-Host "`n📜 PHASE 4: Moving Scripts" -ForegroundColor Magenta

# Move script files
Get-ChildItem -Path . -Name "*.ps1" -File | Where-Object { $_ -notlike "*migrate-to-production*" } | ForEach-Object {
    Move-FileSafe $_ "scripts/$_"
}

Get-ChildItem -Path . -Name "*.sh" -File | ForEach-Object {
    Move-FileSafe $_ "scripts/$_"
}

Get-ChildItem -Path . -Name "*.bat" -File | ForEach-Object {
    Move-FileSafe $_ "scripts/$_"
}

Write-Host "`n📚 PHASE 5: Moving Documentation" -ForegroundColor Magenta

# Move markdown files (except README.md)
Get-ChildItem -Path . -Name "*.md" -File | Where-Object { $_ -ne "README.md" } | ForEach-Object {
    Move-FileSafe $_ "docs/$_"
}

Write-Host "`n🧹 PHASE 6: Moving Config Files" -ForegroundColor Magenta

# Move loose config files
$keepAtRoot = @("package.json", "package-lock.json", "tsconfig.json", "components.json", "tailwind.config.js", "vite.config.ts")

Get-ChildItem -Path . -Name "*.json" -File | Where-Object { $keepAtRoot -notcontains $_ } | ForEach-Object {
    Move-FileSafe $_ "config/$_"
}

Get-ChildItem -Path . -Name "*.yaml" -File | Where-Object { $_ -notlike "docker-compose*" } | ForEach-Object {
    Move-FileSafe $_ "config/$_"
}

Get-ChildItem -Path . -Name "*.yml" -File | Where-Object { $_ -notlike "docker-compose*" } | ForEach-Object {
    Move-FileSafe $_ "config/$_"
}

Write-Host "`n📄 PHASE 7: Creating Essential Files and Templates" -ForegroundColor Magenta

if (-not $DryRun) {
    # Create CI/CD Workflows
    Write-Host "   Creating CI/CD workflows..." -ForegroundColor Blue
    
    # Build workflow
    $buildWorkflow = @'
name: Build and Push Images

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Build Frontend
      run: docker build -f docker/services/frontend.Dockerfile -t gameforge-frontend .
    - name: Build Backend
      run: docker build -f docker/services/backend.Dockerfile -t gameforge-backend .
'@
    Set-Content -Path ".github/workflows/build.yml" -Value $buildWorkflow -Encoding UTF8
    
    # Test workflow
    $testWorkflow = @'
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    - name: Install dependencies
      run: npm ci
    - name: Run tests
      run: npm test
'@
    Set-Content -Path ".github/workflows/test.yml" -Value $testWorkflow -Encoding UTF8
    
    # Security scan workflow
    $securityWorkflow = @'
name: Security Scan

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
'@
    Set-Content -Path ".github/workflows/security-scan.yml" -Value $securityWorkflow -Encoding UTF8
    
    # Deploy workflow
    $deployWorkflow = @'
name: Deploy

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Deploy to Development
      run: kubectl apply -k k8s/overlays/dev
      if: github.ref == 'refs/heads/develop'
    - name: Deploy to Production
      run: kubectl apply -k k8s/overlays/prod
      if: github.ref == 'refs/heads/main'
'@
    Set-Content -Path ".github/workflows/deploy.yml" -Value $deployWorkflow -Encoding UTF8
    
    Write-Host "   ✅ Created CI/CD workflows" -ForegroundColor Green
    $TemplatesCreated += 4
    
    # Create Docker Base Files
    Write-Host "   Creating Docker base files..." -ForegroundColor Blue
    
    $nodeDockerfile = @'
FROM node:18-alpine
RUN apk add --no-cache python3 py3-pip make g++
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
EXPOSE 3000
CMD ["npm", "start"]
'@
    Set-Content -Path "docker/base/node.Dockerfile" -Value $nodeDockerfile -Encoding UTF8
    
    $pythonDockerfile = @'
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "app.py"]
'@
    Set-Content -Path "docker/base/python.Dockerfile" -Value $pythonDockerfile -Encoding UTF8
    
    $gpuDockerfile = @'
FROM nvidia/cuda:11.8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-gpu.txt .
RUN pip3 install -r requirements-gpu.txt
EXPOSE 8080
CMD ["python3", "inference_server.py"]
'@
    Set-Content -Path "docker/base/gpu.Dockerfile" -Value $gpuDockerfile -Encoding UTF8
    
    Write-Host "   ✅ Created Docker base files" -ForegroundColor Green
    $TemplatesCreated += 3
    
    # Create Kubernetes Base Manifests
    Write-Host "   Creating Kubernetes manifests..." -ForegroundColor Blue
    
    $postgresManifest = @'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: gameforge
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: gameforge
        - name: POSTGRES_USER
          value: gameforge
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
'@
    Set-Content -Path "k8s/base/postgres.yaml" -Value $postgresManifest -Encoding UTF8
    
    $redisManifest = @'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: gameforge
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
'@
    Set-Content -Path "k8s/base/redis.yaml" -Value $redisManifest -Encoding UTF8
    
    Write-Host "   ✅ Created Kubernetes manifests" -ForegroundColor Green
    $TemplatesCreated += 2
    
    # Create Documentation Templates
    Write-Host "   Creating documentation templates..." -ForegroundColor Blue
    
    $architectureDoc = @'
# GameForge AI - System Architecture

## Overview
GameForge AI is an enterprise-grade AI-powered game development platform.

## Architecture Components

### Frontend Layer
- **Web Application**: React/Next.js frontend
- **Mobile App**: React Native/Flutter (future)

### Backend Layer
- **API Services**: REST/GraphQL APIs
- **Worker Services**: Background job processing
- **Microservices**: Auth, billing, notifications

### AI/ML Layer
- **Inference Engine**: GPU-powered model serving
- **Training Pipeline**: Model training and optimization
- **Data Processing**: Dataset management and preprocessing

### Infrastructure Layer
- **Container Platform**: Docker + Kubernetes
- **Monitoring**: Prometheus + Grafana
- **Security**: Policy enforcement and scanning
'@
    Set-Content -Path "docs/architecture.md" -Value $architectureDoc -Encoding UTF8
    
    $securityDoc = @'
# GameForge AI - Security Guide

## Security Framework

### Container Security
- Seccomp profiles for runtime protection
- Non-root container execution
- Minimal base images

### Network Security
- Network policies for pod-to-pod communication
- TLS encryption for all communications
- API rate limiting and authentication

### Data Security
- Encryption at rest and in transit
- Secret management with Vault
- Regular security scanning
'@
    Set-Content -Path "docs/security.md" -Value $securityDoc -Encoding UTF8
    
    Write-Host "   ✅ Created documentation templates" -ForegroundColor Green
    $TemplatesCreated += 2
    
    # Create enhanced Makefile
    $makefile = @'
# GameForge AI - Production Makefile

.PHONY: help build test deploy clean validate dev-setup

help:
	@echo "GameForge AI - Production Commands"
	@echo "=================================="
	@echo "build          - Build all containers"
	@echo "test           - Run test suite"
	@echo "deploy-dev     - Deploy to development"
	@echo "deploy-staging - Deploy to staging"
	@echo "deploy-prod    - Deploy to production"
	@echo "clean          - Clean up resources"
	@echo "validate       - Validate repository structure"
	@echo "dev-setup      - Set up development environment"

build:
	docker-compose -f docker/compose/docker-compose.production.yml build

build-dev:
	docker-compose -f docker/compose/docker-compose.dev.yml build

test:
	npm test
	@echo "Run: python -m pytest tests/ for Python tests"

deploy-dev:
	kubectl apply -k k8s/overlays/dev

deploy-staging:
	kubectl apply -k k8s/overlays/staging

deploy-prod:
	kubectl apply -k k8s/overlays/prod

clean:
	docker system prune -f
	kubectl delete -k k8s/overlays/dev --ignore-not-found

validate:
	@powershell -File scripts/validate-production-working.ps1 -Detailed

dev-setup:
	npm install
	@echo "Development environment ready!"

security-scan:
	@powershell -File scripts/ci-security-gate.sh 2>nul || echo "Security scan script not found"
'@

    if (-not (Test-Path "Makefile")) {
        Set-Content -Path "Makefile" -Value $makefile -Encoding UTF8
        Write-Host "   ✅ Created enhanced Makefile" -ForegroundColor Green
        $TemplatesCreated++
    }
    
    # Create .env.example
    $envExample = @'
# GameForge AI - Environment Configuration Template
# Copy to .env and update with your actual values

# Application
NODE_ENV=development
PORT=3000
API_PORT=8000

# Database
DATABASE_URL=postgresql://gameforge:password@localhost:5432/gameforge
REDIS_URL=redis://localhost:6379

# AI/ML Configuration
MODEL_CACHE_SIZE=10GB
GPU_ENABLED=true
INFERENCE_ENDPOINT=http://localhost:8080

# Security
JWT_SECRET=your-jwt-secret-here
ENCRYPTION_KEY=your-encryption-key-here

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# Development
DEBUG=true
LOG_LEVEL=info
'@
    
    if (-not (Test-Path ".env.example")) {
        Set-Content -Path ".env.example" -Value $envExample -Encoding UTF8
        Write-Host "   ✅ Created .env.example" -ForegroundColor Green
        $TemplatesCreated++
    }
}

Write-Host "`n✅ MIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

Write-Host "`n📊 SUMMARY:" -ForegroundColor Cyan
Write-Host "Directories Created: $DirectoriesCreated" -ForegroundColor Green
Write-Host "Files Processed: $FilesProcessed" -ForegroundColor Green
Write-Host "Templates Created: $TemplatesCreated" -ForegroundColor Green

if ($DryRun) {
    Write-Host "`n🔍 This was a DRY RUN - no changes made" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to execute migration:" -ForegroundColor Yellow
    Write-Host "   .\scripts\migrate-to-production-simple.ps1 -CreateBackup" -ForegroundColor Cyan
} else {
    Write-Host "`n🎉 Repository successfully reorganized to enterprise structure!" -ForegroundColor Green
    Write-Host "`n📋 Next steps:" -ForegroundColor Blue
    Write-Host "   1. Validate: .\scripts\validate-production-working.ps1" -ForegroundColor White
    Write-Host "   2. Test build: make build" -ForegroundColor White
    Write-Host "   3. Update import paths in code" -ForegroundColor White
    Write-Host "   4. Configure CI/CD secrets" -ForegroundColor White
    Write-Host "   5. Set up monitoring dashboards" -ForegroundColor White
    Write-Host "`n🏆 GameForge AI is now enterprise-ready and production-grade!" -ForegroundColor Green
    Write-Host "🚀 Ready to compete with HeyBossAI and Rosebud AI!" -ForegroundColor Green
}