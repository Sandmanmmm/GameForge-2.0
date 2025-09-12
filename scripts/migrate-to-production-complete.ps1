# GameForge AI - Quick Migration Executor
# This script performs a complete migration in one command

param(
    [switch]$Execute,
    [switch]$NoValidation,
    [switch]$NoBackup
)

Write-Host "🚀 GameForge AI - One-Click Production Migration" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

if (-not $Execute) {
    Write-Host "⚠️  This is a DRY RUN. Use -Execute to perform actual migration." -ForegroundColor Yellow
    Write-Host "💡 Command: .\migrate-to-production-complete.ps1 -Execute" -ForegroundColor Blue
}

$ScriptPath = $PSScriptRoot
$RepoRoot = Split-Path $ScriptPath -Parent

Write-Host "📁 Repository: $RepoRoot" -ForegroundColor Green
Write-Host "🔧 Script Path: $ScriptPath" -ForegroundColor Green

# Step 1: Run the main migration script
Write-Host "`n🔄 STEP 1: Running Migration Script" -ForegroundColor Magenta
$migrationArgs = @()
if (-not $Execute) { $migrationArgs += "-DryRun" }
if (-not $NoBackup) { $migrationArgs += "-CreateBackup" }

try {
    $migrationScript = Join-Path $ScriptPath "migrate-to-production-structure.ps1"
    if (Test-Path $migrationScript) {
        & $migrationScript @migrationArgs
        Write-Host "✅ Migration script completed" -ForegroundColor Green
    } else {
        Write-Host "❌ Migration script not found: $migrationScript" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Migration failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Validate the migration
if (-not $NoValidation) {
    Write-Host "`n🔍 STEP 2: Validating Migration" -ForegroundColor Magenta
    try {
        $validationScript = Join-Path $ScriptPath "validate-production-structure.ps1"
        if (Test-Path $validationScript) {
            $validationArgs = @("-Detailed")
            if ($Execute) { $validationArgs += "-FixIssues" }
            
            & $validationScript @validationArgs
            Write-Host "✅ Validation completed" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Validation script not found: $validationScript" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Validation failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Step 3: Create essential missing files
if ($Execute) {
    Write-Host "`n📝 STEP 3: Creating Essential Files" -ForegroundColor Magenta
    
    # Create enhanced Makefile
    $makefileContent = @"
# GameForge AI - Production Makefile
.PHONY: help build test deploy clean

# Default target
help:
	@echo "GameForge AI - Production Commands"
	@echo "=================================="
	@echo "build          - Build all containers"
	@echo "test           - Run test suite"
	@echo "deploy-dev     - Deploy to development"
	@echo "deploy-prod    - Deploy to production"
	@echo "clean          - Clean up resources"
	@echo "security-scan  - Run security scans"
	@echo "validate       - Validate structure"

# Build targets
build:
	docker-compose -f docker/compose/docker-compose.production.yml build

build-dev:
	docker-compose -f docker/compose/docker-compose.dev.yml build

# Test targets
test:
	npm test
	python -m pytest tests/

test-integration:
	./scripts/run-integration-tests.ps1

# Deployment targets
deploy-dev:
	kubectl apply -k k8s/overlays/dev

deploy-staging:
	kubectl apply -k k8s/overlays/staging

deploy-prod:
	kubectl apply -k k8s/overlays/prod

# Security targets
security-scan:
	./scripts/ci-security-gate.sh

# Utility targets
clean:
	docker system prune -f
	kubectl delete -k k8s/overlays/dev --ignore-not-found

validate:
	./scripts/validate-production-structure.ps1

# Development targets
dev-setup:
	npm install
	pip install -r requirements.txt
	./scripts/setup-development.ps1

dev-start:
	docker-compose -f docker/compose/docker-compose.dev.yml up
"@

    if (-not (Test-Path "Makefile")) {
        Set-Content -Path "Makefile" -Value $makefileContent
        Write-Host "   ✅ Created enhanced Makefile" -ForegroundColor Green
    }
    
    # Create README updates
    $readmeAddition = @"

## 🏗️ Production Structure

This repository follows enterprise-grade organization:

```
gameforge-ai/
├── .github/          # CI/CD workflows
├── docker/           # Container definitions
├── k8s/              # Kubernetes manifests
├── src/              # Application source code
│   ├── frontend/     # Web & mobile clients
│   ├── backend/      # API services
│   ├── ai/           # ML/AI pipelines
│   └── common/       # Shared utilities
├── scripts/          # Automation scripts
├── monitoring/       # Observability stack
├── security/         # Security policies
├── tests/            # Test suites
└── docs/             # Documentation
```

## 🚀 Quick Start

```bash
# Development setup
make dev-setup
make dev-start

# Production deployment
make build
make deploy-prod

# Run tests
make test

# Security scan
make security-scan
```

## 🔄 Migration

This repository was migrated to production structure using:
```bash
./scripts/migrate-to-production-complete.ps1 -Execute
```
"@

    if (Test-Path "README.md") {
        $currentReadme = Get-Content "README.md" -Raw
        if ($currentReadme -notlike "*Production Structure*") {
            Add-Content -Path "README.md" -Value $readmeAddition
            Write-Host "   ✅ Updated README.md with production info" -ForegroundColor Green
        }
    }
}

# Step 4: Summary and next steps
Write-Host "`n📋 MIGRATION SUMMARY" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan

if ($Execute) {
    Write-Host "✅ Repository successfully migrated to production structure!" -ForegroundColor Green
    Write-Host "`n🔄 Next Steps:" -ForegroundColor Blue
    Write-Host "   1. Update import paths in source code" -ForegroundColor White
    Write-Host "   2. Test builds: make build" -ForegroundColor White  
    Write-Host "   3. Test deployments: make deploy-dev" -ForegroundColor White
    Write-Host "   4. Run security scan: make security-scan" -ForegroundColor White
    Write-Host "   5. Update team documentation" -ForegroundColor White
    
    Write-Host "`n💡 Useful Commands:" -ForegroundColor Blue
    Write-Host "   make help                    # Show all available commands" -ForegroundColor Gray
    Write-Host "   make validate                # Validate repository structure" -ForegroundColor Gray
    Write-Host "   make test                    # Run full test suite" -ForegroundColor Gray
    Write-Host "   make deploy-dev              # Deploy to development" -ForegroundColor Gray
} else {
    Write-Host "🔍 Dry run completed successfully!" -ForegroundColor Yellow
    Write-Host "📋 Review the planned changes above" -ForegroundColor Yellow
    Write-Host "🚀 Run with -Execute to perform actual migration" -ForegroundColor Yellow
}

Write-Host "`n🎉 GameForge AI is ready to compete with HeyBossAI and Rosebud AI!" -ForegroundColor Green