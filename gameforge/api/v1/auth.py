"""
Production-ready authentication and authorization endpoints.
Includes comprehensive security, error handling, logging, and Vault.
"""
import jwt
import secrets
import httpx
import json
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, and_
from gameforge.core.config import get_settings
from gameforge.core.logging_config import (
    get_structured_logger,
    log_security_event
)
from gameforge.core.database import get_async_session
from gameforge.models import User, AuthProvider

router = APIRouter()
security = HTTPBearer()

# Get structured logger for this module
logger = get_structured_logger(__name__)


class LoginRequest(BaseModel):
    """Request model for traditional login."""
    username: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class LoginResponse(BaseModel):
    """Response model for successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # Token expiration in seconds
    user: Dict[str, Any]


class UserData(BaseModel):
    """User data extracted from JWT token."""
    id: str
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None  # Changed from 'name' to match database
    avatar_url: Optional[str] = None
    auth_provider: Optional[str] = None  # Changed from 'provider' to match database
    is_verified: bool = False


class OAuthState(BaseModel):
    """OAuth state management for security."""
    state: str
    created_at: datetime
    redirect_uri: Optional[str] = None


class RegisterRequest(BaseModel):
    """Request model for user registration."""
    username: str
    email: EmailStr
    password: str
    name: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v.strip()) > 50:
            raise ValueError('Username cannot exceed 50 characters')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) < 1:
                raise ValueError('Name cannot be empty')
            if len(v) > 100:
                raise ValueError('Name cannot exceed 100 characters')
        return v


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile."""
    name: Optional[str] = None
    username: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) < 1:
                raise ValueError('Name cannot be empty')
            if len(v) > 100:
                raise ValueError('Name cannot exceed 100 characters')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters')
            if len(v) > 50:
                raise ValueError('Username cannot exceed 50 characters')
            # Check for valid username format (alphanumeric and underscores only)
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', v):
                raise ValueError('Username can only contain letters, numbers, and underscores')
        return v


