#!/bin/bash
# Test script to debug security scoring
set -x  # Enable debug output

SHARED_DIR="/shared"
SECURITY_STATUS_DIR="$SHARED_DIR/security"
SECURITYFS_MOUNT="/sys/kernel/security"
SECURITY_READINESS_FILE="$SECURITY_STATUS_DIR/security-readiness.json"

mkdir -p "$SECURITY_STATUS_DIR"

# Mount SecurityFS
mount -t securityfs securityfs "$SECURITYFS_MOUNT" 2>/dev/null

echo "=== TESTING SECURITY SCORE ==="

SECURITY_SCORE=0
TOTAL_CHECKS=6

echo "Testing each security component:"

# Check securityfs
if [ -d "$SECURITYFS_MOUNT" ] && mountpoint -q "$SECURITYFS_MOUNT"; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "✅ SecurityFS: PASS (score: $SECURITY_SCORE)"
else
    echo "❌ SecurityFS: FAIL (score: $SECURITY_SCORE)"
fi

# Check LSM availability
if [ -f "$SECURITYFS_MOUNT/lsm" ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "✅ LSM: PASS (score: $SECURITY_SCORE)"
else
    echo "❌ LSM: FAIL (score: $SECURITY_SCORE)"
fi

# Check namespaces
if [ -f /proc/self/ns/pid ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "✅ PID NS: PASS (score: $SECURITY_SCORE)"
else
    echo "❌ PID NS: FAIL (score: $SECURITY_SCORE)"
fi

if [ -f /proc/self/ns/user ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "✅ User NS: PASS (score: $SECURITY_SCORE)"
else
    echo "❌ User NS: FAIL (score: $SECURITY_SCORE)"
fi

# Check cgroups
if [ -f /sys/fs/cgroup/cgroup.controllers ] || [ -d /sys/fs/cgroup/memory ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "✅ Cgroups: PASS (score: $SECURITY_SCORE)"
else
    echo "❌ Cgroups: FAIL (score: $SECURITY_SCORE)"
fi

# Check seccomp (corrected)
if grep -q 'Seccomp:.*[12]' /proc/self/status 2>/dev/null; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "✅ Seccomp: PASS (score: $SECURITY_SCORE)"
else
    echo "❌ Seccomp: FAIL (score: $SECURITY_SCORE)"
fi

SECURITY_PERCENTAGE=$((SECURITY_SCORE * 100 / TOTAL_CHECKS))

echo "=== FINAL RESULTS ==="
echo "Security Score: $SECURITY_SCORE/$TOTAL_CHECKS ($SECURITY_PERCENTAGE%)"

# Determine minimum score based on environment
if grep -q "microsoft\|WSL" /proc/version 2>/dev/null || [ -n "${WSL_DISTRO_NAME:-}" ] || [ -n "${WSLENV:-}" ]; then
    MINIMUM_SCORE=3  # Docker Desktop/WSL2: relaxed requirements
    echo "Environment: Docker Desktop/WSL2"
    echo "Minimum Required Score: $MINIMUM_SCORE"
else
    MINIMUM_SCORE=4  # Native Linux: standard requirements
    echo "Environment: Native Linux"
    echo "Minimum Required Score: $MINIMUM_SCORE"
fi

# Test readiness
if [ $SECURITY_SCORE -ge $MINIMUM_SCORE ]; then
    echo "✅ SECURITY READY: Score $SECURITY_SCORE >= $MINIMUM_SCORE"
    exit 0
else
    echo "❌ SECURITY NOT READY: Score $SECURITY_SCORE < $MINIMUM_SCORE"
    exit 1
fi
