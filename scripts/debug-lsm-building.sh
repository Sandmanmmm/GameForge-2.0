#!/bin/bash
# Debug LSM analysis building

set -euo pipefail

# Simulate the LSM list from actual detection
lsm_list="capability,landlock,yama,safesetid,selinux"
lsm_analysis=""

# Add SELinux (should be added since it's in the list)
if echo "$lsm_list" | grep -q "selinux"; then
    selinux_status="enabled"
    selinux_mode=""
    selinux_policy=""
    
    lsm_analysis="$lsm_analysis
    \"selinux\": {
      \"status\": \"$selinux_status\",
      \"mode\": \"$selinux_mode\",
      \"policy_version\": \"$selinux_policy\",
      \"interface\": \"/sys/fs/selinux\"
    },"
    echo "Added SELinux to analysis"
fi

# Add AppArmor (should NOT be added since it's not in the list)
if echo "$lsm_list" | grep -q "apparmor"; then
    echo "AppArmor detected"
else
    lsm_analysis="$lsm_analysis
    \"apparmor\": {
      \"status\": \"disabled\",
      \"profiles_loaded\": 0,
      \"interface\": \"not_available\"
    },"
    echo "Added AppArmor as disabled"
fi

# Add Capability (should be added since it's in the list)
if echo "$lsm_list" | grep -q "capability"; then
    lsm_analysis="$lsm_analysis
    \"capability\": {
      \"status\": \"enabled\",
      \"interface\": \"built_in\"
    },"
    echo "Added Capability"
fi

echo ""
echo "Raw lsm_analysis before comma removal:"
echo "'$lsm_analysis'"

# Remove trailing comma
lsm_analysis=$(echo "$lsm_analysis" | sed 's/,$//')

echo ""
echo "After comma removal:"
echo "'$lsm_analysis'"

# Test complete JSON
test_json=$(cat <<EOF
{
  "lsm_details": {$lsm_analysis
  }
}
EOF
)

echo ""
echo "Complete JSON:"
echo "$test_json"

echo ""
echo "JSON validation:"
echo "$test_json" | jq . 2>&1 || echo "JSON is invalid"
