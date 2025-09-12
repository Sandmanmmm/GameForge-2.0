#!/bin/bash
# Docker Desktop/WSL2 Security Compatibility Analysis

echo "========================================================"
echo "Docker Desktop/WSL2 Security Compatibility Analysis"
echo "========================================================"
echo ""

# Environment Detection
echo "ENVIRONMENT:"
echo "- Kernel: $(uname -r)"
echo "- OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "- Container: $(grep microsoft /proc/version >/dev/null 2>&1 && echo "WSL2/Docker Desktop" || echo "Native Linux")"
echo ""

# Core Security Features
echo "CORE SECURITY FEATURES:"
AVAILABLE=0
TOTAL=6

# SecurityFS
if [ -d /sys/kernel/security ] && mountpoint -q /sys/kernel/security 2>/dev/null; then
    echo "✅ SecurityFS: mounted at /sys/kernel/security"
    AVAILABLE=$((AVAILABLE + 1))
else
    echo "❌ SecurityFS: not mounted"
fi

# LSM Interface
if [ -f /sys/kernel/security/lsm ]; then
    echo "✅ LSM Interface: $(cat /sys/kernel/security/lsm)"
    AVAILABLE=$((AVAILABLE + 1))
else
    echo "❌ LSM Interface: not available"
fi

# PID Namespaces
if [ -f /proc/self/ns/pid ]; then
    echo "✅ PID Namespaces: supported"
    AVAILABLE=$((AVAILABLE + 1))
else
    echo "❌ PID Namespaces: not supported"
fi

# User Namespaces
if [ -f /proc/self/ns/user ]; then
    echo "✅ User Namespaces: supported"
    AVAILABLE=$((AVAILABLE + 1))
else
    echo "❌ User Namespaces: not supported"
fi

# Cgroups
if [ -f /sys/fs/cgroup/cgroup.controllers ] || [ -d /sys/fs/cgroup/memory ]; then
    echo "✅ Cgroups: available"
    AVAILABLE=$((AVAILABLE + 1))
else
    echo "❌ Cgroups: not available"
fi

# Seccomp
if grep -q seccomp /proc/self/status 2>/dev/null; then
    echo "✅ Seccomp: supported"
    AVAILABLE=$((AVAILABLE + 1))
else
    echo "❌ Seccomp: not supported"
fi

echo ""
echo "SYSCTL PARAMETER AVAILABILITY:"

# Test critical sysctl parameters
SYSCTL_AVAILABLE=0
SYSCTL_TOTAL=12

sysctl_params=(
    "net.ipv4.ip_forward"
    "net.ipv4.conf.all.send_redirects"
    "kernel.dmesg_restrict"
    "kernel.kptr_restrict"
    "kernel.yama.ptrace_scope"
    "vm.mmap_rnd_bits"
    "fs.protected_hardlinks"
    "fs.protected_symlinks"
    "user.max_user_namespaces"
    "net.core.bpf_jit_harden"
    "kernel.unprivileged_bpf_disabled"
    "net.ipv4.tcp_syncookies"
)

for param in "${sysctl_params[@]}"; do
    if sysctl "$param" >/dev/null 2>&1; then
        echo "✅ $param: available"
        SYSCTL_AVAILABLE=$((SYSCTL_AVAILABLE + 1))
    else
        echo "❌ $param: not available"
    fi
done

echo ""
echo "========================================================"
echo "COMPATIBILITY SUMMARY"
echo "========================================================"
echo "Core Security Features: $AVAILABLE/$TOTAL ($(($AVAILABLE * 100 / $TOTAL))%)"
echo "Sysctl Parameters: $SYSCTL_AVAILABLE/$SYSCTL_TOTAL ($(($SYSCTL_AVAILABLE * 100 / $SYSCTL_TOTAL))%)"

if [ $AVAILABLE -ge 4 ]; then
    echo "✅ Security baseline: ACCEPTABLE for Docker Desktop"
else
    echo "❌ Security baseline: INSUFFICIENT"
fi

if [ $SYSCTL_AVAILABLE -eq 0 ]; then
    echo "⚠️  Kernel hardening: COMPLETELY UNAVAILABLE"
elif [ $SYSCTL_AVAILABLE -lt 6 ]; then
    echo "⚠️  Kernel hardening: PARTIALLY AVAILABLE"
else
    echo "✅ Kernel hardening: MOSTLY AVAILABLE"
fi

echo ""
echo "RECOMMENDATIONS:"
echo "1. Focus on container-level security (capabilities, seccomp profiles)"
echo "2. Use Docker security features (user namespaces, read-only mounts)"
echo "3. Implement application-level security controls"
echo "4. Consider host-level security for production deployments"
echo "========================================================"
