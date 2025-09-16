"""
Security configuration for GameForge AI Platform.
Defines security policies, allowed paths, and validation rules.
"""

# ============================================================================
# Model Security Configuration
# ============================================================================

# Allowed directories for AI model loading (relative to app root)
ALLOWED_MODEL_DIRECTORIES = [
    "/app/models",
    "/data/models", 
    "/mnt/models",
    "/opt/models",
    "./models",
    "models",
    # Add your specific model directories here
]

# Allowed model file extensions
ALLOWED_MODEL_EXTENSIONS = {
    '.bin', '.safetensors', '.pt', '.pth', '.onnx', 
    '.pkl', '.joblib', '.h5', '.pb', '.tflite',
    '.msgpack', '.json'  # For tokenizers and configs
}

# Maximum model file size (in bytes) - 10GB
MAX_MODEL_FILE_SIZE = 10 * 1024 * 1024 * 1024


# ============================================================================
# Content Security Policies
# ============================================================================

# Rate limiting configuration
RATE_LIMITS = {
    "ai_generation": {
        "max_requests": 50,
        "window_seconds": 3600,  # 1 hour
        "burst_allowance": 5
    },
    "super_resolution": {
        "max_requests": 30,
        "window_seconds": 3600,  # 1 hour
        "burst_allowance": 3
    },
    "api_general": {
        "max_requests": 1000,
        "window_seconds": 3600,  # 1 hour
        "burst_allowance": 50
    }
}

# Content validation rules
CONTENT_VALIDATION = {
    "max_prompt_length": 2000,
    "max_filename_length": 255,
    "max_metadata_field_length": 500,
    "allowed_image_types": [
        "image/jpeg", "image/png", "image/webp", 
        "image/bmp", "image/tiff"
    ],
    "max_image_size_mb": 50
}

# Prohibited content patterns (case-insensitive)
PROHIBITED_CONTENT_PATTERNS = [
    # Explicit content
    'nsfw', 'explicit', 'nude', 'naked', 'porn', 'sexual',
    
    # Violence and harmful content
    'violent', 'gore', 'blood', 'death', 'kill', 'murder',
    'torture', 'weapon', 'gun', 'bomb', 'explosive',
    
    # Hate speech and discrimination
    'hate', 'racist', 'sexist', 'homophobic', 'transphobic',
    'nazi', 'fascist', 'supremacist',
    
    # Illegal activities
    'illegal', 'drug', 'narcotic', 'terrorism', 'extremist',
    'fraud', 'scam', 'phishing',
    
    # Self-harm
    'suicide', 'self-harm', 'cutting', 'anorexia', 'bulimia'
]

# Sensitive information patterns (regex)
SENSITIVE_INFO_PATTERNS = [
    r'\b(?:api[_-]?key|token|password|secret|credential)\b',
    r'\b(?:ssh[_-]?key|private[_-]?key|rsa[_-]?key)\b',
    r'\b(?:access[_-]?token|bearer|authorization)\b',
    r'\b(?:aws[_-]?secret|azure[_-]?key|gcp[_-]?key)\b',
    r'\b(?:database[_-]?url|connection[_-]?string)\b',
    r'\b(?:smtp[_-]?password|email[_-]?password)\b',
    
    # Credit card patterns
    r'\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b',
    
    # Social security numbers
    r'\b(?:\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
    
    # Phone numbers (basic pattern)
    r'\b(?:\+?1[-\s]?)?\(?[2-9]\d{2}\)?[-\s]?\d{3}[-\s]?\d{4}\b'
]


# ============================================================================
# Security Headers Configuration
# ============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY", 
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}

# CORS configuration
CORS_SETTINGS = {
    "allow_origins": [
        "https://gameforge.ai",
        "https://app.gameforge.ai",
        "https://api.gameforge.ai",
        # Frontend development servers
        "http://localhost:5173",
        "http://localhost:5000",  # Added for current Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5000",  # Added for current Vite dev server
        "http://127.0.0.1:3000"
        # Add your frontend domains here
    ],
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": [
        "Authorization", "Content-Type", "X-Requested-With",
        "X-CSRF-Token", "X-API-Key"
    ],
    "allow_credentials": True,
    "max_age": 86400  # 24 hours
}


# ============================================================================
# Authentication & Authorization
# ============================================================================

JWT_SETTINGS = {
    "algorithm": "HS256",
    "access_token_expire_minutes": 60,  # 1 hour
    "refresh_token_expire_days": 30,
    "issuer": "gameforge-ai",
    "audience": "gameforge-users"
}

# User roles and permissions
USER_ROLES = {
    "user": {
        "permissions": [
            "ai:generate", "ai:status", "assets:read", 
            "projects:read", "projects:write"
        ],
        "rate_limits": RATE_LIMITS["ai_generation"]
    },
    "premium": {
        "permissions": [
            "ai:generate", "ai:status", "ai:priority",
            "assets:read", "assets:write", 
            "projects:read", "projects:write"
        ],
        "rate_limits": {
            "max_requests": 200,  # Higher limits for premium users
            "window_seconds": 3600,
            "burst_allowance": 20
        }
    },
    "admin": {
        "permissions": ["*"],  # All permissions
        "rate_limits": {
            "max_requests": 10000,
            "window_seconds": 3600,
            "burst_allowance": 100
        }
    }
}


# ============================================================================
# Audit and Monitoring
# ============================================================================

# Security events to log
SECURITY_LOG_EVENTS = [
    "authentication_failed",
    "rate_limit_exceeded", 
    "prohibited_content_detected",
    "sensitive_info_detected",
    "path_traversal_attempt",
    "sql_injection_attempt",
    "script_injection_attempt",
    "unauthorized_access_attempt",
    "model_path_validation_failed",
    "file_upload_security_violation"
]

# Alerting thresholds
SECURITY_ALERT_THRESHOLDS = {
    "failed_auth_attempts": {
        "count": 10,
        "window_seconds": 300,  # 5 minutes
        "severity": "warning"
    },
    "rate_limit_violations": {
        "count": 5,
        "window_seconds": 600,  # 10 minutes
        "severity": "warning"
    },
    "injection_attempts": {
        "count": 1,
        "window_seconds": 60,
        "severity": "critical"
    }
}


# ============================================================================
# Environment-Specific Overrides
# ============================================================================

import os

# Development environment adjustments
if os.getenv("GAMEFORGE_ENV") == "development":
    CORS_SETTINGS["allow_origins"] = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # More lenient rate limits for development
    for config in RATE_LIMITS.values():
        config["max_requests"] *= 10  # 10x higher limits in dev

# Production environment (stricter settings)
elif os.getenv("GAMEFORGE_ENV") == "production":
    # Ensure HTTPS only in production
    SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    
    # Stricter CSP for production
    SECURITY_HEADERS["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )