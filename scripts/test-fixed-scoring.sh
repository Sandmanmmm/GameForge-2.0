#!/bin/bash
# Test the new fixed security scoring logic

set -euo pipefail

echo "Testing fixed security scoring logic..."

SECURITYFS_MOUNT="/sys/kernel/security"
SECURITY_SCORE=0
TOTAL_CHECKS=6

# Mount securityfs first
mount -t securityfs securityfs /sys/kernel/security >/dev/null 2>&1 || echo "SecurityFS already mounted"

echo "Testing each check with new if-statement logic:"

# Check securityfs
echo -n "1. SecurityFS check: "
if [ -d "$SECURITYFS_MOUNT" ] && mountpoint -q "$SECURITYFS_MOUNT"; then
    ((SECURITY_SCORE++))
    echo "✅ PASS (score: $SECURITY_SCORE)"
else
    echo "❌ FAIL"
fi

# Check LSM availability
echo -n "2. LSM check: "
if [ -f "$SECURITYFS_MOUNT/lsm" ]; then
    ((SECURITY_SCORE++))
    echo "✅ PASS (score: $SECURITY_SCORE)"
else
    echo "❌ FAIL"
fi

# Check namespaces
echo -n "3. PID NS check: "
if [ -f /proc/self/ns/pid ]; then
    ((SECURITY_SCORE++))
    echo "✅ PASS (score: $SECURITY_SCORE)"
else
    echo "❌ FAIL"
fi

echo -n "4. User NS check: "
if [ -f /proc/self/ns/user ]; then
    ((SECURITY_SCORE++))
    echo "✅ PASS (score: $SECURITY_SCORE)"
else
    echo "❌ FAIL"
fi

# Check cgroups
echo -n "5. Cgroups check: "
if [ -f /sys/fs/cgroup/cgroup.controllers ] || [ -d /sys/fs/cgroup/memory ]; then
    ((SECURITY_SCORE++))
    echo "✅ PASS (score: $SECURITY_SCORE)"
else
    echo "❌ FAIL"
fi

# Check seccomp
echo -n "6. Seccomp check: "
if grep -q 'Seccomp:.*[12]' /proc/self/status 2>/dev/null; then
    ((SECURITY_SCORE++))
    echo "✅ PASS (score: $SECURITY_SCORE)"
else
    echo "❌ FAIL"
fi

SECURITY_PERCENTAGE=$((SECURITY_SCORE * 100 / TOTAL_CHECKS))

echo ""
echo "📈 Security Score: $SECURITY_SCORE/$TOTAL_CHECKS ($SECURITY_PERCENTAGE%)"

# Test environment detection
if grep -q "microsoft\|WSL" /proc/version 2>/dev/null || [ -n "${WSL_DISTRO_NAME:-}" ] || [ -n "${WSLENV:-}" ]; then
    MINIMUM_SCORE=3
    echo "🐳 Docker Desktop environment: minimum security score = $MINIMUM_SCORE"
else
    MINIMUM_SCORE=4
    echo "🖥️ Native Linux environment: minimum security score = $MINIMUM_SCORE"
fi

if [ $SECURITY_SCORE -ge $MINIMUM_SCORE ]; then
    echo "✅ Security check PASSED: $SECURITY_SCORE >= $MINIMUM_SCORE"
    exit 0
else
    echo "❌ Security check FAILED: $SECURITY_SCORE < $MINIMUM_SCORE"
    exit 1
fi
