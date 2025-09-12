#!/bin/bash
# Test JSON generation to identify comma issues

set -euo pipefail

echo "Testing JSON generation..."

# Test variables
selinux_status="enabled"
selinux_mode=""
selinux_policy=""

# Test basic JSON generation
json_test=$(cat <<EOF
{
  "selinux": {
    "status": "$selinux_status",
    "mode": "$selinux_mode",
    "policy_version": "$selinux_policy",
    "interface": "/sys/fs/selinux"
  }
}
EOF
)

echo "Generated JSON:"
echo "$json_test"

echo ""
echo "Testing with jq:"
echo "$json_test" | jq -r '.selinux.status'
