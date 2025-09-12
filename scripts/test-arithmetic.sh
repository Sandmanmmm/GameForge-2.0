#!/bin/bash
# Test basic arithmetic operations

set -euo pipefail

echo "Testing basic arithmetic..."

SECURITY_SCORE=0
echo "Initial SECURITY_SCORE: $SECURITY_SCORE"

echo "Testing increment operations..."

# Test simple increment
SECURITY_SCORE=1
echo "After setting to 1: $SECURITY_SCORE"

# Test compound assignment
((SECURITY_SCORE++))
echo "After ((SECURITY_SCORE++)): $SECURITY_SCORE"

# Test conditional increment
SECURITY_SCORE=0
echo "Reset to 0: $SECURITY_SCORE"

if [ -d "/tmp" ]; then
    ((SECURITY_SCORE++))
    echo "After conditional increment: $SECURITY_SCORE"
fi

# Test the exact pattern from main script
SECURITY_SCORE=0
[ -d "/tmp" ] && ((SECURITY_SCORE++))
echo "After [ -d /tmp ] && ((SECURITY_SCORE++)): $SECURITY_SCORE"

echo "✅ Arithmetic tests completed"
