#!/bin/bash

# Policy Validation Test Suite
# Tests OPA policies against various scenarios

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
POLICY_DIR="ci/policies"
TEST_DATA_DIR="ci/tests/policy-test-data"
CONFTEST_VERSION="0.46.0"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[TEST] ${message}${NC}"
}

# Function to run policy test
run_policy_test() {
    local test_name=$1
    local policy_file=$2
    local test_file=$3
    local expected_result=$4  # "pass" or "fail"
    
    print_status "$BLUE" "Running test: $test_name"
    
    # Run conftest
    if conftest verify --policy "$POLICY_DIR/$policy_file" "$test_file" >/dev/null 2>&1; then
        result="pass"
    else
        result="fail"
    fi
    
    # Check if result matches expectation
    if [ "$result" = "$expected_result" ]; then
        print_status "$GREEN" "✓ $test_name: PASSED (expected $expected_result, got $result)"
        return 0
    else
        print_status "$RED" "✗ $test_name: FAILED (expected $expected_result, got $result)"
        return 1
    fi
}

# Create test data directory
mkdir -p "$TEST_DATA_DIR"

# Create test files for security policy tests
create_security_test_files() {
    # Valid secure deployment
    cat > "$TEST_DATA_DIR/secure-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
  namespace: gameforge
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
      - name: app
        image: gameforge/app:v1.0.0
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
            - ALL
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
EOF

    # Insecure deployment (should fail)
    cat > "$TEST_DATA_DIR/insecure-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: insecure-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: app:latest
        securityContext:
          privileged: true
          runAsUser: 0
EOF

    # Valid network policy
    cat > "$TEST_DATA_DIR/secure-network-policy.yaml" << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: secure-policy
  namespace: gameforge
spec:
  podSelector:
    matchLabels:
      app: gameforge
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: gameforge
    ports:
    - protocol: TCP
      port: 8080
EOF

    # Missing network policy (should fail compliance)
    cat > "$TEST_DATA_DIR/no-network-policy-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-without-netpol
  namespace: gameforge
spec:
  template:
    spec:
      containers:
      - name: app
        image: gameforge/app:v1.0.0
EOF
}

# Create test files for Docker policy tests
create_docker_test_files() {
    # Valid Docker Compose
    cat > "$TEST_DATA_DIR/secure-docker-compose.yml" << 'EOF'
version: '3.8'
services:
  api:
    image: gameforge/api:1.0.0
    user: "1000:1000"
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:noexec,nosuid,size=50m
    networks:
      - gameforge-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

networks:
  gameforge-network:
    driver: bridge
EOF

    # Insecure Docker Compose (should fail)
    cat > "$TEST_DATA_DIR/insecure-docker-compose.yml" << 'EOF'
version: '3.8'
services:
  api:
    image: app:latest
    privileged: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    network_mode: host
EOF
}

# Create test files for compliance policy tests
create_compliance_test_files() {
    # Valid compliance deployment
    cat > "$TEST_DATA_DIR/compliant-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gameforge-api-service
  namespace: gameforge
  labels:
    app: gameforge-api
    version: "1.0.0"
    environment: production
    team: platform
spec:
  template:
    metadata:
      labels:
        app: gameforge-api
        version: "1.0.0"
    spec:
      containers:
      - name: api
        image: gameforge/api:1.0.0
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
EOF

    # Non-compliant deployment (should fail)
    cat > "$TEST_DATA_DIR/non-compliant-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-app
  namespace: default
spec:
  template:
    spec:
      containers:
      - name: app
        image: app:latest
EOF
}

# Main test execution
main() {
    print_status "$BLUE" "Starting Policy Validation Test Suite"
    echo
    
    # Create test data
    print_status "$BLUE" "Creating test data..."
    create_security_test_files
    create_docker_test_files
    create_compliance_test_files
    
    # Test counters
    total_tests=0
    passed_tests=0
    
    echo
    print_status "$BLUE" "Running Security Policy Tests..."
    echo "─────────────────────────────────────────────────────────"
    
    # Security policy tests
    tests=(
        "Secure deployment should pass|security.rego|$TEST_DATA_DIR/secure-deployment.yaml|pass"
        "Insecure deployment should fail|security.rego|$TEST_DATA_DIR/insecure-deployment.yaml|fail"
        "Network policy should pass|security.rego|$TEST_DATA_DIR/secure-network-policy.yaml|pass"
    )
    
    for test in "${tests[@]}"; do
        IFS='|' read -r name policy file expected <<< "$test"
        total_tests=$((total_tests + 1))
        if run_policy_test "$name" "$policy" "$file" "$expected"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    echo
    print_status "$BLUE" "Running Docker Policy Tests..."
    echo "─────────────────────────────────────────────────────────"
    
    # Docker policy tests
    docker_tests=(
        "Secure Docker Compose should pass|docker.rego|$TEST_DATA_DIR/secure-docker-compose.yml|pass"
        "Insecure Docker Compose should fail|docker.rego|$TEST_DATA_DIR/insecure-docker-compose.yml|fail"
    )
    
    for test in "${docker_tests[@]}"; do
        IFS='|' read -r name policy file expected <<< "$test"
        total_tests=$((total_tests + 1))
        if run_policy_test "$name" "$policy" "$file" "$expected"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    echo
    print_status "$BLUE" "Running Compliance Policy Tests..."
    echo "─────────────────────────────────────────────────────────"
    
    # Compliance policy tests
    compliance_tests=(
        "Compliant deployment should pass|compliance.rego|$TEST_DATA_DIR/compliant-deployment.yaml|pass"
        "Non-compliant deployment should fail|compliance.rego|$TEST_DATA_DIR/non-compliant-deployment.yaml|fail"
    )
    
    for test in "${compliance_tests[@]}"; do
        IFS='|' read -r name policy file expected <<< "$test"
        total_tests=$((total_tests + 1))
        if run_policy_test "$name" "$policy" "$file" "$expected"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    # Generate test report
    echo
    echo "═══════════════════════════════════════════════════════════"
    print_status "$BLUE" "Test Summary"
    echo "═══════════════════════════════════════════════════════════"
    echo "Total tests: $total_tests"
    echo "Passed: $passed_tests"
    echo "Failed: $((total_tests - passed_tests))"
    
    if [ $passed_tests -eq $total_tests ]; then
        print_status "$GREEN" "All tests passed! 🎉"
        exit 0
    else
        print_status "$RED" "Some tests failed! ❌"
        exit 1
    fi
}

# Run tests
main "$@"
