# Compliance and Governance Policies for GameForge
# Ensures adherence to operational standards and regulatory requirements

package gameforge.compliance

# Resource Governance
deny[msg] {
    input.kind == "Deployment"
    input.spec.replicas > 10
    not input.metadata.annotations["gameforge.io/high-replica-approved"]
    msg := "Deployments with >10 replicas require approval annotation"
}

deny[msg] {
    input.kind == "PersistentVolumeClaim"
    storage_size := input.spec.resources.requests.storage
    storage_gb := to_number(trim_suffix(storage_size, "Gi"))
    storage_gb > 100
    not input.metadata.annotations["gameforge.io/large-storage-approved"]
    msg := "PVC >100Gi requires approval annotation"
}

# Naming Conventions
deny[msg] {
    input.kind == "Deployment"
    name := input.metadata.name
    not regex.match("^[a-z][a-z0-9-]*[a-z0-9]$", name)
    msg := "Deployment names must follow kebab-case convention"
}

deny[msg] {
    input.kind == "Service"
    name := input.metadata.name
    not regex.match("^[a-z][a-z0-9-]*[a-z0-9]$", name)
    msg := "Service names must follow kebab-case convention"
}

# Required Labels
required_labels := [
    "app",
    "version", 
    "environment",
    "component",
    "managed-by"
]

deny[msg] {
    input.kind in ["Deployment", "Service", "Ingress"]
    missing := required_labels[_]
    not input.metadata.labels[missing]
    msg := sprintf("Missing required label: %s", [missing])
}

# Environment-specific policies
deny[msg] {
    input.kind == "Deployment"
    input.metadata.labels.environment == "production"
    input.spec.replicas < 2
    msg := "Production deployments must have at least 2 replicas"
}

deny[msg] {
    input.kind == "Deployment" 
    input.metadata.labels.environment == "production"
    container := input.spec.template.spec.containers[_]
    container.resources.limits.memory
    memory_str := container.resources.limits.memory
    memory_mb := to_number(trim_suffix(memory_str, "Mi"))
    memory_mb < 256
    msg := "Production containers must have at least 256Mi memory limit"
}

# Data Protection
deny[msg] {
    input.kind == "Secret"
    input.metadata.labels.environment == "production"
    not input.metadata.annotations["gameforge.io/encrypted"]
    msg := "Production secrets must be encrypted at rest"
}

deny[msg] {
    input.kind == "PersistentVolumeClaim"
    input.metadata.labels.contains-pii == "true"
    not input.spec.storageClassName == "encrypted-ssd"
    msg := "PVC containing PII must use encrypted storage class"
}

# Monitoring and Observability Requirements
deny[msg] {
    input.kind == "Deployment"
    input.metadata.labels.environment in ["staging", "production"]
    not input.metadata.annotations["prometheus.io/scrape"]
    msg := "Staging and production deployments must enable Prometheus scraping"
}

deny[msg] {
    input.kind == "Deployment"
    input.metadata.labels.component == "api"
    container := input.spec.template.spec.containers[_]
    not has_tracing_env(container.env)
    msg := "API components must have distributed tracing enabled"
}

has_tracing_env(env_vars) {
    env_var := env_vars[_]
    env_var.name == "OTEL_EXPORTER_OTLP_ENDPOINT"
}

# GameForge ML/AI Specific Policies
deny[msg] {
    input.kind == "Deployment"
    input.metadata.labels.component == "gpu-inference"
    not input.spec.template.spec.nodeSelector["gameforge.io/gpu-type"]
    msg := "GPU inference workloads must specify GPU type node selector"
}

deny[msg] {
    input.kind == "Deployment"
    input.metadata.labels.component in ["ml-training", "gpu-inference"]
    container := input.spec.template.spec.containers[_]
    not container.resources.limits["nvidia.com/gpu"]
    msg := "ML workloads must specify GPU resource limits"
}

# Cost Optimization
warn[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    cpu_limit := container.resources.limits.cpu
    cpu_request := container.resources.requests.cpu
    cpu_limit_num := to_number(trim_suffix(cpu_limit, "m"))
    cpu_request_num := to_number(trim_suffix(cpu_request, "m"))
    ratio := cpu_limit_num / cpu_request_num
    ratio > 4
    msg := sprintf("Container %s has high CPU limit/request ratio (%.1f), consider optimization", [container.name, ratio])
}
