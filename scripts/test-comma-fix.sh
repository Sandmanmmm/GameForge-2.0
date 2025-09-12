#!/bin/bash
# Test the fixed comma removal

set -euo pipefail

# Simulate the problematic content
lsm_analysis='
    "selinux": {
      "status": "enabled",
      "mode": "",
      "policy_version": "",
      "interface": "/sys/fs/selinux"
    },
    "apparmor": {
      "status": "disabled",
      "profiles_loaded": 0,
      "interface": "not_available"
    },
    "capability": {
      "status": "enabled",
      "interface": "built_in"
    },'

echo "Before comma removal:"
echo "'$lsm_analysis'"

# Test the old method (breaks everything)
echo ""
echo "Old method (breaks JSON):"
old_method=$(echo "$lsm_analysis" | sed 's/,$//')
echo "'$old_method'"

# Test the new method
echo ""
echo "New method (should preserve internal commas):"
new_method=$(echo "$lsm_analysis" | sed 's/,\([[:space:]]*\)$/\1/')
echo "'$new_method'"

# Test complete JSON with new method
test_json=$(cat <<EOF
{
  "lsm_details": {$new_method
  }
}
EOF
)

echo ""
echo "Complete JSON with new method:"
echo "$test_json"

echo ""
echo "JSON validation:"
echo "$test_json" | jq . 2>&1 || echo "JSON is invalid"
