# Kubernetes Security Policy - Conftest
# Validates Kubernetes manifest security

package kubernetes.security

import rego.v1

# Deny pods without security context
deny contains msg if {
	input.kind == "Pod"
	not input.spec.securityContext
	msg := "Pod must specify securityContext"
}

deny contains msg if {
	input.kind in ["Deployment", "StatefulSet", "DaemonSet"]
	not input.spec.template.spec.securityContext
	msg := sprintf("%s must specify pod securityContext", [input.kind])
}

# Require specific security context fields
deny contains msg if {
	input.kind == "Pod"
	not input.spec.securityContext.runAsNonRoot
	msg := "Pod securityContext must set runAsNonRoot: true"
}

deny contains msg if {
	input.kind in ["Deployment", "StatefulSet", "DaemonSet"] 
	not input.spec.template.spec.securityContext.runAsNonRoot
	msg := sprintf("%s pod securityContext must set runAsNonRoot: true", [input.kind])
}

# Require container security context
deny contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	not container.securityContext
	msg := sprintf("Container '%s' must specify securityContext", [container.name])
}

deny contains msg if {
	input.kind in ["Deployment", "StatefulSet", "DaemonSet"]
	some container in input.spec.template.spec.containers
	not container.securityContext
	msg := sprintf("Container '%s' must specify securityContext", [container.name])
}

# Require resource limits
deny contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	not container.resources.limits
	msg := sprintf("Container '%s' must specify resource limits", [container.name])
}

deny contains msg if {
	input.kind in ["Deployment", "StatefulSet", "DaemonSet"]
	some container in input.spec.template.spec.containers
	not container.resources.limits
	msg := sprintf("Container '%s' must specify resource limits", [container.name])
}

# Require image pull secrets for private registries
warn contains msg if {
	input.kind == "Pod"
	some container in input.spec.containers
	startswith(container.image, "gameforge.azurecr.io")
	not input.spec.imagePullSecrets
	msg := "Pod with private registry images should specify imagePullSecrets"
}

# Require readiness probes for services
warn contains msg if {
	input.kind in ["Deployment", "StatefulSet"]
	input.metadata.labels.type == "service"
	some container in input.spec.template.spec.containers
	not container.readinessProbe
	msg := sprintf("Service container '%s' should have readinessProbe", [container.name])
}

# Deny hostNetwork for non-system pods
deny contains msg if {
	input.kind == "Pod"
	input.spec.hostNetwork == true
	not input.metadata.namespace in ["kube-system", "kube-public"]
	msg := "hostNetwork should only be used in system namespaces"
}

# Deny hostPID and hostIPC
deny contains msg if {
	input.kind == "Pod"
	input.spec.hostPID == true
	msg := "hostPID is not allowed for security reasons"
}

deny contains msg if {
	input.kind == "Pod"
	input.spec.hostIPC == true
	msg := "hostIPC is not allowed for security reasons"
}

# Require specific service account (not default)
warn contains msg if {
	input.kind in ["Deployment", "StatefulSet", "DaemonSet", "Pod"]
	service_account := get_service_account(input)
	service_account == "default"
	msg := "Consider using a specific service account instead of 'default'"
}

get_service_account(resource) := resource.spec.serviceAccountName if {
	input.kind == "Pod"
}

get_service_account(resource) := resource.spec.template.spec.serviceAccountName if {
	input.kind in ["Deployment", "StatefulSet", "DaemonSet"]
}

get_service_account(resource) := "default" if {
	not resource.spec.serviceAccountName
	input.kind == "Pod"
}

get_service_account(resource) := "default" if {
	not resource.spec.template.spec.serviceAccountName
	input.kind in ["Deployment", "StatefulSet", "DaemonSet"]
}