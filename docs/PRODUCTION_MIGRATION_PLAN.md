# GameForge AI - Production Repository Migration Plan

## Overview
This document outlines the complete migration strategy to transform the current repository structure into a production-ready, enterprise-grade layout that rivals HeyBossAI and Rosebud AI.

## Current State Analysis
- **200+ loose files** at repository root
- Scattered configuration files across multiple locations
- Docker files and compose files mixed with source code
- Security and monitoring components exist but unorganized
- Kubernetes manifests present but need consolidation

## Target Production Structure

```
gameforge-ai/
├── .github/                      # CI/CD pipelines
├── docker/                       # Containerization layer
├── k8s/                          # Kubernetes manifests
├── src/                          # Core application source
├── scripts/                      # Automation utilities
├── monitoring/                   # Observability stack
├── security/                     # Security hardening & policies
├── tests/                        # Automated tests
├── docs/                         # Documentation
└── Configuration files           # Root-level configs
```

## Migration File Mapping

### 1. CI/CD Pipeline Organization (.github/)
**KEEP EXISTING:**
- `.github/workflows/` → Keep as-is (already well organized)
- Add missing workflow files for comprehensive CI/CD

**ACTIONS:**
- ✅ Already has: deploy.yml, security-scan.yml, security-pipeline.yml
- ➕ Add: build.yml, test.yml (create new)

### 2. Docker Containerization (docker/)
**CREATE NEW STRUCTURE:**
```
docker/
├── base/                         # Shared base Dockerfiles
│   ├── node.Dockerfile          # From: Dockerfile.frontend
│   ├── python.Dockerfile        # From: Dockerfile.production
│   └── gpu.Dockerfile           # From: Dockerfile.gpu-workload
├── services/                     # Service-specific images
│   ├── frontend.Dockerfile      # From: Dockerfile.frontend
│   ├── backend.Dockerfile       # From: backend/Dockerfile
│   ├── ai-inference.Dockerfile  # From: Dockerfile.model-optimized
│   ├── ai-training.Dockerfile   # From: Dockerfile.vastai-gpu
│   └── monitoring.Dockerfile    # New: consolidate monitoring
└── compose/                      # Local-only compose stacks
    ├── docker-compose.dev.yml   # From: docker-compose.yml
    └── docker-compose.production.yml  # From: docker-compose.production.yml
```

**MOVE OPERATIONS:**
- All `Dockerfile*` files → `docker/services/` or `docker/base/`
- All `docker-compose*.yml` files → `docker/compose/`

### 3. Kubernetes Manifests (k8s/)
**REORGANIZE EXISTING:**
```
k8s/
├── base/                         # Common deployments
│   ├── postgres.yaml            # From: k8s/postgres-deployment.yaml
│   ├── redis.yaml               # From: k8s/redis-deployment.yaml
│   ├── vault.yaml               # From: vault/ configs
│   ├── elasticsearch.yaml       # From: elasticsearch/ configs
│   └── monitoring.yaml          # From: monitoring/ k8s configs
├── overlays/                     # Environment-specific overlays
│   ├── dev/                     # From: k8s/overlays/dev/
│   ├── staging/                 # New
│   └── prod/                    # From: k8s/overlays/prod/
└── templates/                    # Helm/kustomize templates
    └── gameforge/               # From: helm/gameforge/
```

### 4. Source Code Organization (src/)
**REORGANIZE EXISTING:**
```
src/
├── frontend/                     # User-facing clients
│   ├── web/                     # From: src/ (React/Next.js components)
│   └── mobile/                  # New: Future mobile app
├── backend/                      # From: backend/
│   ├── api/                     # From: backend/src/
│   ├── worker/                  # New: Background jobs
│   └── services/                # New: Microservices
├── ai/                          # ML/AI pipelines
│   ├── inference/               # From: AI model files scattered
│   ├── training/                # From: training scripts
│   ├── datasets/                # From: data/ directory
│   └── evaluation/              # New: Benchmarking
└── common/                       # Shared libraries & utils
    ├── logging/                 # From: logging configs
    ├── monitoring/              # From: monitoring utilities
    ├── security/                # From: security utilities
    └── utils/                   # From: utility scripts
```

