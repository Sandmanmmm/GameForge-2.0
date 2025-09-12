# Resource Security Policy - OPA  
# Enforces resource management and compliance

package resource.security

import rego.v1

# Require resource quotas in non-system namespaces
deny_missing_resource_quota contains msg if {
	input.kind == "Namespace"
	not is_system_namespace(input.metadata.name)
	not has_resource_quota_label(input)
	msg := sprintf("Namespace '%s' must have resource quota enforcement", [input.metadata.name])
}

is_system_namespace(name) if {
	system_namespaces := {"kube-system", "kube-public", "kube-node-lease", "default"}
	name in system_namespaces
}

has_resource_quota_label(namespace) if {
	namespace.metadata.labels["resource-quota"] == "enabled"
}

# Enforce Pod Security Standards
deny_non_restricted_pod_security contains msg if {
	input.kind == "Namespace"
	not is_system_namespace(input.metadata.name)
	input.metadata.labels["pod-security.kubernetes.io/enforce"] != "restricted"
	msg := sprintf("Namespace '%s' must enforce 'restricted' pod security standard", [input.metadata.name])
}

# Require security context for all workloads
deny_missing_security_context contains msg if {
	input.kind in {"Deployment", "StatefulSet", "DaemonSet"}
	not input.spec.template.spec.securityContext
	msg := sprintf("%s '%s' must specify pod security context", [input.kind, input.metadata.name])
}

# Enforce image pull policy
deny_incorrect_pull_policy contains msg if {
	input.kind in {"Deployment", "StatefulSet", "DaemonSet", "Pod"}
	some container in get_containers(input)
	container.imagePullPolicy != "Always"
	ends_with(container.image, ":latest")
	msg := sprintf("Container '%s' with :latest tag must use imagePullPolicy: Always", [container.name])
}

get_containers(resource) := resource.spec.containers if {
	input.kind == "Pod"
}

get_containers(resource) := resource.spec.template.spec.containers if {
	input.kind in {"Deployment", "StatefulSet", "DaemonSet"}
}

# Require labels for resource management
required_labels := ["app", "version", "environment"]

deny_missing_required_labels contains msg if {
	input.kind in {"Deployment", "StatefulSet", "DaemonSet", "Service"}
	some label in required_labels
	not input.metadata.labels[label]
	msg := sprintf("%s '%s' must have label '%s'", [input.kind, input.metadata.name, label])
}

# Enforce naming conventions
deny_invalid_naming contains msg if {
	input.kind in {"Deployment", "StatefulSet", "DaemonSet", "Service"}
	not regex.match("^[a-z][a-z0-9-]*[a-z0-9]$", input.metadata.name)
	msg := sprintf("%s name '%s' must follow kebab-case naming convention", [input.kind, input.metadata.name])
}