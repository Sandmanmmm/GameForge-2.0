"""
HashiCorp Vault integration for GameForge AI Platform.
Secure secrets management for API keys, database credentials, and model tokens.
"""
import os
import hvac
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import time
from gameforge.core.logging_config import get_structured_logger, log_security_event

logger = get_structured_logger(__name__)


class VaultClient:
    """
    HashiCorp Vault client for secure secrets management.
    
    Manages API keys, database credentials, model tokens, and other sensitive data.
    """
    
    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_point: str = "gameforge"
    ):
        """
        Initialize Vault client.
        
        Args:
            vault_url: Vault server URL (defaults to VAULT_ADDR env var)
            vault_token: Vault authentication token (defaults to VAULT_TOKEN)
            mount_point: Vault mount point for GameForge secrets
        """
        self.vault_url = vault_url or os.getenv(
            "VAULT_ADDR", "http://localhost:8200"
        )
        self.vault_token = vault_token or os.getenv(
            "VAULT_TOKEN", "gameforge-vault-root-token-2025"
        )
        self.mount_point = mount_point
        
        # Initialize HVAC client
        self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
        self._authenticated = None  # Lazy authentication check
        
        logger.info(
            "Vault client initialized",
            vault_url=self.vault_url,
            mount_point=self.mount_point
        )
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated (lazy check)."""
        if self._authenticated is None:
            try:
                self._authenticated = self.client.is_authenticated()
                if not self._authenticated:
                    logger.warning(
                        f"Failed to authenticate with Vault at {self.vault_url}"
                    )
            except Exception as e:
                logger.warning(f"Vault authentication check failed: {e}")
                self._authenticated = False
        return self._authenticated
    
    def get_secret(self, path: str, key: str = None) -> Optional[Any]:
        """
        Retrieve a secret from Vault.
        
        Args:
            path: Secret path (relative to mount point)
            key: Specific key within the secret (optional)
            
        Returns:
            Secret value or None if not found
        """
        try:
            full_path = f"{self.mount_point}/data/{path}"
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self.mount_point
            )
            
            if not response or 'data' not in response:
                logger.warning(
                    "Secret not found",
                    path=path,
                    mount_point=self.mount_point
                )
                return None
            
            secret_data = response['data']['data']
            
            if key:
                result = secret_data.get(key)
                if result is None:
                    logger.warning(
                        "Secret key not found",
                        path=path,
                        key=key
                    )
                return result
            
            log_security_event(
                event_type="secret_accessed",
                severity="info",
                secret_path=path,
                has_key=bool(key)
            )
            
            return secret_data
            
        except Exception as e:
            logger.error(
                "Failed to retrieve secret",
                path=path,
                key=key,
                error=str(e)
            )
            log_security_event(
                event_type="secret_access_failed",
                severity="error",
                secret_path=path,
                error=str(e)
            )
            return None
    
    def set_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Store a secret in Vault.
        
        Args:
            path: Secret path (relative to mount point)
            data: Secret data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            secret_data = data.copy()
            secret_data["created_at"] = datetime.utcnow().isoformat()
            secret_data["created_by"] = "gameforge-ai"
            
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret_data,
                mount_point=self.mount_point
            )
            
            log_security_event(
                event_type="secret_stored",
                severity="info",
                secret_path=path,
                keys=list(data.keys())
            )
            
            logger.info(
                "Secret stored successfully",
                path=path,
                keys=list(data.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to store secret",
                path=path,
                error=str(e)
            )
            log_security_event(
                event_type="secret_store_failed",
                severity="error",
                secret_path=path,
                error=str(e)
            )
            return False
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: Secret path (relative to mount point)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path, mount_point=self.mount_point
            )
            
            log_security_event(
                event_type="secret_deleted",
                severity="warning",
                secret_path=path
            )
            
            logger.info("Secret deleted successfully", path=path)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete secret",
                path=path,
                error=str(e)
            )
            return False
    
    def get_model_token(self, model_provider: str) -> Optional[str]:
        """
        Get API token for AI model provider.
        
        Args:
            model_provider: Provider name (huggingface, openai, stability, etc.)
            
        Returns:
            API token or None if not found
        """
        path = f"models/{model_provider}"
        
        if model_provider == "huggingface":
            return self.get_secret(path, "token")
        elif model_provider in ["openai", "stability"]:
            return self.get_secret(path, "api_key")
        else:
            # Generic token retrieval
            secret = self.get_secret(path)
            if secret:
                return secret.get("token") or secret.get("api_key")
            return None
    
    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get database connection credentials.
        
        Returns:
            Dictionary with database credentials or None
        """
        secret = self.get_secret("secrets/database")
        if secret:
            return {
                "password": secret.get("password"),
                "username": secret.get("username", "gameforge"),
                "host": secret.get("host", "postgres"),
                "port": secret.get("port", "5432"),
                "database": secret.get("database", "gameforge")
            }
        return None
    
    def get_jwt_secret(self) -> Optional[str]:
        """
        Get JWT signing secret.
        
        Returns:
            JWT secret key or None
        """
        return self.get_secret("secrets/jwt", "secret")
    
    def rotate_secret(self, path: str, new_data: Dict[str, Any]) -> bool:
        """
        Rotate a secret by updating it with new data.
        
        Args:
            path: Secret path
            new_data: New secret data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current secret for backup
            current = self.get_secret(path)
            
            # Store new secret
            success = self.set_secret(path, new_data)
            
            if success:
                log_security_event(
                    event_type="secret_rotated",
                    severity="info",
                    secret_path=path,
                    rotation_time=datetime.utcnow().isoformat()
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to rotate secret",
                path=path,
                error=str(e)
            )
            return False
    
    async def create_policy(self, policy_name: str, policy_document: str) -> bool:
        """
        Create a Vault policy for access control.
        
        Args:
            policy_name: Name of the policy
            policy_document: HCL policy document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_authenticated():
                logger.error("Vault client not authenticated for policy creation")
                return False
            
            # Use HVAC client to create policy
            self.client.sys.create_or_update_policy(
                name=policy_name,
                policy=policy_document
            )
            
            log_security_event(
                event_type="vault_policy_created",
                severity="info",
                policy_name=policy_name
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to create Vault policy",
                policy_name=policy_name,
                error=str(e)
            )
            return False
    
    async def create_token(self, policies: Optional[List[str]] = None, ttl: Optional[str] = None, explicit_max_ttl: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a Vault token with specified policies and TTL.
        
        Args:
            policies: List of policy names
            ttl: Token time-to-live
            explicit_max_ttl: Maximum token lifetime
            
        Returns:
            Token response dict or None
        """
        try:
            if not self.is_authenticated():
                logger.error("Vault client not authenticated for token creation")
                return None
            
            token_data = {}
            if policies:
                token_data["policies"] = policies
            if ttl:
                token_data["ttl"] = ttl
            if explicit_max_ttl:
                token_data["explicit_max_ttl"] = explicit_max_ttl
            
            # Create token using HVAC client
            response = self.client.auth.token.create(**token_data)
            
            if response and "auth" in response:
                log_security_event(
                    event_type="vault_token_created",
                    severity="info",
                    policies=policies,
                    ttl=ttl
                )
                return response["auth"]
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to create Vault token",
                policies=policies,
                ttl=ttl,
                error=str(e)
            )
            return None
    
    async def lookup_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Lookup token information.
        
        Args:
            token: Token to lookup
            
        Returns:
            Token info dict or None
        """
        try:
            if not self.is_authenticated():
                logger.error("Vault client not authenticated for token lookup")
                return None
            
            # Lookup token using HVAC client
            response = self.client.auth.token.lookup(token)
            
            if response and "data" in response:
                return response["data"]
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to lookup Vault token",
                error=str(e)
            )
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a Vault token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_authenticated():
                logger.error("Vault client not authenticated for token revocation")
                return False
            
            # Revoke token using HVAC client
            self.client.auth.token.revoke(token)
            
            log_security_event(
                event_type="vault_token_revoked",
                severity="info",
                token_prefix=token[:8] + "..."
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to revoke Vault token",
                error=str(e)
            )
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Vault health and connectivity.
        
        Returns:
            Health status dictionary
        """
        try:
            health = self.client.sys.read_health_status()
            authenticated = self.is_authenticated()
            
            status = {
                "vault_url": self.vault_url,
                "authenticated": authenticated,
                "sealed": health.get("sealed", True),
                "standby": health.get("standby", True),
                "cluster_name": health.get("cluster_name"),
                "version": health.get("version"),
                "healthy": authenticated and not health.get("sealed", True)
            }
            
            if status["healthy"]:
                logger.info("Vault health check passed", **status)
            else:
                logger.warning("Vault health check failed", **status)
            
            return status
            
        except Exception as e:
            logger.error("Vault health check failed", error=str(e))
            return {
                "vault_url": self.vault_url,
                "authenticated": False,
                "healthy": False,
                "error": str(e)
            }


# Global Vault client instance
_vault_client: Optional[VaultClient] = None


def get_vault_client() -> VaultClient:
    """
    Get the global Vault client instance.
    
    Returns:
        Initialized VaultClient instance
    """
    global _vault_client
    
    if _vault_client is None:
        _vault_client = VaultClient()
    
    return _vault_client


def init_vault_client(vault_url: Optional[str] = None, vault_token: Optional[str] = None):
    """
    Initialize the global Vault client with custom parameters.
    
    Args:
        vault_url: Custom Vault URL
        vault_token: Custom Vault token
    """
    global _vault_client
    _vault_client = VaultClient(vault_url=vault_url, vault_token=vault_token)


# Convenience functions for common operations
def get_ai_model_token(provider: str) -> Optional[str]:
    """Get AI model API token from Vault."""
    return get_vault_client().get_model_token(provider)


def get_db_password() -> Optional[str]:
    """Get database password from Vault."""
    creds = get_vault_client().get_database_credentials()
    return creds.get("password") if creds else None


def get_jwt_secret_key() -> Optional[str]:
    """Get JWT secret key from Vault."""
    return get_vault_client().get_jwt_secret()


def vault_health() -> Dict[str, Any]:
    """Check Vault health status."""
    return get_vault_client().health_check()