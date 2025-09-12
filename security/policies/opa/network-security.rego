# Network Security Policy - OPA
# Enforces secure network configurations

package network.security

import rego.v1

# Deny services with NodePort (security risk)
deny_nodeport contains msg if {
	input.kind == "Service"
	input.spec.type == "NodePort"
	msg := "NodePort services are not allowed for security reasons. Use LoadBalancer or ClusterIP instead."
}

# Require TLS for LoadBalancer services
deny_insecure_loadbalancer contains msg if {
	input.kind == "Service"
	input.spec.type == "LoadBalancer"
	not has_tls_annotation(input)
	msg := "LoadBalancer services must specify TLS configuration via annotations"
}

has_tls_annotation(service) if {
	service.metadata.annotations["service.beta.kubernetes.io/azure-load-balancer-backend-protocol"] == "https"
}

has_tls_annotation(service) if {
	service.metadata.annotations["kubernetes.io/tls-acme"] == "true"
}

# Require NetworkPolicy for namespace isolation
deny_missing_network_policy contains msg if {
	input.kind == "Namespace"
	input.metadata.name != "kube-system"
	input.metadata.name != "kube-public" 
	not has_network_policy_label(input)
	msg := sprintf("Namespace '%s' must have network policy enforcement", [input.metadata.name])
}

has_network_policy_label(namespace) if {
	namespace.metadata.labels["network-policy"] == "enabled"
}

# Deny ingress without TLS
deny_insecure_ingress contains msg if {
	input.kind == "Ingress"
	not input.spec.tls
	msg := "Ingress must specify TLS configuration for HTTPS"
}

# Require specific ingress classes (security-vetted)
deny_unvetted_ingress_class contains msg if {
	input.kind == "Ingress"
	allowed_classes := {"nginx", "traefik", "istio"}
	ingress_class := input.spec.ingressClassName
	not ingress_class in allowed_classes
	msg := sprintf("Ingress class '%s' is not allowed. Use: %v", [ingress_class, allowed_classes])
}