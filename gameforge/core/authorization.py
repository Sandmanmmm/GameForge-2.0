"""
Role-Based Access Control (RBAC) System for GameForge AI Platform
================================================================

Comprehensive authorization system providing:
- Role-based permissions
- Resource-level access control
- JWT token management with refresh
- Permission decorators and middleware
- Security logging and audit trails
"""

import jwt
import enum
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Callable, Any
from functools import wraps
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from gameforge.core.config import get_settings
from gameforge.core.database import get_async_session
from gameforge.core.logging_config import get_structured_logger, log_security_event
from gameforge.models.collaboration import CollaborationRole

logger = get_structured_logger(__name__)
security = HTTPBearer()


# ============================================================================
# Permission System
# ============================================================================

class Permission(enum.Enum):
    """System-wide permissions."""
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    PROJECT_ADMIN = "project:admin"
    PROJECT_COLLABORATE = "project:collaborate"
    
    # Asset permissions
    ASSET_READ = "asset:read"
    ASSET_WRITE = "asset:write"
    ASSET_DELETE = "asset:delete"
    ASSET_UPLOAD = "asset:upload"
    
    # AI and ML permissions
    AI_GENERATE = "ai:generate"
    AI_ADMIN = "ai:admin"
    ML_TRAIN = "ml:train"
    ML_DEPLOY = "ml:deploy"
    
    # Billing permissions
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_ADMIN = "billing:admin"
    
    # Organization permissions
    ORG_READ = "org:read"
    ORG_WRITE = "org:write"
    ORG_ADMIN = "org:admin"
    ORG_INVITE = "org:invite"
    
    # Marketplace permissions
    MARKETPLACE_READ = "marketplace:read"
    MARKETPLACE_SELL = "marketplace:sell"
    MARKETPLACE_ADMIN = "marketplace:admin"
    
    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"
    AUDIT_READ = "audit:read"


class Role(enum.Enum):
    """User roles with associated permissions."""
    GUEST = "guest"
    USER = "user"
    PRO_USER = "pro_user"
    TEAM_LEADER = "team_leader"
    ORGANIZATION_ADMIN = "org_admin"
    PLATFORM_ADMIN = "platform_admin"
    SUPER_ADMIN = "super_admin"


# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: {
        Permission.PROJECT_READ,
        Permission.ASSET_READ,
        Permission.MARKETPLACE_READ,
    },
    Role.USER: {
        Permission.USER_READ,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_COLLABORATE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_UPLOAD,
        Permission.AI_GENERATE,
        Permission.BILLING_READ,
        Permission.MARKETPLACE_READ,
    },
    Role.PRO_USER: {
        Permission.USER_READ,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_COLLABORATE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_DELETE,
        Permission.ASSET_UPLOAD,
        Permission.AI_GENERATE,
        Permission.ML_TRAIN,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.ORG_READ,
        Permission.MARKETPLACE_READ,
        Permission.MARKETPLACE_SELL,
    },
    Role.TEAM_LEADER: {
        Permission.USER_READ,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_ADMIN,
        Permission.PROJECT_COLLABORATE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_DELETE,
        Permission.ASSET_UPLOAD,
        Permission.AI_GENERATE,
        Permission.ML_TRAIN,
        Permission.ML_DEPLOY,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.ORG_READ,
        Permission.ORG_WRITE,
        Permission.ORG_INVITE,
        Permission.MARKETPLACE_READ,
        Permission.MARKETPLACE_SELL,
    },
    Role.ORGANIZATION_ADMIN: {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_ADMIN,
        Permission.PROJECT_COLLABORATE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_DELETE,
        Permission.ASSET_UPLOAD,
        Permission.AI_GENERATE,
        Permission.AI_ADMIN,
        Permission.ML_TRAIN,
        Permission.ML_DEPLOY,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.BILLING_ADMIN,
        Permission.ORG_READ,
        Permission.ORG_WRITE,
        Permission.ORG_ADMIN,
        Permission.ORG_INVITE,
        Permission.MARKETPLACE_READ,
        Permission.MARKETPLACE_SELL,
        Permission.SYSTEM_MONITOR,
    },
    Role.PLATFORM_ADMIN: {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.USER_ADMIN,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_ADMIN,
        Permission.PROJECT_COLLABORATE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_DELETE,
        Permission.ASSET_UPLOAD,
        Permission.AI_GENERATE,
        Permission.AI_ADMIN,
        Permission.ML_TRAIN,
        Permission.ML_DEPLOY,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.BILLING_ADMIN,
        Permission.ORG_READ,
        Permission.ORG_WRITE,
        Permission.ORG_ADMIN,
        Permission.ORG_INVITE,
        Permission.MARKETPLACE_READ,
        Permission.MARKETPLACE_SELL,
        Permission.MARKETPLACE_ADMIN,
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_MONITOR,
        Permission.AUDIT_READ,
    },
    Role.SUPER_ADMIN: set(Permission),  # All permissions
}


