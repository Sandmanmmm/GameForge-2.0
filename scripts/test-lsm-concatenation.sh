#!/bin/bash
# Test the exact LSM analysis concatenation method

set -euo pipefail

echo "Testing LSM analysis concatenation..."

# Simulate the exact method used in LSM detector
lsm_analysis=""
selinux_status="enabled"
selinux_mode=""
selinux_policy=""

# Test the exact concatenation method used in the script
lsm_analysis="$lsm_analysis
    \"selinux\": {
      \"status\": \"$selinux_status\",
      \"mode\": \"$selinux_mode\",
      \"policy_version\": \"$selinux_policy\",
      \"interface\": \"/sys/fs/selinux\"
    },"

echo "Raw lsm_analysis content:"
echo "'$lsm_analysis'"

echo ""
echo "Formatted lsm_analysis:"
echo "$lsm_analysis"

# Test in a complete JSON structure
test_json=$(cat <<EOF
{
  "test": true,
  "lsm_details": {$lsm_analysis
  }
}
EOF
)

echo ""
echo "Complete JSON test:"
echo "$test_json"

echo ""
echo "Testing with jq:"
echo "$test_json" | jq . 2>&1 || echo "JSON is invalid"
