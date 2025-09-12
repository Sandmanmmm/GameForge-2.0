#!/bin/bash

# GameForge Production Phase 2 Build Script
# Enhanced Multi-stage Build with CPU/GPU Variants
# Linux/CI Implementation

set -euo pipefail

# Default values
VARIANT="gpu"
TAG=""
PUSH=false
NO_BUILD_ARG=false
CLEAN=false
VALIDATE=false
SIZE_CHECK=false
REGISTRY="${REGISTRY:-your-registry.com/gameforge}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${CYAN}$1${NC}"
}

log_success() {
    echo -e "${GREEN}$1${NC}"
}

log_warning() {
    echo -e "${YELLOW}$1${NC}"
}

log_error() {
    echo -e "${RED}$1${NC}"
}

log_gray() {
    echo -e "${GRAY}$1${NC}"
}

log_section() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================================${NC}"
}

show_help() {
    cat << EOF
GameForge Production Phase 2 Build Script

Usage: $0 [OPTIONS]

Options:
    -v, --variant VARIANT    Build variant: cpu, gpu, or both (default: gpu)
    -t, --tag TAG           Custom tag for the image (default: auto-generated)
    -p, --push              Push images to registry after build
    -c, --clean             Clean up dangling images before build
    -n, --no-build-arg      Skip pre-build hygiene checks
    --validate              Run security validation tests
    --size-check            Check image size against targets
    -r, --registry REGISTRY  Container registry (default: your-registry.com/gameforge)
    -h, --help              Show this help message

Examples:
    $0 --variant both --push --validate
    $0 -v cpu -t latest --size-check
    $0 --clean --variant gpu --push

EOF
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "❌ Docker is not installed"
        return 1
    fi
    
    if ! docker version &> /dev/null; then
        log_error "❌ Docker is not running"
        return 1
    fi
    
    return 0
}

get_build_metadata() {
    local build_date
    local vcs_ref
    local build_version
    
    build_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if command -v git &> /dev/null && git rev-parse --git-dir &> /dev/null; then
        vcs_ref=$(git rev-parse --short HEAD)
        build_version=$(git describe --tags --always --dirty 2>/dev/null || echo "${vcs_ref}")
    else
        log_warning "⚠️  Git not available, using fallback metadata"
        vcs_ref="unknown"
        build_version="dev-build"
    fi
    
    echo "$build_date|$vcs_ref|$build_version"
}

run_prebuild_hygiene() {
    log_section "Pre-Build Hygiene Checks"
    
    if [[ -f "phase1-simple.ps1" ]] && command -v powershell &> /dev/null; then
        log_info "🧹 Running Phase 1 hygiene checks with PowerShell..."
        if powershell -ExecutionPolicy Bypass -File phase1-simple.ps1; then
            log_success "✅ Pre-build hygiene checks passed"
        else
            log_error "❌ Pre-build hygiene checks failed"
            return 1
        fi
    elif [[ -f "phase1-simple.sh" ]]; then
        log_info "🧹 Running Phase 1 hygiene checks with Bash..."
        if bash phase1-simple.sh; then
            log_success "✅ Pre-build hygiene checks passed"
        else
            log_error "❌ Pre-build hygiene checks failed"
            return 1
        fi
    else
        log_warning "⚠️  Phase 1 hygiene script not found, skipping checks"
    fi
}

