#!/bin/bash
# Test the exact security scoring and JSON generation from main script

set -euo pipefail

echo "Testing security init scoring section..."

# Set up variables exactly as in main script
SECURITY_STATUS_DIR="/shared/security"
SECURITY_READINESS_FILE="$SECURITY_STATUS_DIR/security-readiness.json"
SECURITYFS_MOUNT="/sys/kernel/security"

mkdir -p "$SECURITY_STATUS_DIR"
mount -t securityfs securityfs /sys/kernel/security >/dev/null 2>&1 || echo "SecurityFS already mounted"

echo "Step 1: Calculate security score..."

SECURITY_SCORE=0
TOTAL_CHECKS=6

# Check securityfs
[ -d "$SECURITYFS_MOUNT" ] && mountpoint -q "$SECURITYFS_MOUNT" && ((SECURITY_SCORE++))
echo "SecurityFS check: $SECURITY_SCORE"

# Check LSM availability
[ -f "$SECURITYFS_MOUNT/lsm" ] && ((SECURITY_SCORE++))
echo "LSM check: $SECURITY_SCORE"

# Check namespaces
[ -f /proc/self/ns/pid ] && ((SECURITY_SCORE++))
echo "PID NS check: $SECURITY_SCORE"

[ -f /proc/self/ns/user ] && ((SECURITY_SCORE++))
echo "User NS check: $SECURITY_SCORE"

# Check cgroups
([ -f /sys/fs/cgroup/cgroup.controllers ] || [ -d /sys/fs/cgroup/memory ]) && ((SECURITY_SCORE++))
echo "Cgroups check: $SECURITY_SCORE"

# Check seccomp
grep -q 'Seccomp:.*[12]' /proc/self/status 2>/dev/null && ((SECURITY_SCORE++))
echo "Seccomp check: $SECURITY_SCORE"

SECURITY_PERCENTAGE=$((SECURITY_SCORE * 100 / TOTAL_CHECKS))

echo "📈 Security Score: $SECURITY_SCORE/$TOTAL_CHECKS ($SECURITY_PERCENTAGE%)"

echo "Step 2: Determine minimum score..."

# Determine minimum score based on environment
if grep -q "microsoft\|WSL" /proc/version 2>/dev/null || [ -n "${WSL_DISTRO_NAME:-}" ] || [ -n "${WSLENV:-}" ]; then
    MINIMUM_SCORE=3  # Docker Desktop/WSL2: relaxed requirements
    echo "🐳 Docker Desktop environment: minimum security score = $MINIMUM_SCORE"
else
    MINIMUM_SCORE=4  # Native Linux: standard requirements
    echo "🖥️ Native Linux environment: minimum security score = $MINIMUM_SCORE"
fi

echo "Step 3: Generate readiness status..."

# Generate final readiness status
READY=$([ $SECURITY_SCORE -ge $MINIMUM_SCORE ] && echo "true" || echo "false")
TIMESTAMP=$(date -Iseconds)

echo "READY=$READY, TIMESTAMP=$TIMESTAMP"

echo "Step 4: Create JSON file..."

# Simple JSON generation without complex HEREDOC
cat > "$SECURITY_READINESS_FILE" << EOF
{
  "ready": $READY,
  "score": $SECURITY_SCORE,
  "total": $TOTAL_CHECKS,
  "percentage": $SECURITY_PERCENTAGE,
  "minimum_required": $MINIMUM_SCORE,
  "timestamp": "$TIMESTAMP",
  "issues": []
}
EOF

echo "Step 5: Verify JSON..."
if [ -f "$SECURITY_READINESS_FILE" ]; then
    echo "✅ JSON file created successfully"
    cat "$SECURITY_READINESS_FILE"
    echo ""
    echo "JSON validation:"
    jq . "$SECURITY_READINESS_FILE" || echo "❌ JSON is invalid"
else
    echo "❌ JSON file was not created"
fi

echo "Step 6: Check final condition..."
if [ $SECURITY_SCORE -ge $MINIMUM_SCORE ]; then
    echo "✅ Security check passed: $SECURITY_SCORE >= $MINIMUM_SCORE"
else
    echo "❌ Security check failed: $SECURITY_SCORE < $MINIMUM_SCORE"
fi
