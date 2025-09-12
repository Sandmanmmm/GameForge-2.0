#!/bin/bash
# GameForge Production Guardrails - Pre-commit Hook
# Place this in .git/hooks/pre-commit and make it executable
# Or run manually before committing: ./scripts/guardrails-check.sh

set -e

echo "🛡️ GameForge Production Guardrails Check"
echo "========================================"

VIOLATIONS=0

# ========================================================================
# Security Checks
# ========================================================================
echo ""
echo "🔒 SECURITY CHECKS"
echo "------------------"

# Check for .env files
echo "Checking for .env files..."
ENV_FILES=$(git diff --cached --name-only --diff-filter=A | grep -E '\.env($|\.)' | grep -v -E '\.(example|template)$' || true)
if [ ! -z "$ENV_FILES" ]; then
    echo "❌ BLOCKED: .env files detected in commit!"
    echo "$ENV_FILES"
    echo "💡 Use .env.example instead and add secrets to Vault/K8s"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No .env files in commit"
fi

# Check for certificate/key files
echo "Checking for certificate/key files..."
CERT_FILES=$(git diff --cached --name-only --diff-filter=A | grep -E '\.(pem|key|crt|p12|pfx)$' || true)
if [ ! -z "$CERT_FILES" ]; then
    echo "❌ BLOCKED: Certificate/key files detected!"
    echo "$CERT_FILES"
    echo "💡 Use K8s TLS secrets or certificate managers"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No certificate/key files in commit"
fi

# ========================================================================
# Structure Checks
# ========================================================================
echo ""
echo "🏗️ STRUCTURE CHECKS"
echo "-------------------"

# Check for unauthorized top-level files
echo "Checking top-level file additions..."
NEW_TOP_LEVEL=$(git diff --cached --name-only --diff-filter=A | grep -v '/' | grep -v -E '^(README\.md|LICENSE|CHANGELOG\.md|CONTRIBUTING\.md|package\.json|package-lock\.json|yarn\.lock|tsconfig\.json|Dockerfile|docker-compose.*\.yml|\.gitignore|\.dockerignore|\.npmrc|\.env\.example|\.env\.template|docker\.env\.example|components\.json|DOCKER_STRUCTURE\.md)$' || true)
if [ ! -z "$NEW_TOP_LEVEL" ]; then
    echo "❌ BLOCKED: Unauthorized top-level files!"
    echo "$NEW_TOP_LEVEL"
    echo "💡 Move files to appropriate subdirectories (src/, docker/, k8s/, etc.)"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No unauthorized top-level files"
fi

# Check Docker Compose file count
echo "Checking Docker Compose file count..."
COMPOSE_COUNT=$(find . -name "docker-compose*.yml" -o -name "docker-compose*.yaml" | wc -l)
if [ $COMPOSE_COUNT -gt 4 ]; then
    echo "❌ BLOCKED: Too many Docker Compose files ($COMPOSE_COUNT > 4)!"
    echo "💡 Consolidate compose files or use overrides"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ Docker Compose file count OK ($COMPOSE_COUNT/4)"
fi

# ========================================================================
# Dockerfile Checks
# ========================================================================
echo ""
echo "🐳 DOCKERFILE CHECKS"
echo "--------------------"

DOCKERFILE_COUNT=$(find . -name "Dockerfile*" -not -path "./node_modules/*" | wc -l)
if [ $DOCKERFILE_COUNT -gt 10 ]; then
    echo "❌ BLOCKED: Too many Dockerfiles ($DOCKERFILE_COUNT > 10)!"
    echo "💡 Use multi-stage builds instead"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ Dockerfile count reasonable ($DOCKERFILE_COUNT/10)"
fi

# ========================================================================
# Dependency Checks
# ========================================================================
echo ""
echo "📦 DEPENDENCY CHECKS"
echo "--------------------"

# Check for package.json proliferation
PACKAGE_JSON_COUNT=$(find . -name "package.json" -not -path "./node_modules/*" | wc -l)
if [ $PACKAGE_JSON_COUNT -gt 3 ]; then
    echo "⚠️  WARNING: Many package.json files ($PACKAGE_JSON_COUNT > 3)"
    echo "💡 Consider monorepo structure"
else
    echo "✅ Package.json count reasonable ($PACKAGE_JSON_COUNT/3)"
fi

# Check for mixed package managers
NPM_LOCKS=$(find . -name "package-lock.json" -not -path "./node_modules/*" | wc -l)
YARN_LOCKS=$(find . -name "yarn.lock" -not -path "./node_modules/*" | wc -l)
if [ $NPM_LOCKS -gt 0 ] && [ $YARN_LOCKS -gt 0 ]; then
    echo "❌ BLOCKED: Mixed package managers detected!"
    echo "💡 Choose either npm or yarn consistently"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ Package manager consistency maintained"
fi

# ========================================================================
# File Size Checks
# ========================================================================
echo ""
echo "📏 FILE SIZE CHECKS"
echo "-------------------"

# Check for large files being added
LARGE_FILES=$(git diff --cached --name-only --diff-filter=A | xargs -I {} find {} -size +50M 2>/dev/null || true)
if [ ! -z "$LARGE_FILES" ]; then
    echo "❌ BLOCKED: Large files detected (>50MB)!"
    echo "$LARGE_FILES"
    echo "💡 Use Git LFS for large files or external storage"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No large files in commit"
fi

# ========================================================================
# Final Report
# ========================================================================
echo ""
echo "📊 GUARDRAILS SUMMARY"
echo "====================="

if [ $VIOLATIONS -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED - Commit allowed!"
    echo ""
    echo "🎯 Your commit maintains:"
    echo "  ✅ Security standards (no secrets)"
    echo "  ✅ Clean structure (proper organization)"
    echo "  ✅ Reasonable file counts"
    echo "  ✅ Consistent dependency management"
    echo ""
    echo "🚀 Ready for production deployment!"
    exit 0
else
    echo "❌ $VIOLATIONS VIOLATION(S) DETECTED - Commit blocked!"
    echo ""
    echo "🔧 Please fix the issues above and try again"
    echo ""
    echo "💡 Quick fixes:"
    echo "  - Remove .env files and use .env.example"
    echo "  - Move top-level files to proper directories"
    echo "  - Consolidate redundant Docker files"
    echo "  - Use secure secret management"
    exit 1
fi