build_image() {
    local build_variant="$1"
    local build_date="$2"
    local vcs_ref="$3"
    local build_version="$4"
    local image_tag="$5"
    
    log_section "Building ${build_variant^^} Variant"
    
    local build_args=(
        "--build-arg" "BUILD_DATE=${build_date}"
        "--build-arg" "VCS_REF=${vcs_ref}"
        "--build-arg" "BUILD_VERSION=${build_version}"
        "--build-arg" "VARIANT=${build_variant}"
        "--build-arg" "PYTHON_VERSION=3.10"
    )
    
    # Add platform-specific optimizations
    if [[ "$build_variant" == "cpu" ]]; then
        build_args+=("--build-arg" "CPU_BASE_IMAGE=ubuntu:22.04")
    else
        build_args+=("--build-arg" "GPU_BASE_IMAGE=nvidia/cuda:12.1-devel-ubuntu22.04")
    fi
    
    log_info "🔨 Building: $image_tag"
    log_gray "Command: docker build -f Dockerfile.production.enhanced -t $image_tag ${build_args[*]} ."
    
    local start_time=$(date +%s)
    
    if docker build \
        -f Dockerfile.production.enhanced \
        -t "$image_tag" \
        "${build_args[@]}" \
        .; then
        
        local end_time=$(date +%s)
        local duration=$(( (end_time - start_time) / 60 ))
        log_success "✅ Build completed successfully in ${duration} minutes"
        return 0
    else
        log_error "❌ Build failed"
        return 1
    fi
}

validate_image_security() {
    local image_tag="$1"
    
    log_info "🔒 Security validation for: $image_tag"
    
    # Test non-root user
    local user_id
    if user_id=$(docker run --rm "$image_tag" id -u 2>/dev/null); then
        if [[ "$user_id" == "1001" ]]; then
            log_success "✅ Running as non-root user (UID: $user_id)"
        else
            log_error "❌ Security issue: Not running as expected user (UID: $user_id)"
            return 1
        fi
    else
        log_error "❌ Failed to verify user ID"
        return 1
    fi
    
    # Test environment validation
    if docker run --rm -e GAMEFORGE_ENV=development "$image_tag" echo "test" &>/dev/null; then
        log_error "❌ Security issue: Environment validation not working"
        return 1
    else
        log_success "✅ Environment validation working (rejected non-production)"
    fi
    
    return 0
}

get_image_size() {
    local image_tag="$1"
    
    if docker images "$image_tag" --format "table {{.Size}}" | tail -n +2; then
        return 0
    else
        echo "Unknown"
        return 1
    fi
}

check_image_size() {
    local image_tag="$1"
    local variant="$2"
    
    local size
    size=$(get_image_size "$image_tag")
    log_info "📦 Image size: $size"
    
    # Size targets (MB)
    local target
    case "$variant" in
        "cpu") target=500 ;;
        "gpu") target=3000 ;;
        *) target=1000 ;;
    esac
    
    if [[ "$size" =~ ([0-9]+\.?[0-9]*)(MB|GB) ]]; then
        local size_value="${BASH_REMATCH[1]}"
        local unit="${BASH_REMATCH[2]}"
        
        if [[ "$unit" == "GB" ]]; then
            size_value=$(echo "$size_value * 1024" | bc)
        fi
        
        if (( $(echo "$size_value <= $target" | bc) )); then
            log_success "✅ Image size within target (${target}MB)"
            return 0
        else
            log_warning "⚠️  Image size exceeds target (${target}MB). Consider optimization."
            return 1
        fi
    else
        log_warning "⚠️  Could not parse image size for validation"
        return 1
    fi
}

cleanup_images() {
    log_section "Cleanup"
    
    log_info "🧹 Cleaning up dangling images..."
    if docker image prune -f &>/dev/null; then
        log_success "✅ Cleanup completed"
    else
        log_warning "⚠️  Cleanup failed"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--variant)
            VARIANT="$2"
            if [[ ! "$VARIANT" =~ ^(cpu|gpu|both)$ ]]; then
                log_error "Invalid variant: $VARIANT. Must be cpu, gpu, or both"
                exit 1
            fi
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -n|--no-build-arg)
            NO_BUILD_ARG=true
            shift
            ;;
        --validate)
            VALIDATE=true
            shift
            ;;
        --size-check)
            SIZE_CHECK=true
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# ========================================================================
# Main Execution
# ========================================================================

log_section "GameForge Production Phase 2 Build"
log_info "Enhanced Multi-stage Build with CPU/GPU Variants"

# Validate prerequisites
if ! check_docker; then
    exit 1
fi

# Clean up if requested
if [[ "$CLEAN" == true ]]; then
    cleanup_images
fi