# ============================================================================
# Models
# ============================================================================

class UserAuth(BaseModel):
    """Current authenticated user information."""
    id: str
    email: str
    username: str
    role: Role
    permissions: Set[Permission]
    is_active: bool
    is_verified: bool
    organization_id: Optional[str] = None
    subscription_tier: Optional[str] = None


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    email: str
    username: str
    role: str
    permissions: List[str]
    organization_id: Optional[str] = None
    exp: datetime
    iat: datetime
    token_type: str = "access"


class RefreshTokenData(BaseModel):
    """Refresh token payload data."""
    user_id: str
    token_id: str
    exp: datetime
    iat: datetime
    token_type: str = "refresh"


# ============================================================================
# JWT Token Management
# ============================================================================

class TokenManager:
    """Manages JWT token creation, validation, and refresh."""
    
    def __init__(self):
        self.settings = get_settings()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 30
    
    def create_access_token(self, user: UserAuth) -> str:
        """Create an access token for a user."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
            "permissions": [perm.value for perm in user.permissions],
            "organization_id": user.organization_id,
            "subscription_tier": user.subscription_tier,
            "exp": expire,
            "iat": now,
            "token_type": "access"
        }
        
        return jwt.encode(payload, self.settings.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str, token_id: str) -> str:
        """Create a refresh token for a user."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "user_id": user_id,
            "token_id": token_id,
            "exp": expire,
            "iat": now,
            "token_type": "refresh"
        }
        
        return jwt.encode(payload, self.settings.secret_key, algorithm=self.algorithm)
    
    def verify_access_token(self, token: str) -> TokenData:
        """Verify and decode an access token."""
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=[self.algorithm])
            
            if payload.get("token_type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Check expiration
            exp = datetime.fromtimestamp(payload["exp"])
            if exp < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )
            
            return TokenData(
                user_id=payload["user_id"],
                email=payload["email"],
                username=payload["username"],
                role=payload["role"],
                permissions=payload["permissions"],
                organization_id=payload.get("organization_id"),
                exp=exp,
                iat=datetime.fromtimestamp(payload["iat"])
            )
            
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def verify_refresh_token(self, token: str) -> RefreshTokenData:
        """Verify and decode a refresh token."""
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=[self.algorithm])
            
            if payload.get("token_type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Check expiration
            exp = datetime.fromtimestamp(payload["exp"])
            if exp < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired"
                )
            
            return RefreshTokenData(
                user_id=payload["user_id"],
                token_id=payload["token_id"],
                exp=exp,
                iat=datetime.fromtimestamp(payload["iat"])
            )
            
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(e)}"
            )


# Global token manager instance
token_manager = TokenManager()


# ============================================================================
# Authentication Helpers
# ============================================================================

