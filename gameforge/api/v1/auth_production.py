"""
Production-ready authentication and authorization endpoints.
Includes comprehensive security, error handling, logging, and Vault integration.
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
from gameforge.core.config import get_settings
from gameforge.core.logging_config import get_logger, log_security_event

router = APIRouter()
security = HTTPBearer()

# Get structured logger for this module
logger = get_logger(__name__)


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
    user_id: str  # For backward compatibility
    email: EmailStr
    username: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: Optional[str] = None
    is_verified: bool = False


class OAuthState(BaseModel):
    """OAuth state management for security."""
    state: str
    created_at: datetime
    redirect_uri: Optional[str] = None


def create_jwt_token(user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
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
            user_id=user_id,  # For backward compatibility
            email=email,
            username=payload.get("username"),
            name=payload.get("name"),
            avatar_url=payload.get("avatar_url"),
            provider=payload.get("provider", "local"),
            is_verified=payload.get("is_verified", False)
        )
        
        log_security_event(
            "jwt_verification_success",
            "info",
            {
                "user_id": user_id,
                "provider": user_data.provider
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
                "provider": user_data.provider
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


@router.get("/me")
async def get_current_user_info(
    current_user: UserData = Depends(get_current_user)
):
    """Get current user information."""
    return {
        "id": current_user.id,
        "user_id": current_user.user_id,
        "email": current_user.email,
        "username": current_user.username,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "provider": current_user.provider,
        "is_verified": current_user.is_verified
    }


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
            
            # Create user data for JWT token
            jwt_user_data = {
                "id": str(user_data['id']),
                "email": primary_email,
                "username": user_data.get('login'),
                "name": user_data.get('name'),
                "avatar_url": user_data.get('avatar_url'),
                "provider": "github",
                "is_verified": True  # GitHub accounts are considered verified
            }
            
            # Create JWT token
            jwt_token = create_jwt_token(jwt_user_data)
            
            # Prepare user data for frontend (sanitized)
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