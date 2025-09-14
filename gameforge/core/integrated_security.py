"""
Integrated Security Manager for GameForge
========================================

This module provides a unified interface for all GameForge security components:
- Storage Security & Encryption (KMS, storage tiers, asset management)
- TLS Security & Certificate Management (CA, service certificates, mTLS)
- Access Control & IAM (policies, short-lived credentials, presigned URLs)

The IntegratedSecurityManager orchestrates these components to provide
comprehensive security for the GameForge platform.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass

from .storage_security import StorageSecurityManager, StorageConfig, StorageTier
from .tls_security import TLSSecurityManager, TLSMode, TLSConfig
from .access_control import AccessControlManager, AccessRequest, ResourceType
from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SecurityPolicy:
    """Unified security policy configuration."""
    
    # Storage encryption settings
    encrypt_at_rest: bool = True
    encrypt_in_transit: bool = True
    kms_provider: str = "vault-transit"  # aws-kms, azure-kv, gcp-kms, vault-transit
    storage_tier_default: StorageTier = StorageTier.HOT
    
    # TLS/Certificate settings
    tls_mode: TLSMode = TLSMode.MTLS
    require_client_certs: bool = True
    cert_validity_days: int = 90
    ca_validity_days: int = 3650
    
    # Access control settings
    default_token_ttl: int = 3600  # 1 hour
    max_token_ttl: int = 43200    # 12 hours
    require_mfa: bool = False
    enforce_rbac: bool = True
    
    # Compliance settings
    audit_all_access: bool = True
    retention_days: int = 2555  # 7 years for compliance
    pii_encryption_required: bool = True
    

@dataclass
class SecurityContext:
    """Runtime security context for operations."""
    
    user_id: str
    session_id: str
    client_cert_fingerprint: Optional[str] = None
    access_level: str = "standard"
    mfa_verified: bool = False
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class IntegratedSecurityManager:
    """
    Unified security manager that orchestrates storage security,
    TLS/certificate management, and access control.
    """
    
    def __init__(self, settings: Settings, policy: Optional[SecurityPolicy] = None):
        self.settings = settings
        self.policy = policy or SecurityPolicy()
        
        # Initialize component managers
        self.storage_security: Optional[StorageSecurityManager] = None
        self.tls_security: Optional[TLSSecurityManager] = None
        self.access_control: Optional[AccessControlManager] = None
        
        # Security state
        self._initialized = False
        self._active_sessions: Dict[str, SecurityContext] = {}
        
        logger.info("IntegratedSecurityManager initialized")
    
    async def initialize(self) -> None:
        """Initialize all security components."""
        try:
            logger.info("Initializing integrated security system...")
            
            # Initialize storage security
            self.storage_security = StorageSecurityManager()
            
            # Initialize TLS security
            self.tls_security = TLSSecurityManager()
            
            # Initialize access control
            self.access_control = AccessControlManager()
            
            self._initialized = True
            logger.info("Integrated security system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize integrated security: {e}")
            raise
    
    async def create_secure_session(
        self,
        user_id: str,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_cert: Optional[bytes] = None
    ) -> SecurityContext:
        """Create a new secure session with full security validation."""
        if not self._initialized:
            await self.initialize()
        
        # Generate session ID
        session_id = f"sess_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Validate client certificate if provided
        client_cert_fingerprint = None
        if client_cert and self.tls_security:
            cert_info = await self.tls_security.validate_client_certificate(client_cert)
            if cert_info and cert_info.get("valid"):
                client_cert_fingerprint = cert_info.get("fingerprint")
            elif self.policy.require_client_certs:
                raise ValueError("Valid client certificate required")
        
        # Create security context
        context = SecurityContext(
            user_id=user_id,
            session_id=session_id,
            client_cert_fingerprint=client_cert_fingerprint,
            source_ip=source_ip,
            user_agent=user_agent
        )
        
        # Store active session
        self._active_sessions[session_id] = context
        
        logger.info(f"Created secure session {session_id} for user {user_id}")
        return context
    
    async def secure_store_asset(
        self,
        context: SecurityContext,
        asset_data: bytes,
        asset_id: str,
        asset_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        tier: Optional[StorageTier] = None
    ) -> Dict[str, Any]:
        """
        Securely store an asset with encryption, access control, and audit logging.
        """
        if not self._initialized:
            await self.initialize()
        
        # Validate session
        if context.session_id not in self._active_sessions:
            raise ValueError("Invalid or expired session")
        
        # Check access permissions
        access_request = AccessRequest(
            user_id=context.user_id,
            resource_type=ResourceType.STORAGE,
            resource_id=f"assets/{asset_id}",
            action="write",
            context={"asset_type": asset_type}
        )
        
        if not await self.access_control.validate_access(access_request):
            raise PermissionError("Access denied for asset storage")
        
        # Determine storage tier
        if tier is None:
            tier = self.policy.storage_tier_default
        
        # Determine if PII encryption is needed
        is_pii = metadata and metadata.get("contains_pii", False)
        encrypt_asset = self.policy.encrypt_at_rest or (is_pii and self.policy.pii_encryption_required)
        
        # Store asset securely
        result = await self.storage_security.store_encrypted_asset(
            asset_data=asset_data,
            asset_id=asset_id,
            metadata=metadata or {},
            tier=tier,
            encrypt=encrypt_asset
        )
        
        # Audit log the storage operation
        await self._audit_log({
            "action": "asset_stored",
            "user_id": context.user_id,
            "session_id": context.session_id,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "tier": tier.value,
            "encrypted": encrypt_asset,
            "size_bytes": len(asset_data),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    
    async def secure_retrieve_asset(
        self,
        context: SecurityContext,
        asset_id: str,
        decrypt: bool = True
    ) -> Dict[str, Any]:
        """
        Securely retrieve an asset with access validation and audit logging.
        """
        if not self._initialized:
            await self.initialize()
        
        # Validate session
        if context.session_id not in self._active_sessions:
            raise ValueError("Invalid or expired session")
        
        # Check access permissions
        access_request = AccessRequest(
            user_id=context.user_id,
            resource_type=ResourceType.STORAGE,
            resource_id=f"assets/{asset_id}",
            action="read"
        )
        
        if not await self.access_control.validate_access(access_request):
            raise PermissionError("Access denied for asset retrieval")
        
        # Retrieve asset
        result = await self.storage_security.retrieve_encrypted_asset(
            asset_id=asset_id,
            decrypt=decrypt
        )
        
        # Audit log the retrieval operation
        await self._audit_log({
            "action": "asset_retrieved",
            "user_id": context.user_id,
            "session_id": context.session_id,
            "asset_id": asset_id,
            "decrypted": decrypt,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    
    async def generate_presigned_url(
        self,
        context: SecurityContext,
        resource_id: str,
        action: str,
        expires_in: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL with integrated security validation.
        """
        if not self._initialized:
            await self.initialize()
        
        # Validate session
        if context.session_id not in self._active_sessions:
            raise ValueError("Invalid or expired session")
        
        # Use policy default if not specified
        if expires_in is None:
            expires_in = self.policy.default_token_ttl
        
        # Enforce maximum TTL
        if expires_in > self.policy.max_token_ttl:
            expires_in = self.policy.max_token_ttl
        
        # Generate presigned URL through access control
        access_request = AccessRequest(
            user_id=context.user_id,
            resource_type=ResourceType.STORAGE,
            resource_id=resource_id,
            action=action
        )
        
        result = await self.access_control.generate_presigned_url(
            request=access_request,
            expires_in=expires_in
        )
        
        # Audit log
        await self._audit_log({
            "action": "presigned_url_generated",
            "user_id": context.user_id,
            "session_id": context.session_id,
            "resource_id": resource_id,
            "url_action": action,
            "expires_in": expires_in,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    
    async def create_service_certificates(
        self,
        service_name: str,
        domains: List[str],
        enable_mtls: bool = True
    ) -> Dict[str, Any]:
        """
        Create TLS certificates for a service with optional mTLS.
        """
        if not self._initialized:
            await self.initialize()
        
        # Generate service certificates
        result = await self.tls_security.create_service_certificate(
            service_name=service_name,
            domains=domains,
            enable_client_auth=enable_mtls
        )
        
        # Audit log
        await self._audit_log({
            "action": "service_certificates_created",
            "service_name": service_name,
            "domains": domains,
            "mtls_enabled": enable_mtls,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
    
    async def rotate_encryption_keys(self, key_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Rotate encryption keys across all storage systems.
        """
        if not self._initialized:
            await self.initialize()
        
        results = []
        
        # Rotate storage encryption keys
        if self.storage_security:
            storage_result = await self.storage_security.rotate_encryption_keys(key_ids)
            results.append({"component": "storage", "result": storage_result})
        
        # Rotate TLS certificates if needed
        if self.tls_security:
            cert_result = await self.tls_security.rotate_certificates()
            results.append({"component": "tls", "result": cert_result})
        
        # Audit log
        await self._audit_log({
            "action": "encryption_keys_rotated",
            "key_ids": key_ids or "all",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {"rotation_results": results}
    
    async def validate_security_posture(self) -> Dict[str, Any]:
        """
        Validate the overall security posture of the system.
        """
        if not self._initialized:
            await self.initialize()
        
        posture = {
            "overall_status": "healthy",
            "components": {},
            "recommendations": [],
            "compliance_status": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check storage security
        if self.storage_security:
            storage_status = await self.storage_security.validate_security_posture()
            posture["components"]["storage"] = storage_status
        
        # Check TLS security
        if self.tls_security:
            tls_status = await self.tls_security.validate_certificates()
            posture["components"]["tls"] = tls_status
        
        # Check access control
        if self.access_control:
            access_status = await self.access_control.validate_policies()
            posture["components"]["access_control"] = access_status
        
        # Generate recommendations
        for component, status in posture["components"].items():
            if not status.get("healthy", True):
                posture["recommendations"].append(f"Review {component} configuration")
                posture["overall_status"] = "warning"
        
        # Compliance checks
        posture["compliance_status"] = {
            "encryption_at_rest": self.policy.encrypt_at_rest,
            "encryption_in_transit": self.policy.encrypt_in_transit,
            "audit_logging": self.policy.audit_all_access,
            "access_controls": self.policy.enforce_rbac,
            "certificate_validation": self.policy.tls_mode != TLSMode.NONE
        }
        
        return posture
    
    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired security sessions."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, context in self._active_sessions.items():
            if context.timestamp and context.timestamp < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self._active_sessions[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)
    
    async def _audit_log(self, event: Dict[str, Any]) -> None:
        """Log security events for audit purposes."""
        try:
            # In production, this would write to a secure audit log system
            logger.info(f"SECURITY_AUDIT: {event}")
            
            # Store in storage system if available
            if self.storage_security and self.policy.audit_all_access:
                audit_data = {
                    "event_type": "security_audit",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": event
                }
                
                # Store with long retention
                await self.storage_security.store_encrypted_asset(
                    asset_data=str(audit_data).encode(),
                    asset_id=f"audit/{datetime.utcnow().strftime('%Y/%m/%d')}/{event.get('session_id', 'system')}_{int(datetime.utcnow().timestamp())}",
                    metadata={"type": "audit_log", "retention_days": self.policy.retention_days},
                    tier=StorageTier.COLD,
                    encrypt=True
                )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the integrated security system."""
        logger.info("Shutting down integrated security system...")
        
        try:
            # Cleanup active sessions
            self._active_sessions.clear()
            
            # Shutdown components
            if self.storage_security:
                await self.storage_security.shutdown()
            
            if self.tls_security:
                await self.tls_security.shutdown()
            
            self._initialized = False
            logger.info("Integrated security system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during security system shutdown: {e}")


# Convenience factory function
async def create_integrated_security(
    settings: Settings,
    policy: Optional[SecurityPolicy] = None
) -> IntegratedSecurityManager:
    """
    Factory function to create and initialize an IntegratedSecurityManager.
    """
    manager = IntegratedSecurityManager(settings, policy)
    await manager.initialize()
    return manager


# Export main classes
__all__ = [
    "IntegratedSecurityManager",
    "SecurityPolicy", 
    "SecurityContext",
    "create_integrated_security"
]