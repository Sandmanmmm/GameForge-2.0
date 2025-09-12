"""
Authentication middleware for GameForge API
Implements JWT token authentication with role-based access control
"""

import jwt
import hashlib
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List
import redis
import json

# Security configuration
SECRET_KEY = "your-jwt-secret-key-here"  # Use environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Redis for token blacklisting
redis_client = redis.Redis(host='localhost', port=6379, db=1)

class UserRole(str):
    ADMIN = "admin"
    DEVELOPER = "developer" 
    USER = "user"
    API_KEY = "api_key"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = []
    scopes: List[str] = []

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    roles: List[str] = ["user"]

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""
    try:
        # Check if token is blacklisted
        if redis_client.get(f"blacklist:{token}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        roles: List[str] = payload.get("roles", [])
        scopes: List[str] = payload.get("scopes", [])

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return TokenData(
            user_id=user_id,
            username=username, 
            roles=roles,
            scopes=scopes
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user"""
    token = credentials.credentials
    return verify_token(token)

def require_roles(required_roles: List[str]):
    """Decorator to require specific roles"""
    def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return current_user
    return role_checker

def blacklist_token(token: str):
    """Add token to blacklist"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp:
            # Calculate TTL for Redis
            exp_datetime = datetime.fromtimestamp(exp)
            ttl = int((exp_datetime - datetime.utcnow()).total_seconds())
            if ttl > 0:
                redis_client.setex(f"blacklist:{token}", ttl, "true")
    except jwt.JWTError:
        pass  # Invalid token, no need to blacklist

# API Key authentication
class APIKeyAuth:
    def __init__(self):
        self.api_keys = {}  # In production, store in database

    def create_api_key(self, user_id: str, name: str, scopes: List[str]) -> str:
        """Create a new API key"""
        api_key = f"gf_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        self.api_keys[key_hash] = {
            "user_id": user_id,
            "name": name,
            "scopes": scopes,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "active": True
        }

        return api_key

    def verify_api_key(self, api_key: str) -> Optional[dict]:
        """Verify API key and return user data"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_data = self.api_keys.get(key_hash)

        if key_data and key_data["active"]:
            # Update last used timestamp
            key_data["last_used"] = datetime.utcnow().isoformat()
            return key_data

        return None

api_key_auth = APIKeyAuth()

def get_api_key_user(api_key: str = None) -> Optional[TokenData]:
    """Authenticate via API key"""
    if not api_key or not api_key.startswith("gf_"):
        return None

    key_data = api_key_auth.verify_api_key(api_key)
    if key_data:
        return TokenData(
            user_id=key_data["user_id"],
            username=f"api_key_{key_data['name']}",
            roles=["api_key"],
            scopes=key_data["scopes"]
        )

    return None
