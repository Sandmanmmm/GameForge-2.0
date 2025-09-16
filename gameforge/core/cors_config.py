"""
Production-Ready CORS Configuration for GameForge Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List

def configure_production_cors(app: FastAPI):
    """
    Configure CORS for production with secure domain restrictions
    """
    
    # Production domains - NEVER use * in production
    production_origins = [
        "https://gameforge.app",
        "https://www.gameforge.app",
        "https://app.gameforge.com",
        "https://www.gameforge.com"
    ]
    
    # Staging domains
    staging_origins = [
        "https://staging.gameforge.app",
        "https://staging-app.gameforge.app",
        "https://gameforge-staging.vercel.app"
    ]
    
    # Development domains (only in dev environment)
    development_origins = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173"
    ]
    
    # Determine environment
    environment = os.getenv("NODE_ENV", "development").lower()
    
    # Build allowed origins based on environment
    allowed_origins: List[str] = []
    
    if environment == "production":
        allowed_origins = production_origins
    elif environment == "staging":
        allowed_origins = staging_origins + production_origins
    else:  # development
        allowed_origins = development_origins + staging_origins + production_origins
    
    # Add CORS middleware with secure settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,  # Allow cookies/auth headers
        allow_methods=[
            "GET",
            "POST", 
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS"
        ],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token",
            "X-Request-ID"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ],
        max_age=600  # Cache preflight requests for 10 minutes
    )
    
    print(f"🔒 CORS configured for {environment} environment")
    print(f"📍 Allowed origins: {allowed_origins}")
    
    return app

def get_cors_origins() -> List[str]:
    """
    Get the allowed CORS origins for current environment
    """
    environment = os.getenv("NODE_ENV", "development").lower()
    
    if environment == "production":
        return [
            "https://gameforge.app",
            "https://www.gameforge.app"
        ]
    elif environment == "staging":
        return [
            "https://staging.gameforge.app",
            "https://gameforge-staging.vercel.app"
        ]
    else:
        return [
            "http://localhost:3000",
            "http://localhost:5000",
            "http://localhost:5173"
        ]

# Example usage in FastAPI app
"""
from fastapi import FastAPI
from .cors_config import configure_production_cors

app = FastAPI()
configure_production_cors(app)
"""