# Get build metadata
IFS='|' read -r build_date vcs_ref build_version <<< "$(get_build_metadata)"

log_info "Build Metadata:"
log_gray "  Date: $build_date"
log_gray "  Commit: $vcs_ref"
log_gray "  Version: $build_version"

# Run pre-build hygiene unless disabled
if [[ "$NO_BUILD_ARG" != true ]]; then
    if ! run_prebuild_hygiene; then
        exit 1
    fi
fi

# Determine variants to build
case "$VARIANT" in
    "both") variants=("cpu" "gpu") ;;
    *) variants=("$VARIANT") ;;
esac

# Build tracking
declare -A build_results
build_success=true

for build_variant in "${variants[@]}"; do
    # Generate image tag
    if [[ -n "$TAG" ]]; then
        image_tag="${REGISTRY}:${TAG}-${build_variant}"
    else
        image_tag="${REGISTRY}:${build_version}-${build_variant}"
    fi
    
    # Build image
    if build_image "$build_variant" "$build_date" "$vcs_ref" "$build_version" "$image_tag"; then
        build_results["${build_variant}_success"]=true
        build_results["${build_variant}_tag"]="$image_tag"
        build_results["${build_variant}_size"]=$(get_image_size "$image_tag")
        
        # Validate if requested
        if [[ "$VALIDATE" == true ]]; then
            if validate_image_security "$image_tag"; then
                build_results["${build_variant}_security"]=true
            else
                build_results["${build_variant}_security"]=false
                build_success=false
            fi
        fi
        
        # Size check if requested
        if [[ "$SIZE_CHECK" == true ]]; then
            if check_image_size "$image_tag" "$build_variant"; then
                build_results["${build_variant}_size_check"]=true
            else
                build_results["${build_variant}_size_check"]=false
            fi
        fi
        
        # Push if requested
        if [[ "$PUSH" == true ]]; then
            log_info "📤 Pushing: $image_tag"
            if docker push "$image_tag"; then
                log_success "✅ Push successful"
                build_results["${build_variant}_pushed"]=true
            else
                log_error "❌ Push failed"
                build_results["${build_variant}_pushed"]=false
                build_success=false
            fi
        fi
    else
        build_results["${build_variant}_success"]=false
        build_success=false
    fi
done

# Summary
log_section "Build Summary"

for variant in "${variants[@]}"; do
    if [[ "${build_results[${variant}_success]}" == true ]]; then
        status="✅"
        color="$GREEN"
    else
        status="❌"
        color="$RED"
    fi
    
    echo -e "${color}$status ${variant^^} Variant:${NC}"
    echo -e "${GRAY}  Tag: ${build_results[${variant}_tag]}${NC}"
    echo -e "${GRAY}  Size: ${build_results[${variant}_size]}${NC}"
    
    if [[ "$VALIDATE" == true && -n "${build_results[${variant}_security]:-}" ]]; then
        if [[ "${build_results[${variant}_security]}" == true ]]; then
            echo -e "${GREEN}  Security: ✅${NC}"
        else
            echo -e "${RED}  Security: ❌${NC}"
        fi
    fi
    
    if [[ "$SIZE_CHECK" == true && -n "${build_results[${variant}_size_check]:-}" ]]; then
        if [[ "${build_results[${variant}_size_check]}" == true ]]; then
            echo -e "${GREEN}  Size Check: ✅${NC}"
        else
            echo -e "${YELLOW}  Size Check: ⚠️${NC}"
        fi
    fi
    
    if [[ "$PUSH" == true && -n "${build_results[${variant}_pushed]:-}" ]]; then
        if [[ "${build_results[${variant}_pushed]}" == true ]]; then
            echo -e "${GREEN}  Pushed: ✅${NC}"
        else
            echo -e "${RED}  Pushed: ❌${NC}"
        fi
    fi
done

echo ""
if [[ "$build_success" == true ]]; then
    log_success "🎉 All builds completed successfully!"
    exit 0
else
    log_error "💥 Some builds failed. Check output above."
    exit 1
fi
