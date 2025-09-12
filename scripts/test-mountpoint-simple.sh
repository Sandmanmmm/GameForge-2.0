#!/bin/bash
# Test the mountpoint command without strict error handling

echo "Testing mountpoint without set -e..."

SECURITYFS_MOUNT="/sys/kernel/security"

echo "Mounting securityfs..."
mount -t securityfs securityfs /sys/kernel/security

echo "Checking directory exists:"
if [ -d "$SECURITYFS_MOUNT" ]; then
    echo "✅ Directory exists"
else
    echo "❌ Directory missing"
fi

echo "Testing mountpoint command:"
if mountpoint -q "$SECURITYFS_MOUNT"; then
    echo "✅ Mountpoint detected"
else
    echo "❌ Mountpoint not detected"
fi

echo "Testing combined condition:"
if [ -d "$SECURITYFS_MOUNT" ] && mountpoint -q "$SECURITYFS_MOUNT"; then
    echo "✅ Combined condition passed"
else
    echo "❌ Combined condition failed"
fi

echo "✅ Tests completed"
