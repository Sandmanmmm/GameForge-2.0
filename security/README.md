# GameForge Security Configuration

This directory contains security hardening configurations and policies:

## Components

- **seccomp/** - JSON seccomp profiles for container isolation
- **policies/** - OPA/Conftest security policies and admission controllers
- **scripts/** - Security automation and hardening scripts
- **vault/** - HashiCorp Vault policies and configuration templates

## Security Files

- `security_checklist.json` - Security compliance checklist
- `security_config.json` - Security configuration parameters

## Usage

Security configurations are applied during:
- Container deployment (seccomp profiles)
- Kubernetes admission control (OPA policies) 
- Infrastructure hardening (scripts)
- Secret management (Vault policies)