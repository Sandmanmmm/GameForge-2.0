"""
Security middleware integration for GameForge API
Combines authentication, rate limiting, and security headers
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
import logging

from auth_middleware import get_current_user, require_roles, UserRole
from rate_limit_middleware import rate_limit_middleware

def setup_security_middleware(app: FastAPI):
    """Setup all security middleware"""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
    )

    # Rate limiting middleware
    app.middleware("http")(rate_limit_middleware)

    # Security headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response

    return app

# Example protected endpoints
def create_protected_routes(app: FastAPI):
    """Create example protected routes"""

    @app.post("/api/v1/auth/login")
    async def login(credentials: dict):
        """User login endpoint"""
        # Implementation here
        pass

    @app.post("/api/v1/auth/refresh")
    async def refresh_token(refresh_token: str):
        """Token refresh endpoint"""
        # Implementation here
        pass

    @app.post("/api/v1/auth/logout")
    async def logout(current_user: dict = Depends(get_current_user)):
        """User logout endpoint"""
        # Implementation here
        pass

    @app.get("/api/v1/assets/generate")
    async def generate_asset(
        prompt: str,
        current_user: dict = Depends(require_roles([UserRole.USER, UserRole.DEVELOPER]))
    ):
        """Protected asset generation endpoint"""
        # Implementation here
        pass

    @app.get("/api/v1/admin/stats")
    async def admin_stats(
        current_user: dict = Depends(require_roles([UserRole.ADMIN]))
    ):
        """Admin-only statistics endpoint"""
        # Implementation here
        pass

    @app.post("/api/v1/api-keys")
    async def create_api_key(
        name: str,
        scopes: list,
        current_user: dict = Depends(get_current_user)
    ):
        """Create new API key"""
        # Implementation here
        pass
