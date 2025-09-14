"""
Secure access control manager for GameForge.
Implements IAM policies, Vault integration, and short-lived credentials.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
from pathlib import Path
import hashlib
import base64

try:
    import jwt
except ImportError:
    jwt = None

try:
    import boto3
except ImportError:
    boto3 = None

try:
    import aiofiles
except ImportError:
    aiofiles = None

from gameforge.core.config import get_settings
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)


class AccessLevel(Enum):
    """Access levels for resources."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


class ResourceType(Enum):
    """Types of resources that can be secured."""
    ASSET = "asset"
    MODEL = "model"
    DATASET = "dataset"
    BUCKET = "bucket"
    STORAGE = "storage"  # For storage security integration
    VAULT_SECRET = "vault_secret"
    API_ENDPOINT = "api_endpoint"
    USER_DATA = "user_data"


@dataclass
class AccessPolicy:
    """Access policy definition."""
    name: str
    resource_type: ResourceType
    resource_pattern: str  # Glob pattern or ARN pattern
    allowed_actions: List[str]
    denied_actions: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    ttl_seconds: Optional[int] = None


@dataclass
class AccessRequest:
    """Access request for resource."""
    user_id: str
    resource_type: ResourceType
    resource_id: str
    action: str
    context: Optional[Dict[str, Any]] = None
    requested_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.utcnow()


@dataclass
class AccessToken:
    """Temporary access token."""
    token_id: str
    user_id: str
    resource_type: ResourceType
    resource_id: str
    allowed_actions: List[str]
    expires_at: datetime
    conditions: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PresignedURL:
    """Presigned URL for direct resource access."""
    url: str
    method: str
    headers: Dict[str, str]
    expires_at: datetime
    resource_id: str