### 5. Scripts Consolidation (scripts/)
**ORGANIZE EXISTING:**
- ✅ `scripts/` directory exists and is well-organized
- Move root-level `.ps1` and `.sh` files → `scripts/`
- Organize by function: deployment, security, migration, monitoring

### 6. Monitoring Stack (monitoring/)
**KEEP AND ENHANCE:**
- ✅ `monitoring/` directory exists
- Already contains: grafana/, prometheus/, alertmanager/
- Consolidate loose monitoring files from root

### 7. Security Policies (security/)
**KEEP AND ENHANCE:**
- ✅ `security/` directory exists
- Contains: policies/, seccomp/, scripts/
- Move security-related root files → `security/`

### 8. Testing Framework (tests/)
**CREATE NEW:**
```
tests/
├── unit/                        # New: Unit tests
├── integration/                 # New: Integration tests
└── load/                        # From: load-testing scripts
```

### 9. Documentation (docs/)
**CONSOLIDATE:**
```
docs/
├── architecture.md              # New: System architecture
├── security.md                 # From: security documentation
├── migration.md                # This document
├── api-specs/                   # From: API documentation
└── runbooks/                    # From: operational guides
```

## Root-Level Files to Organize

### Configuration Files (KEEP AT ROOT)
- `.env*` files → Keep but consolidate
- `package.json`, `tsconfig.json` → Keep
- `components.json`, `tailwind.config.js` → Keep
- `Makefile` → Keep/Create enhanced version
- `LICENSE`, `README.md` → Keep

### Files to MOVE/REORGANIZE
- All deployment scripts (`deploy-*.ps1`, `deploy-*.sh`) → `scripts/`
- All build scripts (`build-*.ps1`, `build-*.sh`) → `scripts/`
- All test scripts (`test-*.ps1`, `test-*.sh`) → `scripts/`
- All validation scripts (`validate-*.ps1`, `validate-*.sh`) → `scripts/`
- Security scripts → `security/scripts/`
- Monitoring configs → `monitoring/`
- Database files → `src/backend/database/`

## Migration Phases

### Phase 1: Prepare New Structure
1. Create new directory hierarchy
2. Backup current repository state
3. Prepare migration scripts

### Phase 2: Move Docker Assets
1. Organize all Dockerfiles into `docker/` structure
2. Consolidate docker-compose files
3. Update image references

### Phase 3: Reorganize Source Code
1. Move frontend code to `src/frontend/web/`
2. Ensure backend stays in `src/backend/`
3. Create AI pipeline structure
4. Organize common utilities

### Phase 4: Consolidate Scripts
1. Move all scripts from root to `scripts/`
2. Organize by function
3. Update script references

### Phase 5: Finalize and Validate
1. Update all references and imports
2. Test all deployments
3. Validate CI/CD pipelines
4. Update documentation

## Success Metrics
- ✅ Zero loose files at repository root (except essential configs)
- ✅ All components properly organized by function
- ✅ CI/CD pipelines working with new structure
- ✅ Docker builds successful with new paths
- ✅ Kubernetes deployments functional
- ✅ All scripts and automation working

## Risk Mitigation
- Complete backup before migration
- Incremental migration with validation at each step
- Preserve all existing functionality
- Update all path references systematically
- Test deployments after each phase

## Next Steps
1. Run migration automation scripts
2. Validate new structure
3. Update CI/CD pipeline references
4. Test complete deployment cycle
5. Update team documentation

---
*This migration will transform the repository into an enterprise-grade, production-ready codebase that can compete with leading AI game development platforms.*