async def get_current_user_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> UserAuth:
    """Get current authenticated user with full authorization context."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Verify token
        token_data = token_manager.verify_access_token(credentials.credentials)
        
        # Convert role string back to enum
        try:
            user_role = Role(token_data.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid role in token"
            )
        
        # Get permissions for role
        permissions = ROLE_PERMISSIONS.get(user_role, set())
        
        # Create user auth object
        user_auth = UserAuth(
            id=token_data.user_id,
            email=token_data.email,
            username=token_data.username,
            role=user_role,
            permissions=permissions,
            is_active=True,  # TODO: Check in database
            is_verified=True,  # TODO: Check in database
            organization_id=token_data.organization_id
        )
        
        # Log successful authentication
        log_security_event(
            "user_authentication_success",
            user_id=user_auth.id,
            ip_address=client_ip,
            severity="info",
            username=user_auth.username,
            role=user_auth.role.value,
            user_agent=user_agent,
            token_exp=token_data.exp.isoformat()
        )
        
        return user_auth
        
    except HTTPException:
        # Log failed authentication
        log_security_event(
            "user_authentication_failed",
            ip_address=client_ip,
            severity="warning",
            user_agent=user_agent,
            token_preview=credentials.credentials[:20] + "..." if len(credentials.credentials) > 20 else credentials.credentials
        )
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


def get_current_user_id() -> Callable:
    """Dependency to get current user ID."""
    async def _get_current_user_id(user: UserAuth = Depends(get_current_user_auth)) -> str:
        return user.id
    return _get_current_user_id


# ============================================================================
# Permission Checking
# ============================================================================

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from dependencies
            user = None
            for key, value in kwargs.items():
                if isinstance(value, UserAuth):
                    user = value
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if permission not in user.permissions:
                log_security_event(
                    "permission_denied",
                    user_id=user.id,
                    severity="warning",
                    username=user.username,
                    required_permission=permission.value,
                    user_role=user.role.value,
                    endpoint=func.__name__
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(min_role: Role):
    """Decorator to require minimum role level."""
    role_hierarchy = [
        Role.GUEST,
        Role.USER,
        Role.PRO_USER,
        Role.TEAM_LEADER,
        Role.ORGANIZATION_ADMIN,
        Role.PLATFORM_ADMIN,
        Role.SUPER_ADMIN
    ]
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from dependencies
            user = None
            for key, value in kwargs.items():
                if isinstance(value, UserAuth):
                    user = value
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            try:
                user_role_index = role_hierarchy.index(user.role)
                min_role_index = role_hierarchy.index(min_role)
                
                if user_role_index < min_role_index:
                    log_security_event(
                        "role_access_denied",
                        user_id=user.id,
                        severity="warning",
                        username=user.username,
                        user_role=user.role.value,
                        required_role=min_role.value,
                        endpoint=func.__name__
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient role: {min_role.value} or higher required"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid role configuration"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_resource_access(
    user: UserAuth,
    resource_type: str,
    resource_id: str,
    permission: Permission,
    db: AsyncSession
) -> bool:
    """Check if user has permission to access specific resource."""
    # Basic permission check
    if permission not in user.permissions:
        return False
    
    # Resource-specific access control
    if resource_type == "project":
        # Check if user owns project or is a collaborator
        from gameforge.services.collaboration import CollaborationService
        collaboration_service = CollaborationService(db)
        return await collaboration_service.can_user_access_project(resource_id, user.id)
    
    elif resource_type == "organization":
        # Check organization membership
        # TODO: Implement organization service check
        return user.organization_id == resource_id
    
    elif resource_type == "billing":
        # Users can only access their own billing info
        return True  # Basic implementation - should check user_id in billing records
    
    # Default: allow if user has the permission
    return True


# ============================================================================
# Resource-Level Authorization Decorators
# ============================================================================

def require_resource_access(resource_type: str, permission: Permission, resource_id_param: str = "resource_id"):
    """Decorator to check resource-level access."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user and database session
            user = None
            db = None
            resource_id = kwargs.get(resource_id_param)
            
            for key, value in kwargs.items():
                if isinstance(value, UserAuth):
                    user = value
                elif hasattr(value, "execute"):  # AsyncSession
                    db = value
            
            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing authentication or database context"
                )
            
            if not resource_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing {resource_id_param} parameter"
                )
            
            # Check resource access
            has_access = await check_resource_access(
                user, resource_type, resource_id, permission, db
            )
            
            if not has_access:
                log_security_event(
                    "resource_access_denied",
                    user_id=user.id,
                    severity="warning",
                    username=user.username,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission=permission.value,
                    endpoint=func.__name__
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to {resource_type} {resource_id}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Convenience Dependencies
# ============================================================================

def RequirePermission(permission: Permission):
    """FastAPI dependency for permission checking."""
    async def dependency(user: UserAuth = Depends(get_current_user_auth)):
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
        return user
    return dependency


def RequireRole(min_role: Role):
    """FastAPI dependency for role checking."""
    role_hierarchy = [Role.GUEST, Role.USER, Role.PRO_USER, Role.TEAM_LEADER, 
                     Role.ORGANIZATION_ADMIN, Role.PLATFORM_ADMIN, Role.SUPER_ADMIN]
    
    async def dependency(user: UserAuth = Depends(get_current_user_auth)):
        try:
            user_role_index = role_hierarchy.index(user.role)
            min_role_index = role_hierarchy.index(min_role)
            
            if user_role_index < min_role_index:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role: {min_role.value} or higher required"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid role configuration"
            )
        return user
    return dependency


# Export commonly used dependencies
CurrentUser = Depends(get_current_user_auth)
CurrentUserId = Depends(get_current_user_id())

# Permission-based dependencies
RequireUser = RequireRole(Role.USER)
RequireProUser = RequireRole(Role.PRO_USER)
RequireTeamLeader = RequireRole(Role.TEAM_LEADER)
RequireOrgAdmin = RequireRole(Role.ORGANIZATION_ADMIN)
RequirePlatformAdmin = RequireRole(Role.PLATFORM_ADMIN)
RequireSuperAdmin = RequireRole(Role.SUPER_ADMIN)

# Permission-specific dependencies
RequireProjectRead = RequirePermission(Permission.PROJECT_READ)
RequireProjectWrite = RequirePermission(Permission.PROJECT_WRITE)
RequireProjectAdmin = RequirePermission(Permission.PROJECT_ADMIN)
RequireBillingRead = RequirePermission(Permission.BILLING_READ)
RequireBillingAdmin = RequirePermission(Permission.BILLING_ADMIN)
RequireSystemAdmin = RequirePermission(Permission.SYSTEM_ADMIN)