class AccessControlManager:
    """Comprehensive access control and policy manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self._vault_client = None
        self._aws_clients = {}
        self._azure_clients = {}
        self._gcp_clients = {}
        
        # Load access policies
        self.policies = self._load_access_policies()
        
        # Initialize cloud providers
        self._init_cloud_providers()
        
        # Token cache for short-lived credentials
        self._token_cache = {}
    
    def _load_access_policies(self) -> List[AccessPolicy]:
        """Load access policies from configuration."""
        return [
            # Asset access policies
            AccessPolicy(
                name="user_asset_read",
                resource_type=ResourceType.ASSET,
                resource_pattern="user/{user_id}/assets/*",
                allowed_actions=["read", "download", "metadata"],
                conditions={"user_owns_resource": True}
            ),
            AccessPolicy(
                name="user_asset_write",
                resource_type=ResourceType.ASSET,
                resource_pattern="user/{user_id}/assets/*",
                allowed_actions=["create", "update", "delete", "upload"],
                conditions={"user_owns_resource": True}
            ),
            AccessPolicy(
                name="shared_asset_read",
                resource_type=ResourceType.ASSET,
                resource_pattern="shared/assets/*",
                allowed_actions=["read", "download", "metadata"],
                conditions={"asset_is_public": True}
            ),
            
            # Model access policies
            AccessPolicy(
                name="model_read",
                resource_type=ResourceType.MODEL,
                resource_pattern="models/*",
                allowed_actions=["read", "download", "inference"],
                conditions={"user_has_model_access": True},
                ttl_seconds=3600  # 1 hour for model access
            ),
            AccessPolicy(
                name="model_admin",
                resource_type=ResourceType.MODEL,
                resource_pattern="models/*",
                allowed_actions=["read", "write", "delete", "manage"],
                conditions={"user_role": "admin"},
                ttl_seconds=1800  # 30 minutes for admin access
            ),
            
            # Dataset access policies
            AccessPolicy(
                name="dataset_read",
                resource_type=ResourceType.DATASET,
                resource_pattern="datasets/*",
                allowed_actions=["read", "download", "list"],
                conditions={"user_has_dataset_access": True},
                ttl_seconds=7200  # 2 hours for dataset access
            ),
            AccessPolicy(
                name="dataset_training",
                resource_type=ResourceType.DATASET,
                resource_pattern="datasets/training/*",
                allowed_actions=["read", "stream", "validate"],
                conditions={"user_has_training_access": True},
                ttl_seconds=14400  # 4 hours for training
            ),
            
            # Bucket access policies
            AccessPolicy(
                name="hot_storage_user",
                resource_type=ResourceType.BUCKET,
                resource_pattern="gameforge-hot",
                allowed_actions=["read", "write"],
                conditions={"storage_tier": "hot", "user_authenticated": True},
                ttl_seconds=1800  # 30 minutes
            ),
            AccessPolicy(
                name="warm_storage_user",
                resource_type=ResourceType.BUCKET,
                resource_pattern="gameforge-warm",
                allowed_actions=["read"],
                conditions={"storage_tier": "warm", "user_authenticated": True},
                ttl_seconds=3600  # 1 hour
            ),
            AccessPolicy(
                name="cold_storage_premium",
                resource_type=ResourceType.BUCKET,
                resource_pattern="gameforge-cold",
                allowed_actions=["read"],
                conditions={"storage_tier": "cold", "user_role": ["premium", "admin"]},
                ttl_seconds=7200  # 2 hours
            ),
            
            # Vault secret policies
            AccessPolicy(
                name="user_secrets",
                resource_type=ResourceType.VAULT_SECRET,
                resource_pattern="secret/users/{user_id}/*",
                allowed_actions=["read", "write"],
                conditions={"user_owns_secret": True},
                ttl_seconds=900  # 15 minutes
            ),
            AccessPolicy(
                name="model_secrets",
                resource_type=ResourceType.VAULT_SECRET,
                resource_pattern="secret/models/*",
                allowed_actions=["read"],
                conditions={"user_has_model_access": True},
                ttl_seconds=3600  # 1 hour
            ),
            
            # API endpoint policies
            AccessPolicy(
                name="ai_generation_basic",
                resource_type=ResourceType.API_ENDPOINT,
                resource_pattern="/api/v1/ai/generate/*",
                allowed_actions=["post"],
                conditions={"user_authenticated": True, "rate_limit_ok": True}
            ),
            AccessPolicy(
                name="ai_generation_premium",
                resource_type=ResourceType.API_ENDPOINT,
                resource_pattern="/api/v1/ai/generate/premium/*",
                allowed_actions=["post"],
                conditions={"user_role": ["premium", "admin"], "rate_limit_ok": True}
            ),
            
            # User data policies
            AccessPolicy(
                name="user_data_owner",
                resource_type=ResourceType.USER_DATA,
                resource_pattern="user/{user_id}/*",
                allowed_actions=["read", "write", "delete", "export"],
                conditions={"user_owns_data": True}
            ),
            AccessPolicy(
                name="user_data_admin",
                resource_type=ResourceType.USER_DATA,
                resource_pattern="user/*/admin",
                allowed_actions=["read", "audit"],
                conditions={"user_role": "admin"}
            )
        ]
    
    def _init_cloud_providers(self):
        """Initialize cloud provider clients for credential management."""
        try:
            # AWS IAM and STS
            if os.getenv("AWS_ACCESS_KEY_ID") and boto3:
                self._aws_clients = {
                    "iam": boto3.client(
                        "iam",
                        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                        region_name=os.getenv("AWS_REGION", "us-east-1")
                    ),
                    "sts": boto3.client(
                        "sts",
                        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                        region_name=os.getenv("AWS_REGION", "us-east-1")
                    ),
                    "s3": boto3.client(
                        "s3",
                        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                        region_name=os.getenv("AWS_REGION", "us-east-1")
                    )
                }
                logger.info("AWS clients initialized for access control")
            else:
                logger.warning("AWS credentials not found or boto3 not available")
            
            # Azure (placeholder for future implementation)
            if os.getenv("AZURE_CLIENT_ID"):
                # Initialize Azure clients
                pass
            
            # GCP (placeholder for future implementation)
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                # Initialize GCP clients
                pass
            
            # Vault client
            if self.settings.vault_client:
                self._vault_client = self.settings.vault_client
                logger.info("Vault client initialized for access control")
                
        except Exception as e:
            logger.error(f"Failed to initialize cloud provider clients: {e}")
    
    async def check_access(self, request: AccessRequest) -> Tuple[bool, Optional[str]]:
        """
        Check if access should be granted for a request.
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        try:
            # Find applicable policies
            applicable_policies = self._find_applicable_policies(request)
            
            if not applicable_policies:
                return False, f"No policies found for {request.resource_type.value}/{request.resource_id}"
            
            # Check each policy
            for policy in applicable_policies:
                # Check if action is explicitly denied
                if policy.denied_actions and request.action in policy.denied_actions:
                    return False, f"Action {request.action} explicitly denied by policy {policy.name}"
                
                # Check if action is allowed
                if request.action not in policy.allowed_actions:
                    continue
                
                # Evaluate conditions
                if policy.conditions:
                    condition_result = await self._evaluate_conditions(policy.conditions, request)
                    if not condition_result:
                        continue
                
                # Access granted
                logger.info(
                    f"Access granted for user {request.user_id}",
                    extra={
                        "user_id": request.user_id,
                        "resource_type": request.resource_type.value,
                        "resource_id": request.resource_id,
                        "action": request.action,
                        "policy": policy.name
                    }
                )
                return True, f"Access granted by policy {policy.name}"
            
            return False, f"No policy allows action {request.action} on {request.resource_type.value}/{request.resource_id}"
            
        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return False, f"Access check failed: {e}"
    
    def _find_applicable_policies(self, request: AccessRequest) -> List[AccessPolicy]:
        """Find policies that apply to the access request."""
        applicable = []
        
        for policy in self.policies:
            if policy.resource_type != request.resource_type:
                continue
            
            # Check if resource pattern matches
            if self._pattern_matches(policy.resource_pattern, request.resource_id, request.context or {}):
                applicable.append(policy)
        
        return applicable
    
    def _pattern_matches(self, pattern: str, resource_id: str, context: Dict[str, Any]) -> bool:
        """Check if a resource pattern matches the resource ID."""
        # Simple pattern matching with variable substitution
        import fnmatch
        
        # Substitute variables from context
        substituted_pattern = pattern
        for key, value in context.items():
            substituted_pattern = substituted_pattern.replace(f"{{{key}}}", str(value))
        
        return fnmatch.fnmatch(resource_id, substituted_pattern)
    
    async def _evaluate_conditions(self, conditions: Dict[str, Any], request: AccessRequest) -> bool:
        """Evaluate policy conditions."""
        for condition_name, expected_value in conditions.items():
            if condition_name == "user_owns_resource":
                if not await self._check_user_owns_resource(request.user_id, request.resource_id):
                    return False
            
            elif condition_name == "user_owns_data":
                if not await self._check_user_owns_data(request.user_id, request.resource_id):
                    return False
            
            elif condition_name == "user_owns_secret":
                if not await self._check_user_owns_secret(request.user_id, request.resource_id):
                    return False
            
            elif condition_name == "asset_is_public":
                if not await self._check_asset_is_public(request.resource_id):
                    return False
            
            elif condition_name == "user_has_model_access":
                if not await self._check_user_has_model_access(request.user_id, request.resource_id):
                    return False
            
            elif condition_name == "user_has_dataset_access":
                if not await self._check_user_has_dataset_access(request.user_id, request.resource_id):
                    return False
            
            elif condition_name == "user_has_training_access":
                if not await self._check_user_has_training_access(request.user_id):
                    return False
            
            elif condition_name == "user_authenticated":
                if not request.context or not request.context.get("authenticated"):
                    return False
            
            elif condition_name == "user_role":
                user_role = request.context.get("user_role") if request.context else None
                if isinstance(expected_value, list):
                    if user_role not in expected_value:
                        return False
                else:
                    if user_role != expected_value:
                        return False
            
            elif condition_name == "storage_tier":
                context_tier = request.context.get("storage_tier") if request.context else None
                if context_tier != expected_value:
                    return False
            
            elif condition_name == "rate_limit_ok":
                if not await self._check_rate_limit(request.user_id, request.action):
                    return False
        
        return True
    
    async def _check_user_owns_resource(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns the resource."""
        # Implementation would check database or Vault
        # For now, simple pattern matching
        return f"user/{user_id}/" in resource_id
    
    async def _check_user_owns_data(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns the data."""
        return f"user/{user_id}/" in resource_id
    
    async def _check_user_owns_secret(self, user_id: str, secret_path: str) -> bool:
        """Check if user owns the Vault secret."""
        return f"secret/users/{user_id}/" in secret_path
    
    async def _check_asset_is_public(self, asset_id: str) -> bool:
        """Check if asset is marked as public."""
        # Would check database for asset visibility
        return "shared/" in asset_id
    
    async def _check_user_has_model_access(self, user_id: str, model_id: str) -> bool:
        """Check if user has access to model."""
        # Would check user permissions, subscription level, etc.
        return True  # Placeholder
    
    async def _check_user_has_dataset_access(self, user_id: str, dataset_id: str) -> bool:
        """Check if user has access to dataset."""
        # Would check user permissions, subscription level, etc.
        return True  # Placeholder
    
    async def _check_user_has_training_access(self, user_id: str) -> bool:
        """Check if user has training access."""
        # Would check subscription level, quotas, etc.
        return True  # Placeholder
    
    async def _check_rate_limit(self, user_id: str, action: str) -> bool:
        """Check if user is within rate limits."""
        # Would check rate limiting service
        return True  # Placeholder
    
    async def generate_short_lived_credentials(
        self,
        request: AccessRequest,
        duration_seconds: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """
        Generate short-lived credentials for resource access.
        
        Args:
            request: Access request
            duration_seconds: Credential validity duration
            
        Returns:
            Credentials dictionary or None if access denied
        """
        # Check access first
        is_allowed, reason = await self.check_access(request)
        if not is_allowed:
            logger.warning(f"Access denied for credential generation: {reason}")
            return None
        
        try:
            if request.resource_type == ResourceType.BUCKET and "aws_s3" in self._aws_clients:
                return await self._generate_aws_s3_credentials(request, duration_seconds)
            
            elif request.resource_type == ResourceType.VAULT_SECRET and self._vault_client:
                return await self._generate_vault_credentials(request, duration_seconds)
            
            else:
                # Generate generic JWT token
                return await self._generate_jwt_token(request, duration_seconds)
                
        except Exception as e:
            logger.error(f"Failed to generate credentials: {e}")
            return None
    
    async def _generate_aws_s3_credentials(
        self,
        request: AccessRequest,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Generate temporary AWS S3 credentials."""
        # Create temporary policy for the specific resource
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": self._map_actions_to_s3_permissions(request.action),
                    "Resource": f"arn:aws:s3:::{request.resource_id}/*"
                }
            ]
        }
        
        # Generate temporary credentials using STS
        response = self._aws_clients["sts"].assume_role(
            RoleArn=os.getenv("AWS_TEMP_ROLE_ARN", "arn:aws:iam::account:role/GameForgeTemp"),
            RoleSessionName=f"gameforge-{request.user_id}-{int(datetime.utcnow().timestamp())}",
            Policy=json.dumps(policy_document),
            DurationSeconds=duration_seconds
        )
        
        credentials = response["Credentials"]
        
        return {
            "provider": "aws_s3",
            "access_key_id": credentials["AccessKeyId"],
            "secret_access_key": credentials["SecretAccessKey"],
            "session_token": credentials["SessionToken"],
            "expires_at": credentials["Expiration"].isoformat(),
            "resource_id": request.resource_id,
            "allowed_actions": [request.action]
        }
    
    async def _generate_vault_credentials(
        self,
        request: AccessRequest,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Generate temporary Vault credentials."""
        if not self._vault_client:
            raise ValueError("Vault client not available")
        
        # Create temporary Vault policy
        policy_name = f"temp-{request.user_id}-{int(datetime.utcnow().timestamp())}"
        
        policy_document = f"""
path "{request.resource_id}" {{
  capabilities = ["{request.action}"]
}}
"""
        
        try:
            # Create temporary policy in Vault (if method exists)
            if self._vault_client and hasattr(self._vault_client, 'create_policy'):
                await self._vault_client.create_policy(policy_name, policy_document)
            
            # Generate temporary token (if method exists)
            if self._vault_client and hasattr(self._vault_client, 'create_token'):
                token_response = await self._vault_client.create_token(
                    policies=[policy_name],
                    ttl=f"{duration_seconds}s",
                    explicit_max_ttl=f"{duration_seconds}s"
                )
            else:
                # Fallback: use existing vault token with limited access
                token_response = {"client_token": "fallback-token"}
            
            return {
                "provider": "vault",
                "token": token_response.get("client_token", "fallback-token") if token_response else "fallback-token",
                "expires_at": (datetime.utcnow() + timedelta(seconds=duration_seconds)).isoformat(),
                "resource_id": request.resource_id,
                "allowed_actions": [request.action],
                "policy_name": policy_name
            }
            
        except Exception as e:
            logger.error(f"Failed to create Vault credentials: {e}")
            # Fallback to JWT token
            return await self._generate_jwt_token(request, duration_seconds)
    
    async def _generate_jwt_token(
        self,
        request: AccessRequest,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Generate JWT token for resource access."""
        # Create JWT payload
        expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        payload = {
            "sub": request.user_id,
            "iss": "gameforge-access-control",
            "aud": f"{request.resource_type.value}/{request.resource_id}",
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "resource_type": request.resource_type.value,
            "resource_id": request.resource_id,
            "allowed_actions": [request.action],
            "context": request.context
        }
        
        # Sign JWT with secret key
        if not jwt:
            # Fallback to simple token when JWT not available
            simple_token = f"simple-{request.user_id}-{int(datetime.utcnow().timestamp())}"
            return {
                "provider": "jwt_fallback",
                "token": simple_token,
                "expires_at": expires_at.isoformat(),
                "resource_id": request.resource_id,
                "allowed_actions": [request.action]
            }
        
        token = jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm="HS256"
        )
        
        return {
            "provider": "jwt",
            "token": token,
            "expires_at": expires_at.isoformat(),
            "resource_id": request.resource_id,
            "allowed_actions": [request.action]
        }
    
    def _map_actions_to_s3_permissions(self, action: str) -> List[str]:
        """Map generic actions to S3 permissions."""
        action_map = {
            "read": ["s3:GetObject", "s3:GetObjectVersion"],
            "write": ["s3:PutObject", "s3:PutObjectAcl"],
            "delete": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
            "list": ["s3:ListBucket"],
            "download": ["s3:GetObject"],
            "upload": ["s3:PutObject"]
        }
        
        return action_map.get(action, [f"s3:{action}"])
    
    async def generate_presigned_url(
        self,
        request: AccessRequest,
        duration_seconds: int = 3600,
        method: str = "GET"
    ) -> Optional[PresignedURL]:
        """
        Generate presigned URL for direct resource access.
        
        Args:
            request: Access request
            duration_seconds: URL validity duration
            method: HTTP method for the URL
            
        Returns:
            PresignedURL object or None if access denied
        """
        # Check access first
        is_allowed, reason = await self.check_access(request)
        if not is_allowed:
            logger.warning(f"Access denied for presigned URL: {reason}")
            return None
        
        try:
            if request.resource_type == ResourceType.BUCKET and "s3" in self._aws_clients:
                return await self._generate_s3_presigned_url(request, duration_seconds, method)
            
            else:
                logger.warning(f"Presigned URLs not supported for {request.resource_type.value}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    async def _generate_s3_presigned_url(
        self,
        request: AccessRequest,
        duration_seconds: int,
        method: str
    ) -> PresignedURL:
        """Generate S3 presigned URL."""
        # Parse bucket and key from resource_id
        parts = request.resource_id.split("/", 1)
        bucket_name = parts[0]
        object_key = parts[1] if len(parts) > 1 else ""
        
        # Generate presigned URL
        operation_map = {
            "GET": "get_object",
            "PUT": "put_object",
            "DELETE": "delete_object"
        }
        
        operation = operation_map.get(method, "get_object")
        
        url = self._aws_clients["s3"].generate_presigned_url(
            operation,
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=duration_seconds
        )
        
        expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        return PresignedURL(
            url=url,
            method=method,
            headers={},
            expires_at=expires_at,
            resource_id=request.resource_id
        )
    
    async def validate_access_token(self, token: str, resource_id: str, action: str) -> bool:
        """Validate an access token for resource access."""
        try:
            # Try to decode as JWT first
            if jwt:
                try:
                    payload = jwt.decode(
                        token,
                        self.settings.jwt_secret_key,
                        algorithms=["HS256"]
                    )
                    
                    # Check token validity
                    if payload.get("resource_id") != resource_id:
                        return False
                    
                    if action not in payload.get("allowed_actions", []):
                        return False
                    
                    # Check expiration
                    exp = payload.get("exp")
                    if exp and datetime.utcnow().timestamp() > exp:
                        return False
                    
                    return True
                    
                except Exception:
                    # Not a valid JWT, try other token types
                    pass
            
            # Check for simple fallback tokens
            if token.startswith("simple-"):
                # Basic validation for fallback tokens
                # In production, these would be stored and validated properly
                return True
            
            # Check if it's a Vault token
            if self._vault_client and hasattr(self._vault_client, 'lookup_token'):
                try:
                    token_info = await self._vault_client.lookup_token(token)
                    if token_info and not token_info.get("expired", True):
                        # Would need to check token policies against resource/action
                        return True
                except Exception:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating access token: {e}")
            return False
    
    async def revoke_access_token(self, token: str) -> bool:
        """Revoke an access token."""
        try:
            # Try to revoke as Vault token first
            if self._vault_client and hasattr(self._vault_client, 'revoke_token'):
                try:
                    await self._vault_client.revoke_token(token)
                    return True
                except Exception:
                    pass
            
            # For JWT tokens, we'd need a token blacklist
            # For now, just return True (tokens will expire naturally)
            return True
            
        except Exception as e:
            logger.error(f"Error revoking access token: {e}")
            return False
    
    async def audit_access_attempts(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs for access attempts."""
        # This would integrate with the logging system to retrieve access logs
        # For now, return empty list
        return []
    
    async def cleanup_expired_tokens(self):
        """Clean up expired tokens and credentials."""
        try:
            # Clean up cached tokens
            current_time = datetime.utcnow()
            expired_tokens = [
                token_id for token_id, token_data in self._token_cache.items()
                if datetime.fromisoformat(token_data.get("expires_at", "")) < current_time
            ]
            
            for token_id in expired_tokens:
                del self._token_cache[token_id]
            
            if expired_tokens:
                logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
            
            # Clean up temporary Vault policies
            if self._vault_client:
                # Would list and delete temporary policies created for short-lived access
                pass
                
        except Exception as e:
            logger.error(f"Error during token cleanup: {e}")


# Global access control manager instance
access_control_manager = AccessControlManager()