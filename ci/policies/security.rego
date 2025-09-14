# Security Policies for GameForge Infrastructure
# These policies enforce security best practices across all infrastructure components

package gameforge.security

# Container Security Policies
deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.securityContext.runAsNonRoot == true
    msg := sprintf("Container %s must run as non-root user", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("Container %s cannot run in privileged mode", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.securityContext.readOnlyRootFilesystem == true
    msg := sprintf("Container %s must have read-only root filesystem", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.securityContext.allowPrivilegeEscalation == false
    msg := sprintf("Container %s must not allow privilege escalation", [container.name])
}

# Image Security
deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    endswith(container.image, ":latest")
    msg := sprintf("Container %s cannot use 'latest' tag", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not contains(container.image, ":")
    msg := sprintf("Container %s must specify image tag", [container.name])
}

# Network Security
deny[msg] {
    input.kind == "Service"
    input.spec.type == "LoadBalancer"
    not input.spec.loadBalancerSourceRanges
    msg := "LoadBalancer services must specify source IP ranges"
}

deny[msg] {
    input.kind == "Ingress"
    not input.spec.tls
    msg := "Ingress must enable TLS/HTTPS"
}

# Resource Limits
deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %s must specify memory limits", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.resources.limits.cpu
    msg := sprintf("Container %s must specify CPU limits", [container.name])
}

# Health Checks
deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.livenessProbe
    msg := sprintf("Container %s must define liveness probe", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not container.readinessProbe
    msg := sprintf("Container %s must define readiness probe", [container.name])
}

# GameForge-specific policies
deny[msg] {
    input.kind == "Deployment"
    input.metadata.namespace != "gameforge"
    input.metadata.labels.app
    startswith(input.metadata.labels.app, "gameforge")
    msg := "GameForge applications must be deployed in 'gameforge' namespace"
}

deny[msg] {
    input.kind == "Deployment"
    not input.metadata.labels.version
    msg := "Deployment must have version label for blue/green deployments"
}

deny[msg] {
    input.kind == "Deployment"
    not input.metadata.labels.environment
    msg := "Deployment must have environment label"
}
