#!/bin/bash
# Test the fixed comma removal with different methods

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

echo "Original with trailing comma:"
echo "'$lsm_analysis'"

# Test sed with -z flag (null separated)
echo ""
echo "Using sed -z method:"
fixed_analysis=$(printf "%s" "$lsm_analysis" | sed -z 's/,\s*$//')
echo "'$fixed_analysis'"

# Test complete JSON
test_json=$(cat <<EOF
{
  "lsm_details": {$fixed_analysis
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
