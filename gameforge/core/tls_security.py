"""
TLS/HTTPS security configuration and certificate management for GameForge.
Implements encryption in transit with mTLS support.
"""
import os
import ssl
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import aiofiles
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from gameforge.core.config import get_settings
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)


class TLSMode(Enum):
    """TLS configuration modes."""
    NONE = "none"                    # No TLS (development only)
    TLS = "tls"                     # Standard TLS
    MTLS = "mtls"                   # Mutual TLS
    STRICT_MTLS = "strict_mtls"     # Strict mutual TLS with client cert validation


class CertificateType(Enum):
    """Certificate types."""
    SERVER = "server"               # Server certificates
    CLIENT = "client"               # Client certificates
    CA = "ca"                       # Certificate Authority
    INTERMEDIATE = "intermediate"    # Intermediate CA


@dataclass
class TLSConfig:
    """TLS configuration for a service."""
    service_name: str
    mode: TLSMode
    cert_path: str
    key_path: str
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    verify_client: bool = False
    verify_hostname: bool = True
    min_tls_version: str = "TLSv1.2"
    max_tls_version: str = "TLSv1.3"
    cipher_suites: Optional[List[str]] = None
    certificate_transparency: bool = True


@dataclass
class CertificateInfo:
    """Certificate information."""
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    san_domains: List[str]
    key_size: int
    signature_algorithm: str
    is_ca: bool
    is_self_signed: bool


