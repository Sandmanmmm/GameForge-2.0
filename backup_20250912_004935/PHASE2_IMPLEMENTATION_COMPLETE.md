# GameForge Production Phase 2 Implementation Guide
## Enhanced Multi-stage Dockerfile with CPU/GPU Variants

### Overview

GameForge Production Phase 2 enhances the existing Docker build process with:

1. **Enhanced Multi-stage Build Architecture** - Optimized 5-stage build process
2. **CPU/GPU Variant Support** - Dynamic base image selection for different deployment targets
3. **Advanced Security Hardening** - Comprehensive security measures and validation
4. **Build Automation** - PowerShell and Bash scripts for cross-platform builds
5. **Comprehensive Validation** - Automated testing for security, size, and functionality

### Architecture

#### Multi-stage Build Process

```
Stage 1: System Foundation    → Security-hardened base with minimal packages
Stage 2: Build Dependencies   → Temporary build tools (discarded in final image)
Stage 3: Python Builder       → Optimized Python environment creation
Stage 4: Application Builder  → Bytecode compilation and optimization
Stage 5: Production Runtime   → Minimal runtime environment
```

#### Variant Support

| Variant | Base Image | Target Use Case | Size Target |
|---------|------------|-----------------|-------------|
| CPU     | ubuntu:22.04 | CPU-only deployments, development | <500MB |
| GPU     | nvidia/cuda:12.1-devel-ubuntu22.04 | GPU-accelerated production | <3GB |

### Files Created/Modified

#### Core Docker Files
- `Dockerfile.production.enhanced` - Enhanced multi-stage Dockerfile with CPU/GPU support
- `docker-compose.phase2-test.yml` - Testing configuration for both variants

#### Build Scripts
- `build-phase2.ps1` - Windows PowerShell build script with validation
- `build-phase2.sh` - Linux/CI Bash build script with validation
- `validate-phase2.ps1` - Comprehensive validation testing script

### Usage

#### Building Images

**Windows PowerShell:**
```powershell
# Build GPU variant (default)
.\build-phase2.ps1

# Build CPU variant
.\build-phase2.ps1 -Variant cpu

# Build both variants with validation
.\build-phase2.ps1 -Variant both -Validate -SizeCheck

# Build and push to registry
.\build-phase2.ps1 -Variant both -Push -Registry "your-registry.com/gameforge"

# Clean build with custom tag
.\build-phase2.ps1 -Clean -Tag "v2.0.0" -Variant gpu
```

**Linux/CI:**
```bash
# Make script executable
chmod +x build-phase2.sh

# Build GPU variant (default)
./build-phase2.sh

# Build CPU variant with size check
./build-phase2.sh --variant cpu --size-check

# Build both variants with full validation
./build-phase2.sh --variant both --validate --size-check

# CI/CD pipeline usage
./build-phase2.sh --variant both --push --clean --registry "your-registry.com/gameforge"
```

#### Validation Testing

```powershell
# Test both variants
.\validate-phase2.ps1

# Test specific variant with detailed output
.\validate-phase2.ps1 -Variant gpu -Detailed

# Skip specific test categories
.\validate-phase2.ps1 -SkipSizeCheck -SkipFunctionalCheck
```

#### Local Testing with Docker Compose

```bash
# Test CPU variant only
GAMEFORGE_VERSION=latest docker-compose -f docker-compose.phase2-test.yml --profile cpu up

# Test GPU variant only  
GAMEFORGE_VERSION=latest docker-compose -f docker-compose.phase2-test.yml --profile gpu up

# Test both variants with monitoring
GAMEFORGE_VERSION=latest docker-compose -f docker-compose.phase2-test.yml --profile all up
```

### Security Features

#### Runtime Security
- **Non-root execution**: Containers run as user `gameforge` (UID: 1001)
- **Environment validation**: Strict production environment checks
- **Directory permissions**: Proper read/write permissions for application directories
- **Python environment isolation**: Dedicated virtual environment with minimal permissions

#### Build-time Security
- **Minimal base images**: Only essential packages installed
- **Security updates**: Latest security patches applied during build
- **Layer optimization**: Reduced attack surface through layer consolidation
- **Dependency validation**: Locked requirements with integrity checking

#### Validation Tests
1. **User ID verification**: Ensures non-root execution
2. **Environment validation**: Tests production environment enforcement
3. **Directory permissions**: Validates writable application directories
4. **Python environment**: Tests Python runtime functionality
5. **Health check validation**: Tests application startup and health endpoints

### Size Optimization

#### Techniques Applied
1. **Multi-stage builds**: Discard build dependencies in final image
2. **Bytecode compilation**: Python source files compiled and originals removed
3. **Layer consolidation**: Combined RUN commands to reduce layers
4. **Cache cleanup**: Removed package manager caches and temporary files
5. **Minimal runtime**: Only essential runtime dependencies included

#### Size Targets
- **CPU variant**: Target <500MB (typical: 350-450MB)
- **GPU variant**: Target <3GB (typical: 2.2-2.8GB)

### Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `BUILD_DATE` | Auto | RFC3339 build timestamp |
| `VCS_REF` | Auto | Git commit hash (short) |
| `BUILD_VERSION` | Auto | Git describe version |
| `VARIANT` | `gpu` | Build variant: `cpu` or `gpu` |
| `PYTHON_VERSION` | `3.10` | Python version to install |
| `CPU_BASE_IMAGE` | `ubuntu:22.04` | Base image for CPU variant |
| `GPU_BASE_IMAGE` | `nvidia/cuda:12.1-devel-ubuntu22.04` | Base image for GPU variant |

### Environment Variables

#### Production Configuration
```bash
GAMEFORGE_ENV=production          # Required: Must be 'production'
VARIANT=gpu                       # Build variant identifier
LOG_LEVEL=info                    # Logging level
WORKERS=4                         # Gunicorn worker count
MAX_WORKERS=8                     # Maximum worker limit
WORKER_TIMEOUT=300                # Worker timeout in seconds
```

#### GPU Configuration (GPU variant only)
```bash
NVIDIA_VISIBLE_DEVICES=all                    # GPU visibility
NVIDIA_DRIVER_CAPABILITIES=compute,utility    # Driver capabilities
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 # CUDA memory allocation
```

### Integration with Phase 1

Phase 2 builds upon Phase 1 pre-build hygiene by:

1. **Automatic hygiene execution**: Build scripts run Phase 1 checks automatically
2. **Locked dependencies**: Uses `requirements-locked-demo.txt` if available
3. **SBOM integration**: Leverages Phase 1 software bill of materials
4. **Security scanning**: Integrates with Phase 1 security patterns

### CI/CD Integration

#### GitHub Actions Example
```yaml
- name: Build GameForge Production Images
  run: |
    chmod +x build-phase2.sh
    ./build-phase2.sh --variant both --validate --size-check --push
  env:
    REGISTRY: ${{ secrets.CONTAINER_REGISTRY }}
```

#### Jenkins Pipeline Example
```groovy
stage('Build Production Images') {
    parallel {
        stage('CPU Variant') {
            steps {
                script {
                    sh './build-phase2.sh --variant cpu --validate --size-check'
                }
            }
        }
        stage('GPU Variant') {
            steps {
                script {
                    sh './build-phase2.sh --variant gpu --validate --size-check'
                }
            }
        }
    }
}
```

### Monitoring and Validation

#### Health Check Configuration
- **Interval**: 30 seconds
- **Timeout**: 15 seconds
- **Start period**: 120 seconds (allows for model loading)
- **Retries**: 3 attempts before marking unhealthy

#### Validation Tests
1. **Security validation**: User, environment, and permission checks
2. **Size validation**: Image size against targets
3. **Functionality validation**: Container startup and health checks
4. **GPU validation**: GPU accessibility for GPU variant

### Troubleshooting

#### Common Issues

**Build Failures:**
1. Check Docker daemon is running
2. Ensure sufficient disk space (>10GB for GPU variant)
3. Verify network connectivity for package downloads
4. Check Phase 1 hygiene script completion

**Size Optimization:**
1. Review installed packages in build logs
2. Check for large files in `/tmp` directories
3. Verify bytecode compilation completed
4. Consider additional package cleanup

**Security Validation Failures:**
1. Verify non-root user creation in Dockerfile
2. Check environment variable validation logic
3. Ensure directory permissions are set correctly
4. Validate entrypoint script functionality

#### Debug Commands
```bash
# Check build stages
docker build --target system-foundation -f Dockerfile.production.enhanced .

# Inspect final image
docker run -it --rm <image-tag> bash

# Check image layers
docker history <image-tag>

# Validate security
docker run --rm <image-tag> id
docker run --rm -e GAMEFORGE_ENV=development <image-tag> echo "test"
```

### Performance Characteristics

#### Build Times (Approximate)
- **CPU variant**: 8-12 minutes
- **GPU variant**: 15-25 minutes  
- **Both variants**: 20-35 minutes (parallel build)

#### Runtime Performance
- **Cold start**: 30-60 seconds (model loading)
- **Warm requests**: <100ms response time
- **Memory usage**: 2-8GB depending on variant and workload
- **CPU usage**: 2-6 cores depending on configuration

### Future Enhancements

1. **Multi-architecture builds**: ARM64 support for cloud deployments
2. **Distroless variants**: Even smaller runtime images
3. **Layer caching**: BuildKit cache mounts for faster builds
4. **Security scanning**: Integrated Trivy/Snyk scanning
5. **Performance profiling**: Automated performance regression testing

### Compliance and Standards

Phase 2 implementation follows:
- **CIS Docker Benchmark**: Container security best practices
- **NIST Cybersecurity Framework**: Security controls implementation
- **OCI Image Format**: Standard container image specification
- **SLSA Build Levels**: Supply chain security requirements