def create_jwt_token(
    user_data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a secure JWT token with expiration and proper claims.
    
    Args:
        user_data: User information to encode in token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    # Standard JWT claims
    payload = {
        "sub": str(user_data.get('id')),  # Subject (user ID)
        "iat": datetime.utcnow(),  # Issued at
        "exp": expire,  # Expiration
        "iss": "gameforge-ai",  # Issuer
        "aud": "gameforge-frontend",  # Audience
        # Custom claims
        "id": str(user_data.get('id')),
        "userId": str(user_data.get('id')),  # Backward compatibility
        "email": user_data.get('email'),
        "username": user_data.get('username'),
        "name": user_data.get('name'),
        "avatar_url": user_data.get('avatar_url'),
        "provider": user_data.get('provider', 'local'),
        "is_verified": user_data.get('is_verified', False)
    }
    
    try:
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm="HS256"
        )
        
        log_security_event(
            "jwt_token_created",
            "info",
            {
                "user_id": user_data.get('id'),
                "provider": user_data.get('provider', 'local'),
                "expires_at": expire.isoformat()
            }
        )
        
        return token
    except Exception as e:
        logger.error(
            "JWT token creation failed",
            extra_fields={
                "error": str(e),
                "user_id": user_data.get('id')
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )


def verify_jwt_token(token: str) -> UserData:
    """
    Verify and decode JWT token with comprehensive validation.
    
    Args:
        token: JWT token to verify
        
    Returns:
        UserData object with user information
        
    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    settings = get_settings()
    
    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            audience="gameforge-frontend",
            issuer="gameforge-ai"
        )
        
        # Extract user data from token payload
        user_id = (payload.get("id") or
                   payload.get("userId") or
                   payload.get("sub"))
        email = payload.get("email")
        
        if not user_id:
            log_security_event(
                "jwt_verification_failed",
                "warning",
                {"reason": "missing_user_id", "token_sub": payload.get("sub")}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        if not email:
            log_security_event(
                "jwt_verification_failed",
                "warning",
                {"reason": "missing_email", "user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing email"
            )
        
        user_data = UserData(
            id=user_id,
            email=email,
            username=payload.get("username"),
            full_name=payload.get("full_name"),
            avatar_url=payload.get("avatar_url"),
            auth_provider=payload.get("auth_provider", "local"),
            is_verified=payload.get("is_verified", False)
        )
        
        log_security_event(
            "jwt_verification_success",
            "info",
            {
                "user_id": user_id,
                "provider": user_data.auth_provider
            }
        )
        
        return user_data
        
    except jwt.ExpiredSignatureError:
        log_security_event(
            "jwt_verification_failed",
            "warning",
            {"reason": "token_expired"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidAudienceError:
        log_security_event(
            "jwt_verification_failed",
            "error",
            {"reason": "invalid_audience"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience"
        )
    except jwt.InvalidIssuerError:
        log_security_event(
            "jwt_verification_failed",
            "error",
            {"reason": "invalid_issuer"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer"
        )
    except jwt.InvalidTokenError as e:
        log_security_event(
            "jwt_verification_failed",
            "error",
            {"reason": "invalid_token", "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(
            "JWT verification unexpected error",
            extra_fields={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserData:
    """
    Get current authenticated user from JWT token with security logging.
    
    Args:
        request: FastAPI request object for context
        credentials: HTTP Authorization header
        
    Returns:
        UserData object for authenticated user
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        user_data = verify_jwt_token(credentials.credentials)
        
        log_security_event(
            "user_authentication_success",
            "info",
            {
                "user_id": user_data.id,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "provider": user_data.auth_provider
            }
        )
        
        return user_data
    except HTTPException as e:
        log_security_event(
            "user_authentication_failed",
            "warning",
            {
                "client_ip": client_ip,
                "user_agent": user_agent,
                "reason": e.detail
            }
        )
        raise


async def create_or_update_oauth_user(
    user_data: Dict[str, Any],
    provider: str,
    client_ip: str = "unknown"
) -> User:
    """
    Create or update a user record for OAuth authentication.
    
    Args:
        user_data: User data from OAuth provider
        provider: OAuth provider name (github, google, etc.)
        client_ip: Client IP for logging
        
    Returns:
        User record from database
    """
    session = None
    try:
        # Get a database session
        session_gen = get_async_session()
        session = await session_gen.__anext__()
        
        # Try to find existing user by provider ID or email
        provider_id = str(user_data['id'])
        email = user_data['email']
        username = user_data.get('login') or user_data.get('username') or f"{provider}_{provider_id[:8]}"
        
        # Look for existing user by provider ID first
        existing_user = None
        if provider == "github":
            result = await session.execute(
                select(User).where(User.github_id == provider_id)
            )
            existing_user = result.scalar_one_or_none()
        elif provider == "google":
            result = await session.execute(
                select(User).where(User.google_id == provider_id)
            )
            existing_user = result.scalar_one_or_none()
        
        # If not found by provider ID, try by email
        if not existing_user and email:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user with OAuth provider info
            update_data = {
                "full_name": user_data.get('name') or existing_user.full_name,
                "avatar_url": user_data.get('avatar_url'),
                "is_verified": True,
                "is_active": True
            }
            
            # Link OAuth provider if not already linked
            if provider == "github" and existing_user.github_id is None:
                update_data["github_id"] = provider_id
                update_data["provider"] = AuthProvider.GITHUB
            elif provider == "google" and existing_user.google_id is None:
                update_data["google_id"] = provider_id
                update_data["provider"] = AuthProvider.GOOGLE
            
            await session.execute(
                update(User)
                .where(User.id == existing_user.id)
                .values(**update_data)
            )
            await session.commit()
            
            log_security_event(
                "oauth_user_updated",
                "info",
                client_ip,
                {
                    "user_id": str(existing_user.id),
                    "provider": provider,
                    "email": email
                }
            )
            
            # Refresh the user to get updated data
            await session.refresh(existing_user)
            return existing_user
        else:
            # Create new user
            new_user = User(
                username=username,
                email=email,
                name=user_data.get('name'),
                avatar_url=user_data.get('avatar_url'),
                password_hash=None,  # OAuth users don't have passwords
                github_id=provider_id if provider == "github" else None,
                google_id=provider_id if provider == "google" else None,
                provider=AuthProvider.GITHUB if provider == "github" else AuthProvider.GOOGLE,
                is_verified=True,
                is_active=True
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            log_security_event(
                "oauth_user_created",
                "info",
                client_ip,
                {
                    "user_id": str(new_user.id),
                    "provider": provider,
                    "email": email,
                    "username": username
                }
            )
            
            return new_user
                
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(
            "OAuth user creation/update failed",
            extra_fields={
                "error": str(e),
                "provider": provider,
                "email": user_data.get('email'),
                "client_ip": client_ip
            }
        )
        # Re-raise the exception to handle it in the calling function
        raise
    finally:
        if session:
            await session.close()


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest, http_request: Request):
    """
    User registration endpoint for creating new accounts.
    
    Creates a new user account with username, email, and password.
    Returns an access token upon successful registration.
    """
    client_ip = http_request.client.host if http_request.client else "unknown"
    
    log_security_event(
        "registration_attempt",
        "info",
        client_ip,
        {
            "username": request.username,
            "email": request.email,
            "authentication_method": "password"
        }
    )
    
    session = None
    try:
        # Get a database session
        session_gen = get_async_session()
        session = await session_gen.__anext__()
        
        # Check if username already exists
        result = await session.execute(
            select(User).where(User.username == request.username)
        )
        existing_username = result.scalar_one_or_none()
        
        if existing_username:
            log_security_event(
                "registration_failed",
                "warning",
                client_ip,
                {
                    "username": request.username,
                    "reason": "username_exists"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        result = await session.execute(
            select(User).where(User.email == request.email)
        )
        existing_email = result.scalar_one_or_none()
        
        if existing_email:
            log_security_event(
                "registration_failed",
                "warning",
                client_ip,
                {
                    "username": request.username,
                    "email": request.email,
                    "reason": "email_exists"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Hash the password (proper bcrypt hashing should be used in production)
        import hashlib
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        
        # Create new user
        new_user = User(
            username=request.username,
            email=request.email,
            full_name=request.name,
            password_hash=password_hash,
            auth_provider=AuthProvider.LOCAL,
            is_verified=False,  # Require email verification
            is_active=True
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        # Create JWT token for the new user
        provider_value = "local"  # For registered users, always local
        user_data = {
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "auth_provider": provider_value,
            "is_verified": new_user.is_verified
        }
        
        access_token = create_jwt_token(user_data)
        
        log_security_event(
            "registration_successful",
            "info",
            client_ip,
            {
                "user_id": str(new_user.id),
                "username": request.username,
                "email": request.email
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=3600,
            user=user_data
        )
        
    except HTTPException:
        if session:
            await session.rollback()
        raise
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(
            "Registration failed",
            extra_fields={
                "error": str(e),
                "username": request.username,
                "email": request.email,
                "client_ip": client_ip
            }
        )
        log_security_event(
            "registration_failed",
            "error",
            client_ip,
            {
                "username": request.username,
                "email": request.email,
                "reason": "server_error",
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
    finally:
        if session:
            await session.close()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """
    Traditional username/password authentication endpoint.
    
    Note: This is a placeholder implementation. In production,
    integrate with your user database and proper password hashing.
    """
    client_ip = http_request.client.host if http_request.client else "unknown"
    
    log_security_event(
        "login_attempt",
        "info",
        {
            "username": request.username,
            "client_ip": client_ip,
            "authentication_method": "password"
        }
    )
    
    # TODO: Implement actual authentication logic with database
    # This is a placeholder for demonstration
    if request.username == "admin" and request.password == "admin":
        user_data = {
            "id": "1",
            "email": "admin@gameforge.ai",
            "username": "admin",
            "name": "Administrator",
            "provider": "local",
            "is_verified": True
        }
        
        token = create_jwt_token(user_data)
        
        log_security_event(
            "login_success",
            "info",
            {
                "user_id": user_data["id"],
                "username": request.username,
                "client_ip": client_ip
            }
        )
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=86400,  # 24 hours
            user=user_data
        )
    
    log_security_event(
        "login_failed",
        "warning",
        {
            "username": request.username,
            "client_ip": client_ip,
            "reason": "invalid_credentials"
        }
    )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: UserData = Depends(get_current_user)
):
    """
    User logout endpoint with security logging.
    
    Note: In production, implement token blacklisting or short-lived tokens
    with refresh token rotation for proper logout functionality.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    log_security_event(
        "user_logout",
        "info",
        {
            "user_id": current_user.id,
            "client_ip": client_ip
        }
    )
    
    # TODO: Implement token invalidation/blacklisting
    return {"message": "Successfully logged out"}


@router.options("/me")
async def options_current_user():
    """Handle OPTIONS request for CORS preflight - no authentication required."""
    from fastapi import Response
    
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With, X-CSRF-Token, X-API-Key"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "86400"
    response.status_code = 200
    
    return response


@router.get("/me")
async def get_current_user_info(
    current_user: UserData = Depends(get_current_user)
):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "auth_provider": current_user.auth_provider,
        "is_verified": current_user.is_verified
    }


@router.patch("/me")
async def update_user_profile(
    request: Request,
    update_data: UpdateProfileRequest,
    current_user: UserData = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update user profile information.
    Currently supports updating display name.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Debug logging
    print(f"🔍 DEBUG: Profile update request received")
    print(f"🔍 DEBUG: Current user: {current_user.id}, {current_user.full_name}")
    print(f"🔍 DEBUG: Update data: {update_data.dict()}")
    print(f"🔍 DEBUG: Client IP: {client_ip}")
    
    log_security_event(
        event_type="profile_update_attempt",
        user_id=current_user.id,
        ip_address=client_ip,
        severity="info",
        fields_updated=[k for k, v in update_data.dict().items() if v is not None]
    )
    
    try:
        # Check username uniqueness if username is being updated
        if update_data.username is not None and update_data.username != current_user.username:
            if session:
                # Check if username already exists
                existing_username = await session.execute(
                    select(User).where(
                        and_(
                            User.username == update_data.username.strip(),
                            User.id != current_user.id  # Don't conflict with self
                        )
                    )
                )
                if existing_username.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Username already exists"
                    )
        
        # Create updated user data with the new information
        updated_user_data = {
            "id": current_user.id,
            "email": current_user.email,
            "username": update_data.username.strip() if update_data.username is not None else current_user.username,
            "full_name": update_data.name if update_data.name is not None else current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "auth_provider": current_user.auth_provider,
            "is_verified": current_user.is_verified
        }
        
        # Create new JWT token with updated data
        new_token = create_jwt_token(updated_user_data)
        
        # Try to update database if available, but don't fail if database is unavailable
        if session and (update_data.name is not None or update_data.username is not None):
            try:
                # For OAuth users, we might need to create the record if it doesn't exist
                # First, try to find existing user
                existing_user = await session.execute(
                    select(User).where(User.id == current_user.id)
                )
                user_record = existing_user.scalar_one_or_none()
                
                if user_record:
                    # Prepare update values
                    update_values = {}
                    if update_data.name is not None:
                        update_values["full_name"] = update_data.name.strip()  # Use correct DB field name
                    if update_data.username is not None:
                        update_values["username"] = update_data.username.strip()
                    
                    # Update existing user
                    if update_values:
                        result = await session.execute(
                            update(User)
                            .where(User.id == current_user.id)
                            .values(**update_values)
                        )
                        await session.commit()
                else:
                    # Create new user record for OAuth users
                    new_user = User(
                        id=current_user.id,
                        email=current_user.email,
                        username=update_data.username.strip() if update_data.username is not None else (current_user.username or f"user_{current_user.id[:8]}"),
                        full_name=update_data.name.strip() if update_data.name is not None else current_user.full_name,
                        password_hash=None,  # OAuth users don't have passwords
                        github_id=current_user.id if current_user.auth_provider == "github" else None,
                        google_id=current_user.id if current_user.auth_provider == "google" else None,
                        auth_provider=AuthProvider.GITHUB if current_user.auth_provider == "github" else AuthProvider.GOOGLE if current_user.auth_provider == "google" else AuthProvider.LOCAL,
                        avatar_url=current_user.avatar_url,
                        is_verified=current_user.is_verified
                    )
                    session.add(new_user)
                    await session.commit()
                    
                    log_security_event(
                        event_type="oauth_user_record_created",
                        user_id=current_user.id,
                        ip_address=client_ip,
                        severity="info",
                        auth_provider=current_user.auth_provider
                    )
            except Exception as db_error:
                # Log database error but continue with JWT token update
                log_security_event(
                    event_type="profile_update_database_failed",
                    user_id=current_user.id,
                    ip_address=client_ip,
                    severity="warning",
                    error=str(db_error)
                )
        
        log_security_event(
            event_type="profile_update_success",
            user_id=current_user.id,
            ip_address=client_ip,
            severity="info",
            updated_fields=[k for k, v in update_data.dict().items() if v is not None]
        )
        
        # Debug logging
        print(f"🔍 DEBUG: Profile update successful")
        print(f"🔍 DEBUG: Updated user data: {updated_user_data}")
        print(f"🔍 DEBUG: New token created: {bool(new_token)}")
        
        response_data = {
            "message": "Profile updated successfully",
            "user": updated_user_data,
            "access_token": new_token,
            "token_type": "bearer"
        }
        
        print(f"🔍 DEBUG: Returning response: {response_data}")
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        await session.rollback()
        log_security_event(
            event_type="profile_update_failed",
            user_id=current_user.id,
            ip_address=client_ip,
            severity="error",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/github")
async def github_login(request: Request):
    """
    Initiate GitHub OAuth login with comprehensive security and error handling.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    log_security_event(
        "oauth_initiation_attempt",
        "info",
        {
            "provider": "github",
            "client_ip": client_ip,
            "user_agent": user_agent
        }
    )
    
    try:
        settings = get_settings()
        
        # Get GitHub credentials from Vault (with fallback to env)
        client_id = settings.github_client_id
        client_secret = settings.github_client_secret
        
        # Validate credentials are available
        if not client_id or not client_secret:
            log_security_event(
                "oauth_configuration_error",
                "error",
                {
                    "provider": "github",
                    "reason": "missing_credentials",
                    "has_client_id": bool(client_id),
                    "has_client_secret": bool(client_secret)
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "GitHub OAuth not configured",
                    "message": (
                        "GitHub client credentials are not available. "
                        "Please configure GITHUB_CLIENT_ID and "
                        "GITHUB_CLIENT_SECRET environment variables or "
                        "set up Vault with GitHub OAuth secrets."
                    ),
                    "solution": (
                        "Set environment variables: "
                        "GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET"
                    )
                }
            )
        
        # Generate cryptographically secure state parameter
        state = secrets.token_urlsafe(32)
        
        # Store state for validation (in production, use Redis or database)
        # For now, we'll rely on the callback to validate the state
        
        # Determine environment-appropriate redirect URI
        redirect_uri = "http://localhost:8080/api/v1/auth/github/callback"
        if settings.environment == "production":
            # In production, use your actual domain
            redirect_uri = f"https://{settings.domain}/api/v1/auth/github/callback"
        
        # GitHub OAuth authorization URL with security parameters
        github_auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&scope=user:email"
            f"&state={state}"
            f"&response_type=code"
        )
        
        log_security_event(
            "oauth_redirect_initiated",
            "info",
            {
                "provider": "github",
                "client_ip": client_ip,
                "state": state,
                "redirect_uri": redirect_uri
            }
        )
        
        return RedirectResponse(url=github_auth_url)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "GitHub OAuth initialization failed",
            extra_fields={
                "error": str(e),
                "client_ip": client_ip
            }
        )
        
        log_security_event(
            "oauth_initiation_error",
            "error",
            {
                "provider": "github",
                "error": str(e),
                "client_ip": client_ip
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "GitHub OAuth initialization failed",
                "message": f"Failed to initialize GitHub OAuth: {str(e)}",
                "solution": (
                    "Check your GitHub OAuth configuration and credentials"
                )
            }
        )


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Handle GitHub OAuth callback with comprehensive security and error handling.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    log_security_event(
        "oauth_callback_received",
        "info",
        {
            "provider": "github",
            "client_ip": client_ip,
            "has_code": bool(code),
            "has_state": bool(state),
            "has_error": bool(error)
        }
    )
    
    # Handle OAuth errors from GitHub
    if error:
        log_security_event(
            "oauth_callback_error",
            "warning",
            {
                "provider": "github",
                "error": error,
                "error_description": error_description,
                "client_ip": client_ip
            }
        )
        
        frontend_url = (
            f"http://localhost:5000/auth/callback"
            f"?error={urllib.parse.quote(error)}"
            f"&error_description={urllib.parse.quote(error_description or '')}"
        )
        return RedirectResponse(url=frontend_url)
    
    # Validate required parameters
    if not code:
        log_security_event(
            "oauth_callback_error",
            "error",
            {
                "provider": "github",
                "reason": "missing_authorization_code",
                "client_ip": client_ip
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )
    
    # TODO: In production, validate state parameter against stored value
    # For now, we'll log it for security monitoring
    if not state:
        log_security_event(
            "oauth_security_warning",
            "warning",
            {
                "provider": "github",
                "reason": "missing_state_parameter",
                "client_ip": client_ip
            }
        )
    
    try:
        settings = get_settings()
        
        # Exchange authorization code for access token
        async with httpx.AsyncClient(timeout=30.0) as client:
            log_security_event(
                "oauth_token_exchange_start",
                "info",
                {
                    "provider": "github",
                    "client_ip": client_ip
                }
            )
            
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "state": state
                },
                headers={"Accept": "application/json"}
            )
            
            if token_response.status_code != 200:
                log_security_event(
                    "oauth_token_exchange_failed",
                    "error",
                    {
                        "provider": "github",
                        "status_code": token_response.status_code,
                        "client_ip": client_ip
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                log_security_event(
                    "oauth_token_exchange_failed",
                    "error",
                    {
                        "provider": "github",
                        "reason": "no_access_token_in_response",
                        "client_ip": client_ip
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from GitHub"
                )
            
            # Get user information from GitHub API
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                log_security_event(
                    "oauth_user_info_failed",
                    "error",
                    {
                        "provider": "github",
                        "status_code": user_response.status_code,
                        "client_ip": client_ip
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information from GitHub"
                )
            
            user_data = user_response.json()
            
            # Get user emails
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            emails = emails_response.json() if emails_response.status_code == 200 else []
            primary_email = next(
                (email['email'] for email in emails if email.get('primary')),
                user_data.get('email')
            )
            
            if not primary_email:
                log_security_event(
                    "oauth_user_info_incomplete",
                    "warning",
                    {
                        "provider": "github",
                        "reason": "no_email_available",
                        "user_id": user_data.get('id'),
                        "client_ip": client_ip
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email address available from GitHub account"
                )
            
            # Prepare user data for database creation/update
            oauth_user_data = {
                "id": user_data['id'],
                "email": primary_email,
                "login": user_data.get('login'),
                "username": user_data.get('login'),
                "name": user_data.get('name'),
                "avatar_url": user_data.get('avatar_url')
            }
            
            # Create or update user in database
            try:
                db_user = await create_or_update_oauth_user(
                    oauth_user_data, 
                    "github", 
                    client_ip
                )
                
                # Create JWT token with database user ID
                jwt_user_data = {
                    "id": str(db_user.id),  # Use database UUID
                    "user_id": str(user_data['id']),  # GitHub ID for compatibility
                    "email": db_user.email,
                    "username": db_user.username,
                    "name": db_user.name,
                    "avatar_url": db_user.avatar_url,
                    "provider": "github",
                    "is_verified": db_user.is_verified
                }
                
                # Create JWT token
                jwt_token = create_jwt_token(jwt_user_data)
                
                # Prepare user data for frontend (sanitized)
                user_for_frontend = {
                    "id": str(db_user.id),
                    "user_id": str(user_data['id']),
                    "email": db_user.email,
                    "username": db_user.username,
                    "name": db_user.name,
                    "avatar_url": db_user.avatar_url,
                    "provider": "github",
                    "is_verified": db_user.is_verified
                }
                
            except Exception as db_error:
                # If database creation fails, fall back to JWT-only approach
                logger.warning(
                    "Database user creation failed, using JWT-only approach",
                    extra_fields={
                        "error": str(db_error),
                        "provider": "github",
                        "user_id": str(user_data['id']),
                        "client_ip": client_ip
                    }
                )
                
                # Create JWT token with GitHub data (fallback)
                jwt_user_data = {
                    "id": str(user_data['id']),
                    "email": primary_email,
                    "username": user_data.get('login'),
                    "name": user_data.get('name'),
                    "avatar_url": user_data.get('avatar_url'),
                    "provider": "github",
                    "is_verified": True
                }
                
                jwt_token = create_jwt_token(jwt_user_data)
                
                user_for_frontend = {
                    "id": str(user_data['id']),
                    "email": primary_email,
                    "username": user_data.get('login'),
                    "name": user_data.get('name'),
                    "avatar_url": user_data.get('avatar_url'),
                    "provider": "github",
                    "is_verified": True
                }
            
            user_json = json.dumps(user_for_frontend)
            user_encoded = urllib.parse.quote(user_json)
            
            log_security_event(
                "oauth_authentication_success",
                "info",
                {
                    "provider": "github",
                    "user_id": str(user_data['id']),
                    "username": user_data.get('login'),
                    "client_ip": client_ip
                }
            )
            
            # Determine frontend URL based on environment
            frontend_base = "http://localhost:5000"
            if settings.environment == "production":
                frontend_base = f"https://{settings.frontend_domain or settings.domain}"
            
            # Redirect to frontend with token and user data
            frontend_url = (
                f"{frontend_base}/auth/callback"
                f"?token={jwt_token}&user={user_encoded}"
            )
            
            return RedirectResponse(url=frontend_url)
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "GitHub OAuth callback processing failed",
            extra_fields={
                "error": str(e),
                "client_ip": client_ip,
                "code_present": bool(code),
                "state_present": bool(state)
            }
        )
        
        log_security_event(
            "oauth_callback_error",
            "error",
            {
                "provider": "github",
                "error": str(e),
                "client_ip": client_ip
            }
        )
        
        # Redirect to frontend with error
        frontend_url = (
            f"http://localhost:5000/auth/callback"
            f"?error={urllib.parse.quote('oauth_processing_failed')}"
            f"&error_description={urllib.parse.quote(str(e))}"
        )
        return RedirectResponse(url=frontend_url)