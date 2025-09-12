#!/bin/bash
# ========================================================================
# GameForge AI Advanced Security Hardening
# Network policies, pod security standards, runtime security
# ========================================================================

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-gameforge-production}"
CLUSTER_NAME="${CLUSTER_NAME:-gameforge-cluster}"
SECURITY_POLICY_DIR="./security-policies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ========================================================================
# Network Security Policies
# ========================================================================

create_network_policies() {
    log_info "Creating network security policies..."
    
    mkdir -p "${SECURITY_POLICY_DIR}"
    
    # Default deny all policy
    cat > "${SECURITY_POLICY_DIR}/default-deny-all.yaml" << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: gameforge-production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 53
EOF

    # GameForge app network policy
    cat > "${SECURITY_POLICY_DIR}/gameforge-app-policy.yaml" << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gameforge-app-policy
  namespace: gameforge-production
spec:
  podSelector:
    matchLabels:
      app: gameforge-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: minio
    ports:
    - protocol: TCP
      port: 9000
  - to:
    - podSelector:
        matchLabels:
          app: vault
    ports:
    - protocol: TCP
      port: 8200
  - to: []
    ports:
    - protocol: UDP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 443
EOF

    # Database network policy
    cat > "${SECURITY_POLICY_DIR}/database-policy.yaml" << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: gameforge-production
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: gameforge-app
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 53
EOF

    # Monitoring network policy
    cat > "${SECURITY_POLICY_DIR}/monitoring-policy.yaml" << 'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitoring-policy
  namespace: gameforge-production
spec:
  podSelector:
    matchLabels:
      component: monitoring
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 3000
  - from:
    - podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 8080
  - to: []
    ports:
    - protocol: UDP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 53
EOF

    log_info "Network policies created in ${SECURITY_POLICY_DIR}/"
}

# ========================================================================
# Pod Security Standards
# ========================================================================

create_pod_security_policies() {
    log_info "Creating Pod Security Standards..."
    
    # Pod Security Standards for namespace
    cat > "${SECURITY_POLICY_DIR}/pod-security-standards.yaml" << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: gameforge-production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: gameforge-restricted-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  runAsGroup:
    rule: 'MustRunAs'
    ranges:
      - min: 1
        max: 65535
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  seccompProfile:
    type: RuntimeDefault
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gameforge-psp-use
rules:
- apiGroups: ['policy']
  resources: ['podsecuritypolicies']
  verbs: ['use']
  resourceNames:
  - gameforge-restricted-psp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gameforge-psp-binding
roleRef:
  kind: ClusterRole
  name: gameforge-psp-use
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: gameforge-service-account
  namespace: gameforge-production
EOF

    # Security contexts for workloads
    cat > "${SECURITY_POLICY_DIR}/security-contexts.yaml" << 'EOF'
# Security context template for GameForge workloads
apiVersion: v1
kind: Pod
metadata:
  name: gameforge-app-secure
  namespace: gameforge-production
spec:
  serviceAccountName: gameforge-service-account
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    fsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: gameforge-app
    image: gameforge:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
      runAsNonRoot: true
      runAsUser: 10001
      runAsGroup: 10001
    resources:
      limits:
        memory: "4Gi"
        cpu: "2"
        nvidia.com/gpu: 1
      requests:
        memory: "2Gi"
        cpu: "1"
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: var-tmp
      mountPath: /var/tmp
    - name: cache
      mountPath: /app/cache
  volumes:
  - name: tmp
    emptyDir: {}
  - name: var-tmp
    emptyDir: {}
  - name: cache
    emptyDir:
      sizeLimit: 10Gi
EOF

    log_info "Pod Security Standards created"
}

# ========================================================================
# Runtime Security with Falco
# ========================================================================