class TLSSecurityManager:
    """Comprehensive TLS/HTTPS security manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self.cert_dir = Path(os.getenv("TLS_CERT_DIR", "/app/certs"))
        self.ca_dir = Path(os.getenv("TLS_CA_DIR", "/app/certs/ca"))
        
        # Create certificate directories
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.ca_dir.mkdir(parents=True, exist_ok=True)
        
        # Load TLS configurations
        self.tls_configs = self._load_tls_configs()
        
        # Initialize certificate authority if needed
        self._init_ca()
    
    def _load_tls_configs(self) -> Dict[str, TLSConfig]:
        """Load TLS configurations for all services."""
        environment = os.getenv("GAMEFORGE_ENV", "development")
        
        configs = {
            "nginx": TLSConfig(
                service_name="nginx",
                mode=TLSMode.TLS if environment == "production" else TLSMode.NONE,
                cert_path=str(self.cert_dir / "nginx" / "server.crt"),
                key_path=str(self.cert_dir / "nginx" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                verify_hostname=True,
                min_tls_version="TLSv1.2",
                cipher_suites=[
                    "ECDHE-ECDSA-AES256-GCM-SHA384",
                    "ECDHE-RSA-AES256-GCM-SHA384",
                    "ECDHE-ECDSA-CHACHA20-POLY1305",
                    "ECDHE-RSA-CHACHA20-POLY1305",
                    "ECDHE-ECDSA-AES128-GCM-SHA256",
                    "ECDHE-RSA-AES128-GCM-SHA256",
                ]
            ),
            "gameforge-app": TLSConfig(
                service_name="gameforge-app",
                mode=TLSMode.MTLS if environment == "production" else TLSMode.TLS,
                cert_path=str(self.cert_dir / "app" / "server.crt"),
                key_path=str(self.cert_dir / "app" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                client_cert_path=str(self.cert_dir / "app" / "client.crt"),
                client_key_path=str(self.cert_dir / "app" / "client.key"),
                verify_client=environment == "production",
                verify_hostname=True
            ),
            "postgres": TLSConfig(
                service_name="postgres",
                mode=TLSMode.TLS,
                cert_path=str(self.cert_dir / "postgres" / "server.crt"),
                key_path=str(self.cert_dir / "postgres" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                verify_hostname=False  # Database connections often use IP
            ),
            "redis": TLSConfig(
                service_name="redis",
                mode=TLSMode.TLS if environment == "production" else TLSMode.NONE,
                cert_path=str(self.cert_dir / "redis" / "server.crt"),
                key_path=str(self.cert_dir / "redis" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                verify_hostname=False
            ),
            "vault": TLSConfig(
                service_name="vault",
                mode=TLSMode.STRICT_MTLS,
                cert_path=str(self.cert_dir / "vault" / "server.crt"),
                key_path=str(self.cert_dir / "vault" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                client_cert_path=str(self.cert_dir / "vault" / "client.crt"),
                client_key_path=str(self.cert_dir / "vault" / "client.key"),
                verify_client=True,
                verify_hostname=True,
                min_tls_version="TLSv1.3"  # Strict TLS for Vault
            ),
            "minio": TLSConfig(
                service_name="minio",
                mode=TLSMode.TLS,
                cert_path=str(self.cert_dir / "minio" / "server.crt"),
                key_path=str(self.cert_dir / "minio" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                verify_hostname=True
            ),
            "monitoring": TLSConfig(
                service_name="monitoring",
                mode=TLSMode.TLS,
                cert_path=str(self.cert_dir / "monitoring" / "server.crt"),
                key_path=str(self.cert_dir / "monitoring" / "server.key"),
                ca_cert_path=str(self.ca_dir / "ca.crt"),
                verify_hostname=True
            )
        }
        
        return configs
    
    def _init_ca(self):
        """Initialize Certificate Authority if it doesn't exist."""
        ca_cert_path = self.ca_dir / "ca.crt"
        ca_key_path = self.ca_dir / "ca.key"
        
        if not ca_cert_path.exists() or not ca_key_path.exists():
            logger.info("Creating new Certificate Authority")
            self._create_ca()
        else:
            logger.info("Using existing Certificate Authority")
    
    def _create_ca(self):
        """Create a new Certificate Authority."""
        try:
            # Generate CA private key
            ca_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            
            # Create CA certificate
            ca_name = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GameForge AI"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security"),
                x509.NameAttribute(NameOID.COMMON_NAME, "GameForge Root CA"),
            ])
            
            ca_cert = x509.CertificateBuilder().subject_name(
                ca_name
            ).issuer_name(
                ca_name  # Self-signed
            ).public_key(
                ca_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=3650)  # 10 years for CA
            ).add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    content_commitment=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True,
            ).add_extension(
                x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
                critical=False,
            ).sign(ca_key, hashes.SHA256(), default_backend())
            
            # Save CA certificate and key
            ca_cert_path = self.ca_dir / "ca.crt"
            ca_key_path = self.ca_dir / "ca.key"
            
            with open(ca_cert_path, "wb") as f:
                f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
            
            with open(ca_key_path, "wb") as f:
                f.write(ca_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Secure the private key
            os.chmod(ca_key_path, 0o600)
            
            logger.info(f"Created CA certificate: {ca_cert_path}")
            
        except Exception as e:
            logger.error(f"Failed to create CA: {e}")
            raise
    
    async def generate_service_certificates(self):
        """Generate certificates for all services."""
        for service_name, config in self.tls_configs.items():
            if config.mode == TLSMode.NONE:
                logger.info(f"Skipping certificate generation for {service_name} (TLS disabled)")
                continue
            
            try:
                await self._generate_service_certificate(service_name, config)
                
                if config.mode in [TLSMode.MTLS, TLSMode.STRICT_MTLS]:
                    await self._generate_client_certificate(service_name, config)
                
                logger.info(f"Generated certificates for {service_name}")
                
            except Exception as e:
                logger.error(f"Failed to generate certificates for {service_name}: {e}")
    
    async def _generate_service_certificate(self, service_name: str, config: TLSConfig):
        """Generate server certificate for a service."""
        cert_dir = Path(config.cert_path).parent
        cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if certificate already exists and is valid
        if await self._is_certificate_valid(config.cert_path):
            logger.info(f"Valid certificate already exists for {service_name}")
            return
        
        # Load CA
        ca_cert, ca_key = self._load_ca()
        
        # Generate service private key
        service_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Define subject alternative names
        san_list = [
            x509.DNSName(service_name),
            x509.DNSName(f"{service_name}.gameforge.local"),
            x509.DNSName(f"{service_name}.{os.getenv('DOMAIN', 'localhost')}"),
            x509.DNSName("localhost"),
            x509.IPAddress("127.0.0.1"),
        ]
        
        # Add production domains if configured
        if os.getenv("PRODUCTION_DOMAIN"):
            san_list.extend([
                x509.DNSName(os.getenv("PRODUCTION_DOMAIN")),
                x509.DNSName(f"{service_name}.{os.getenv('PRODUCTION_DOMAIN')}")
            ])
        
        # Create certificate
        service_name_attr = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GameForge AI"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Services"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.gameforge.local"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            service_name_attr
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            service_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1 year for service certs
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(ca_key, hashes.SHA256(), default_backend())
        
        # Save certificate and key
        with open(config.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(config.key_path, "wb") as f:
            f.write(service_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Secure the private key
        os.chmod(config.key_path, 0o600)
        
        logger.info(f"Generated server certificate for {service_name}")
    
    async def _generate_client_certificate(self, service_name: str, config: TLSConfig):
        """Generate client certificate for mutual TLS."""
        if not config.client_cert_path or not config.client_key_path:
            return
        
        client_cert_dir = Path(config.client_cert_path).parent
        client_cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if client certificate already exists and is valid
        if await self._is_certificate_valid(config.client_cert_path):
            logger.info(f"Valid client certificate already exists for {service_name}")
            return
        
        # Load CA
        ca_cert, ca_key = self._load_ca()
        
        # Generate client private key
        client_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create client certificate
        client_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GameForge AI"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Clients"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}-client"),
        ])
        
        client_cert = x509.CertificateBuilder().subject_name(
            client_name
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            client_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1 year for client certs
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(ca_key, hashes.SHA256(), default_backend())
        
        # Save client certificate and key
        with open(config.client_cert_path, "wb") as f:
            f.write(client_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(config.client_key_path, "wb") as f:
            f.write(client_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Secure the private key
        os.chmod(config.client_key_path, 0o600)
        
        logger.info(f"Generated client certificate for {service_name}")
    
    def _load_ca(self) -> tuple:
        """Load CA certificate and private key."""
        ca_cert_path = self.ca_dir / "ca.crt"
        ca_key_path = self.ca_dir / "ca.key"
        
        with open(ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        
        with open(ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        return ca_cert, ca_key
    
    async def _is_certificate_valid(self, cert_path: str) -> bool:
        """Check if a certificate exists and is valid."""
        cert_file = Path(cert_path)
        
        if not cert_file.exists():
            return False
        
        try:
            with open(cert_file, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            
            # Check if certificate is still valid (not expired and not expiring soon)
            now = datetime.utcnow()
            expires_soon = now + timedelta(days=30)  # Renew 30 days before expiry
            
            if cert.not_valid_after <= expires_soon:
                logger.warning(f"Certificate {cert_path} expires soon: {cert.not_valid_after}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate certificate {cert_path}: {e}")
            return False
    
    async def get_certificate_info(self, cert_path: str) -> Optional[CertificateInfo]:
        """Get information about a certificate."""
        cert_file = Path(cert_path)
        
        if not cert_file.exists():
            return None
        
        try:
            with open(cert_file, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            
            # Extract SAN domains
            san_domains = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                san_domains = [name.value for name in san_ext.value if isinstance(name, x509.DNSName)]
            except x509.ExtensionNotFound:
                pass
            
            return CertificateInfo(
                subject=cert.subject.rfc4514_string(),
                issuer=cert.issuer.rfc4514_string(),
                serial_number=str(cert.serial_number),
                not_before=cert.not_valid_before,
                not_after=cert.not_valid_after,
                san_domains=san_domains,
                key_size=cert.public_key().key_size,
                signature_algorithm=cert.signature_algorithm_oid._name,
                is_ca=self._is_ca_certificate(cert),
                is_self_signed=cert.issuer == cert.subject
            )
            
        except Exception as e:
            logger.error(f"Failed to get certificate info for {cert_path}: {e}")
            return None
    
    def _is_ca_certificate(self, cert: x509.Certificate) -> bool:
        """Check if certificate is a CA certificate."""
        try:
            basic_constraints = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.BASIC_CONSTRAINTS
            )
            return basic_constraints.value.ca
        except x509.ExtensionNotFound:
            return False
    
    async def generate_nginx_config(self) -> str:
        """Generate nginx configuration with TLS settings."""
        config = self.tls_configs["nginx"]
        
        if config.mode == TLSMode.NONE:
            return self._generate_nginx_http_config()
        
        return f"""
# GameForge Nginx TLS Configuration
server {{
    listen 80;
    server_name {os.getenv('DOMAIN', 'localhost')};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {os.getenv('DOMAIN', 'localhost')};
    
    # TLS Configuration
    ssl_certificate {config.cert_path};
    ssl_certificate_key {config.key_path};
    ssl_trusted_certificate {config.ca_cert_path};
    
    # TLS Protocol Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers {':'.join(config.cipher_suites or [])};
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security Headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
    
    # Client certificate verification (if mTLS)
    {"ssl_verify_client on;" if config.mode in [TLSMode.MTLS, TLSMode.STRICT_MTLS] else ""}
    {"ssl_client_certificate " + config.ca_cert_path + ";" if config.mode in [TLSMode.MTLS, TLSMode.STRICT_MTLS] else ""}
    
    # Proxy to application
    location / {{
        proxy_pass http://gameforge-app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Pass client certificate info if available
        proxy_set_header X-Client-Cert-CN $ssl_client_s_dn_cn;
        proxy_set_header X-Client-Cert-Serial $ssl_client_serial;
        proxy_set_header X-Client-Cert-Verify $ssl_client_verify;
    }}
    
    # Health check endpoint
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
}}
"""
    
    def _generate_nginx_http_config(self) -> str:
        """Generate nginx HTTP-only configuration for development."""
        return f"""
# GameForge Nginx HTTP Configuration (Development)
server {{
    listen 80;
    server_name {os.getenv('DOMAIN', 'localhost')};
    
    # Security Headers (even for HTTP)
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to application
    location / {{
        proxy_pass http://gameforge-app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # Health check endpoint
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
}}
"""
    
    async def generate_docker_compose_tls_override(self) -> str:
        """Generate Docker Compose override with TLS configurations."""
        services = {}
        
        for service_name, config in self.tls_configs.items():
            if config.mode == TLSMode.NONE:
                continue
            
            service_config = {
                "volumes": [
                    f"{config.cert_path}:/etc/ssl/certs/server.crt:ro",
                    f"{config.key_path}:/etc/ssl/private/server.key:ro",
                    f"{config.ca_cert_path}:/etc/ssl/certs/ca.crt:ro"
                ],
                "environment": [
                    "TLS_ENABLED=true",
                    f"TLS_CERT_PATH=/etc/ssl/certs/server.crt",
                    f"TLS_KEY_PATH=/etc/ssl/private/server.key",
                    f"TLS_CA_PATH=/etc/ssl/certs/ca.crt",
                    f"TLS_VERIFY_CLIENT={'true' if config.verify_client else 'false'}",
                    f"TLS_MIN_VERSION={config.min_tls_version}",
                    f"TLS_MAX_VERSION={config.max_tls_version}"
                ]
            }
            
            if config.mode in [TLSMode.MTLS, TLSMode.STRICT_MTLS] and config.client_cert_path:
                service_config["volumes"].extend([
                    f"{config.client_cert_path}:/etc/ssl/certs/client.crt:ro",
                    f"{config.client_key_path}:/etc/ssl/private/client.key:ro"
                ])
                service_config["environment"].extend([
                    "TLS_CLIENT_CERT_PATH=/etc/ssl/certs/client.crt",
                    "TLS_CLIENT_KEY_PATH=/etc/ssl/private/client.key"
                ])
            
            services[service_name] = service_config
        
        compose_config = {
            "version": "3.8",
            "services": services
        }
        
        import yaml
        return yaml.dump(compose_config, default_flow_style=False)
    
    def get_ssl_context(self, service_name: str) -> ssl.SSLContext:
        """Get SSL context for a service."""
        config = self.tls_configs.get(service_name)
        if not config or config.mode == TLSMode.NONE:
            raise ValueError(f"TLS not configured for service: {service_name}")
        
        # Create SSL context
        if config.mode in [TLSMode.MTLS, TLSMode.STRICT_MTLS]:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = config.verify_hostname
            context.verify_mode = ssl.CERT_REQUIRED if config.verify_client else ssl.CERT_OPTIONAL
        else:
            context = ssl.create_default_context()
            context.check_hostname = config.verify_hostname
        
        # Load certificates
        if Path(config.cert_path).exists() and Path(config.key_path).exists():
            context.load_cert_chain(config.cert_path, config.key_path)
        
        if config.ca_cert_path and Path(config.ca_cert_path).exists():
            context.load_verify_locations(config.ca_cert_path)
        
        # Configure TLS versions
        if config.min_tls_version == "TLSv1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3
        elif config.min_tls_version == "TLSv1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        if config.max_tls_version == "TLSv1.3":
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        elif config.max_tls_version == "TLSv1.2":
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        # Configure cipher suites
        if config.cipher_suites:
            context.set_ciphers(':'.join(config.cipher_suites))
        
        return context
    
    async def validate_all_certificates(self) -> Dict[str, Dict[str, Any]]:
        """Validate all service certificates."""
        results = {}
        
        for service_name, config in self.tls_configs.items():
            if config.mode == TLSMode.NONE:
                results[service_name] = {"status": "disabled", "message": "TLS disabled"}
                continue
            
            service_results = {}
            
            # Check server certificate
            cert_info = await self.get_certificate_info(config.cert_path)
            if cert_info:
                service_results["server_cert"] = {
                    "status": "valid",
                    "expires": cert_info.not_after.isoformat(),
                    "subject": cert_info.subject,
                    "san_domains": cert_info.san_domains
                }
            else:
                service_results["server_cert"] = {
                    "status": "missing",
                    "message": f"Certificate not found: {config.cert_path}"
                }
            
            # Check client certificate if mTLS
            if config.mode in [TLSMode.MTLS, TLSMode.STRICT_MTLS] and config.client_cert_path:
                client_cert_info = await self.get_certificate_info(config.client_cert_path)
                if client_cert_info:
                    service_results["client_cert"] = {
                        "status": "valid",
                        "expires": client_cert_info.not_after.isoformat(),
                        "subject": client_cert_info.subject
                    }
                else:
                    service_results["client_cert"] = {
                        "status": "missing",
                        "message": f"Client certificate not found: {config.client_cert_path}"
                    }
            
            results[service_name] = service_results
        
        return results


# Global TLS security manager instance
tls_security_manager = TLSSecurityManager()