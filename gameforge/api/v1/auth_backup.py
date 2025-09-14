"""
Authentication and authorization endpoints.
"""
import jwt
import secrets
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from gameforge.core.config import get_settings

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserData(BaseModel):
    """User data extracted from JWT token."""
    id: str
    user_id: str  # For backward compatibility
    email: str
    username: Optional[str] = None
    name: Optional[str] = None


def verify_jwt_token(token: str) -> UserData:
    """Verify and decode JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )
        
        # Extract user data from token payload
        user_id = (payload.get("id") or
                   payload.get("userId") or
                   payload.get("sub"))
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return UserData(
            id=user_id,
            user_id=user_id,  # For backward compatibility
            email=email or "",
            username=payload.get("username"),
            name=payload.get("name")
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserData:
    """Get current authenticated user from JWT token."""
    return verify_jwt_token(credentials.credentials)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """User authentication endpoint."""
    # TODO: Implement actual authentication logic
    # This is a placeholder for now
    if request.username == "admin" and request.password == "admin":
        return LoginResponse(
            access_token="fake-jwt-token",
            token_type="bearer"
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.post("/logout")
async def logout(current_user: UserData = Depends(get_current_user)):
    """User logout endpoint."""
    # TODO: Implement token invalidation
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
        "name": current_user.name
    }


# Authentication dependency function for reuse in other modules


@router.get("/github")
async def github_login():
    """Initiate GitHub OAuth login."""
    try:
        settings = get_settings()
        
        # Check if GitHub credentials are available
        client_id = settings.github_client_id
        client_secret = settings.github_client_secret
        
        if not client_id or not client_secret:
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
        
        # Generate state parameter for security
        state = secrets.token_urlsafe(32)
        
        # GitHub OAuth authorization URL
        github_auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri=http://localhost:8080/api/v1/auth/github/callback"
            f"&scope=user:email"
            f"&state={state}"
        )
        
        return RedirectResponse(url=github_auth_url)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle any other configuration errors gracefully
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "GitHub OAuth configuration error",
                "message": f"Failed to initialize GitHub OAuth: {str(e)}",
                "solution": (
                    "Check your GitHub OAuth configuration and credentials"
                )
            }
        )


@router.get("/github/callback")
async def github_callback(code: str, state: Optional[str] = None):
    """Handle GitHub OAuth callback."""
    settings = get_settings()
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"}
            )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from GitHub"
                )
            
            # Get user info from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_data = user_response.json()
            
            # Get user emails
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            emails = emails_response.json()
            primary_email = next(
                (email['email'] for email in emails if email['primary']),
                user_data.get('email')
            )
            
            # Create JWT token for the user
            jwt_payload = {
                "id": str(user_data['id']),
                "userId": str(user_data['id']),
                "email": primary_email,
                "username": user_data.get('login'),
                "name": user_data.get('name'),
                "avatar_url": user_data.get('avatar_url'),
                "provider": "github"
            }
            
            jwt_token = jwt.encode(
                jwt_payload,
                settings.jwt_secret_key,
                algorithm="HS256"
            )
            
            # Prepare user data for frontend
            import urllib.parse
            import json
            user_for_frontend = {
                "id": str(user_data['id']),
                "email": primary_email,
                "username": user_data.get('login'),
                "name": user_data.get('name'),
                "avatar_url": user_data.get('avatar_url')
            }
            user_json = json.dumps(user_for_frontend)
            user_encoded = urllib.parse.quote(user_json)
            
            # Redirect to frontend with token and user data
            frontend_url = (
                f"http://localhost:5000/auth/callback"
                f"?token={jwt_token}&user={user_encoded}"
            )
            return RedirectResponse(url=frontend_url)
            
    except Exception as e:
        # Redirect to frontend with error
        frontend_url = f"http://localhost:5000/auth/callback?error={str(e)}"
        return RedirectResponse(url=frontend_url) 
 