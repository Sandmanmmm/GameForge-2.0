# Container Security Policy - OPA
# Enforces hardened container configurations

package container.security

import rego.v1

# Deny containers running as root
deny_root_user contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	container.securityContext.runAsUser == 0
	msg := sprintf("Container '%s' must not run as root (runAsUser: 0)", [container.name])
}

deny_root_user contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	not has_key(container, "securityContext")
	msg := sprintf("Container '%s' must specify securityContext with runAsUser", [container.name])
}

# Require read-only root filesystem
deny_writable_root contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	container.securityContext.readOnlyRootFilesystem != true
	msg := sprintf("Container '%s' must have read-only root filesystem", [container.name])
}

# Deny privileged containers
deny_privileged contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	container.securityContext.privileged == true
	msg := sprintf("Container '%s' must not be privileged", [container.name])
}

# Require security capabilities to be dropped
deny_dangerous_capabilities contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	dangerous_caps := {"SYS_ADMIN", "NET_ADMIN", "SYS_TIME", "SYS_MODULE"}
	some cap in container.securityContext.capabilities.add
	cap in dangerous_caps
	msg := sprintf("Container '%s' must not add dangerous capability '%s'", [container.name, cap])
}

# Require allowPrivilegeEscalation to be false
deny_privilege_escalation contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	container.securityContext.allowPrivilegeEscalation != false
	msg := sprintf("Container '%s' must set allowPrivilegeEscalation: false", [container.name])
}

# Enforce hardened base images (Alpine/Distroless only)
deny_non_hardened_images contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	not is_hardened_image(container.image)
	msg := sprintf("Container '%s' must use hardened base image (Alpine/Distroless), got: %s", [container.name, container.image])
}

# Helper function to check if image is hardened
is_hardened_image(image) if {
	hardened_patterns := [
		"alpine",
		"distroless",
		"scratch",
		":.*-alpine.*",
		"gcr.io/distroless/",
	]
	some pattern in hardened_patterns
	regex.match(pattern, image)
}

# Require resource limits
deny_missing_resources contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	not has_resource_limits(container)
	msg := sprintf("Container '%s' must specify resource limits (CPU and memory)", [container.name])
}

has_resource_limits(container) if {
	container.resources.limits.cpu
	container.resources.limits.memory
}

# Require liveness and readiness probes for production
deny_missing_probes contains msg if {
	input.kind == "Pod"
	input.metadata.labels.environment == "production"
	some container in input.spec.containers
	not has_probes(container)
	msg := sprintf("Production container '%s' must have liveness and readiness probes", [container.name])
}

has_probes(container) if {
	container.livenessProbe
	container.readinessProbe
}

# Utility function
has_key(obj, key) if obj[key]