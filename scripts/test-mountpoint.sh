#!/bin/bash
# Test mountpoint operations

set -euo pipefail

echo "Testing mountpoint operations..."

SECURITYFS_MOUNT="/sys/kernel/security"

echo "1. Testing directory existence:"
if [ -d "$SECURITYFS_MOUNT" ]; then
    echo "✅ Directory exists: $SECURITYFS_MOUNT"
else
    echo "❌ Directory does not exist: $SECURITYFS_MOUNT"
fi

echo "2. Testing mountpoint without mounting:"
if mountpoint -q "$SECURITYFS_MOUNT"; then
    echo "✅ Already mounted: $SECURITYFS_MOUNT"
else
    echo "❌ Not mounted: $SECURITYFS_MOUNT"
fi

echo "3. Mounting securityfs..."
mount -t securityfs securityfs /sys/kernel/security

echo "4. Testing mountpoint after mounting:"
if mountpoint -q "$SECURITYFS_MOUNT"; then
    echo "✅ Successfully mounted: $SECURITYFS_MOUNT"
else
    echo "❌ Mount failed: $SECURITYFS_MOUNT"
fi

echo "5. Testing combined condition:"
SECURITY_SCORE=0
if [ -d "$SECURITYFS_MOUNT" ] && mountpoint -q "$SECURITYFS_MOUNT"; then
    ((SECURITY_SCORE++))
    echo "✅ Combined test passed, score: $SECURITY_SCORE"
else
    echo "❌ Combined test failed"
fi

echo "6. Testing with && operator:"
SECURITY_SCORE=0
[ -d "$SECURITYFS_MOUNT" ] && mountpoint -q "$SECURITYFS_MOUNT" && ((SECURITY_SCORE++))
echo "After && operator test, score: $SECURITY_SCORE"

echo "✅ Mountpoint tests completed"
