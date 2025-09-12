package gameforge.security

import future.keywords.if
import future.keywords.in

# Default deny policy
default allow := false

# Allow deployment if security conditions are met
allow if {
    input.type == "deployment"
    security_requirements_met
}

# Security requirements validation
security_requirements_met if {
    vulnerability_check
    image_policy_check
    resource_limits_check
    security_context_check
}

# Vulnerability policy
vulnerability_check if {
    input.vulnerabilities.critical == 0
    input.vulnerabilities.high <= 5
}

# Image policy checks
image_policy_check if {
    # Require specific image registries
    allowed_registries := [
        "ghcr.io/gameforge",
        "harbor.gameforge.com",
        "gcr.io/gameforge-prod"
    ]

    some registry in allowed_registries
    startswith(input.image, registry)

    # Require image signing
    input.image_signed == true

    # Prohibit latest tag in production
    not endswith(input.image, ":latest")
}

# Resource limits enforcement
resource_limits_check if {
    input.resources.limits.memory != null
    input.resources.limits.cpu != null
    input.resources.requests.memory != null
    input.resources.requests.cpu != null
}

# Security context requirements
security_context_check if {
    # Require non-root user
    input.securityContext.runAsNonRoot == true
    input.securityContext.runAsUser > 0

    # Require read-only root filesystem
    input.securityContext.readOnlyRootFilesystem == true

    # Drop all capabilities
    input.securityContext.capabilities.drop[_] == "ALL"

    # Prohibit privileged containers
    input.securityContext.privileged != true

    # Prohibit privilege escalation
    input.securityContext.allowPrivilegeEscalation == false
}

# Network policy validation
network_policy_check if {
    # Require network policies for pod communication
    input.networkPolicy.enabled == true

    # Restrict egress traffic
    allowed_egress_ports := [80, 443, 5432, 6379]
    input.networkPolicy.egress.ports[_] in allowed_egress_ports
}
