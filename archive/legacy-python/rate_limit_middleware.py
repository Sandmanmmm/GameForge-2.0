"""
Rate limiting middleware for GameForge API
Implements sliding window rate limiting with Redis backend
"""

import time
import json
import redis
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import asyncio
from datetime import datetime, timedelta

# Redis client for rate limiting
redis_client = redis.Redis(host='localhost', port=6379, db=2)

class RateLimitConfig:
    """Rate limit configuration for different user types"""

    LIMITS = {
        "anonymous": {
            "requests_per_minute": 10,
            "requests_per_hour": 100,
            "requests_per_day": 1000
        },
        "user": {
            "requests_per_minute": 30,
            "requests_per_hour": 500, 
            "requests_per_day": 5000
        },
        "developer": {
            "requests_per_minute": 100,
            "requests_per_hour": 2000,
            "requests_per_day": 20000
        },
        "admin": {
            "requests_per_minute": 1000,
            "requests_per_hour": 10000,
            "requests_per_day": 100000
        },
        "api_key": {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        }
    }

    # Special limits for resource-intensive endpoints
    ENDPOINT_LIMITS = {
        "/api/v1/assets/generate": {
            "requests_per_minute": 5,
            "requests_per_hour": 50,
            "requests_per_day": 200
        },
        "/api/v1/assets/batch-generate": {
            "requests_per_minute": 2,
            "requests_per_hour": 20,
            "requests_per_day": 100
        }
    }

class RateLimiter:
    def __init__(self):
        self.redis_client = redis_client

    def _get_user_type(self, user_data: Optional[dict]) -> str:
        """Determine user type for rate limiting"""
        if not user_data:
            return "anonymous"

        roles = user_data.get("roles", [])
        if "admin" in roles:
            return "admin"
        elif "developer" in roles:
            return "developer"
        elif "api_key" in roles:
            return "api_key"
        elif "user" in roles:
            return "user"
        else:
            return "anonymous"

    def _get_identifier(self, request: Request, user_data: Optional[dict]) -> str:
        """Get unique identifier for rate limiting"""
        if user_data and user_data.get("user_id"):
            return f"user:{user_data['user_id']}"
        else:
            # Use IP address for anonymous users
            client_ip = request.client.host
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            return f"ip:{client_ip}"

    def _check_limit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, dict]:
        """Check if request is within rate limit using sliding window"""
        now = time.time()
        window_start = now - window_seconds

        pipe = self.redis_client.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiration
        pipe.expire(key, window_seconds)

        results = pipe.execute()
        current_count = results[1]

        remaining = max(0, limit - current_count - 1)
        reset_time = int(now + window_seconds)

        return current_count < limit, {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "current": current_count + 1
        }

    def check_rate_limit(self, request: Request, user_data: Optional[dict] = None) -> dict:
        """Check all applicable rate limits"""
        user_type = self._get_user_type(user_data)
        identifier = self._get_identifier(request, user_data)
        endpoint = request.url.path

        # Get rate limit configuration
        limits = RateLimitConfig.LIMITS.get(user_type, RateLimitConfig.LIMITS["anonymous"])
        endpoint_limits = RateLimitConfig.ENDPOINT_LIMITS.get(endpoint, {})

        # Combine general and endpoint-specific limits
        all_limits = {**limits, **endpoint_limits}

        results = {}

        # Check each time window
        for period, limit in all_limits.items():
            if period == "requests_per_minute":
                window_seconds = 60
            elif period == "requests_per_hour":
                window_seconds = 3600
            elif period == "requests_per_day":
                window_seconds = 86400
            else:
                continue

            key = f"rate_limit:{identifier}:{endpoint}:{period}"
            allowed, info = self._check_limit(key, limit, window_seconds)

            results[period] = {
                "allowed": allowed,
                **info
            }

            # If any limit is exceeded, return failure
            if not allowed:
                return {
                    "allowed": False,
                    "limit_type": period,
                    "user_type": user_type,
                    **info
                }

        return {
            "allowed": True,
            "user_type": user_type,
            "limits": results
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/api/v1/health"]:
        response = await call_next(request)
        return response

    # Get user data from request state (set by auth middleware)
    user_data = getattr(request.state, "user", None)

    # Check rate limits
    rate_limit_result = rate_limiter.check_rate_limit(request, user_data)

    if not rate_limit_result["allowed"]:
        # Rate limit exceeded
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests for {rate_limit_result['user_type']} user",
                "limit_type": rate_limit_result["limit_type"],
                "limit": rate_limit_result["limit"],
                "remaining": rate_limit_result["remaining"],
                "reset": rate_limit_result["reset"]
            },
            headers={
                "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                "X-RateLimit-Reset": str(rate_limit_result["reset"]),
                "Retry-After": str(rate_limit_result["reset"] - int(time.time()))
            }
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers to response
    if "limits" in rate_limit_result:
        # Use the most restrictive limit for headers
        most_restrictive = min(
            rate_limit_result["limits"].values(),
            key=lambda x: x["remaining"]
        )

        response.headers["X-RateLimit-Limit"] = str(most_restrictive["limit"])
        response.headers["X-RateLimit-Remaining"] = str(most_restrictive["remaining"])
        response.headers["X-RateLimit-Reset"] = str(most_restrictive["reset"])

    return response

class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded"""
    def __init__(self, limit_info: dict):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit_info['limit']}, Reset: {limit_info['reset']}"
        )
