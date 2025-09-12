#!/bin/bash
SECURITY_SCORE=0
echo "Testing security features:"

# Check securityfs
if [ -d /sys/kernel/security ] && mountpoint -q /sys/kernel/security; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "SecurityFS: ✓"
else
    echo "SecurityFS: ✗"
fi

# Check LSM
if [ -f /sys/kernel/security/lsm ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "LSM: ✓"
else
    echo "LSM: ✗"
fi

# Check namespaces  
if [ -f /proc/self/ns/pid ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "PID NS: ✓"
else
    echo "PID NS: ✗"
fi

if [ -f /proc/self/ns/user ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "User NS: ✓"
else
    echo "User NS: ✗"
fi

# Check cgroups
if [ -f /sys/fs/cgroup/cgroup.controllers ] || [ -d /sys/fs/cgroup/memory ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "Cgroups: ✓"
else
    echo "Cgroups: ✗"
fi

# Check seccomp (corrected)
if grep -q 'Seccomp:.*[12]' /proc/self/status 2>/dev/null; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "Seccomp: ✓"
else
    echo "Seccomp: ✗"
fi

echo "Total Score: $SECURITY_SCORE/6"
