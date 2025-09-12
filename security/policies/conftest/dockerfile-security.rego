# Dockerfile Security Policy - Conftest
# Validates Dockerfile security best practices

package dockerfile.security

import rego.v1

# Deny running as root user
deny contains msg if {
	input[i].Cmd == "user"
	val := input[i].Value
	is_array(val)
	val[0] == "root"
	msg := "Dockerfile must not specify USER root"
}

deny contains msg if {
	input[i].Cmd == "user" 
	val := input[i].Value
	is_string(val)
	val == "root"
	msg := "Dockerfile must not specify USER root"
}

# Require USER instruction
warn contains msg if {
	not has_user_instruction
	msg := "Dockerfile should specify a non-root USER"
}

has_user_instruction if {
	some i
	input[i].Cmd == "user"
}

# Deny ADD instruction (prefer COPY)
deny contains msg if {
	input[i].Cmd == "add"
	msg := "Use COPY instead of ADD for better security and predictability"
}

# Require specific base images (hardened only)
deny contains msg if {
	input[i].Cmd == "from"
	val := input[i].Value
	image := val[0]
	not is_hardened_base_image(image)
	msg := sprintf("Base image '%s' is not hardened. Use Alpine, Distroless, or scratch images", [image])
}

is_hardened_base_image(image) if {
	hardened_patterns := [
		"alpine",
		"distroless", 
		"scratch",
		"gcr.io/distroless/",
	]
	some pattern in hardened_patterns
	contains(image, pattern)
}

# Require HEALTHCHECK for production images
warn contains msg if {
	not has_healthcheck
	msg := "Production Dockerfile should include HEALTHCHECK instruction"
}

has_healthcheck if {
	some i
	input[i].Cmd == "healthcheck"
}

# Deny running package managers without cleanup
deny contains msg if {
	input[i].Cmd == "run"
	val := input[i].Value[0]
	contains(val, "apt-get install")
	not contains(val, "rm -rf /var/lib/apt/lists/*")
	msg := "apt-get install must include cleanup: rm -rf /var/lib/apt/lists/*"
}

deny contains msg if {
	input[i].Cmd == "run"
	val := input[i].Value[0]
	contains(val, "apk add")
	not contains(val, "--no-cache")
	not contains(val, "rm -rf /var/cache/apk/*")
	msg := "apk add should use --no-cache or include cleanup"
}

# Require explicit versions for base images (no :latest)
warn contains msg if {
	input[i].Cmd == "from"
	val := input[i].Value
	image := val[0]
	ends_with(image, ":latest")
	msg := sprintf("Base image '%s' should specify explicit version instead of :latest", [image])
}

# Deny unnecessary packages
deny contains msg if {
	input[i].Cmd == "run"
	val := input[i].Value[0]
	dangerous_packages := ["sudo", "ssh", "telnet", "ftp"]
	some pkg in dangerous_packages
	contains(val, pkg)
	msg := sprintf("Package '%s' should not be installed for security reasons", [pkg])
}