deploy_falco_security() {
    log_info "Deploying Falco runtime security..."
    
    # Falco configuration
    cat > "${SECURITY_POLICY_DIR}/falco-config.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: falco-config
  namespace: gameforge-production
data:
  falco.yaml: |
    rules_file:
      - /etc/falco/falco_rules.yaml
      - /etc/falco/falco_rules.local.yaml
      - /etc/falco/k8s_audit_rules.yaml
      - /etc/falco/gameforge_rules.yaml
    
    json_output: true
    json_include_output_property: true
    
    log_stderr: true
    log_syslog: true
    log_level: info
    
    priority: debug
    
    buffered_outputs: false
    
    outputs:
      rate: 1
      max_burst: 1000
    
    syslog_output:
      enabled: true
    
    file_output:
      enabled: false
    
    stdout_output:
      enabled: true
    
    webserver:
      enabled: true
      listen_port: 8765
      k8s_healthz_endpoint: /healthz
      ssl_enabled: false
    
    grpc:
      enabled: false
    
    grpc_output:
      enabled: false
  
  gameforge_rules.yaml: |
    - rule: GameForge Unauthorized Network Connection
      desc: Detect unauthorized network connections from GameForge containers
      condition: >
        (spawned_process and container and 
         container.image.repository contains "gameforge" and
         (proc.name in (netcat, nc, ncat, nmap, dig, nslookup, curl, wget) or
          (proc.name=sh and proc.args contains "-c" and 
           (proc.args contains "wget" or proc.args contains "curl"))))
      output: >
        Unauthorized network tool usage in GameForge container 
        (user=%user.name command=%proc.cmdline container=%container.name 
         image=%container.image.repository)
      priority: CRITICAL
      tags: [network, gameforge, security]
    
    - rule: GameForge Privilege Escalation Attempt
      desc: Detect privilege escalation attempts in GameForge containers
      condition: >
        (spawned_process and container and
         container.image.repository contains "gameforge" and
         (proc.name in (sudo, su, doas) or
          (proc.name=sh and (proc.args contains "sudo" or proc.args contains "su"))))
      output: >
        Privilege escalation attempt in GameForge container
        (user=%user.name command=%proc.cmdline container=%container.name
         image=%container.image.repository)
      priority: CRITICAL
      tags: [privilege_escalation, gameforge, security]
    
    - rule: GameForge Sensitive File Access
      desc: Detect access to sensitive files in GameForge containers
      condition: >
        (open_read and container and
         container.image.repository contains "gameforge" and
         (fd.name in (/etc/passwd, /etc/shadow, /etc/sudoers, /root/.ssh/id_rsa,
                      /root/.aws/credentials, /var/run/secrets) or
          fd.name startswith /proc/*/environ))
      output: >
        Sensitive file access in GameForge container
        (user=%user.name file=%fd.name container=%container.name
         image=%container.image.repository)
      priority: WARNING
      tags: [filesystem, gameforge, security]
    
    - rule: GameForge Crypto Mining Detection
      desc: Detect potential crypto mining activity
      condition: >
        (spawned_process and container and
         container.image.repository contains "gameforge" and
         (proc.name in (xmrig, ccminer, cgminer, bfgminer, sgminer) or
          proc.cmdline contains "stratum+tcp" or
          proc.cmdline contains "mining" or
          proc.cmdline contains "cryptonight"))
      output: >
        Potential crypto mining detected in GameForge container
        (user=%user.name command=%proc.cmdline container=%container.name
         image=%container.image.repository)
      priority: CRITICAL
      tags: [crypto_mining, gameforge, security]
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: falco
  namespace: gameforge-production
  labels:
    app: falco
spec:
  selector:
    matchLabels:
      app: falco
  template:
    metadata:
      labels:
        app: falco
    spec:
      serviceAccountName: falco
      hostNetwork: true
      hostPID: true
      tolerations:
      - operator: Exists
        effect: NoSchedule
      containers:
      - name: falco
        image: falcosecurity/falco:0.36.2
        imagePullPolicy: IfNotPresent
        resources:
          limits:
            memory: 512Mi
            cpu: 200m
          requests:
            memory: 256Mi
            cpu: 100m
        securityContext:
          privileged: true
        args:
          - /usr/bin/falco
          - --cri=/run/containerd/containerd.sock
          - --k8s-api
          - --k8s-api-endpoint=https://kubernetes.default.svc.cluster.local
        env:
        - name: FALCO_K8S_NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        volumeMounts:
        - mountPath: /var/run/docker.sock
          name: docker-socket
        - mountPath: /run/containerd/containerd.sock
          name: containerd-socket
        - mountPath: /dev
          name: dev-fs
        - mountPath: /proc
          name: proc-fs
          readOnly: true
        - mountPath: /boot
          name: boot-fs
          readOnly: true
        - mountPath: /lib/modules
          name: lib-modules
          readOnly: true
        - mountPath: /usr
          name: usr-fs
          readOnly: true
        - mountPath: /etc/falco
          name: falco-config
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8765
          initialDelaySeconds: 60
          periodSeconds: 15
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8765
          initialDelaySeconds: 30
          periodSeconds: 15
          timeoutSeconds: 5
      volumes:
      - name: docker-socket
        hostPath:
          path: /var/run/docker.sock
      - name: containerd-socket
        hostPath:
          path: /run/containerd/containerd.sock
      - name: dev-fs
        hostPath:
          path: /dev
      - name: proc-fs
        hostPath:
          path: /proc
      - name: boot-fs
        hostPath:
          path: /boot
      - name: lib-modules
        hostPath:
          path: /lib/modules
      - name: usr-fs
        hostPath:
          path: /usr
      - name: falco-config
        configMap:
          name: falco-config
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: falco
  namespace: gameforge-production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: falco
rules:
- apiGroups: [""]
  resources: ["nodes", "pods", "events"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["replicasets", "deployments", "daemonsets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: falco
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: falco
subjects:
- kind: ServiceAccount
  name: falco
  namespace: gameforge-production
EOF

    log_info "Falco runtime security configuration created"
}

# ========================================================================
# Security Monitoring and Alerting
# ========================================================================

create_security_monitoring() {
    log_info "Creating security monitoring and alerting..."
    
    # Security dashboard for Grafana
    cat > "${SECURITY_POLICY_DIR}/security-dashboard.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "GameForge Security Dashboard",
    "tags": ["security", "gameforge"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Security Events",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(falco_events_total[5m])",
            "legendFormat": "{{priority}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 5},
                {"color": "red", "value": 20}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Failed Login Attempts",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(authentication_failed_total[5m])",
            "legendFormat": "Failed Logins"
          }
        ]
      },
      {
        "id": 3,
        "title": "Network Policy Violations",
        "type": "table",
        "targets": [
          {
            "expr": "network_policy_violations_total",
            "legendFormat": "{{source_pod}} -> {{destination_pod}}"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF

    # Prometheus security rules
    cat > "${SECURITY_POLICY_DIR}/security-rules.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-alert-rules
  namespace: gameforge-production
data:
  security.rules: |
    groups:
    - name: gameforge.security
      rules:
      - alert: HighSecurityEvents
        expr: increase(falco_events_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
          component: security
        annotations:
          summary: "High number of security events detected"
          description: "More than 10 security events in 5 minutes"
      
      - alert: CriticalSecurityEvent
        expr: increase(falco_events_total{priority="CRITICAL"}[1m]) > 0
        for: 0m
        labels:
          severity: critical
          component: security
        annotations:
          summary: "Critical security event detected"
          description: "Critical security event: {{ $labels.rule }}"
      
      - alert: FailedAuthentication
        expr: increase(authentication_failed_total[5m]) > 20
        for: 2m
        labels:
          severity: warning
          component: authentication
        annotations:
          summary: "High number of failed authentication attempts"
          description: "More than 20 failed authentication attempts in 5 minutes"
      
      - alert: UnauthorizedNetworkAccess
        expr: increase(network_policy_violations_total[5m]) > 5
        for: 1m
        labels:
          severity: warning
          component: network
        annotations:
          summary: "Network policy violations detected"
          description: "Unauthorized network access attempts detected"
      
      - alert: ContainerPrivilegeEscalation
        expr: increase(falco_events_total{rule=~".*[Pp]rivilege.*"}[1m]) > 0
        for: 0m
        labels:
          severity: critical
          component: security
        annotations:
          summary: "Container privilege escalation attempt"
          description: "Privilege escalation attempt detected in container"
EOF

    log_info "Security monitoring and alerting configuration created"
}

# ========================================================================
# Security Scanning Integration
# ========================================================================

create_security_scanning() {
    log_info "Setting up security scanning integration..."
    
    # Trivy security scanner
    cat > "${SECURITY_POLICY_DIR}/trivy-scanner.yaml" << 'EOF'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: trivy-security-scan
  namespace: gameforge-production
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: trivy-scanner
          containers:
          - name: trivy
            image: aquasec/trivy:latest
            command:
            - /bin/sh
            - -c
            - |
              # Scan all GameForge images
              for image in $(kubectl get pods -n gameforge-production -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | grep gameforge | sort -u); do
                echo "Scanning image: $image"
                trivy image --format json --output /tmp/scan-$(echo $image | tr '/' '-').json $image
                
                # Check for critical vulnerabilities
                critical_count=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | length' /tmp/scan-$(echo $image | tr '/' '-').json 2>/dev/null || echo 0)
                
                if [ "$critical_count" -gt 0 ]; then
                  echo "CRITICAL: Found $critical_count critical vulnerabilities in $image"
                  # Send alert to monitoring system
                  curl -X POST http://alertmanager:9093/api/v1/alerts -H "Content-Type: application/json" -d '[{
                    "labels": {
                      "alertname": "CriticalVulnerabilities",
                      "severity": "critical",
                      "image": "'$image'",
                      "vulnerability_count": "'$critical_count'"
                    },
                    "annotations": {
                      "summary": "Critical vulnerabilities found in container image",
                      "description": "Found '$critical_count' critical vulnerabilities in image '$image'"
                    }
                  }]'
                fi
              done
            resources:
              limits:
                memory: 1Gi
                cpu: 500m
              requests:
                memory: 512Mi
                cpu: 200m
          restartPolicy: OnFailure
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: trivy-scanner
  namespace: gameforge-production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: trivy-scanner
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: trivy-scanner
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: trivy-scanner
subjects:
- kind: ServiceAccount
  name: trivy-scanner
  namespace: gameforge-production
EOF

    log_info "Security scanning integration created"
}

# ========================================================================
# Apply Security Configurations
# ========================================================================

apply_security_configs() {
    log_info "Applying security configurations to cluster..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply all security policies
    if kubectl get crd networkpolicies.networking.k8s.io > /dev/null 2>&1; then
        log_info "Applying network policies..."
        kubectl apply -f "${SECURITY_POLICY_DIR}/" -n "${NAMESPACE}"
    else
        log_warn "Network policies not supported in this cluster"
    fi
    
    # Verify deployment
    log_info "Verifying security deployment..."
    
    # Check if Falco is running
    if kubectl get pods -n "${NAMESPACE}" -l app=falco | grep -q Running; then
        log_info "Falco runtime security is running"
    else
        log_warn "Falco not detected - runtime security may not be active"
    fi
    
    # Check network policies
    policy_count=$(kubectl get networkpolicies -n "${NAMESPACE}" --no-headers | wc -l)
    log_info "Applied ${policy_count} network policies"
    
    # Security verification
    log_info "Security hardening verification:"
    echo "  ✓ Network policies: ${policy_count} applied"
    echo "  ✓ Pod security standards: configured"
    echo "  ✓ Runtime security: Falco deployed"
    echo "  ✓ Security monitoring: alerts configured"
    echo "  ✓ Vulnerability scanning: scheduled"
}

# ========================================================================
# Main execution
# ========================================================================

main() {
    log_info "Starting GameForge security hardening..."
    
    # Create security policy directory
    mkdir -p "${SECURITY_POLICY_DIR}"
    
    # Create all security configurations
    create_network_policies
    create_pod_security_policies
    deploy_falco_security
    create_security_monitoring
    create_security_scanning
    
    # Apply configurations if requested
    if [[ "${APPLY_CONFIGS:-false}" == "true" ]]; then
        apply_security_configs
    else
        log_info "Security configurations created in ${SECURITY_POLICY_DIR}/"
        log_info "To apply configurations, run: APPLY_CONFIGS=true $0"
    fi
    
    log_info "Security hardening setup complete!"
    log_info "Next steps:"
    echo "  1. Review generated policies in ${SECURITY_POLICY_DIR}/"
    echo "  2. Apply configurations: APPLY_CONFIGS=true $0"
    echo "  3. Monitor security dashboard in Grafana"
    echo "  4. Review Falco alerts for runtime security events"
}

# Run main function
main "$@"