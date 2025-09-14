# Docker and Container Policies for GameForge
# Validates Docker Compose and container configurations

package gameforge.docker

# Base Image Security
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    image := service.image
    endswith(image, ":latest")
    msg := sprintf("Service '%s' cannot use 'latest' tag", [service_name])
}

deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    service.privileged == true
    msg := sprintf("Service '%s' cannot run in privileged mode", [service_name])
}

# Resource Limits
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    not service.deploy.resources.limits.memory
    msg := sprintf("Service '%s' must specify memory limits", [service_name])
}

deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    not service.deploy.resources.limits.cpus
    msg := sprintf("Service '%s' must specify CPU limits", [service_name])
}

# Health Checks
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    not service.healthcheck
    startswith(service_name, "gameforge-")
    msg := sprintf("GameForge service '%s' must define health check", [service_name])
}

# Security Context
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    service.user == "root"
    msg := sprintf("Service '%s' should not run as root user", [service_name])
}

deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    not service.read_only
    startswith(service_name, "gameforge-")
    msg := sprintf("GameForge service '%s' should use read-only filesystem", [service_name])
}

# Network Security
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    port := service.ports[_]
    # Check if port is exposed to all interfaces
    contains(port, "0.0.0.0:")
    not service_name in ["nginx", "traefik", "ingress"]
    msg := sprintf("Service '%s' should not expose ports to all interfaces", [service_name])
}

# Secrets Management
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    env_var := service.environment[_]
    contains(lower(env_var), "password")
    not contains(env_var, "_FILE")
    not contains(env_var, "${")
    msg := sprintf("Service '%s' should not have plaintext passwords in environment", [service_name])
}

deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    env_var := service.environment[_]
    contains(lower(env_var), "secret")
    not contains(env_var, "_FILE")
    not contains(env_var, "${")
    msg := sprintf("Service '%s' should not have plaintext secrets in environment", [service_name])
}

# Volume Security
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    volume := service.volumes[_]
    contains(volume, "/var/run/docker.sock")
    not service_name in ["docker-registry", "ci-runner"]
    msg := sprintf("Service '%s' should not mount Docker socket unless necessary", [service_name])
}

# GameForge Production Requirements
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    startswith(service_name, "gameforge-")
    not service.restart
    msg := sprintf("GameForge service '%s' must specify restart policy", [service_name])
}

deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    startswith(service_name, "gameforge-")
    not service.logging
    msg := sprintf("GameForge service '%s' must specify logging configuration", [service_name])
}

# Container Registry Validation
deny[msg] {
    input.services[service_name]
    service := input.services[service_name]
    image := service.image
    startswith(service_name, "gameforge-")
    not startswith(image, "registry.gameforge.local/")
    not startswith(image, "ghcr.io/gameforge/")
    msg := sprintf("GameForge service '%s' must use approved container registry", [service_name])
}
