"""
Security middleware for GameForge AI Platform.
Implements global security headers, rate limiting, and exception handling.
"""
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from gameforge.core.security_config import (
    SECURITY_HEADERS, CORS_SETTINGS, RATE_LIMITS
)
from gameforge.core.security import rate_limiter
from gameforge.core.logging_config import (
    get_structured_logger, log_security_event
)

logger = get_structured_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        
        return response


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware for API protection."""
    
    def __init__(
        self, app, max_requests: int = 1000, window_seconds: int = 3600
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def dispatch(self, request: Request, call_next):
        """Apply global rate limiting."""
        # Skip rate limiting for health checks and static files
        excluded_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if request.url.path in excluded_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, info = rate_limiter.is_allowed(
            client_id, self.max_requests, self.window_seconds
        )
        
        if not allowed:
            log_security_event(
                event_type="global_rate_limit_exceeded",
                severity="warning",
                client_id=client_id,
                path=request.url.path,
                method=request.method,
                current_count=info["current_count"],
                max_requests=self.max_requests
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": info.get("reset_time", time.time() + 3600),
                    "limit": self.max_requests,
                    "window": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(
                        info.get("reset_time", time.time() + 3600)
                    ))
                }
            )
        
        # Add rate limit headers to successful responses
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            info.get("remaining", 0)
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time() + self.window_seconds)
        )
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from JWT token if available
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # Extract user ID from token (simplified)
                # In practice, you'd decode the JWT
                return f"user_{auth_header[-10:]}"  # Use last 10 chars as ID
            except Exception:
                pass
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log security-relevant events."""
    
    async def dispatch(self, request: Request, call_next):
        """Log security events and API calls."""
        start_time = time.time()
        
        # Log incoming request
        client_id = self._get_client_id(request)
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log API request
            log_security_event(
                event_type="api_request_completed",
                severity="info",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                client_id=client_id,
                user_agent=request.headers.get("User-Agent", "unknown")
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log failed request
            log_security_event(
                event_type="api_request_failed",
                severity="error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=duration,
                client_id=client_id
            )
            
            raise
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def setup_security_middleware(app: FastAPI, settings) -> None:
    """
    Configure all security middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        settings: Application settings
    """
    logger.info("🔒 Setting up security middleware...")
    
    # 1. CORS Middleware (first in chain)
    cors_origins = CORS_SETTINGS["allow_origins"]
    if settings.environment == "development":
        cors_origins.extend([
            "http://localhost:3000",
            "http://localhost:5000",  # Added for current Vite dev server
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000",  # Added for current Vite dev server
            "http://127.0.0.1:8080"
        ])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=CORS_SETTINGS["allow_credentials"],
        allow_methods=CORS_SETTINGS["allow_methods"],
        allow_headers=CORS_SETTINGS["allow_headers"],
        max_age=CORS_SETTINGS["max_age"]
    )
    
    # 2. Trusted Host Middleware
    if settings.environment == "production":
        trusted_hosts = [
            "gameforge.ai",
            "*.gameforge.ai",
            "api.gameforge.ai"
        ]
    else:
        trusted_hosts = ["*"]  # Allow all in development
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts
    )
    
    # 3. Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. Global Rate Limiting Middleware
    global_limits = RATE_LIMITS["api_general"]
    app.add_middleware(
        GlobalRateLimitMiddleware,
        max_requests=global_limits["max_requests"],
        window_seconds=global_limits["window_seconds"]
    )
    
    # 5. Security Logging Middleware (last, to capture everything)
    app.add_middleware(SecurityLoggingMiddleware)
    
    logger.info("✅ Security middleware setup complete")


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup global exception handlers for security errors.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(ValueError)
    async def validation_exception_handler(request: Request, exc: ValueError):
        """Handle validation errors (including security validation)."""
        log_security_event(
            event_type="validation_error",
            severity="warning",
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation Error",
                "message": str(exc),
                "type": "validation_error"
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with security logging."""
        if exc.status_code == 429:
            # Rate limit exceeded
            log_security_event(
                event_type="rate_limit_exception",
                severity="warning",
                status_code=exc.status_code,
                path=request.url.path,
                method=request.method
            )
        elif exc.status_code in [401, 403]:
            # Authentication/Authorization errors
            log_security_event(
                event_type="auth_exception",
                severity="warning",
                status_code=exc.status_code,
                path=request.url.path,
                method=request.method
            )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                "status_code": exc.status_code,
                "type": "http_error"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors with security logging."""
        log_security_event(
            event_type="unexpected_error",
            severity="error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "type": "server_error"
            }
        )
    
    logger.info("✅ Global exception handlers configured")