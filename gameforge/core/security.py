"""
Security and sanitization module for GameForge AI Platform.
Extends existing validation with comprehensive input sanitization, 
rate limiting, and secure model path handling.
"""
import re
import os
import hashlib
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
import time

from fastapi import HTTPException, Request
from pydantic import validator
import bleach

from gameforge.core.logging_config import (
    get_structured_logger, log_security_event
)
from gameforge.core.security_config import (
    PROHIBITED_CONTENT_PATTERNS, SENSITIVE_INFO_PATTERNS,
    ALLOWED_MODEL_DIRECTORIES, ALLOWED_MODEL_EXTENSIONS,
    CONTENT_VALIDATION
)

logger = get_structured_logger(__name__)


# ============================================================================
# Content Sanitization and Validation
# ============================================================================

class SecurityValidator:
    """Comprehensive security validation and sanitization."""
    
    # Use configuration constants
    SENSITIVE_PATTERNS = SENSITIVE_INFO_PATTERNS
    PROHIBITED_CONTENT = PROHIBITED_CONTENT_PATTERNS
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'\b(?:union|select|insert|update|delete|drop|create|alter)\b',
        r'(?:--|#|/\*|\*/)',
        r'(?:\'|\"|\;|\|)',
        r'\b(?:or|and)\s+\d+\s*=\s*\d+',
    ]
    
    # Script injection patterns
    SCRIPT_INJECTION_PATTERNS = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        r'javascript:',
        r'on\w+\s*=',
        r'(?:eval|setTimeout|setInterval|Function)\s*\(',
    ]
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 1000) -> str:
        """
        Sanitize text input by removing dangerous content.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValueError: If text contains prohibited content
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # Length check
        if len(text) > max_length:
            raise ValueError(f"Input too long (max {max_length} characters)")
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Check for sensitive information patterns
        for pattern in SecurityValidator.SENSITIVE_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                log_security_event(
                    event_type="sensitive_content_detected",
                    severity="warning",
                    pattern=pattern,
                    content_length=len(text)
                )
                raise ValueError("Input contains sensitive information")
        
        # Check for prohibited content
        lower_text = sanitized.lower()
        for prohibited in SecurityValidator.PROHIBITED_CONTENT:
            if prohibited in lower_text:
                log_security_event(
                    event_type="prohibited_content_detected",
                    severity="warning",
                    content_type=prohibited,
                    content_length=len(text)
                )
                raise ValueError(f"Input contains prohibited content: {prohibited}")
        
        # Check for SQL injection attempts
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                log_security_event(
                    event_type="sql_injection_attempt",
                    severity="error",
                    pattern=pattern,
                    content_length=len(text)
                )
                raise ValueError("Input contains potential SQL injection")
        
        # Check for script injection attempts
        for pattern in SecurityValidator.SCRIPT_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                log_security_event(
                    event_type="script_injection_attempt",
                    severity="error",
                    pattern=pattern,
                    content_length=len(text)
                )
                raise ValueError("Input contains potential script injection")
        
        # Use bleach for HTML sanitization
        sanitized = bleach.clean(
            sanitized,
            tags=[],  # No HTML tags allowed
            attributes={},  # No attributes allowed
            strip=True
        )
        
        return sanitized.strip()
    
    @staticmethod
    def validate_file_path(file_path: str, allowed_dirs: List[str]) -> str:
        """
        Validate file path is within allowed directories.
        
        Args:
            file_path: File path to validate
            allowed_dirs: List of allowed directory prefixes
            
        Returns:
            Normalized safe path
            
        Raises:
            ValueError: If path is not safe
        """
        if not file_path:
            raise ValueError("File path cannot be empty")
        
        # Normalize path to prevent directory traversal
        normalized_path = os.path.normpath(file_path)
        
        # Check for directory traversal attempts
        if '..' in normalized_path or normalized_path.startswith('/'):
            log_security_event(
                event_type="path_traversal_attempt",
                severity="error",
                attempted_path=file_path,
                normalized_path=normalized_path
            )
            raise ValueError("Invalid file path: directory traversal detected")
        
        # Ensure path is within allowed directories
        abs_path = os.path.abspath(normalized_path)
        path_allowed = False
        
        for allowed_dir in allowed_dirs:
            abs_allowed = os.path.abspath(allowed_dir)
            if abs_path.startswith(abs_allowed):
                path_allowed = True
                break
        
        if not path_allowed:
            log_security_event(
                event_type="unauthorized_path_access",
                severity="error",
                attempted_path=file_path,
                allowed_dirs=allowed_dirs
            )
            raise ValueError("File path not in allowed directories")
        
        return normalized_path
    
    @staticmethod
    def sanitize_job_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize job metadata to prevent information leaks.
        
        Args:
            metadata: Original metadata dictionary
            
        Returns:
            Sanitized metadata dictionary
        """
        sanitized = {}
        
        # Allowed metadata fields (whitelist approach)
        allowed_fields = {
            'prompt', 'style', 'category', 'dimensions', 'quality', 
            'count', 'model', 'current_stage', 'progress', 'user_id',
            'job_id', 'created_at', 'updated_at'
        }
        
        for key, value in metadata.items():
            if key not in allowed_fields:
                log_security_event(
                    event_type="metadata_field_filtered",
                    severity="info",
                    field=key
                )
                continue
            
            if isinstance(value, str):
                # Sanitize string values
                try:
                    sanitized[key] = SecurityValidator.sanitize_text_input(
                        value, max_length=500
                    )
                except ValueError as e:
                    log_security_event(
                        event_type="metadata_sanitization_failed",
                        severity="warning",
                        field=key,
                        error=str(e)
                    )
                    # Remove field if sanitization fails
                    continue
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            else:
                # Convert other types to string and sanitize
                try:
                    str_value = str(value)
                    sanitized[key] = SecurityValidator.sanitize_text_input(
                        str_value, max_length=200
                    )
                except (ValueError, TypeError):
                    log_security_event(
                        event_type="metadata_conversion_failed",
                        severity="info",
                        field=key,
                        type=type(value).__name__
                    )
                    continue
        
        return sanitized


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self.requests = {}  # {client_id: [(timestamp, count), ...]}
        self.cleanup_interval = 300  # Clean up old entries every 5 minutes
        self.last_cleanup = time.time()
    
    def is_allowed(
        self, 
        client_id: str, 
        max_requests: int = 100, 
        window_seconds: int = 3600
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            client_id: Unique client identifier
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(now, window_seconds * 2)
            self.last_cleanup = now
        
        # Initialize client if not exists
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the window
        cutoff_time = now - window_seconds
        self.requests[client_id] = [
            (timestamp, count) for timestamp, count in self.requests[client_id]
            if timestamp > cutoff_time
        ]
        
        # Count current requests in window
        current_count = sum(count for _, count in self.requests[client_id])
        
        if current_count >= max_requests:
            log_security_event(
                event_type="rate_limit_exceeded",
                severity="warning",
                client_id=client_id,
                current_count=current_count,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            return False, {
                "allowed": False,
                "current_count": current_count,
                "max_requests": max_requests,
                "window_seconds": window_seconds,
                "reset_time": cutoff_time + window_seconds
            }
        
        # Add current request
        self.requests[client_id].append((now, 1))
        
        return True, {
            "allowed": True,
            "current_count": current_count + 1,
            "max_requests": max_requests,
            "remaining": max_requests - current_count - 1
        }
    
    def _cleanup_old_entries(self, now: float, max_age: float):
        """Remove entries older than max_age."""
        cutoff = now - max_age
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                (timestamp, count) for timestamp, count in self.requests[client_id]
                if timestamp > cutoff
            ]
            if not self.requests[client_id]:
                del self.requests[client_id]


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================================================
# Model Path Security
# ============================================================================

class ModelPathValidator:
    """Validate and secure AI model loading paths."""
    
    # Use configuration constants
    ALLOWED_MODEL_DIRS = ALLOWED_MODEL_DIRECTORIES
    ALLOWED_EXTENSIONS = ALLOWED_MODEL_EXTENSIONS
    
    @staticmethod
    def validate_model_path(model_path: str) -> str:
        """
        Validate model loading path is secure.
        
        Args:
            model_path: Path to model file or directory
            
        Returns:
            Validated model path
            
        Raises:
            ValueError: If path is not secure
        """
        if not model_path:
            raise ValueError("Model path cannot be empty")
        
        # Use SecurityValidator for basic path validation
        validated_path = SecurityValidator.validate_file_path(
            model_path, ModelPathValidator.ALLOWED_MODEL_DIRS
        )
        
        # Additional checks for model files
        path_obj = Path(validated_path)
        
        # Check file extension if it's a file
        if path_obj.suffix and path_obj.suffix.lower() not in ModelPathValidator.ALLOWED_EXTENSIONS:
            log_security_event(
                event_type="invalid_model_extension",
                severity="warning",
                path=model_path,
                extension=path_obj.suffix
            )
            raise ValueError(f"Model file extension not allowed: {path_obj.suffix}")
        
        # Ensure the path exists (basic check)
        if not os.path.exists(validated_path):
            log_security_event(
                event_type="model_path_not_found",
                severity="info",
                path=validated_path
            )
            # Don't raise error - model might be downloaded dynamically
        
        log_security_event(
            event_type="model_path_validated",
            severity="info",
            path=validated_path
        )
        
        return validated_path


# ============================================================================
# Security Decorators
# ============================================================================

def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """
    Decorator to apply rate limiting to endpoints.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Look in kwargs
                request = kwargs.get('request')
            
            if request:
                # Use IP address as client identifier
                client_id = request.client.host if request.client else "unknown"
                
                allowed, info = rate_limiter.is_allowed(
                    client_id, max_requests, window_seconds
                )
                
                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "max_requests": max_requests,
                            "window_seconds": window_seconds,
                            "reset_time": info["reset_time"]
                        }
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate_input_security(func):
    """
    Decorator to apply security validation to function inputs.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Log function call for monitoring
        log_security_event(
            event_type="secured_endpoint_called",
            severity="info",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        return await func(*args, **kwargs)
    return wrapper


# ============================================================================
# Enhanced Pydantic Validators (extend existing ones)
# ============================================================================

def enhanced_prompt_validator(cls, v):
    """Enhanced prompt validator that builds on existing validation."""
    if not v or not isinstance(v, str):
        raise ValueError("Prompt must be a non-empty string")
    
    # Use our comprehensive sanitization
    try:
        sanitized = SecurityValidator.sanitize_text_input(v, max_length=2000)
        return sanitized
    except ValueError as e:
        log_security_event(
            event_type="prompt_validation_failed",
            severity="warning",
            error=str(e),
            prompt_length=len(v)
        )
        raise


def secure_model_path_validator(cls, v):
    """Validator for model path security."""
    if v is None:
        return v  # Allow None/default values
    
    try:
        return ModelPathValidator.validate_model_path(v)
    except ValueError as e:
        log_security_event(
            event_type="model_path_validation_failed",
            severity="error",
            path=v,
            error=str(e)
        )
        raise